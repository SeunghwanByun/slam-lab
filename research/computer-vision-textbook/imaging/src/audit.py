"""Check the integration manuscript, artifacts, provenance, and numeric examples."""
import contextlib
import hashlib
import io
import json
import re
import unittest
from pathlib import Path
from PIL import Image
import numpy as np

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]


def main():
    suite = unittest.defaultTestLoader.discover(str(BASE/'src'), pattern='test_*.py')
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    chapter = (BASE/'notes/chapters.md').read_text()
    anchors = re.findall(r'<a id="([^"]+)"', chapter)
    links = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', chapter)
    checks = {}
    checks['four_chapters'] = len(re.findall(r'^## D[1-4]\.', chapter, re.M)) == 4
    checks['unique_anchors'] = len(anchors) == len(set(anchors))
    checks['lowercase_scoped_anchors'] = all(re.fullmatch('d[1-4](?:-[a-z]+)?', a) for a in anchors)
    checks['twenty_solved_exercises'] = len(re.findall(r'\*\*문제 D[1-4]-[1-5]\.', chapter)) == 20
    checks['thirteen_figures'] = len(links) == 13
    checks['balanced_fences'] = len(re.findall(r'^```', chapter, re.M)) % 2 == 0
    checks['target_length'] = 80000 <= len(chapter.encode()) <= 125000 and 1400 <= len(chapter.splitlines()) <= 2200
    checks['figures_exist'] = all((ROOT/'docs'/p).resolve().is_file() for p in links)
    for link in links:
        with Image.open((ROOT/'docs'/link).resolve()) as im:
            checks[im.filename.split('/')[-1]+'_size_dpi'] = im.width == 1400 and min(im.info.get('dpi', (0, 0))) >= 180
    manifest = json.loads((BASE/'artifacts/manifest.json').read_text())
    for scope, directory in [('source_sha256', BASE), ('input_sha256', ROOT), ('artifact_sha256', BASE/'artifacts')]:
        checks[scope] = all(hashlib.sha256((directory/path).read_bytes()).hexdigest() == expected
                            for path, expected in manifest[scope].items())
    checks['figure_sha256'] = all(hashlib.sha256((BASE/'figures'/path).read_bytes()).hexdigest() == expected
                                  for path, expected in manifest['figure_sha256'].items())
    for module in ['d1', 'd2', 'd3', 'd4']:
        arrays = np.load(BASE/'artifacts'/module/'arrays.npz')
        checks[module+'_arrays_finite'] = all(np.isfinite(arrays[k]).all() for k in arrays.files)
    report = {'unit_tests': result.testsRun, 'unit_failures': len(result.failures), 'unit_errors': len(result.errors),
              'audit_checks': len(checks), 'audit_failures': [k for k, v in checks.items() if not v],
              'chapters_bytes': len(chapter.encode()), 'chapters_lines': len(chapter.splitlines()),
              'anchors': len(anchors), 'figures': len(links), 'checks': checks,
              'unit_log': stream.getvalue(), 'manuscript_sha256': hashlib.sha256(chapter.encode()).hexdigest()}
    (BASE/'artifacts/audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['checks', 'unit_log']}, ensure_ascii=False, indent=2))
    if not result.wasSuccessful() or not all(checks.values()): raise SystemExit(1)


if __name__ == '__main__': main()
