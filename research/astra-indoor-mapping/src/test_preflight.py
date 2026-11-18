import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from preflight import blockers, candidates, inspect_usb, linux_usb, parse_macos_usb


class PreflightTests(unittest.TestCase):
    @patch('preflight.subprocess.run')
    def test_macos_requests_properties_and_handles_dict_root(self, run):
        run.return_value.stdout = plistlib.dumps({'IORegistryEntryChildren': [
            {'idVendor': 123, 'idProduct': 456, 'USB Product Name': 'Astra test'}]})
        result = inspect_usb('Darwin')
        self.assertIn('-l', run.call_args.args[0])
        self.assertEqual(len(result['devices']), 1)
        self.assertEqual(len(result['candidates']), 1)

    def test_nested_plist_and_privacy(self):
        node = [{'IORegistryEntryChildren': [{'idVendor': 123, 'idProduct': 456,
                 'USB Vendor Name': 'Orbbec', 'USB Product Name': 'Astra example',
                 'USB Serial Number': 'DO_NOT_EXPORT'}]}]
        devices = parse_macos_usb(plistlib.dumps(node))
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]['vendor_id'], '007b')
        self.assertNotIn('DO_NOT_EXPORT', str(devices))

    def test_empty_registry(self):
        self.assertEqual(parse_macos_usb(plistlib.dumps([{}])), [])

    def test_invalid_plist(self):
        with self.assertRaises(plistlib.InvalidFileException):
            parse_macos_usb(b'invalid')

    def test_name_match_not_generic_hub(self):
        devices = [{'manufacturer': 'Apple', 'product': 'USB Hub'},
                   {'manufacturer': 'ORBBEC', 'product': 'unknown model'}]
        self.assertEqual(candidates(devices), [devices[1]])

    def test_no_device_is_not_capture_success(self):
        pending = blockers({'status': 'enumerated', 'candidates': []}, None)
        self.assertEqual(len(pending), 3)

    def test_model_does_not_verify_capture(self):
        pending = blockers({'status': 'enumerated', 'candidates': [{}]}, 'Astra 2')
        self.assertEqual(len(pending), 1)
        self.assertIn('unverified', pending[0])

    def test_unsupported_os(self):
        self.assertEqual(inspect_usb('Unsupported')['status'], 'unsupported_host')

    @patch('preflight.subprocess.run', side_effect=FileNotFoundError())
    def test_enumeration_failure_is_explicit(self, _run):
        self.assertEqual(inspect_usb('Darwin')['status'], 'enumeration_failed')

    def test_linux_sysfs_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            device = Path(directory) / '1-1'
            device.mkdir()
            (device / 'idVendor').write_text('1234\n')
            (device / 'idProduct').write_text('0001\n')
            (device / 'product').write_text('Astra test\n')
            found = linux_usb(Path(directory))
            self.assertEqual(found[0]['product'], 'Astra test')
            self.assertEqual(found[0]['manufacturer'], '')


if __name__ == '__main__':
    unittest.main()
