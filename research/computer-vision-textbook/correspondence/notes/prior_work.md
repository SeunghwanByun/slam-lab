# Correspondence primary-source research

## Which local measurements are stable enough to describe?

### Takeaway
Detection repeatability, descriptor distinguishability and geometric correctness
are separate quantities. Compare actual SIFT and ORB without attributing toy
Gaussian arrays to library internals.

### Cited Findings
- Chris Harris and Mike Stephens, 1988, A Combined Corner and Edge Detector:
  local intensity-change criterion. [BMVA](https://www.bmva-archive.org.uk/bmvc/1988/avc-88-023.html).
- Jianbo Shi and Carlo Tomasi, 1994, Good Features to Track: tracking-conditioned
  feature selection. [Author institution](https://scholars.duke.edu/publication/802423).
- Edward Rosten and Tom Drummond, 2006, Machine Learning for High-Speed Corner
  Detection. [Author poster](https://www.edwardrosten.com/work/rosten_2006_machine_poster.pdf).
- David G. Lowe, 2004, Distinctive Image Features from Scale-Invariant Keypoints.
  [Author paper](https://www.cs.ubc.ca/~lowe/papers/ijcv04.pdf).
- Relja Arandjelovic and Andrew Zisserman, 2012, Three Things Everyone Should
  Know to Improve Object Retrieval. [Author paper](https://www.robots.ox.ac.uk/~vgg/publications/2012/Arandjelovic12/arandjelovic12.pdf).
- SIFT parameters and output: [OpenCV](https://docs.opencv.org/4.13.0/d7/d60/classcv_1_1SIFT.html).

### Inferences
Same-image synthetic warps isolate geometric changes but omit real parallax,
sensor noise differences and disocclusion. They are suitable for teaching only.

### Gaps
No broad detector ranking, patent or legal assertion, nor production timing claim.

## How should correspondence and registration expose uncertainty?

### Takeaway
Nearest-neighbor ratios, transport assignments and RANSAC inliers represent
different constraints; none is a calibrated probability by default.

### Cited Findings
- Marius Muja and David G. Lowe, 2009, Fast Approximate Nearest Neighbors with
  Automatic Algorithm Configuration. [Publisher](https://www.scitepress.org/PublishedPapers/2009/17878/pdf/index.html).
- Daniel DeTone, Tomasz Malisiewicz, Andrew Rabinovich, 2018, SuperPoint:
  Self-Supervised Interest Point Detection and Description; preprint 2017.
  [Paper](https://arxiv.org/abs/1712.07629).
- Paul-Edouard Sarlin, Daniel DeTone, Tomasz Malisiewicz, Andrew Rabinovich,
  2020, SuperGlue: Learning Feature Matching with Graph Neural Networks;
  preprint 2019. [Paper](https://arxiv.org/abs/1911.11763).
- Philipp Lindenberger, Paul-Edouard Sarlin, Marc Pollefeys, 2023, LightGlue:
  Local Feature Matching at Light Speed. [Paper](https://arxiv.org/abs/2306.13643).
- Martin A. Fischler and Robert C. Bolles, 1981, Random Sample Consensus:
  A Paradigm for Model Fitting with Applications to Image Analysis and
  Automated Cartography. [Original paper](https://www.cs.cmu.edu/~motionplanning/papers/sbp_papers/f/p381-fischler.pdf).
- Simon Baker and Iain Matthews, 2004, Lucas-Kanade 20 Years On: A Unifying
  Framework. [Author institution](https://publications.ri.cmu.edu/storage/publications/pub_files/pub3/baker_simon_2004_1/baker_simon_2004_1.pdf).
- Georgios D. Evangelidis and Emmanouil Z. Psarakis, 2008, Parametric Image
  Alignment Using Enhanced Correlation Coefficient Maximization, TPAMI,
  DOI 10.1109/TPAMI.2008.113. [Authors' full paper](https://www.researchgate.net/profile/Emmanouil-Psarakis/publication/23171525_Parametric_Image_Alignment_Using_Enhanced_Correlation_Coefficient_Maximization/links/09e41512d0d8ea67c8000000/Parametric-Image-Alignment-Using-Enhanced-Correlation-Coefficient-Maximization.pdf).

### Inferences
Classical methods are immediately executable. Neural architecture descriptions
and small transport examples are feasible, but pretrained quality is unmeasured.

### Gaps
CVF HTML returned 403; arXiv author copies and full-text HTML were verified
instead. No neural inference, learned confidence calibration or runtime comparison.

## What does apparent motion identify, and what does it not?

### Takeaway
Flow is a pixel displacement field; object tracking maintains box identities.
Neither alone is a metric 3D velocity estimator.

### Cited Findings
- Bruce D. Lucas and Takeo Kanade, 1981, An Iterative Image Registration
  Technique with an Application to Stereo Vision. [IJCAI](https://ijcai.org/proceedings/1981/127).
- Berthold K. P. Horn and Brian G. Schunck, 1981, Determining Optical Flow.
  [Publisher](https://doi.org/10.1016/0004-3702(81)90024-2).
- Gunnar Farneback, 2003, Two-Frame Motion Estimation Based on Polynomial
  Expansion. [Author institution](https://www.ida.liu.se/ext/WITAS-ev/Computer_Vision_Technologies/Papers/scia03_farneback.pdf).
- Zachary Teed and Jia Deng, 2020, RAFT: Recurrent All-Pairs Field Transforms
  for Optical Flow. [Paper](https://arxiv.org/abs/2003.12039).
- Alex Bewley, Zongyuan Ge, Lionel Ott, Fabio Ramos, Ben Upcroft, 2016,
  Simple Online and Realtime Tracking. [Paper](https://arxiv.org/abs/1602.00763).
- Nicolai Wojke, Alex Bewley, Dietrich Paulus, 2017, Simple Online and Realtime
  Tracking with a Deep Association Metric. [Paper](https://arxiv.org/abs/1703.07402).
- Yifu Zhang, Peize Sun, Yi Jiang, Dongdong Yu, Fucheng Weng, Zehuan Yuan,
  Ping Luo, Wenyu Liu, Xinggang Wang, 2022, ByteTrack: Multi-Object Tracking
  by Associating Every Detection Box; preprint 2021.
  [Paper](https://arxiv.org/abs/2110.06864).

### Inferences
Use observed temporal overlays for real imagery, exact warp GT for flow error,
and synthetic matrices for Hungarian/Kalman logic. Do not call the latter MOT.

### Gaps
No physical velocity, occlusion ground truth or ID-switch benchmark is available.

### Applicability table
| Method | Required data | Available | Extraction | Runtime status | Decision |
|---|---|---|---|---|---|
| SIFT/ORB/BF/FLANN | uint8 image pair | yes | OpenCV | locally measured | execute |
| H/ECC/LK/Farneback | pixels and point pairs | yes | OpenCV | locally measured | execute |
| DLT/Sinkhorn toy | small numeric arrays | generated | NumPy/SciPy | teaching only | execute |
| SuperPoint/Glue/LightGlue | weights and image contract | no weights | not run | unmeasured | literature only |
| RAFT | weights, RGB contract | grayscale only | not run | unmeasured | literature only |
| SORT/DeepSORT/ByteTrack benchmark | detections and identity GT | no | synthetic cost example | not benchmarked | explain only |
