#!/usr/bin/env python3
"""Finite, synthetic M0 probes. No task dispatch and no sudo."""
import argparse, hashlib, json, os, pathlib, selectors, signal, socket, subprocess, threading, time

OUTPUT_LIMIT = 1 << 20
STOP_DEADLINE_SECONDS = 10
CASE_DEADLINE_SECONDS = 42

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

def drain_until_complete(sel, case, started, base, name, cid, captured, total, commands,
                         output_limit=OUTPUT_LIMIT, case_deadline=CASE_DEADLINE_SECONDS,
                         stop_deadline=STOP_DEADLINE_SECONDS, diagnostics=None, on_cgroup=None):
 """Drain attached streams while a bounded Docker stop request is in flight."""
 reason=None;stop_proc=None;stop_started=None;cancel_seconds=None;stop_exit_code=None;stop_completed=False;cgroup=None
 command=base+['stop','--time','2',name]
 try:
  while sel.get_map() or (stop_proc is not None and stop_proc.poll() is None):
   now=time.monotonic()
   if now-started>case_deadline:
    raise TimeoutError('probe termination exceeded the case deadline')
   if cgroup is None:
    uid=os.getuid()
    root=pathlib.Path('/sys/fs/cgroup/user.slice')/f'user-{uid}.slice'/f'user@{uid}.service'
    matches=list(root.glob('**/docker-'+cid+'.scope'))
    if matches:
     cgroup=matches[0]
     if on_cgroup is not None:on_cgroup(cgroup)
   if stop_proc is not None and stop_proc.poll() is None and now-stop_started>=stop_deadline:
    try:os.killpg(stop_proc.pid, signal.SIGKILL)
    except ProcessLookupError:pass
    try:stop_proc.wait(timeout=2)
    except subprocess.TimeoutExpired:raise RuntimeError('Docker stop client survived SIGKILL')
    raise subprocess.TimeoutExpired(command, stop_deadline)
   if stop_proc is not None and not stop_completed and stop_proc.poll() is not None:
    cancel_seconds=time.monotonic()-stop_started
    stop_exit_code=stop_proc.returncode
    stop_completed=True
    if stop_exit_code:
     raise RuntimeError('Docker stop exited '+str(stop_exit_code))
   if reason is None and ((case=='tree' and now-started>=2) or now-started>=30 or
                          (case=='output' and total['seen']>output_limit)):
    reason='cancel' if case=='tree' else ('output_limit' if case=='output' and total['seen']>output_limit else 'deadline')
    commands.append(command)
    stop_started=time.monotonic()
    stop_proc=subprocess.Popen(command,stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,start_new_session=True)
   if sel.get_map():
    wait_for=.05
    if stop_proc is not None and stop_proc.poll() is None:
     wait_for=min(wait_for,max(0,stop_started+stop_deadline-time.monotonic()))
    wait_for=min(wait_for,max(0,started+case_deadline-time.monotonic()))
    ready=sel.select(wait_for)
    for key,_ in ready:
     data=os.read(key.fileobj.fileno(),65536)
     if not data:
      sel.unregister(key.fileobj)
      continue
     remaining=max(0,output_limit-sum(len(value) for value in captured.values()))
     captured[key.data].extend(data[:remaining])
     total['seen']+=len(data)
   elif stop_proc is not None and stop_proc.poll() is None:
    wait_for=min(.05,max(0,stop_started+stop_deadline-time.monotonic()))
    wait_for=min(wait_for,max(0,started+case_deadline-time.monotonic()))
    time.sleep(wait_for)
  if stop_proc is not None:
   stop_exit_code=stop_proc.wait(timeout=1)
   if not stop_completed:cancel_seconds=time.monotonic()-stop_started
   if stop_exit_code:
    raise RuntimeError('Docker stop exited '+str(stop_exit_code))
  retained=sum(len(value) for value in captured.values())
  return {'termination_reason':reason,'termination_seconds':cancel_seconds,
          'stop_exit_code':stop_exit_code,'cgroup_path':str(cgroup) if cgroup else None,
          'retained_bytes':retained,'truncated':total['seen']>retained}
 finally:
  if diagnostics is not None:
   retained=sum(len(value) for value in captured.values())
   diagnostics.update(termination_reason=reason,
                      termination_seconds=(time.monotonic()-stop_started if stop_started is not None else None),
                      stop_exit_code=(stop_proc.poll() if stop_proc is not None else None),
                      stop_deadline_seconds=stop_deadline, output_bytes_seen=total['seen'],
                      retained_bytes=retained, truncated=total['seen']>retained,
                      cgroup_path=str(cgroup) if cgroup else None)
  if stop_proc is not None:
   try:os.killpg(stop_proc.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   stop_proc.wait(timeout=2)

def close_attach_client(proc):
 """Bound cleanup independently of output progress; always close both pipes."""
 try:
  if proc.poll() is None:
   try:os.killpg(proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:proc.wait(timeout=2)
   except subprocess.TimeoutExpired:
    try:os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    proc.wait(timeout=2)
  else:proc.wait(timeout=1)
 finally:
  try:
   # A reaped leader does not establish that its process group is empty.
   try:os.killpg(proc.pid,signal.SIGKILL)
   except ProcessLookupError:pass
  finally:
   for stream in (proc.stdout,proc.stderr):
    if stream:stream.close()

def drain_attached(argv, case, started, base, name, cid, captured, total, commands,
                   *, env=None, **drain_options):
 """Own the attach client and descriptors from launch through any failure."""
 proc=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                       env=env,start_new_session=True)
 sel=None
 try:
  commands.append(argv)
  sel=selectors.DefaultSelector()
  sel.register(proc.stdout,selectors.EVENT_READ,'stdout')
  sel.register(proc.stderr,selectors.EVENT_READ,'stderr')
  outcome=drain_until_complete(sel,case,started,base,name,cid,captured,total,
                               commands,**drain_options)
 finally:
  try:
   if sel is not None:sel.close()
  finally:close_attach_client(proc)
 return outcome,proc.returncode

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
   start=time.monotonic()
   captured={'stdout':bytearray(),'stderr':bytearray()};total={'seen':0};diagnostics={}
   try:
    outcome,code=drain_attached(base+['start','--attach',name],case,start,base,name,cid,
                                captured,total,commands,diagnostics=diagnostics,
                                env={**os.environ,'DRYDOCK_SYNTHETIC_SECRET':'synthetic-not-for-container'})
   except Exception as exc:
    results.append({'case':case,'status':'INCONCLUSIVE','error':repr(exc),
                    'duration_seconds':time.monotonic()-start,**diagnostics})
    raise
   finally:
    for stream,data in captured.items():(out/(case+'.'+stream)).write_bytes(data)
   reason=outcome['termination_reason'];cancel_seconds=outcome['termination_seconds']
   cgroup=pathlib.Path(outcome['cgroup_path']) if outcome['cgroup_path'] else None
   state=json.loads(call(['inspect',name]))[0]['State']
   row={'case':case,'exit_code':code,'state':state,'duration_seconds':time.monotonic()-start,'termination_reason':reason,'termination_seconds':cancel_seconds,'stop_exit_code':outcome['stop_exit_code'],'stop_deadline_seconds':STOP_DEADLINE_SECONDS,'output_bytes_seen':total['seen'],'truncated':outcome['truncated'],'retained_bytes':outcome['retained_bytes'],'retained_limit':OUTPUT_LIMIT,'cgroup_path':str(cgroup) if cgroup else None}
   empty=cgroup is not None and (not cgroup.exists() or (cgroup/'cgroup.procs').read_text().strip()=='')
   row['cgroup_empty_or_removed']=empty
   passed=evaluate(case,code,captured['stdout'].decode(),state)
   if case=='tree':passed=passed and reason=='cancel' and cancel_seconds<=10 and empty
   if case=='output':passed=passed and reason=='output_limit' and cancel_seconds<=STOP_DEADLINE_SECONDS and empty
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
