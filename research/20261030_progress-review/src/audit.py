"""Recompute descriptive statistics from existing artifacts, not new VO estimates."""
import base64
import csv
import hashlib
import json
import platform
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    study = Path(__file__).resolve().parents[1]
    repo = study.parents[1]
    config = json.loads((study / 'configs/audit.json').read_text())
    artifacts, figures = study / 'artifacts', study / 'figures'
    for name in ('inventory', 'playback', 'analysis', 'provenance'):
        (artifacts / name).mkdir(parents=True, exist_ok=True)
    figures.mkdir(exist_ok=True)
    def save(relative, value):
        (artifacts / relative).write_text(json.dumps(value, indent=2), encoding='utf-8')
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=repo, text=True).strip()
    source = repo / config['playback']
    payload, _ = json.JSONDecoder().raw_decode(source.read_text().split('const data=', 1)[1])
    frames = payload['frames']
    assert len(frames) == config['expected_frames'] and payload['sequence'] == config['sequence']
    save('provenance/environment.json', dict(
        head=git('rev-parse', 'HEAD'), feature_commit=config['feature_commit'],
        status=git('status', '--short', '--branch'), python=platform.python_version(),
        platform=platform.platform(), cv2=cv2.__version__, numpy=np.__version__,
        matplotlib=matplotlib.__version__, playback_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source=str(source.relative_to(repo)),
        original_export_commit_embedded=False))
    # Preserve the code revision referenced by the historical playback workflow.
    for path in ('src/viz/export_playback.py', 'src/viz/playback.html',
                 'src/vo/two_view.py', 'scripts/download_kitti_odometry.py'):
        content = git('show', f'{config["feature_commit"]}:{path}')
        (artifacts / 'provenance' / Path(path).name).write_text(content + '\n')
    dataset = repo / 'data/kitti/dataset'
    inventory = []
    for seq in sorted((dataset / 'sequences').iterdir()):
        counts = {name: len(list((seq / name).glob(pattern))) for name, pattern in
                  [('image_0', '*.png'), ('image_1', '*.png'), ('velodyne', '*.bin')]}
        pose = dataset / 'poses' / f'{seq.name}.txt'
        counts.update(sequence=seq.name, gt_rows=len(pose.read_text().splitlines()) if pose.exists() else 0)
        inventory.append(counts)
    save('inventory/sequences.json', inventory)
    oxts = repo / 'data/kitti/raw/2011_10_03' / config['raw_drive'] / 'oxts'
    paths = sorted((oxts / 'data').glob('*.txt'))
    times = np.array((oxts / 'timestamps.txt').read_text().splitlines(), dtype='datetime64[ns]')
    samples = np.stack([np.loadtxt(path) for path in paths])
    assert samples.shape == (len(times), 30) and np.isfinite(samples).all()
    dt = np.diff(times).astype('timedelta64[ns]').astype(float) / 1e9
    save('inventory/imu.json', dict(rows=len(paths), columns=30, finite=True,
        dt_median_s=float(np.median(dt)), dt_min_s=float(dt.min()), dt_max_s=float(dt.max()),
        nonpositive_intervals=int((dt <= 0).sum()), alignment_to_odometry='not verified'))
    with (artifacts / 'inventory/imu_intervals.csv').open('w') as f:
        writer = csv.writer(f)
        writer.writerow(['from_index', 'to_index', 'from_timestamp', 'to_timestamp', 'dt_s'])
        writer.writerows((i, i+1, str(times[i]), str(times[i+1]), value) for i, value in enumerate(dt))
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(dt, linewidth=0.5)
    ax.axhline(0, color='red', linewidth=0.7)
    ax.set(xlabel='OXTS interval index', ylabel='Delta time (s)', title='Raw timestamp intervals in filename order')
    fig.tight_layout(); fig.savefig(figures / 'imu_intervals.png', dpi=150); plt.close(fig)
    rows = []
    for i, frame in enumerate(frames):
        points = np.array(frame['points'])
        tracks = frame['tracks']
        assert frame['inliers'] == sum(bool(track[4]) for track in tracks)
        cells = set((min(config['grid_columns'] - 1, int(x / payload['width'] * config['grid_columns'])),
                     min(config['grid_rows'] - 1, int(y / payload['height'] * config['grid_rows'])))
                    for x, y in points)
        rows.append(dict(frame=i, time=frame['time'], features=len(points), matches=len(tracks),
                         inliers=frame['inliers'], ratio=frame['inliers']/len(tracks) if tracks else 0,
                         occupied_cells=len(cells), status=frame['status']))
    with (artifacts / 'playback/frames.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    vo = np.array([f['vo'] for f in frames]); gt = np.array([f['gt'] for f in frames])
    timestamps = np.array([f['time'] for f in frames])
    assert np.isfinite(vo).all() and gt.shape == vo.shape and (np.diff(timestamps) > 0).all()
    np.savez(artifacts / 'playback/positions.npz', vo=vo, gt=gt, time=timestamps)
    steps = np.linalg.norm(np.diff(vo, axis=0), axis=1)
    gt_steps = np.linalg.norm(np.diff(gt, axis=0), axis=1)
    ratios = np.array([r['ratio'] for r in rows[1:]])
    worst = int(np.argmin(ratios)) + 1
    metrics = dict(frames=len(frames), transitions=len(frames)-1,
        statuses=dict(Counter(f['status'] for f in frames)),
        features_min=min(r['features'] for r in rows), features_max=max(r['features'] for r in rows),
        inlier_ratio_min=float(ratios.min()), inlier_ratio_median=float(np.median(ratios)),
        inlier_ratio_max=float(ratios.max()), lowest_inlier_frame=worst,
        gt_path_m=float(gt_steps.sum()), vo_path_arbitrary_units=float(steps.sum()),
        vo_step_min=float(steps.min()), vo_step_max=float(steps.max()),
        gt_step_min_m=float(gt_steps.min()), gt_step_max_m=float(gt_steps.max()),
        occupied_cells_min=min(r['occupied_cells'] for r in rows), grid_cells=32,
        accuracy_evaluation='not performed; scales differ; no rotation history in playback')
    save('analysis/metrics.json', metrics)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(gt[:, 0], gt[:, 2], label='GT (m)', color='darkorange')
    axes[0].plot(vo[:, 0], vo[:, 2], label='VO (arbitrary units)', color='teal')
    axes[0].set(title='Unaligned paths: units differ', xlabel='X', ylabel='Z'); axes[0].axis('equal'); axes[0].legend()
    axes[1].plot(gt_steps, label='GT step (m)', color='darkorange')
    axes[1].plot(steps, label='VO step (arbitrary units)', color='teal')
    axes[1].set(title='Per-frame displacement', xlabel='Transition', ylabel='Step length'); axes[1].legend()
    fig.tight_layout(); fig.savefig(figures / 'trajectory_steps.png', dpi=150); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3))
    axes[0].plot(np.arange(1, len(frames)), ratios); axes[0].set(xlabel='Frame', ylabel='Pose inlier fraction', ylim=(0,1))
    axes[1].hist(ratios, bins=15); axes[1].set(xlabel='Pose inlier fraction', ylabel='Frames')
    fig.tight_layout(); fig.savefig(figures / 'inliers.png', dpi=150); plt.close(fig)
    frame = frames[worst]
    image = cv2.imdecode(np.frombuffer(base64.b64decode(frame['image']), np.uint8), cv2.IMREAD_GRAYSCALE)
    overlay = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    for x,y,u,v,accepted in frame['tracks']:
        cv2.line(overlay, (round(x),round(y)), (round(u),round(v)), (30,190,160) if accepted else (245,90,100), 1)
    fig, axes = plt.subplots(2, 1, figsize=(12, 7))
    axes[0].imshow(image, cmap='gray'); axes[0].set_title(f'Frame {worst}: raw image')
    axes[1].imshow(overlay); axes[1].set_title(f'Pose inlier fraction {ratios[worst-1]:.3f}; red = rejected, not ground-truth mismatch labels')
    for ax in axes: ax.axis('off')
    fig.tight_layout(); fig.savefig(figures / 'lowest_inliers.png', dpi=140); plt.close(fig)
    for name in ('playback-desktop.png', 'playback-mobile.png'):
        if (repo / 'outputs' / name).exists(): shutil.copy2(repo / 'outputs' / name, figures / name)
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()
