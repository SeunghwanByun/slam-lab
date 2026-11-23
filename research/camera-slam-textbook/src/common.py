"""Isolated study paths, serialization and calibrated image input. No GT access."""
from pathlib import Path
import csv
import hashlib
import json
import cv2
import numpy as np

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[1]
DATA = ROOT / 'data/kitti/dataset'
CFG = json.loads((STUDY / 'configs/experiment.json').read_text())
SEQ = DATA / 'sequences' / CFG['sequence']
ART = STUDY / 'artifacts'
FIG = STUDY / 'figures'


def directory(name):
    path = ART / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_json(path, value):
    def convert(x):
        if isinstance(x, np.ndarray):
            return x.tolist()
        if isinstance(x, np.generic):
            return x.item()
        raise TypeError(type(x).__name__)
    path.write_text(json.dumps(value, indent=2, default=convert, allow_nan=False) + '\n')


def save_csv(path, rows):
    if not rows:
        return
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def calibration():
    matrices = {}
    for line in (SEQ / 'calib.txt').read_text().splitlines():
        key, values = line.split(':', 1)
        matrices[key] = np.fromstring(values, sep=' ').reshape(3, 4)
    p0, p1 = matrices['P0'], matrices['P1']
    K = p0[:, :3].copy()
    assert np.allclose(p0[:, 3], 0) and np.allclose(K, p1[:, :3])
    baseline = -p1[0, 3] / K[0, 0]
    assert baseline > 0
    return K, baseline, p0, p1


def image(frame, side=0):
    path = SEQ / f'image_{side}' / f'{frame:06d}.png'
    im = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if im is None:
        raise FileNotFoundError(path)
    return im


def initialize():
    cv2.setNumThreads(1)
    cv2.setRNGSeed(CFG['seed'])
    np.random.seed(CFG['seed'])
    FIG.mkdir(parents=True, exist_ok=True)
