# Phase 4: 조사와 선택

검증된 자료:
- Rublee, Rabaud, Konolige, Bradski, ORB: An efficient alternative to SIFT or SURF, ICCV 2011.
  https://docs.opencv.org/4.13.0/d1/d89/tutorial_py_orb.html
  FAST/Harris, pyramid, intensity centroid, steered BRIEF/rBRIEF로 빠른 binary 관측을 만든다.
- Vizzo, Guadagnino, Mersch, Wiesmann, Behley, Stachniss, KISS-ICP, RA-L 2023.
  https://www.ipb.uni-bonn.de/pdfs/vizzo2023ral.pdf
  https://github.com/PRBonn/kiss-icp
  point-to-point 정합에 voxel 표본화, robust kernel, adaptive threshold, motion prediction을 조합한다.
- DeTone, Malisiewicz, Rabinovich, SuperPoint, CVPR workshop 2018.
  https://arxiv.org/abs/1712.07629
  homographic adaptation으로 keypoint 반복성을 학습하고 descriptor를 함께 계산한다.
- Lindenberger, Sarlin, Pollefeys, LightGlue, ICCV 2023.
  https://arxiv.org/abs/2306.13643
  descriptor 최근접 비교를 넘어 문맥 기반 대응을 학습하며 쉬운 쌍의 계산을 줄인다.

| 방법 | 필요/보유 | 추가 산출 | 비용/결합 | 선택 |
|---|---|---|---|---|
| ORB/BF/E | grayscale/K 있음 | intermediate arrays | CPU, 낮음 | baseline 실행 |
| ratio gate | descriptors 있음 | KNN 거리 | 낮음 | quick-win ablation |
| KISS-ICP | XYZ 있음 | local map, scan pose | C++ backend, 중간 | LO 실행 |
| SuperPoint/LightGlue | 영상 있음, weights 없음 | learned features/matches | 모델/성능 검증 필요 | 한계->후속 논문 설명, 이번 실행 안 함 |
| Stereo/PnP | 우측 영상 있음 | depth/3D-2D tracks | 중간 | 다음 연구 제안 |
| VIO/LIO | IMU 있음, 시간 정렬 미완료 | bias/noise/preintegration | 높음 | 이번 적용 안 함 |

ORB 논문 내부의 모든 최적화와 learned test selection을 그대로 다시 학습하지 않는다.
교육용 단계 재구현(FAST/Harris/centroid/BRIEF)과 실제 OpenCV ORB 결과를 명확히 분리한다.
LO 핵심은 검증된 공식 KISS-ICP를 사용하고 단계별 호출을 계측한다. 새 알고리즘을 발명했다고 주장하지 않는다.
