import json
import os
import pathlib
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from behavior import (OUTPUT_LIMIT, STOP_DEADLINE_SECONDS, drain_until_complete,
                      evaluate)

class EvidenceTests(unittest.TestCase):
 def test_memory_requires_oom_evidence(self):
  self.assertFalse(evaluate('memory',137,'',{'OOMKilled':False}))
  self.assertTrue(evaluate('memory',137,'',{'OOMKilled':True}))
 def test_missing_or_failed_disk_evidence_cannot_pass(self):
  self.assertFalse(evaluate('disk',1,'',{}))
  self.assertFalse(evaluate('disk',0,'',{}))
 def test_worker_claim_not_a_verdict(self):
  self.assertFalse(evaluate('unsupported',0,'{"passed":true}',{}))

 def test_output_flood_is_drained_during_bounded_stop_and_reaps_tree(self):
  self.assertEqual(STOP_DEADLINE_SECONDS,10)
  with tempfile.TemporaryDirectory(prefix='drydock-output-drain-') as temp:
   root=pathlib.Path(temp);marker=root/'output-complete';stop_started=root/'stop-started';pids=root/'pids.json'
   stop_script=root/'fake_stop.py'
   stop_script.write_text(
    'import pathlib,sys,time\n'
    'marker=pathlib.Path(sys.argv[1]);started=pathlib.Path(sys.argv[2]);started.write_text("yes");deadline=time.monotonic()+3\n'
    'while not marker.exists() and time.monotonic()<deadline:time.sleep(.01)\n'
    'raise SystemExit(0 if marker.exists() else 2)\n')
   worker=(
    'import os,pathlib,sys,time\n'
    'marker=pathlib.Path(sys.argv[1]);started=pathlib.Path(sys.argv[2]);chunk=b"x"*65536\n'
    'for index in range(32):\n'
    ' os.write(1,chunk);os.write(2,chunk)\n'
    ' if index==15:\n'
    '  deadline=time.monotonic()+2\n'
    '  while not started.exists() and time.monotonic()<deadline:time.sleep(.005)\n'
    'marker.write_text("complete")\n')
   child=(
    'import json,pathlib,subprocess,sys\n'
    'marker=pathlib.Path(sys.argv[1]);started=pathlib.Path(sys.argv[2]);pids=pathlib.Path(sys.argv[3])\n'
    'cmd=[sys.executable,"-c",'+repr(worker)+',str(marker),str(started)]\n'
    'writer=subprocess.Popen(cmd,stdout=1,stderr=2)\n'
    'pids.write_text(json.dumps([writer.pid]))\n'
    'raise SystemExit(writer.wait())\n')
   proc=subprocess.Popen([sys.executable,'-c',child,str(marker),str(stop_started),str(pids)],
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         start_new_session=True)
   selector=selectors.DefaultSelector()
   selector.register(proc.stdout,selectors.EVENT_READ,'stdout')
   selector.register(proc.stderr,selectors.EVENT_READ,'stderr')
   captured={'stdout':bytearray(),'stderr':bytearray()};total={'seen':0};commands=[]
   started=time.monotonic()
   try:
    pid_deadline=started+1
    while not pids.exists() and time.monotonic()<pid_deadline:time.sleep(.005)
    self.assertTrue(pids.exists(),'output child did not start within the test deadline')
    child_pid=json.loads(pids.read_text())[0]
    os.kill(proc.pid,0);os.kill(child_pid,0)
    result=drain_until_complete(selector,'output',started,
                                [sys.executable,str(stop_script),str(marker),str(stop_started)],
                                'synthetic-output-container','synthetic-container-id',
                                captured,total,commands,case_deadline=8)
    self.assertEqual(proc.wait(timeout=2),0)
   finally:
    selector.close()
    for stream in (proc.stdout,proc.stderr):
     if stream:stream.close()
    if proc.poll() is None:
     try:os.killpg(proc.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     proc.wait(timeout=2)
   self.assertEqual(result['termination_reason'],'output_limit')
   self.assertEqual(result['stop_exit_code'],0)
   self.assertTrue(result['truncated'])
   self.assertTrue(stop_started.exists())
   self.assertLess(result['termination_seconds'],STOP_DEADLINE_SECONDS)
   self.assertEqual(commands[-1][-4:],['stop','--time','2','synthetic-output-container'])
   self.assertGreater(total['seen'],OUTPUT_LIMIT)
   self.assertEqual(sum(map(len,captured.values())),OUTPUT_LIMIT)
   self.assertTrue(marker.exists())
   for pid in (proc.pid,child_pid):
    with self.subTest(pid=pid):
     with self.assertRaises(ProcessLookupError):os.kill(pid,0)

 def test_stderr_only_flood_triggers_output_limit_and_caps_retention(self):
  """Deterministic coverage demonstrating stderr alone crosses threshold and is capped."""
  with tempfile.TemporaryDirectory(prefix='drydock-stderr-drain-') as temp:
   root=pathlib.Path(temp);marker=root/'output-complete';stop_started=root/'stop-started';pids=root/'pids.json'
   stop_script=root/'fake_stop.py'
   stop_script.write_text(
    'import pathlib,sys,time\n'
    'marker=pathlib.Path(sys.argv[1]);started=pathlib.Path(sys.argv[2]);started.write_text("yes");deadline=time.monotonic()+3\n'
    'while not marker.exists() and time.monotonic()<deadline:time.sleep(.01)\n'
    'raise SystemExit(0 if marker.exists() else 2)\n')
   worker=(
    'import os,pathlib,sys,time\n'
    'marker=pathlib.Path(sys.argv[1]);started=pathlib.Path(sys.argv[2]);chunk=b"e"*65536\n'
    'for index in range(32):\n'
    ' os.write(2,chunk)\n'
    ' if index==15:\n'
    '  deadline=time.monotonic()+2\n'
    '  while not started.exists() and time.monotonic()<deadline:time.sleep(.005)\n'
    'marker.write_text("complete")\n')
   child=(
    'import json,pathlib,subprocess,sys\n'
    'marker=pathlib.Path(sys.argv[1]);started=pathlib.Path(sys.argv[2]);pids=pathlib.Path(sys.argv[3])\n'
    'cmd=[sys.executable,"-c",'+repr(worker)+',str(marker),str(started)]\n'
    'writer=subprocess.Popen(cmd,stdout=1,stderr=2)\n'
    'pids.write_text(json.dumps([writer.pid]))\n'
    'raise SystemExit(writer.wait())\n')
   proc=subprocess.Popen([sys.executable,'-c',child,str(marker),str(stop_started),str(pids)],
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         start_new_session=True)
   selector=selectors.DefaultSelector()
   selector.register(proc.stdout,selectors.EVENT_READ,'stdout')
   selector.register(proc.stderr,selectors.EVENT_READ,'stderr')
   captured={'stdout':bytearray(),'stderr':bytearray()};total={'seen':0};commands=[]
   started=time.monotonic()
   try:
    pid_deadline=started+1
    while not pids.exists() and time.monotonic()<pid_deadline:time.sleep(.005)
    self.assertTrue(pids.exists(),'output child did not start within the test deadline')
    child_pid=json.loads(pids.read_text())[0]
    os.kill(proc.pid,0);os.kill(child_pid,0)
    result=drain_until_complete(selector,'output',started,
                                [sys.executable,str(stop_script),str(marker),str(stop_started)],
                                'synthetic-output-container','synthetic-container-id',
                                captured,total,commands,case_deadline=8)
    self.assertEqual(proc.wait(timeout=2),0)
   finally:
    selector.close()
    for stream in (proc.stdout,proc.stderr):
     if stream:stream.close()
    if proc.poll() is None:
     try:os.killpg(proc.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     proc.wait(timeout=2)
   self.assertEqual(result['termination_reason'],'output_limit')
   self.assertEqual(result['stop_exit_code'],0)
   self.assertTrue(result['truncated'])
   self.assertTrue(stop_started.exists())
   self.assertLess(result['termination_seconds'],STOP_DEADLINE_SECONDS)
   self.assertEqual(len(captured['stdout']),0)
   self.assertEqual(len(captured['stderr']),OUTPUT_LIMIT)
   self.assertGreater(total['seen'],OUTPUT_LIMIT)
   self.assertTrue(marker.exists())
   for pid in (proc.pid,child_pid):
    with self.subTest(pid=pid):
     with self.assertRaises(ProcessLookupError):os.kill(pid,0)

 def test_stop_nonzero_failure_raises_runtime_error_and_reaps(self):
  """Exercise drain_until_complete failure path when stop exits non-zero."""
  with tempfile.TemporaryDirectory(prefix='drydock-stop-fail-') as temp:
   root=pathlib.Path(temp);pids=root/'pids.json';stop_script=root/'fail_stop.py'
   stop_script.write_text('import sys; raise SystemExit(42)\n')
   worker=(
    'import os,time\n'
    'chunk=b"x"*65536\n'
    'for _ in range(32):\n'
    ' os.write(1,chunk);time.sleep(0.01)\n')
   child=(
    'import json,pathlib,subprocess,sys\n'
    'pids=pathlib.Path(sys.argv[1])\n'
    'cmd=[sys.executable,"-c",'+repr(worker)+']\n'
    'writer=subprocess.Popen(cmd,stdout=1,stderr=2)\n'
    'pids.write_text(json.dumps([writer.pid]))\n'
    'raise SystemExit(writer.wait())\n')
   proc=subprocess.Popen([sys.executable,'-c',child,str(pids)],
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         start_new_session=True)
   selector=selectors.DefaultSelector()
   selector.register(proc.stdout,selectors.EVENT_READ,'stdout')
   selector.register(proc.stderr,selectors.EVENT_READ,'stderr')
   captured={'stdout':bytearray(),'stderr':bytearray()};total={'seen':0};commands=[]
   started=time.monotonic()
   try:
    pid_deadline=started+1
    while not pids.exists() and time.monotonic()<pid_deadline:time.sleep(.005)
    self.assertTrue(pids.exists(),'child did not start within the test deadline')
    child_pid=json.loads(pids.read_text())[0]
    os.kill(proc.pid,0);os.kill(child_pid,0)
    with self.assertRaises(RuntimeError) as ctx:
     drain_until_complete(selector,'output',started,
                          [sys.executable,str(stop_script)],
                          'synthetic-output-container','synthetic-container-id',
                          captured,total,commands,case_deadline=8)
    self.assertIn('Docker stop exited 42',str(ctx.exception))
   finally:
    selector.close()
    for stream in (proc.stdout,proc.stderr):
     if stream:stream.close()
    if proc.poll() is None:
     try:os.killpg(proc.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     proc.wait(timeout=2)
   for pid in (proc.pid,child_pid):
    with self.subTest(pid=pid):
     with self.assertRaises(ProcessLookupError):os.kill(pid,0)

 def test_stop_timeout_kills_stop_proc_and_raises_timeout_expired(self):
  """Exercise drain_until_complete when stop process exceeds stop_deadline."""
  with tempfile.TemporaryDirectory(prefix='drydock-stop-timeout-') as temp:
   root=pathlib.Path(temp);pids=root/'pids.json';stop_pids=root/'stop_pids.json';stop_script=root/'hang_stop.py'
   stop_script.write_text(
    'import json,os,pathlib,sys,time\n'
    'pathlib.Path(sys.argv[1]).write_text(json.dumps([os.getpid()]))\n'
    'while True:time.sleep(0.1)\n')
   worker=(
    'import os,time\n'
    'chunk=b"x"*65536\n'
    'for _ in range(32):\n'
    ' os.write(1,chunk);time.sleep(0.01)\n')
   child=(
    'import json,pathlib,subprocess,sys\n'
    'pids=pathlib.Path(sys.argv[1])\n'
    'cmd=[sys.executable,"-c",'+repr(worker)+']\n'
    'writer=subprocess.Popen(cmd,stdout=1,stderr=2)\n'
    'pids.write_text(json.dumps([writer.pid]))\n'
    'raise SystemExit(writer.wait())\n')
   proc=subprocess.Popen([sys.executable,'-c',child,str(pids)],
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         start_new_session=True)
   selector=selectors.DefaultSelector()
   selector.register(proc.stdout,selectors.EVENT_READ,'stdout')
   selector.register(proc.stderr,selectors.EVENT_READ,'stderr')
   captured={'stdout':bytearray(),'stderr':bytearray()};total={'seen':0};commands=[]
   started=time.monotonic()
   try:
    pid_deadline=started+1
    while not pids.exists() and time.monotonic()<pid_deadline:time.sleep(.005)
    self.assertTrue(pids.exists(),'child did not start within the test deadline')
    child_pid=json.loads(pids.read_text())[0]
    os.kill(proc.pid,0);os.kill(child_pid,0)
    with self.assertRaises(subprocess.TimeoutExpired):
     drain_until_complete(selector,'output',started,
                          [sys.executable,str(stop_script),str(stop_pids)],
                          'synthetic-output-container','synthetic-container-id',
                          captured,total,commands,case_deadline=8,stop_deadline=0.3)
   finally:
    selector.close()
    for stream in (proc.stdout,proc.stderr):
     if stream:stream.close()
    if proc.poll() is None:
     try:os.killpg(proc.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     proc.wait(timeout=2)
   self.assertTrue(stop_pids.exists())
   stop_pid=json.loads(stop_pids.read_text())[0]
   with self.assertRaises(ProcessLookupError):os.kill(stop_pid,0)
   for pid in (proc.pid,child_pid):
    with self.subTest(pid=pid):
     with self.assertRaises(ProcessLookupError):os.kill(pid,0)

 def test_case_deadline_exceeded_raises_timeout_error_and_reaps(self):
  """Exercise drain_until_complete when case_deadline is exceeded."""
  with tempfile.TemporaryDirectory(prefix='drydock-case-timeout-') as temp:
   root=pathlib.Path(temp);pids=root/'pids.json';stop_script=root/'fake_stop.py'
   stop_script.write_text('import sys; raise SystemExit(0)\n')
   worker=(
    'import os,time\n'
    'while True:\n'
    ' os.write(1,b"hello");time.sleep(0.02)\n')
   child=(
    'import json,pathlib,subprocess,sys\n'
    'pids=pathlib.Path(sys.argv[1])\n'
    'cmd=[sys.executable,"-c",'+repr(worker)+']\n'
    'writer=subprocess.Popen(cmd,stdout=1,stderr=2)\n'
    'pids.write_text(json.dumps([writer.pid]))\n'
    'raise SystemExit(writer.wait())\n')
   proc=subprocess.Popen([sys.executable,'-c',child,str(pids)],
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         start_new_session=True)
   selector=selectors.DefaultSelector()
   selector.register(proc.stdout,selectors.EVENT_READ,'stdout')
   selector.register(proc.stderr,selectors.EVENT_READ,'stderr')
   captured={'stdout':bytearray(),'stderr':bytearray()};total={'seen':0};commands=[]
   started=time.monotonic()
   try:
    pid_deadline=started+1
    while not pids.exists() and time.monotonic()<pid_deadline:time.sleep(.005)
    self.assertTrue(pids.exists(),'child did not start within the test deadline')
    child_pid=json.loads(pids.read_text())[0]
    os.kill(proc.pid,0);os.kill(child_pid,0)
    with self.assertRaises(TimeoutError):
     drain_until_complete(selector,'output',started,
                          [sys.executable,str(stop_script)],
                          'synthetic-output-container','synthetic-container-id',
                          captured,total,commands,case_deadline=0.3)
   finally:
    selector.close()
    for stream in (proc.stdout,proc.stderr):
     if stream:stream.close()
    if proc.poll() is None:
     try:os.killpg(proc.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     proc.wait(timeout=2)
   for pid in (proc.pid,child_pid):
    with self.subTest(pid=pid):
     with self.assertRaises(ProcessLookupError):os.kill(pid,0)

if __name__=='__main__':unittest.main()
