#!/usr/bin/env python3
"""Finite, synthetic M0 probes. No task dispatch and no sudo."""
import argparse, hashlib, json, os, pathlib, selectors, socket, subprocess, threading, time

def counters(text):
 return {k:int(v) for k,v in (line.split() for line in text.splitlines())}

def evaluate(case, code, output, state):
 if case=='memory':
  return code==137 and state.get('OOMKilled') is True
 if case in ('tree','output'):
  return not state['Running'] # Caller separately requires bounded termination and cgroup cleanup.
 if code!=0:return False
 if case=='disk':
  rows=[json.loads(x) for x in output.splitlines()]
  return len(rows)==3 and all(x['enospc'] and x['bytes']==limit for x,limit in zip(rows,[64<<20,16<<20,8<<20]))
 obj=json.loads(output)
 if case=='cpu':
  before,after=counters(obj['before']),counters(obj['after'])
  return after['nr_throttled']>before['nr_throttled'] and after['usage_usec']-before['usage_usec'] <= obj['wall_ns']/1000*.70
 if case=='pids':
  return 'error' in obj and counters(obj['after'])['max']>counters(obj['before'])['max']
 if case=='filesystem':
  return not obj['synthetic_environment_present'] and obj['root_write_error']!='<nil>' and all(v!='ACCESSIBLE' for v in obj.values())
 if case=='network':
  return all(not x['connected'] if x['network']=='tcp' else x.get('reply_bytes',0)==0 and (not x['connected'] or x.get('read_error')!='<nil>') for x in obj)
 return False

def main():
 p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 out=pathlib.Path(a.output);out.mkdir(mode=0o700,exist_ok=False)
 prior=json.loads((pathlib.Path(a.inventory)/'commands.json').read_text())
 create=next(x['argv'] for x in prior if x['tag']=='create')
 base=create[:3];results=[];commands=[];owned=None;sentinel=out/'synthetic-controller-secret';sentinel.write_text('synthetic-only-m0-004\n');sentinel.chmod(0o600)
 original=hashlib.sha256(sentinel.read_bytes()).hexdigest()
 def call(args):
  commands.append(base+args)
  r=subprocess.run(base+args,capture_output=True,text=True,timeout=10)
  if r.returncode:raise RuntimeError('Docker control operation failed: '+r.stderr[:1000])
  if len(r.stdout)>1048576:raise RuntimeError('control output too large')
  return r.stdout
 try:
  for case in ['disk','cpu','memory','pids','filesystem','network','tree','output']:
   name='drydock-m0-004-'+case;args=create[3:].copy();args[args.index('--name')+1]=name
   extras=[case]
   sockets=[];threads=[];receipts=[];stop=threading.Event()
   if case=='filesystem':extras.append(str(sentinel.resolve()))
   if case=='network':
    tcp=socket.socket();tcp.bind(('0.0.0.0',0));tcp.listen();port=tcp.getsockname()[1]
    udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);udp.bind(('0.0.0.0',port));sockets=[tcp,udp]
    def server(sock,datagram):
     sock.settimeout(.2)
     while not stop.is_set():
      try:
       if datagram:
        data,address=sock.recvfrom(256);receipts.append(data.decode());sock.sendto(data,address)
       else:
        c,_=sock.accept()
        with c:
         c.settimeout(.3);data=c.recv(256);receipts.append(data.decode());c.sendall(data)
      except socket.timeout:pass
      except OSError:return
    for sock,datagram in [(tcp,False),(udp,True)]:
     t=threading.Thread(target=server,args=(sock,datagram),daemon=True);t.start();threads.append(t)
    # Establish healthy listeners before denying access from the container.
    for typ in [socket.SOCK_STREAM,socket.SOCK_DGRAM]:
     with socket.socket(socket.AF_INET,typ) as c:
      c.settimeout(1);c.connect(('127.0.0.1',port));c.sendall(b'positive-control');assert c.recv(64)==b'positive-control'
    receipts.clear();extras+=['192.168.50.99',str(port)]
   cid=call(args+extras).strip();owned=name
   inspect=json.loads(call(['inspect',name]))[0]
   (out/(case+'.inspect-before.json')).write_text(json.dumps(inspect,indent=2)+'\n')
   start=time.monotonic();proc=subprocess.Popen(base+['start','--attach',name],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'DRYDOCK_SYNTHETIC_SECRET':'synthetic-not-for-container'})
   commands.append(base+['start','--attach',name]);sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ,'stdout');sel.register(proc.stderr,selectors.EVENT_READ,'stderr')
   captured={'stdout':bytearray(),'stderr':bytearray()};total=0;reason=None;cancel_seconds=None;cgroup=None
   while sel.get_map():
    elapsed=time.monotonic()-start
    if cgroup is None:
     matches=list(pathlib.Path('/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service').glob('**/docker-'+cid+'.scope'))
     if matches:cgroup=matches[0]
    if reason is None and ((case=='tree' and elapsed>=2) or elapsed>=30 or total>1048576):
     reason='cancel' if case=='tree' else ('output_limit' if total>1048576 else 'deadline')
     t=time.monotonic();call(['stop','--time','2',name]);cancel_seconds=time.monotonic()-t
    for key,_ in sel.select(.05):
     data=os.read(key.fileobj.fileno(),65536)
     if not data:sel.unregister(key.fileobj);continue
     remaining=max(0,1048576-sum(len(x) for x in captured.values()))
     captured[key.data].extend(data[:remaining]);total+=len(data)
    if time.monotonic()-start>42:raise RuntimeError('termination deadline exceeded')
   code=proc.wait(timeout=1);sel.close()
   state=json.loads(call(['inspect',name]))[0]['State']
   for stream,data in captured.items():(out/(case+'.'+stream)).write_bytes(data)
   row={'case':case,'exit_code':code,'state':state,'duration_seconds':time.monotonic()-start,'termination_reason':reason,'termination_seconds':cancel_seconds,'output_bytes_seen':total,'truncated':total>1048576,'cgroup_path':str(cgroup) if cgroup else None}
   empty=cgroup is not None and (not cgroup.exists() or (cgroup/'cgroup.procs').read_text().strip()=='')
   row['cgroup_empty_or_removed']=empty
   passed=evaluate(case,code,captured['stdout'].decode(),state)
   if case=='tree':passed=passed and reason=='cancel' and cancel_seconds<=10 and empty
   if case=='output':passed=passed and reason=='output_limit' and cancel_seconds<=10 and empty
   if case=='network':
    row['host_receipts']=receipts.copy();passed=passed and not receipts
   if reason and case not in ('tree','output'):passed=False
   row['status']='PASS' if passed else 'FAIL';results.append(row)
   call(['rm',name]);owned=None
   stop.set()
   for sock in sockets:sock.close()
   for t in threads:t.join(timeout=1)
   if not passed:break
  status='FAIL' if any(x['status']=='FAIL' for x in results) else 'INCONCLUSIVE'
  reason='Behavioral probe failed; campaign stopped.' if status=='FAIL' else 'Executed probes passed; remaining qualification requirements must be evaluated.'
 except Exception as e:
  status='INCONCLUSIVE';reason=repr(e)
 finally:
  cleanup='no active container'
  if owned:
   try:call(['rm','--force',owned]);cleanup='active container removed'
   except Exception as e:cleanup=repr(e);status='INCONCLUSIVE'
  unchanged=hashlib.sha256(sentinel.read_bytes()).hexdigest()==original
  sentinel.unlink()
  result={'campaign':'m0-004','status':status,'qualified':False,'reason':reason,'probes':results,'cleanup':cleanup,'synthetic_sentinel_unchanged':unchanged}
  (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps(result,indent=2))
if __name__=='__main__':main()
