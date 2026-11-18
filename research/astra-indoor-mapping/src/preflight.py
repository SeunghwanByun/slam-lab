"""Read-only host/USB inventory. Does not open cameras or install drivers."""
import argparse
import json
import platform
import plistlib
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[1]


def parse_macos_usb(payload):
    """Keep product metadata only; never export serials or the whole registry."""
    result = []

    def walk(node):
        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict):
            vendor, product = node.get('idVendor'), node.get('idProduct')
            if isinstance(vendor, int) and isinstance(product, int):
                result.append({
                    'vendor_id': f'{vendor:04x}',
                    'product_id': f'{product:04x}',
                    'manufacturer': str(node.get('USB Vendor Name', '')),
                    'product': str(node.get('USB Product Name', '')),
                })
            walk(node.get('IORegistryEntryChildren', []))

    walk(plistlib.loads(payload))
    return result


def linux_usb(root=Path('/sys/bus/usb/devices')):
    result = []
    for device in sorted(root.iterdir()):
        if not (device / 'idVendor').exists():
            continue

        def read(name):
            path = device / name
            return path.read_text().strip() if path.exists() else ''

        result.append({'vendor_id': read('idVendor'),
                       'product_id': read('idProduct'),
                       'manufacturer': read('manufacturer'),
                       'product': read('product')})
    return result


def candidates(devices):
    # Name matches are candidates, not an SDK compatibility decision.
    return [d for d in devices if any(
        name in (d['manufacturer'] + ' ' + d['product']).casefold()
        for name in ('orbbec', 'astra'))]


def inspect_usb(system):
    try:
        if system == 'Darwin':
            proc = subprocess.run(['ioreg', '-p', 'IOUSB', '-a', '-l'],
                                  capture_output=True, timeout=20, check=True)
            devices = parse_macos_usb(proc.stdout)
            source = 'ioreg -p IOUSB -a -l (plist with properties)'
        elif system == 'Linux':
            devices = linux_usb()
            source = '/sys/bus/usb/devices'
        else:
            return {'status': 'unsupported_host', 'devices': [], 'candidates': []}
        return {'status': 'enumerated', 'source': source,
                'devices': devices, 'candidates': candidates(devices)}
    except (OSError, ValueError, plistlib.InvalidFileException,
            subprocess.SubprocessError) as error:
        return {'status': 'enumeration_failed', 'error_type': type(error).__name__,
                'devices': [], 'candidates': []}


def blockers(usb, model):
    pending = []
    if usb['status'] != 'enumerated':
        pending.append('USB enumeration unavailable; camera presence is unknown.')
    elif not usb['candidates']:
        pending.append('No Orbbec/Astra name match; absence or incompatibility is not proven.')
    if not model:
        pending.append('Exact model and firmware must be confirmed from the label/viewer.')
    pending.append('SDK/model/firmware/OS compatibility and live RGB-D capture are unverified.')
    return pending


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', help='User-provided label; not independently verified.')
    parser.add_argument('--out', type=Path,
                        default=STUDY / 'artifacts/preflight/environment.json')
    args = parser.parse_args()
    system = platform.system()
    usb = inspect_usb(system)
    disk = shutil.disk_usage(ROOT)
    result = {
        'schema_version': 1,
        'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'base_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'host': {'os': system, 'release': platform.release(),
                 'architecture': platform.machine(), 'python': platform.python_version()},
        'free_disk_gib': round(disk.free / 1024**3, 2),
        'commands_in_current_path': {name: shutil.which(name) for name in
                                     ('ros2', 'rtabmap', 'cmake', 'docker')},
        'usb': usb,
        'user_reported_model': args.model,
        'camera_capture_validated': False,
        'pending': blockers(usb, args.model),
        'scope': 'Host enumeration only. No sensor stream, recording, firmware change or mapping.',
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
