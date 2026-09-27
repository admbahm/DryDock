#!/usr/bin/env python3
"""Bounded local pipe mechanism reproduction; does not invoke Docker."""
import argparse
import json
import os
import platform
import subprocess
import sys
import threading
import time

LIMIT = 1 << 20
TOTAL = 8 << 20
DEADLINE = 5.0
CHILD = "import os\nblock=b'x'*65536\nremaining=8*1024*1024\nwhile remaining:\n n=os.write(1,block[:min(len(block),remaining)])\n remaining-=n\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True)
    result_path = parser.parse_args().result
    command = [sys.executable, "-c", CHILD]
    started = time.monotonic()
    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    retained = bytearray()
    read_before_resume = 0
    remainder = []
    reader_errors = []
    reader_done = threading.Event()
    reader = None
    timed_out_while_paused = False
    result = {"command": command, "platform": platform.platform(), "python": sys.version,
              "retained_limit_bytes": LIMIT, "child_output_bytes_expected": TOTAL,
              "experiment_deadline_seconds": DEADLINE}
    try:
        while read_before_resume <= LIMIT:
            chunk = os.read(child.stdout.fileno(), 65536)
            if not chunk:
                break
            read_before_resume += len(chunk)
            retained.extend(chunk[:max(0, LIMIT-len(retained))])
        if read_before_resume <= LIMIT:
            raise RuntimeError("writer ended before the pause threshold")
        try:
            child.wait(timeout=0.25)
        except subprocess.TimeoutExpired:
            timed_out_while_paused = True
        def drain_remaining():
            try:
                while True:
                    data = os.read(child.stdout.fileno(), 65536)
                    if not data:
                        break
                    remainder.append(len(data))
            except Exception as exc:
                reader_errors.append(repr(exc))
            finally:
                reader_done.set()
        reader = threading.Thread(target=drain_remaining, name="bounded-pipe-drain")
        reader.start()
        child.wait(timeout=max(0.1, DEADLINE-(time.monotonic()-started)))
        reader.join(timeout=max(0.1, DEADLINE-(time.monotonic()-started)))
        if reader.is_alive():
            raise TimeoutError("pipe drain thread exceeded experiment deadline")
        stderr = child.stderr.read(4096)
        result.update(exit_code=child.returncode, wait_without_drain_timed_out=timed_out_while_paused,
                      bytes_read_before_resume=read_before_resume,
                      bytes_read_after_resume=sum(remainder), retained_bytes=len(retained),
                      truncated=(read_before_resume+sum(remainder))>len(retained),
                      retained_limit_respected=len(retained)<=LIMIT,
                      stderr_bytes=len(stderr), reader_errors=reader_errors,
                      reader_joined=reader_done.is_set(), duration_seconds=time.monotonic()-started,
                      cleanup="child reaped; pipes closed")
        passed = (child.returncode == 0 and timed_out_while_paused and
                  read_before_resume+sum(remainder) == TOTAL and len(retained) == LIMIT and
                  reader_done.is_set() and not reader_errors and not stderr)
        result["status"] = "PASS" if passed else "FAIL"
        result["exit_status"] = 0 if passed else 1
        with open(result_path, "x") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
        print(json.dumps(result, indent=2))
        return result["exit_status"]
    except Exception as exc:
        result.update(status="INCONCLUSIVE", exit_status=1, error=repr(exc))
        try:
            with open(result_path, "x") as f:
                json.dump(result, f, indent=2)
                f.write("\n")
        except FileExistsError:
            pass
        print(json.dumps(result, indent=2))
        return 1
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=1)
        if reader and reader.is_alive():
            try:
                child.stdout.close()
            except OSError:
                pass
            reader.join(timeout=1)
        for pipe in (child.stdout, child.stderr):
            if pipe and not pipe.closed:
                pipe.close()


if __name__ == "__main__":
    raise SystemExit(main())
