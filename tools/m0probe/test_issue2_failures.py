"""Local fault injection only: no Docker calls or qualification campaigns."""
import contextlib
import ctypes
import inspect
import io
import json
import os
import pathlib
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import MagicMock, patch

import behavior
import regression_issue2_output as regression


def wait_until(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.005)
    raise AssertionError('synchronized condition did not become true')


def absent(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


class StopGroupTests(unittest.TestCase):
    def test_timeout_reaps_stop_leader_and_terminates_descendant(self):
        self.assertEqual(behavior.STOP_DEADLINE_SECONDS, 10)
        self.assertEqual(inspect.signature(behavior.drain_until_complete).parameters['stop_deadline'].default, 10)
        # Linux needs a subreaper so this test, rather than an arbitrary PID 1,
        # can reap the orphaned synthetic descendant after group SIGKILL.
        libc = None
        previous = ctypes.c_int()
        if sys.platform.startswith('linux'):
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.prctl(37, ctypes.byref(previous), 0, 0, 0) != 0:
                self.fail('cannot inspect child-subreaper setting')
            if libc.prctl(36, 1, 0, 0, 0) != 0:
                self.fail('cannot establish test child-subreaper')
        child_pid = None
        launched = []
        real_popen = subprocess.Popen
        try:
            with tempfile.TemporaryDirectory() as temp:
                marker = pathlib.Path(temp) / 'ready.json'
                script = (
                    'import json,os,pathlib,subprocess,sys,time\n'
                    'child=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"])\n'
                    'p=pathlib.Path(sys.argv[1]);q=p.with_suffix(".tmp")\n'
                    'q.write_text(json.dumps([os.getpid(),child.pid]));q.rename(p)\n'
                    'time.sleep(30)\n')

                def launch(argv, **kwargs):
                    nonlocal child_pid
                    proc = real_popen(argv, **kwargs)
                    launched.append(proc)
                    wait_until(marker.exists)
                    leader, child_pid = json.loads(marker.read_text())
                    self.assertEqual(leader, proc.pid)
                    os.kill(leader, 0)
                    os.kill(child_pid, 0)
                    self.assertEqual(os.getpgid(child_pid), leader)
                    return proc

                read_fd, write_fd = os.pipe()
                with os.fdopen(read_fd, 'rb', buffering=0) as stream, selectors.DefaultSelector() as sel:
                    try:
                        sel.register(stream, selectors.EVENT_READ, 'stdout')
                        with patch.object(behavior.subprocess, 'Popen', side_effect=launch):
                            with self.assertRaises(subprocess.TimeoutExpired) as raised:
                                behavior.drain_until_complete(
                                    sel, 'output', time.monotonic(),
                                    [sys.executable, '-c', script, str(marker)], 'synthetic', 'synthetic',
                                    {'stdout': bytearray(), 'stderr': bytearray()},
                                    {'seen': behavior.OUTPUT_LIMIT + 1}, [], stop_deadline=.5)
                        self.assertEqual(raised.exception.timeout, .5)
                        self.assertEqual(launched[0].returncode, -signal.SIGKILL)
                        self.assertTrue(absent(launched[0].pid))
                        if libc:
                            status = []
                            def reaped():
                                pid, code = os.waitpid(child_pid, os.WNOHANG)
                                if pid:
                                    status.append(code)
                                return bool(pid)
                            wait_until(reaped)
                            self.assertTrue(os.WIFSIGNALED(status[0]))
                            self.assertEqual(os.WTERMSIG(status[0]), signal.SIGKILL)
                        else:
                            wait_until(lambda: absent(child_pid))
                        self.assertTrue(absent(child_pid))
                    finally:
                        os.close(write_fd)
        finally:
            # Fallback cleanup is deliberately after all assertions.
            for proc in launched:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=2)
            if child_pid and libc:
                try:
                    os.waitpid(child_pid, 0)
                except ChildProcessError:
                    pass
            if libc:
                libc.prctl(36, previous.value, 0, 0, 0)


class AttachFailureTests(unittest.TestCase):
    def test_case_timeout_and_stop_failure_clean_actual_worker_tree(self):
        for mode in ('case', 'nonzero'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                marker = pathlib.Path(temp) / 'ready.json'
                child = ('import os,time\n'
                         'os.write(1,b"diagnostic marker\\n")\n' +
                         ('while True: os.write(1,b"x"*65536)\n' if mode == 'nonzero' else 'time.sleep(30)\n'))
                parent = (
                    'import json,os,pathlib,signal,subprocess,sys,time\n'
                    'child=subprocess.Popen([sys.executable,"-c",sys.argv[2]])\n'
                    'def stop(signum,frame):\n'
                    ' child.terminate();child.wait(timeout=2);raise SystemExit(0)\n'
                    'signal.signal(signal.SIGTERM,stop)\n'
                    'p=pathlib.Path(sys.argv[1]);q=p.with_suffix(".tmp")\n'
                    'q.write_text(json.dumps([os.getpid(),child.pid]));q.rename(p)\n'
                    'while True:time.sleep(.01)\n')
                real_popen = subprocess.Popen
                workers = []
                pids = []
                def launch(argv, **kwargs):
                    proc = real_popen(argv, **kwargs)
                    if '-c' in argv and parent in argv:
                        workers.append(proc)
                        wait_until(marker.exists)
                        pids.extend(json.loads(marker.read_text()))
                        for pid in pids:
                            os.kill(pid, 0)
                    return proc
                captured = {'stdout': bytearray(), 'stderr': bytearray()}
                total = {'seen': 0}
                diagnostic = {}
                try:
                    with patch.object(behavior.subprocess, 'Popen', side_effect=launch):
                        with self.assertRaises(TimeoutError if mode == 'case' else RuntimeError):
                            behavior.drain_attached(
                                [sys.executable, '-c', parent, str(marker), child], 'output',
                                time.monotonic(), [sys.executable, '-c', 'raise SystemExit(42)'],
                                'synthetic', 'synthetic', captured, total, [],
                                case_deadline=.5 if mode == 'case' else 5, diagnostics=diagnostic)
                    self.assertEqual(len(pids), 2)
                    for pid in pids:
                        self.assertTrue(absent(pid), f'{pid} survives production cleanup')
                    self.assertTrue(workers[0].stdout.closed)
                    self.assertTrue(workers[0].stderr.closed)
                    self.assertIn(b'diagnostic marker', captured['stdout'])
                    self.assertGreater(diagnostic['output_bytes_seen'], 0)
                    self.assertLessEqual(diagnostic['retained_bytes'], behavior.OUTPUT_LIMIT)
                    if mode == 'nonzero':
                        self.assertEqual(diagnostic['stop_exit_code'], 42)
                finally:
                    for proc in workers:
                        if proc.poll() is None:
                            os.killpg(proc.pid, signal.SIGKILL)
                            proc.wait(timeout=2)

    def test_selector_setup_failure_still_closes_and_reaps_client(self):
        proc = MagicMock()
        proc.poll.return_value = None
        sel = MagicMock()
        sel.register.side_effect = RuntimeError('registration failed')
        with patch.object(behavior.subprocess, 'Popen', return_value=proc), \
             patch.object(behavior.selectors, 'DefaultSelector', return_value=sel), \
             patch.object(behavior.os, 'killpg') as kill:
            with self.assertRaisesRegex(RuntimeError, 'registration failed'):
                behavior.drain_attached(['synthetic'], 'output', time.monotonic(), [],
                                        'name', 'cid', {}, {}, [])
        self.assertEqual([call.args for call in kill.call_args_list],
                         [(proc.pid, signal.SIGTERM), (proc.pid, signal.SIGKILL)])
        proc.wait.assert_called_once_with(timeout=2)
        sel.close.assert_called_once()
        proc.stdout.close.assert_called_once()
        proc.stderr.close.assert_called_once()

    def test_campaign_failure_persists_bounded_output_and_partial_diagnostics(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            inventory = root / 'inventory'
            inventory.mkdir()
            output = root / 'output'
            (inventory / 'commands.json').write_text(json.dumps([{
                'tag': 'create', 'argv': ['docker', '--host', 'synthetic', 'create', '--name', 'name', 'image']}]))
            def call(argv, **kwargs):
                text = json.dumps([{'State': {'Running': True}}]) if 'inspect' in argv else 'synthetic\n'
                return types.SimpleNamespace(returncode=0, stdout=text, stderr='')
            def fail(*args, **kwargs):
                args[6]['stdout'].extend(b'failure diagnostic')
                args[7]['seen'] = behavior.OUTPUT_LIMIT + 1
                kwargs['diagnostics'].update(termination_reason='output_limit',
                                            output_bytes_seen=behavior.OUTPUT_LIMIT + 1,
                                            retained_bytes=18, truncated=True)
                raise TimeoutError('synthetic deadline')
            with patch.object(behavior.subprocess, 'run', side_effect=call) as control, \
                 patch.object(behavior, 'drain_attached', side_effect=fail), \
                 patch.object(sys, 'argv', ['behavior', '--inventory', str(inventory), '--output', str(output)]), \
                 contextlib.redirect_stdout(io.StringIO()):
                behavior.main()
            result = json.loads((output / 'result.json').read_text())
            self.assertEqual(result['status'], 'INCONCLUSIVE')
            self.assertFalse(result['qualified'])
            self.assertEqual(result['probes'][0]['termination_reason'], 'output_limit')
            self.assertTrue(result['probes'][0]['truncated'])
            self.assertIn('synthetic deadline', result['probes'][0]['error'])
            self.assertEqual((output / 'disk.stdout').read_bytes(), b'failure diagnostic')
            self.assertEqual(result['cleanup'], 'active container removed')
            self.assertTrue(any(c.args[0][-3:] == ['rm', '--force', 'drydock-m0-004-disk'] for c in control.call_args_list))


class RegressionEvidenceTests(unittest.TestCase):
    template = ['docker', '--host', 'synthetic', 'create', '--name', 'name',
                '--label', 'old', 'sha256:old', 'output']
    cid = 'a' * 64

    def run_fake(self, observation=None, after=None, failure=None, remove_failure=False):
        def docker(base, args, **kwargs):
            if args[0] == 'inspect':
                return json.dumps([{'Id': self.cid, 'Image': 'sha256:synthetic',
                                    'State': {'Running': False}}]).encode()
            if args[0] == 'rm' and remove_failure:
                raise RuntimeError('removal failed')
            return b''
        def attach(*args, **kwargs):
            args[6]['stdout'].extend(b'diagnostic')
            args[7]['seen'] = regression.OUTPUT_LIMIT + 1
            if observation is not None:
                kwargs['on_cgroup'](pathlib.Path('/sys/fs/cgroup') / f'docker-{self.cid}.scope')
            if failure:
                raise failure
            return dict(termination_reason='output_limit', termination_seconds=.1,
                        stop_exit_code=0, retained_bytes=10, truncated=True,
                        cgroup_path=None), 2
        with patch.object(regression, 'docker', side_effect=docker), \
             patch.object(regression, 'drain_attached', side_effect=attach), \
             patch.object(regression, 'observe_cgroup', return_value=observation), \
             patch.object(regression, 'cgroup_current_state', return_value=after or {'observable': False}):
            return regression.run_regression(self.template[:3], self.template, 'sha256:synthetic', 'review')

    def test_unobservable_existing_or_failed_cleanup_never_passes(self):
        for after in ({'observable': False}, {'observable': False, 'error': 'PermissionError'},
                      {'observable': True, 'exists': True, 'procs': []},
                      {'observable': True, 'exists': True, 'procs': ['123']}):
            with self.subTest(after=after):
                self.assertFalse(self.run_fake(after=after)['cleanup_verified'])
        self.assertFalse(self.run_fake(after={'observable': True, 'exists': False},
                                       remove_failure=True)['cleanup_verified'])

    def test_observed_live_then_absent_scope_and_empty_container_query_pass(self):
        live = {'host_path': '/sys/fs/cgroup/synthetic', 'observed_live': True, 'cgroup_procs': ['123']}
        row = self.run_fake(observation=live, after={'observable': True, 'exists': False})
        self.assertTrue(row['passed'])
        self.assertTrue(row['cleanup_verified'])
        self.assertEqual(row['probe_cgroup_live'], live)

    def test_never_populated_scope_is_not_cleanup_proof(self):
        pending = {'observed_live': False, 'cgroup_procs_raw': '', 'cgroup_events_raw': 'populated 0\n'}
        row = self.run_fake(observation=pending, after={'observable': True, 'exists': False})
        self.assertFalse(row['cleanup_verified'])
        self.assertNotIn('probe_cgroup_live', row)
        self.assertEqual(row['cgroup_last_observation'], pending)
        self.assertEqual(row['cgroup_observation_attempts'], 1)

    def test_attach_failure_is_reported_with_output_and_cleanup(self):
        row = self.run_fake(failure=RuntimeError('snapshot failed'))
        self.assertFalse(row['passed'])
        self.assertFalse(row['cleanup_verified'])
        self.assertIn('snapshot failed', row['error'])
        self.assertTrue(row['cleanup_remove_succeeded'])
        self.assertEqual(bytes.fromhex(row['captured_hex']['stdout']), b'diagnostic')

    def test_callback_failure_reaps_attach_client_and_returns_failure(self):
        proc = MagicMock()
        proc.poll.return_value = None
        proc.returncode = -signal.SIGTERM
        sel = MagicMock()
        sel.get_map.return_value = {'open': True}
        def docker(base, args, **kwargs):
            if args[0] == 'inspect':
                return json.dumps([{'Id': self.cid, 'Image': 'sha256:synthetic'}]).encode()
            return b''
        with patch.object(regression, 'docker', side_effect=docker), \
             patch.object(behavior.subprocess, 'Popen', return_value=proc), \
             patch.object(behavior.selectors, 'DefaultSelector', return_value=sel), \
             patch.object(behavior.pathlib.Path, 'glob', return_value=[pathlib.Path('/synthetic')]), \
             patch.object(regression, 'observe_cgroup', side_effect=PermissionError('snapshot unreadable')), \
             patch.object(behavior.os, 'killpg') as kill, \
             patch.object(behavior.os, 'read', return_value=b'diagnostic'):
            sel.select.return_value = [(types.SimpleNamespace(fileobj=proc.stdout, data='stdout'), None)]
            row = regression.run_regression(self.template[:3], self.template, 'sha256:synthetic', 'review')
        self.assertIn('snapshot unreadable', row['error'])
        self.assertFalse(row['passed'])
        self.assertFalse(row['cleanup_verified'])
        self.assertTrue(row['cleanup_remove_succeeded'])
        self.assertEqual(proc.wait.call_count, 1)
        sel.close.assert_called_once()
        proc.stdout.close.assert_called_once()
        proc.stderr.close.assert_called_once()
        self.assertEqual(kill.call_count, 2)

    def test_runner_main_writes_inconclusive_report_and_failure_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output = pathlib.Path(temp) / 'drydock-issue2-review-result'
            profile = pathlib.Path(__file__).resolve().parents[2] / 'docs/evidence/m0-004/behavior/commands.json'
            row = self.run_fake(failure=RuntimeError('inspection failure'))
            def docker(base, args, **kwargs):
                return b'{}' if args[0] == 'version' else b'[{"Id":"sha256:synthetic"}]'
            argv = ['regression', '--profile', str(profile), '--image', 'sha256:synthetic',
                    '--output', str(output), '--rootfs-sha256', regression.EXPECTED_ROOTFS_SHA256,
                    '--probe-sha256', regression.EXPECTED_PROBE_SHA256]
            with patch.object(sys, 'argv', argv), patch.object(regression, 'docker', side_effect=docker), \
                 patch.object(regression, 'run_regression', return_value=row), \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    regression.main()
            self.assertEqual(error.exception.code, 1)
            report = json.loads((output / 'result.json').read_text())
            self.assertEqual(report['status'], 'INCONCLUSIVE')
            self.assertFalse(report['qualified'])
            self.assertIn('inspection failure', report['regression']['error'])
            self.assertEqual((output / 'output.stdout').read_bytes(), b'diagnostic')
            self.assertNotIn('captured_hex', report['regression'])

    def test_live_scope_requires_matching_id_and_kernel_population(self):
        path = pathlib.Path('/sys/fs/cgroup') / f'docker-{self.cid}.scope'
        def resolved(path, **kwargs):
            return path
        for populated in ('0', '1'):
            def read(path):
                return '' if path.name == 'cgroup.procs' else f'populated {populated}\nfrozen 0\n'
            with patch.object(pathlib.Path, 'resolve', resolved), patch.object(pathlib.Path, 'read_text', read):
                observation = regression.observe_cgroup(path, self.cid)
                self.assertEqual(observation['observed_live'], populated == '1')
                self.assertEqual(observation['cgroup_procs_raw'], '')
                self.assertIn(f'populated {populated}', observation['cgroup_events_raw'])
                with self.assertRaisesRegex(RuntimeError, 'target container scope'):
                    regression.observe_cgroup(path, 'b' * 64)
        with patch.object(pathlib.Path, 'resolve', resolved), \
             patch.object(pathlib.Path, 'read_text', return_value='populated invalid'):
            with self.assertRaisesRegex(RuntimeError, 'invalid populated'):
                regression.observe_cgroup(path, self.cid)
        with patch.object(pathlib.Path, 'resolve', resolved), \
             patch.object(pathlib.Path, 'stat', side_effect=FileNotFoundError):
            self.assertEqual(regression.cgroup_current_state({'host_path': str(path), 'observed_live': True}),
                             {'observable': True, 'exists': False})

    def test_pending_observation_retries_while_output_keeps_draining(self):
        sel = MagicMock()
        stream = MagicMock()
        entries = {'stdout': stream}
        sel.get_map.side_effect = lambda: entries
        sel.unregister.side_effect = lambda stream: entries.clear()
        sel.select.return_value = [(types.SimpleNamespace(fileobj=stream, data='stdout'), None)]
        total = {'seen': 0}
        observations = []
        def observe(path):
            observations.append(total['seen'])
            return len(observations) == 2
        with patch.object(behavior.pathlib.Path, 'glob', return_value=[pathlib.Path('/synthetic')]), \
             patch.object(behavior.os, 'read', side_effect=[b'x', b'y', b'']):
            result = behavior.drain_until_complete(
                sel, 'output', time.monotonic(), [], 'synthetic', 'synthetic',
                {'stdout': bytearray(), 'stderr': bytearray()}, total, [], on_cgroup=observe)
        self.assertEqual(observations, [1, 2])
        self.assertEqual(total['seen'], 2)
        self.assertIsNone(result['termination_reason'])

    def test_permission_error_is_not_absence(self):
        live = {'observed_live': True, 'host_path': '/sys/fs/cgroup/synthetic'}
        with patch.object(pathlib.Path, 'resolve', return_value=pathlib.Path('/sys/fs/cgroup')), \
             patch.object(pathlib.Path, 'stat', side_effect=PermissionError('synthetic')):
            state = regression.cgroup_current_state(live)
        self.assertFalse(state['observable'])
        self.assertIn('PermissionError', state['error'])
        self.assertFalse(regression.cgroup_current_state(None)['observable'])


if __name__ == '__main__':
    unittest.main()
