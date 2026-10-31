import csv
import json
from pathlib import Path
import numpy as np
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[1]
CFG = json.loads((STUDY / 'configs/experiment.json').read_text())
DATA = ROOT / 'data/kitti/dataset'
SEQ = DATA / 'sequences' / CFG['sequence']
ART = STUDY / 'artifacts'
FIG = STUDY / 'figures'
FIG.mkdir(exist_ok=True)
cv2.setRNGSeed(CFG['seed'])
cv2.setNumThreads(1)


def directory(name):
    out = ART / name
    out.mkdir(parents=True, exist_ok=True)
    return out


def image(i):
    out = cv2.imread(str(SEQ / 'image_0' / f'{i:06d}.png'), 0)
    if out is None: raise FileNotFoundError(i)
    return out


def calibration():
    values = {k: np.fromstring(v, sep=' ').reshape(3, 4)
              for k, v in (line.split(':', 1) for line in (SEQ / 'calib.txt').read_text().splitlines())}
    tr = np.eye(4); tr[:3] = values['Tr']
    return values['P0'][:, :3], tr


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False))


def save_csv(path, rows):
    with path.open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def transform(points, pose):
    return points @ pose[:3, :3].T + pose[:3, 3]


def finish(fig, name):
    fig.tight_layout(); fig.savefig(FIG / name, dpi=150); plt.close(fig)


def check_poses(poses):
    assert np.isfinite(poses).all()
    assert np.allclose(poses[:,3,:], [0,0,0,1])
    assert np.allclose(np.linalg.det(poses[:,:3,:3]), 1, atol=1e-4)
