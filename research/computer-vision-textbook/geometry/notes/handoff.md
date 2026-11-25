# Geometry handoff

## Integration

- SOURCE: `research/computer-vision-textbook/geometry/notes/chapters.md`; D13–D16 in order, 53 H3 sections, 57 explicit lowercase anchors, 18 solved exercises. Roughly 114KB / 1948 lines. No artificial line filler or font changes.
- Insert manuscript into canonical report without rewriting its figure paths: all 12 images already use `../research/computer-vision-textbook/geometry/figures/...` relative to docs.
- D13 has figures numbered 1,2,3 in reading order but filenames are 01,03,02; this is intentional ordering of discussion, not missing assets.
- Canonical docs/report.md/pdf, tools, production modules and commits were not touched by this worker. Render/page-count QA belongs to integration; no standalone final PDF created here.
- The 12 PNG files are 7in wide at 200dpi (1400px); height varies by plot. Captions describe units, synthetic/real source, interpretation and limits.

## Files And Reproduction

- Planning: `notes/inventory.md`, `notes/prior_work.md`, `notes/architecture.md`.
- Configuration: `configs/experiment.json` (seed 13141516).
- Code: `src/experiment.py`, `src/test_geometry.py`, `src/audit.py`.
- Per-module outputs: `artifacts/{projective,multiview,stereo,sfm}/{arrays.npz,metrics.json}`.
- Provenance: `artifacts/manifest.json`, `artifacts/qa/audit.json`, `artifacts/qa/tests.txt`.
- Visual QA contact sheet: `artifacts/qa/contact.png` (not a report figure).
- Artifacts directory is ignored by existing repository rules; PNG figures remain available for report integration.

```text
research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/geometry/src/test_geometry.py
research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/geometry/src/experiment.py
research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/geometry/src/audit.py
```

Latest experiment runtime 1.8449 seconds on macOS arm64; not a benchmark. Python3.11.14/NumPy2.4.6/SciPy1.17.1/OpenCV5.0.0/Matplotlib3.11.1. Manifest captures source hashes and commit 75f7140d0dec421971c9b13d088e1967ebe124d5; stereo metrics record input hashes. QA manifest records figure/NPZ hashes.

## Verified Results And Boundaries

- 22/22 numeric tests pass, including exactly8-point full SVD, Zhang constraints, plane homography, SAD/SSD, ZNCC, SGM recurrence, subpixel, depth uncertainty, coupled Schur, scalar rotation averaging.
- Calibration tilted/frontoparallel RMS:0.2084/0.2034px, fx691.1972/5838.1412px vs true700px. Low residual does not ensure identifiable calibration.
- Eight-point raw/normalized true-correspondence Sampson median:7.4132/0.0398px; design singular-value ratio1.6039e7/1223.8540. One synthetic seed, not a benchmark claim.
- Baseline0.02m: median depth error8.2958m/reprojection0.2370px. Baseline0.54m:0.2981m/0.2675px. Pixel fit conceals weak depth.
- Toy two-path P2=0/4/40 MAE:2.0125/1.05625/0.70625px. Clearly distinguished from actual OpenCV SGBM internals.
- KITTI00/000000 real grayscale pair: positive-disparity fraction0.7858496, no GT accuracy claim.
- Coupled Schur full/reduced solution[1/6,5/6,5/6], norm difference2.498e-16. Pose-only example[0.375,0.625] is explicitly a different conditional solve.
- False-loop chain RMSE:odometry0.0979m,L2 3.9681m,Huber0.7751m. Robust loss helps but does not replace loop verification.
- Figures were inspected as full-size selected plots and 12-image contact sheet; corrected overlapping inverse-depth ticks and log-zero rendering.
- Not run: full5point benchmark, optimal Hartley–Sturm solver, fullPatchMatch/MVS, incremental/globalSfM, productionSLAM. Algorithms are explained but not falsely reported as experiments.

Primary citations and access caveats are in `notes/prior_work.md`: Zhang2000; Hartley1995(ICCV original, distinct from1997PAMI); Hartley–Sturm1997; Nistér2004; Zabih–Woodfill1994; Hirschmüller2008; Bleyer–Rhemann–Rother2011; Schönberger–Frahm2016; Triggs etal2000; Chatterjee–Govindu2013; official OpenCV docs. Manuscript uses direct inline primary links. No external performance scores or copied figures.
