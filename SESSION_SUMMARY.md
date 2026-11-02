# Session Summary

## Current Entry Point

Repository renamed to `SeunghwanByun/slam-lab` on 2026-11-02.
The current, versioned study document is `docs/report.md` / `docs/report.pdf`.
The local folder was renamed to `/Users/youth/Project/slam-lab` on 2026-11-03.
Virtual-environment launchers were updated; VSCode uses workspace-relative paths.
Sections below are historical snapshots, not the current implementation or
dataset inventory. Their old paths are retained as historical provenance.

## Progress Through 2026-10-25

This section supersedes the initial setup goals below. Explain in Korean and
teach top-down: inspect system outputs before introducing component math.

- Created a Python 3.11 `.venv` with uv and installed NumPy, OpenCV and Matplotlib.
- Added VSCode interpreter and debug configurations for VO, dataset checks,
  LiDAR inspection and playback export.
- Added KITTI archive download, dataset validation and LiDAR scan inspection
  scripts. The downloader supports Range requests but does not yet validate a
  resumed response's status or Content-Range; use caution with interrupted files.
- Consolidated grayscale sequences 00-21, calibration, timestamps and poses into
  `data/kitti/dataset`. Image directories are real directories, not symlinks.
  Removed duplicate Downloads folders and original ZIPs at the user's request.
  See `LOCAL_DATA.md` for the local inventory. LiDAR data is not installed.
- Ran sequence 00 for 200 frames and generated the trajectory plot.
- Fixed pose inlier counting using `np.count_nonzero` rather than assuming
  the OpenCV mask always contains 255 for accepted points.
- Added offline HTML playback showing synchronized raw images, ORB keypoints,
  accepted/rejected match displacement lines, and GT/estimated trajectories.
  Controls include playback, pause, stepping, seeking and speed selection.
- Verified playback in Chrome via Playwright: playback, seeking, frame stepping,
  nonblank canvases, desktop/mobile screenshots and no horizontal overflow.

Generate playback with:

```bash
.venv/bin/python -m src.viz.export_playback --sequence 00 --max-frames 200
```

Open `outputs/playback.html` directly in a browser. This file embeds the images
and precomputed estimates; it is not a live VO computation benchmark.

Current algorithm: ORB + cross-checked Hamming matching + essential matrix RANSAC
+ relative pose recovery + pose accumulation. This is a monocular VO baseline,
not ORB-SLAM. It assigns unit translation per accepted frame; GT is metric.
Consequently, the overlaid paths are not a metric accuracy evaluation and can
diverge due to varying vehicle speed as well as estimation error. Playback holds
the last position when pose recovery fails or has fewer than five inliers.
There is no 3D map, bundle adjustment, loop closure or LiDAR odometry yet.

Next proposed step: stereo triangulation using image_0/image_1 and temporal
PnP + RANSAC to estimate metric motion, then compare against GT in playback.
Stereo VO has been discussed but not implemented.

Data, virtual environments, caches and generated outputs are excluded from Git.

This file summarizes the prior Codex conversation that led to creating this repo, so a new session can resume with the right context.

## Original Hardware Issue

The starting project was:

```text
/Users/youth/Project/depthcam-core
```

The goal was to run the `Youth` binary with an Orbbec/Astra RGB-D camera on macOS.

The first failure was macOS Gatekeeper blocking the downloaded Orbbec SDK dylib:

```text
Library not loaded: @rpath/libOrbbecSDK.2.dylib
code signature ... not valid for use in process: library load disallowed by system policy
```

Inspection showed:

```text
libOrbbecSDK.2.8.6.dylib had com.apple.quarantine
codesign reported an ad-hoc/linker-signed dylib
```

The quarantine attribute was removed from the extracted SDK:

```bash
xattr -dr com.apple.quarantine /Users/youth/Downloads/OrbbecSDK_v2.8.6_202604272252_6399409_macOS
```

After that, `./Youth` loaded `libOrbbecSDK` successfully.

## Camera Detection Result

After the dylib issue was fixed, the app reached sensor initialization but failed with:

```text
Orbbec SDK v2 initialize failed: No device found
```

macOS did see the camera at the USB level:

```text
USB Product Name = ASTRA
USB Vendor Name = ORBBEC
idVendor = 11205 / 0x2bc5
idProduct = 1025 / 0x0401
iSerialNumber = 0
```

The Orbbec SDK v2 official binary also failed:

```bash
/Users/youth/Downloads/OrbbecSDK_v2.8.6_202604272252_6399409_macOS/bin/ob_benchmark
```

Output:

```text
No devices found.
```

Conclusion: the USB connection itself worked, but this older `ASTRA` device is likely a legacy OpenNI/Astra SDK camera and is not supported by Orbbec SDK v2 on macOS.

## Platform Conclusion

The existing camera could not realistically be used natively on macOS through Orbbec SDK v2.

Likely viable options:

1. Run the legacy Astra/OpenNI path on Ubuntu.
2. Try Ubuntu VM USB passthrough on the Mac.
3. Use Docker only inside a Linux/Ubuntu environment where `/dev/bus/usb` can be passed through.

macOS Docker Desktop alone was considered a poor fit because containers run inside a Linux VM and do not get direct access to macOS USB devices like Linux does.

## Pivot To Visual SLAM Study

Because the physical camera path was blocked, the discussion pivoted to studying SLAM without the Orbbec camera.

The user has an iPhone 13 mini:

```text
iPhone 13 mini
No LiDAR
```

Conclusions:

1. LiDAR/RGB-D SLAM is not available from that iPhone.
2. Monocular visual odometry / visual SLAM is still possible.
3. ARKit can be used as a reference trajectory/logger, while the user implements the core monocular VO/SLAM steps manually.

Recommended learning path:

```text
RGB frames
-> feature detection
-> descriptor matching / tracking
-> essential matrix
-> recover relative pose R, t
-> accumulate trajectory
-> compare against reference / ground truth
-> later add triangulation, keyframes, local BA, loop closure
```

Recommended datasets:

1. KITTI Odometry
2. TUM MonoVO
3. EuRoC MAV
4. ADVIO
5. TUM RGB-D for RGB-D comparison only

KITTI was chosen as the first practical starting point because it is approachable and has ground truth for visual odometry experiments.

## New Repo Created

This repo was created for that pivot:

```text
/Users/youth/Project/visual-slam-lab
```

Recommended public GitHub repo name:

```text
visual-slam-lab
```

Initial local commit:

```text
51be2ae chore: scaffold visual slam lab
```

The repo was later connected to:

```text
origin/main
```

## Initial Repo Contents

The initial structure is Python + OpenCV:

```text
README.md
requirements.txt
src/
  datasets/
    kitti.py
  vo/
    features.py
    two_view.py
    run_kitti.py
  viz/
    plot_trajectory.py
```

The first milestone is:

```text
KITTI image loading
-> ORB features
-> BF descriptor matching
-> essential matrix estimation
-> recoverPose
-> trajectory accumulation
-> trajectory plot
```

Run command documented in `README.md`:

```bash
python -m src.vo.run_kitti --sequence 00 --max-frames 200
```

Expected KITTI layout:

```text
data/kitti/dataset/
  sequences/
    00/
      image_0/
      calib.txt
  poses/
    00.txt
```

## Suggested Next Session Goals

Good next steps for a new session:

1. Verify this repo still has a clean git state.
2. Set up the Python virtual environment.
3. Download or place KITTI Odometry sequence `00`.
4. Run the current baseline VO script.
5. Inspect the resulting trajectory plot.
6. Improve the baseline by adding scale handling from KITTI ground truth or stereo.
7. Add notebooks or tests for two-view geometry.
8. Later, add iPhone/ARKit logging as a separate data source.

## Important Technical Notes

The current monocular pipeline estimates translation direction but not metric scale. KITTI ground truth can be used temporarily to study trajectory shape and scale correction, but the core monocular ambiguity should remain explicit in explanations and code comments.

The iPhone 13 mini path should be treated as a later phase:

```text
iPhone ARKit logger
-> RGB frames + timestamps + intrinsics + ARKit pose
-> local VO implementation
-> compare custom VO against ARKit trajectory
```

