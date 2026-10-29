#!/usr/bin/env python3
"""Offline regression checks for external standalone assets and host packaging."""
import base64
import io
import json
import os
import tempfile
import unittest
import zipfile

import build_standalone as standalone
import build_host as host


class EmbeddedAssetsTest(unittest.TestCase):
    def test_external_assets_and_loader_override(self):
        with tempfile.TemporaryDirectory() as directory:
            asset = os.path.join(directory, 'asset.bin')
            data = b'\x00\xffexternal asset\x00'
            with open(asset, 'wb') as f:
                f.write(data)
            _, loader_key = standalone.load_binary_config()
            files = {'external/payload.elf': asset, loader_key: asset}
            payloads = standalone.load_payloads(['payloads/hello_world.js'])
            html, meta = standalone.build_html(payloads, embedded_files=files)
            self.assertEqual(standalone.check_output(html, payloads, meta), [])
            table = standalone.extract_json_assignment(html, 'EMBEDDED_BINARIES')
            info = standalone.extract_json_assignment(html, 'EMBEDDED_BINARY_INFO')
            for key in files:
                self.assertEqual(base64.b64decode(table[key]), data)
                self.assertEqual(info[key]['size'], len(data))
            html, _ = standalone.build_html(payloads, include_kexp=False,
                                             embedded_files={'external/payload.elf': asset})
            self.assertEqual(set(standalone.extract_json_assignment(html, 'EMBEDDED_BINARIES')),
                             {'external/payload.elf'})

    def test_elfldr_custom_url_override(self):
        with tempfile.TemporaryDirectory() as directory:
            asset = os.path.join(directory, 'elfldr.elf')
            data = b'\x7fELFcustom elfldr\x00'
            with open(asset, 'wb') as f:
                f.write(data)
            custom_url = 'shared/elfldr-ps5-v0.26-bb1e117.elf'
            payloads = standalone.load_payloads(['payloads/hello_world.js'])
            html, meta = standalone.build_html(
                payloads,
                embedded_files={custom_url: asset},
                elfldr_url=custom_url,
            )
            self.assertEqual(standalone.check_output(html, payloads, meta), [])
            table = standalone.extract_json_assignment(html, 'EMBEDDED_BINARIES')
            self.assertIn(custom_url, table)
            _, default_loader = standalone.load_binary_config()
            self.assertNotIn(default_loader, table)
            self.assertEqual(base4_data := base64.b64decode(table[custom_url]), data)
            cfg = standalone.extract_json_assignment(html, 'LOADER_CONFIG')
            self.assertEqual(cfg, {'ELFLDR_ELF': custom_url})

    def test_single_page_host(self):
        with tempfile.TemporaryDirectory() as directory:
            page = os.path.join(directory, 'page.html')
            output = os.path.join(directory, 'host.py')
            data = b'<!doctype html><title>External page</title>'
            with open(page, 'wb') as f:
                f.write(data)
            archive, files = host.build_zip(page)
            self.assertEqual(files, {'index.html': page})
            with zipfile.ZipFile(io.BytesIO(archive)) as zf:
                self.assertEqual(zf.namelist(), ['index.html'])
                self.assertEqual(zf.read('index.html'), data)
            self.assertEqual(host.main(['--page', page, '--output', output,
                                        '--name', 'Custom "host"', '--version', 'test']), 0)
            with open(output) as f:
                source = f.read()
            compile(source, output, 'exec')
            self.assertIn('HOST_NAME = ' + json.dumps('Custom "host"'), source)

    def test_default_host_contains_diagnostics_and_probes(self):
        archive, files = host.build_zip()
        for name in ('index.html', 'loader.html', 'src/diagnostics.js',
                     'probes/canvas-uaf/v573-reclaim-diagnostic.html',
                     'probes/canvas-uaf/v630.html', 'shared/elfldr-ps5-v0.26.elf',
                     'shared/kexp-v0.8-24cf6e5.bin'):
            self.assertTrue(name in files, name)
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            self.assertIn(b'PS5 baseline', bundle.read('index.html'))

    def test_bundle_excludes_private_and_generated_files(self):
        for name in ('probes/.env', 'probes/run.log', 'probes/run.jsonl',
                     'assets/server.key', 'src/__pycache__/file.pyc'):
            self.assertFalse(host.should_include(name), name)

    def test_multi_page_host_and_fw_routing(self):
        from unittest.mock import patch
        import host as live_host

        with tempfile.TemporaryDirectory() as directory:
            relapse = os.path.join(directory, 'relapse.html')
            poops = os.path.join(directory, 'poops.html')
            with open(relapse, 'wb') as f:
                f.write(b'RELAPSE')
            with open(poops, 'wb') as f:
                f.write(b'POOPS')
            for explicit_relapse in (False, True):
                pages = [f'index.html={relapse}', f'poops.html={poops}']
                if explicit_relapse:
                    pages.append(f'relapse.html={relapse}')
                archive, _ = host.build_zip(pages)
                with zipfile.ZipFile(io.BytesIO(archive)) as bundle, \
                        patch.object(live_host, '_embedded_zip_cache', bundle), \
                        patch.object(live_host, '_embedded_zip_loaded', True):
                    for firmware, override, expected in (
                            (7.61, None, b'RELAPSE'), (9.05, None, b'POOPS'),
                            (11.40, None, b'POOPS'), (7.61, 'poops', b'POOPS'),
                            (9.05, 'relapse', b'RELAPSE')):
                        for path in ('/', '/index.html', '/document/en/ps5/index.html'):
                            result = live_host.resolve_file(
                                live_host.normalize_request_path(path), firmware, override)
                            self.assertEqual(result[3], expected, (path, firmware, override))
                    result = live_host.resolve_file('relapse.html')
                    self.assertEqual(result[3], b'RELAPSE')


if __name__ == '__main__':
    unittest.main()
