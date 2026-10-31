# visual-slam-lab

## Offline Debug Playback

```bash
.venv/bin/python -m src.viz.export_playback --sequence 00 --max-frames 200
```

Open `outputs/playback.html` in a browser. No server or internet is required.
The raw image, ORB features, previous-to-current match displacements and GT/VO
trajectory share a frame index. Playback supports pause, stepping, seeking and
speed selection. Space toggles playback; arrow keys step frames.

The exporter computes VO before playback; playback is not a live computation
benchmark. Green matches pass pose recovery; rejected matches can be shown in
red. Feature coordinates are 2D, not a reconstructed 3D map. VO uses unit-length
translation while GT is metric; no ground-truth scale is injected. Failed pose
estimates hold the last position and are marked in the status display.
The generated HTML embeds image data and grows with the requested frame count.

Monocular visual odometry, visual SLAM, and LiDAR SLAM study repo.

## VO / LO Comparison

The research branch includes ORB monocular VO, KISS-ICP LiDAR odometry,
synchronized playback and a GT-based revisit-candidate viewer. Loop detection
and pose-graph optimization are **not** implemented.

```bash
uv venv --python 3.11 research/20261031_vo-lo-study/.venv
uv pip install --python research/20261031_vo-lo-study/.venv/bin/python -r research/20261031_vo-lo-study/configs/requirements-lock.txt
research/20261031_vo-lo-study/.venv/bin/python research/20261031_vo-lo-study/src/run.py
```

Open `research/20261031_vo-lo-study/artifacts/playback/index.html` directly in
a browser. It contains camera images, projected LiDAR, scan BEV and GT/VO/LO
trajectories. Its revisit link opens whole-sequence GT candidates; the VO/LO
estimates cover only the configured first 200 frames.

To rebuild only the viewers from existing estimates, pass `--stage playback`.
VSCode configurations `KITTI: VO + LO research and playback` and
`KITTI: Refresh VO + LO playback` use the research virtual environment.

Reports: [VO/LO study PDF](research/20261031_vo-lo-study/report.pdf),
[revisit readiness PDF](research/20261031_loop-readiness/report.pdf).
Generated artifacts and datasets stay local; sources, figures and reports are
versioned. The research and production VO pipelines remain separate.

The first milestone is a small KITTI odometry pipeline:

1. Load calibrated image sequences.
2. Detect ORB features.
3. Match descriptors between consecutive frames.
4. Estimate an essential matrix.
5. Recover relative camera pose.
6. Accumulate and plot a trajectory.

This repo intentionally starts with Python and OpenCV so the geometry is easy to inspect before moving pieces to C++.

## Study Direction

This repo is intentionally top-down:

```text
SLAM system goal
-> dataset and debugging loop
-> visual odometry front-end
-> mapping and optimization
-> LiDAR odometry / SLAM
```

The current implementation is a first visual odometry baseline, not full SLAM yet.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

VSCode should use:

```text
.venv/bin/python
```

The repo includes launch configs under `.vscode/launch.json`.

## Data

Download KITTI odometry data from:

```text
https://www.cvlibs.net/datasets/kitti/eval_odometry.php
```

For this repo, use the odometry benchmark files:

```text
data_odometry_gray.zip       visual odometry / visual SLAM study
data_odometry_calib.zip      calibration files
data_odometry_poses.zip      ground truth trajectory for sequences 00-10
data_odometry_velodyne.zip   LiDAR SLAM study
```

You can download with:

```bash
python scripts/download_kitti_odometry.py --parts gray poses
```

For the cleanest KITTI odometry layout, include calibration too:

```bash
python scripts/download_kitti_odometry.py --parts gray calib poses
```

For LiDAR SLAM later:

```bash
python scripts/download_kitti_odometry.py --parts velodyne
```

The Velodyne file is large. Download it only when you are ready to study LiDAR.

After extraction, the expected layout is:

```text
data/kitti/dataset/
```

Expected layout:

```text
data/kitti/dataset/
  sequences/
    00/
      image_0/
      calib.txt
  poses/
    00.txt
```

Check the local dataset layout with:

```bash
python scripts/check_kitti_dataset.py --sequence 00
```

## First Run

```bash
python -m src.vo.run_kitti --sequence 00 --max-frames 200
```

For debugging, start smaller:

```bash
python -m src.vo.run_kitti --sequence 00 --max-frames 50
```

## LiDAR First Check

After downloading and extracting `data_odometry_velodyne.zip`, verify one scan:

```bash
python scripts/inspect_kitti_lidar.py --sequence 00 --frame 0
```

This writes a simple top-down point cloud image under `outputs/`.
