#!/usr/bin/env python3
"""M0 inventory gate only. Does not grant qualification or execute task code."""
import argparse, hashlib, json, os, pathlib, resource, subprocess, time
p=argparse.ArgumentParser();p.add_argument('--image',required=True);p.add_argument('--output',required=True);a=p.parse_args()
out=pathlib.Path(a.output);out.mkdir(mode=0o700,parents=True,exist_ok=False)
base=['docker','--host','unix:///run/user/1000/docker.sock']
name='drydock-m0-004-inventory'
commands=[]
def bounded():
 resource.setrlimit(resource.RLIMIT_FSIZE,(1048576,1048576))
def run(tag,args,timeout=15):
 commands.append({'tag':tag,'argv':base+args,'timeout_seconds':timeout,'output_limit_bytes_per_stream':1048576})
 start=time.monotonic()
 with (out/(tag+'.stdout')).open('wb') as so,(out/(tag+'.stderr')).open('wb') as se:
  try:
   result=subprocess.run(base+args,stdout=so,stderr=se,timeout=timeout,preexec_fn=bounded)
   code=result.returncode
  except subprocess.TimeoutExpired:code=None
 commands[-1].update(exit_code=code,duration_seconds=time.monotonic()-start)
 if code!=0:raise RuntimeError(tag+' failed or timed out')
 return (out/(tag+'.stdout')).read_text()
args=['create','--name',name,'--label','drydock.qualification=m0-004','--pull','never','--network','none','--read-only','--user','65532:65532','--cap-drop','ALL','--security-opt','no-new-privileges=true','--cgroupns','private','--ipc','private','--pids-limit','64','--cpus','0.5','--memory','256m','--memory-swap','256m','--shm-size','8m','--ulimit','nofile=256:256','--ulimit','core=0:0','--restart','no','--log-driver','none','--tmpfs','/workspace:rw,nosuid,nodev,size=64m,mode=0700,uid=65532,gid=65532','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777','--workdir','/workspace','--entrypoint','/probe',a.image]
result={'campaign':'m0-004','status':'INCONCLUSIVE','qualified':False,'image':a.image,'checks':[]}
created=False
try:
 run('create',args);created=True
 inspect=json.loads(run('inspect',['inspect',name]))[0]
 h=inspect['HostConfig'];c=inspect['Config']
 assert h['NetworkMode']=='none' and h['ReadonlyRootfs'] and not h['Privileged']
 assert c['User']=='65532:65532' and c['Image']==a.image
 assert h['Memory']==268435456 and h['MemorySwap']==268435456 and h['NanoCpus']==500000000 and h['PidsLimit']==64
 assert not h.get('Binds') and not h.get('Devices') and h['LogConfig']['Type']=='none'
 assert h['CapDrop']==['ALL'] and h['CgroupnsMode']=='private'
 assert 'no-new-privileges=true' in h['SecurityOpt']
 result['checks'].append({'name':'requested_profile','status':'PASS'})
 obs=json.loads(run('probe',['start','--attach',name],30))
 required={'/sys/fs/cgroup/memory.max':'268435456','/sys/fs/cgroup/memory.swap.max':'0','/sys/fs/cgroup/pids.max':'64'}
 for key,value in required.items():
  if not isinstance(obs.get(key),str) or obs[key].strip()!=value:
   result['checks'].append({'name':key,'status':'FAIL','expected':value,'observed':obs.get(key)})
   raise ValueError('effective cgroup limit differs from profile')
 cpu=obs.get('/sys/fs/cgroup/cpu.max','').split()
 if len(cpu)!=2 or cpu[0]=='max' or int(cpu[0])*2!=int(cpu[1]):raise ValueError('effective CPU quota differs')
 result['checks'].append({'name':'effective_cgroup_values','status':'PASS'})
 status=obs['/proc/self/status']
 for key,value in [('CapEff','0000000000000000'),('NoNewPrivs','1'),('Seccomp','2')]:
  parsed=dict(line.split(':',1) for line in status.splitlines() if ':' in line)
  if parsed[key].strip()!=value:raise ValueError('security status mismatch: '+key)
 if obs['uid']!=65532 or obs['gid']!=65532:raise ValueError('unexpected job identity')
 result['checks'].append({'name':'job_identity_and_security_status','status':'PASS'})
 for path,state in obs['runtime_file_write_access'].items():
  if state=='WRITABLE':raise ValueError('runtime file writable on unbounded host-backed mount: '+path)
 for path in ['/workspace/positive-control','/tmp/positive-control']:
  if obs[path]!='write succeeded':raise RuntimeError('positive filesystem control failed')
 result['checks'].append({'name':'runtime_files_not_writable_and_scoped_write_controls','status':'PASS'})
 result['status']='INCONCLUSIVE'
 result['reason']='Inventory gate completed; behavioral isolation probes still required.'
except ValueError as e:
 result['status']='FAIL';result['reason']=str(e)
except Exception as e:
 result['status']='INCONCLUSIVE';result['reason']=str(e)
finally:
 if created:
  try:
   run('cleanup',['rm','--force',name]); result['cleanup']='container removed'
  except Exception as e:result['cleanup']=str(e);result['status']='INCONCLUSIVE'
 (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
