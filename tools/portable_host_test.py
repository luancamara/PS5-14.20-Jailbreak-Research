#!/usr/bin/env python3
"""Build and run the distributable outside the checkout over HTTP and TLS."""
import contextlib
import io
import json
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

import build_host


class PortableHostTest(unittest.TestCase):
    def test_bundle_runs_outside_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            script = work / 'host.py'
            with contextlib.redirect_stdout(io.StringIO()):
                build_host.main(['--output', str(script), '--version', 'portable-test'])
            for tls in (False, True):
                with self.subTest(tls=tls), socket.socket() as reserved:
                    reserved.bind(('127.0.0.1', 0))
                    port = reserved.getsockname()[1]
                    reserved.close()
                    beacon_log = work / f'beacons-{tls}.jsonl'
                    args = [sys.executable, str(script), '--ip', '127.0.0.1', '--no-dns',
                            '--no-watch', '--no-heartbeat', '--beacon-log', str(beacon_log)]
                    args += ['--https-port', str(port)] if tls else ['--no-https', '--http-port', str(port)]
                    context = ssl._create_unverified_context() if tls else None
                    base = f'{"https" if tls else "http"}://127.0.0.1:{port}'
                    with (work / f'host-{tls}.log').open('w+') as output:
                        process = subprocess.Popen(args, cwd=work, stdout=output, stderr=subprocess.STDOUT)
                        try:
                            deadline = time.monotonic() + 15
                            while True:
                                try:
                                    with urllib.request.urlopen(base + '/', context=context, timeout=1) as response:
                                        self.assertIn(b'PS5 baseline', response.read())
                                    break
                                except (urllib.error.URLError, TimeoutError):
                                    if process.poll() is not None or time.monotonic() >= deadline:
                                        output.seek(0)
                                        self.fail('Portable host did not start:\n' + output.read())
                                    time.sleep(0.1)
                            for path in ('/document/pt/ps5/index.html', '/src/diagnostics.js',
                                         '/document/pt/ps5/probes/canvas-uaf/v573-reclaim-diagnostic.html',
                                         '/probes/canvas-uaf/v630.html'):
                                with urllib.request.urlopen(base + path, context=context, timeout=3) as response:
                                    self.assertEqual(response.status, 200)
                                    self.assertTrue(response.read())
                            request = urllib.request.Request(base + '/beacon/BASELINE',
                                                             data=b'{"stage":"portable"}')
                            with urllib.request.urlopen(request, context=context, timeout=3) as response:
                                self.assertEqual(response.status, 204)
                            entry = json.loads(beacon_log.read_text().splitlines()[-1])
                            self.assertEqual(entry['body'], '{"stage":"portable"}')
                        finally:
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
