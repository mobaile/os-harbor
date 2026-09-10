import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from osharbor.core import (HarborError, build, check_image, deploy, digest, merge_config,
                          read_json, register, registry, safe_path, verify, write_json)


class Volumes:
    def __init__(self, root):
        self.root = root
    def identify(self, path):
        return {"volume_id": "stable-volume", "relative_path": Path(path).relative_to(self.root).as_posix()}
    def resolve(self, system):
        if system['volume_id'] != 'stable-volume':
            raise HarborError('Volume unavailable')
        return safe_path(self.root, system['relative_path'])


def fake_link(tool, source, target):
    # Test double only. Production always invokes the official executable.
    target.write_bytes(b'TEST-DOUBLE-' + str(source).encode())


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.images = self.root / 'images'
        self.images.mkdir()
        self.image = self.images / 'Windows 中文.vhdx'
        self.image.write_bytes(b'vhdxfile' + b'0' * 1024)
        self.volumes = Volumes(self.images)
        self.reg = self.root / 'systems.json'
        self.tool = self.root / 'tool.exe'
        self.tool.write_bytes(b'test-tool')
        self.bundle = self.root / 'bundle'
        self.usb = self.root / 'usb'
        (self.usb / 'ventoy').mkdir(parents=True)
        (self.usb / 'ventoy/ventoy_vhdboot.img').write_bytes(b'test-plugin')
        register(self.reg, self.volumes, self.image, 'win11', 'Windows 中文', 'windows')

    def build(self):
        return build(self.reg, self.volumes, self.bundle, self.tool, digest(self.tool), fake_link)

    def deploy(self, **kw):
        return deploy(self.bundle, self.usb, self.volumes, target_validator=lambda x: Path(x), **kw)

    def test_unicode_registry_and_duplicate(self):
        self.assertEqual(registry(self.reg)['systems'][0]['name'], 'Windows 中文')
        with self.assertRaises(HarborError):
            register(self.reg, self.volumes, self.image, 'other', 'Other', 'windows')

    def test_missing_image(self):
        self.image.unlink()
        with self.assertRaises(HarborError): self.build()

    def test_invalid_volume(self):
        data = registry(self.reg)
        data['systems'][0]['volume_id'] = 'missing'
        write_json(self.reg, data)
        with self.assertRaises(HarborError): self.build()

    def test_path_traversal(self):
        for path in ('../escape', '/absolute', 'C:/x', 'x\\y'):
            with self.assertRaises(HarborError): safe_path(self.root, path)

    def test_duplicate_json_keys(self):
        self.reg.write_text('{"schema_version":1,"schema_version":2}')
        with self.assertRaises(HarborError): registry(self.reg)

    def test_wrong_tool_hash(self):
        with self.assertRaises(HarborError):
            build(self.reg, self.volumes, self.bundle, self.tool, '0'*64, fake_link)

    def test_preserve_config_idempotent_and_verify(self):
        self.build()
        original = {'theme': {'file': '/theme.txt'}, 'menu_alias': [{'image': '/rescue.iso', 'alias': 'Rescue'}]}
        write_json(self.usb / 'ventoy/ventoy.json', original)
        result = self.deploy()
        first = read_json(self.usb / 'ventoy/ventoy.json')
        self.deploy()
        self.assertEqual(first, read_json(self.usb / 'ventoy/ventoy.json'))
        self.assertEqual(first['theme'], original['theme'])
        self.assertEqual(read_json(Path(result['backup']) / 'ventoy.json'), original)
        self.assertEqual(verify(self.bundle, self.usb, self.volumes, lambda x:x)['consistency'], 'passed')

    def test_invalid_existing_config_not_overwritten(self):
        self.build()
        cfg = self.usb / 'ventoy/ventoy.json'
        cfg.write_bytes(b'{broken')
        with self.assertRaises(HarborError): self.deploy()
        self.assertEqual(cfg.read_bytes(), b'{broken')

    def test_interruption_before_commit(self):
        self.build()
        cfg = self.usb / 'ventoy/ventoy.json'
        write_json(cfg, {'theme': {'file': '/keep'}})
        before = cfg.read_bytes()
        def fail(): raise OSError('simulated disconnect')
        with self.assertRaises(OSError): self.deploy(before_commit=fail)
        self.assertEqual(cfg.read_bytes(), before)
        self.deploy()

    def test_source_changed(self):
        self.build()
        self.image.write_bytes(self.image.read_bytes() + b'changed')
        with self.assertRaises(HarborError): self.deploy()

    def test_tampered_link(self):
        m = self.build()
        safe_path(self.bundle, m['records'][0]['path']).write_bytes(b'tampered')
        with self.assertRaises(HarborError): self.deploy()

    def test_manifest_path_injection(self):
        m = self.build()
        m['records'][0]['path'] = '../outside'
        write_json(self.bundle/'manifest.json', m)
        with self.assertRaises(HarborError): self.deploy()

    def test_missing_plugin(self):
        self.build()
        (self.usb/'ventoy/ventoy_vhdboot.img').unlink()
        with self.assertRaises(HarborError): self.deploy()

    def test_reject_filter(self):
        with self.assertRaises(HarborError): merge_config({'image_list':['/a.iso']}, {'menu_alias':[]})

    def test_concurrent_config_change(self):
        self.build()
        cfg = self.usb/'ventoy/ventoy.json'
        with self.assertRaises(HarborError):
            self.deploy(before_commit=lambda: write_json(cfg, {'theme':{}}))
        self.assertEqual(read_json(cfg), {'theme':{}})

    def test_fixed_vhd_validation(self):
        footer = bytearray(512)
        footer[:8] = b'conectix'
        footer[48:56] = struct.pack('>Q', 1024)
        footer[60:64] = struct.pack('>I', 2)
        footer[64:68] = struct.pack('>I', ~sum(footer) & 0xffffffff)
        image = self.images/'Omarchy.vhd.vtoy'
        image.write_bytes(b'0'*1024 + footer)
        self.assertEqual(check_image(image, 'omarchy')['format_check'], 'passed')
        footer[60:64] = struct.pack('>I', 3)
        image.write_bytes(b'0'*1024 + footer)
        with self.assertRaises(HarborError): check_image(image, 'omarchy')


if __name__ == '__main__': unittest.main()
