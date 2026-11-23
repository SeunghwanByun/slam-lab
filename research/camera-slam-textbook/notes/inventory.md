# 문제와 리소스 (중간 연구 노트)

## 문제 / 성공 기준
카메라 관측에서 깊이와 이동을 얻는 과정에서 무엇이 관측 가능하고 무엇이 실패하는가?
KITTI 정류 흑백 스테레오에서 검증된 OpenCV 추정기를 연결하는 교육 실험이다.
운영 SLAM, 루프 클로징, 전역 지도 구축, 성능 개선 보장, 100쪽 보고서 작성은 이 작업의 범위 밖이다.
이 자료와 원본 그림은 별도 작성자가 기존 보고서에 통합한다. docs/report.md/pdf와 tools는 수정하지 않는다.

- 고정 설정으로 seq00 [0,200), [400,500) 두 비중첩 구간, 200/100 자세와 199/99 상대 이동을 생성한다.
- 실제 스테레오 metric ATE/RPE가 유한하고, 성공/hold 수를 공개한다. 정확도 개선을 통과 조건으로 삼지 않는다.
- 단안은 매 성공 이동의 norm=1인 비미터 궤적이며 Sim(3) GT 적합은 평가 전용이다.
- 20개 이상 독창적 180dpi 이상 그림, 각 그림의 원본 배열과 실제/합성 표기, A4 단일 칼럼 가독성.
- 8개 이상 불변량 테스트: 역변환/합성/투영/삼각측량/GT 격리/척도/정렬/입력 경계.
- 모듈별 JSON/CSV/NPZ, 입력·설정·소스 SHA256, 의존성·seed·명령, 전체 수치 요약.
- ratio/Hamming/y 게이트 및 LK 전후방 검증의 ablation, 실패 사례와 hold 정책을 공개한다.

## 실측 인벤토리
- 기준 HEAD f09b08eba08ae400b8c647c88a99a8b3ec874eb4; feat/camera-slam-textbook 확인.
- data/kitti/dataset/sequences/00/image_0, image_1: 각각 4541 PNG.
- calib.txt P0/P1: fx=fy=718.856 px, cx=607.1928, cy=185.2157 px.
- 우측 tx=-386.1448 px*m. baseline=-P1[0,3]/fx. 이미 정류된 입력이며 raw distortion 계수는 없다.
- data/kitti/dataset/poses/00.txt는 평가에서만 읽는다. IMU/LiDAR/color 미사용.
- Python: research/20261031_vo-lo-study/.venv/bin/python; cv2 5.0.0, numpy 2.4.6, scipy 1.17.1, matplotlib 3.11.1 확인.
- 기존 vo.py:5 run, vo.py:25 findEssentialMat, vo.py:27 recoverPose: 단안 기준선 참고만; import하지 않는다.
- 기존 evaluate.py:9 sim3, evaluate.py:20 metrics: 정렬/평가 참고만; 새 실험에서 독립 테스트한다.
- 기존 코드는 common 전역 설정에 의존하므로 재사용 import 대신 독립 모듈을 둔다.
- GT depth/flow, raw lens distortion, 동적 객체 mask 부재: 깊이·flow 정확도라고 주장하지 않는다.

## Quick-win (실행 전 결정)
새 알고리즘 대신 ORB ratio 0.75 + Hamming 64 + 정류 y 1.5px + 양의 disparity,
LK forward/backward 1px, PnP RANSAC 2px와 LM 보정으로 작은 관측 파이프라인을 검증한다.
같은 프레임에서 cross-check 대 ratio, ratio-only 대 추가 게이트, LK FB on/off를 비교한다.
실제 검증 결과는 experiments.md 및 artifacts/summary.json에 갱신한다.
실패 시 identity relative pose를 저장하며 성공처럼 표시하지 않는다. GT 기반 fallback/scale 금지.

## 확인한 원문 / 선택
- OpenCV Camera Calibration and 3D Reconstruction: https://legacy-docs.opencv.org/4.x/d9/d0c/group__calib3d.html
  E/recoverPose, triangulatePoints, solvePnPRansac 및 LM: 입력 계약을 갖춘 기존 추정기 선택.
- OpenCV optical flow: https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html
  pyramidal Lucas-Kanade는 작은 국소 밝기 변화 가정. 반복 무늬·가림은 FB 검사도 통과할 수 있다.
- KITTI odometry: https://www.cvlibs.net/datasets/kitti/eval_odometry.php
  공식 100..800m 구간 점수가 아니라 짧은 구간 ATE와 1-frame RPE 연구 평가이다.
- SGBM은 dense correspondence 보조 관측; metric PnP는 sparse ORB 삼각측량만 사용한다.
- joint BA는 필수가 아니다. 고정 3D의 pose-only reprojection 최적화를 우선하며 이를 BA로 부르지 않는다.
