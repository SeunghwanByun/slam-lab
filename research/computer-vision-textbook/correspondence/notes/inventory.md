# Correspondence resource inventory

## Problem and measurable contract

D9-D12 publication-ready Korean teaching chapters deepen detection, correspondence,
alignment and motion. They do not modify production algorithms or canonical report.
Known synthetic warps of real KITTI pixels provide exact coordinate GT; temporal
KITTI frames provide qualitative observations only. No true flow/MOT labels exist
in the selected input. No learned-model benchmark or GPU training is performed.

[Assumption] Educational success: at least 13 legible original figures, numeric
worked examples covered by >=10 tests, persisted intermediate arrays, one failure
or controlled ablation per chapter, and all reported scores generated locally.
No algorithm leaderboard target is imposed on one image.

## Available resources

- Repository HEAD when work began: 75f7140d0dec421971c9b13d088e1967ebe124d5.
- KITTI odometry 00 image_0/000000.png and 000001.png: grayscale uint8,
  original shape 376 x 1241. Resize width 800 with INTER_AREA, retain realized
  x/y scale and original data SHA256. image_1 exists but is not needed here.
- Python: research/20261031_vo-lo-study/.venv/bin/python.
- Checked versions: OpenCV 5.0.0, NumPy 2.4.6, SciPy 1.17.1,
  Matplotlib 3.11.1. cv2.SIFT_create is available.
- Prior teaching code: research/20261031_vo-lo-study/src/orb_stages.py:5 main,
  :33 random BRIEF toy, :50 known-warp experiment. Read only; its random BRIEF
  should not be called actual ORB internal state.
- docs/report.md:887 Harris overview, :2194 LK/PnP chapter,
  :3629 learned matching overview. This assignment develops missing algebra,
  exact intermediate numerical examples and comparisons rather than copying.
- No learned weights, KITTI flow annotations, detector labels or MOT identities
  were loaded. A synthetic matching or assignment example cannot establish
  performance of SuperGlue, RAFT, SORT, DeepSORT or ByteTrack.

## Quick-win decision

Use OpenCV SIFT/ORB, BF/FLANN, findHomography, ECC, PyrLK and Farneback,
and SciPy cKDTree/linear_sum_assignment. A new production algorithm is unnecessary.
Small DLT, Sinkhorn and gradient/Hessian arrays are educational toys only.
Single-image ablations are mechanism tests, not dataset generalization estimates.
All writes remain under this assigned directory. Branch changes, fetch operations,
canonical edits and commits are owned by the coordinator, not this researcher.
