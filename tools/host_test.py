#!/usr/bin/env python3
"""Exercise the actual host over loopback, without DNS, TLS or a console."""
import contextlib
import io
import json
import socket
import struct
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

import host


class HostTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.log = Path(self.directory.name) / 'beacons.jsonl'
        self.beacons = host.BeaconStore(log_path=str(self.log))
        self.server = host.build_server('127.0.0.1', 0, None, host.Stats(), self.beacons, True)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.beacons.close()

    def request(self, path, data=None):
        request = urllib.request.Request(
            f'http://127.0.0.1:{self.server.server_port}{path}', data=data)
        return urllib.request.urlopen(request, timeout=3)

    def test_default_page_and_guide_path_are_diagnostics(self):
        for path in ('/', '/index.html', '/document/pt/ps5/index.html'):
            with self.subTest(path=path), self.request(path) as response:
                body = response.read().decode()
                self.assertIn('PS5 baseline', body)
                self.assertNotIn('http-equiv="refresh"', body)

    def test_documented_probes_and_resources_are_served(self):
        for path in ('/src/diagnostics.js', '/probes/canvas-uaf/v573-reclaim-diagnostic.html',
                     '/document/en/ps5/probes/canvas-uaf/v630.html', '/loader.html'):
            with self.subTest(path=path), self.request(path) as response:
                self.assertEqual(response.status, 200)
                self.assertTrue(response.read())

    def test_get_and_post_beacons_are_persisted(self):
        with self.request('/beacon/V999-BOOT?d=image-beacon') as response:
            self.assertEqual(response.status, 204)
        with self.request('/beacon/BASELINE', b'{"stage":"baseline"}') as response:
            self.assertEqual(response.status, 204)
        entries = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual([entry['method'] for entry in entries], ['GET', 'POST'])
        self.assertIn('d=image-beacon', entries[0]['path'])
        self.assertEqual(entries[1]['body'], '{"stage":"baseline"}')

    def test_beacon_does_not_report_success_when_log_cannot_be_written(self):
        self.beacons._log_path = self.directory.name
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request('/beacon/BASELINE', b'test')
        self.assertEqual(caught.exception.code, 500)
        caught.exception.close()

    def test_firmware_routing_includes_explicit_index_paths(self):
        import zipfile
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as bundle:
            bundle.writestr('index.html', b'INDEX')
            bundle.writestr('poops.html', b'POOPS')
        with zipfile.ZipFile(archive) as bundle, \
                patch.object(host, '_embedded_zip_cache', bundle), \
                patch.object(host, '_embedded_zip_loaded', True):
            for path in ('/', '/index.html', '/document/en/ps5/index.html'):
                resolved = host.resolve_file(host.normalize_request_path(path), firmware=9.05)
                self.assertEqual(resolved[2], 'poops.html', path)

    def test_private_files_and_external_symlinks_are_not_served(self):
        root = Path(self.directory.name) / 'site'
        root.mkdir()
        (root / '.env').write_text('PRIVATE')
        (root / 'server.key').write_text('PRIVATE')
        (root / 'host-beacons.log').write_text('PRIVATE')
        (root / 'outside.txt').symlink_to(self.log)
        self.log.write_text('PRIVATE')
        with patch.object(host, 'REPO_ROOT', str(root)):
            for name in ('.env', 'server.key', 'host-beacons.log', 'outside.txt'):
                self.assertIsNone(host.resolve_file(name), name)

    def test_dns_redirects_only_the_configured_domain(self):
        dns = host.DNSServer(('127.0.0.1', 0), 'manuals.playstation.net',
                             '127.0.0.1', host.Stats(), False)
        threading.Thread(target=dns.serve_forever, daemon=True).start()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.settimeout(3)
                for domain, answers, code in (('manuals.playstation.net', 1, 0),
                                               ('example.org', 0, 3)):
                    question = b''.join(bytes([len(label)]) + label.encode()
                                        for label in domain.split('.')) + b'\0'
                    packet = struct.pack('!6H', 123, 0x100, 1, 0, 0, 0)
                    client.sendto(packet + question + struct.pack('!2H', 1, 1), dns.server_address)
                    response, _ = client.recvfrom(512)
                    header = struct.unpack('!6H', response[:12])
                    self.assertEqual((header[0], header[1] & 15, header[3]), (123, code, answers))
                    if answers:
                        self.assertEqual(response[-4:], socket.inet_aton('127.0.0.1'))
        finally:
            dns.shutdown()
            dns.server_close()


if __name__ == '__main__':
    unittest.main()
