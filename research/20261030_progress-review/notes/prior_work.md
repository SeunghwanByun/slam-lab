# 선행연구와 적용성

이번 요청은 회고다. 기존 구현의 배경과 다음 선택지 검토를 위한 제한된 조사이며,
논문 알고리즘을 새로 구현하거나 성능을 재현한 실험은 없다. 출처 확인일: 2026-10-30.

## 확인된 방법

1. **ORB: An efficient alternative to SIFT or SURF**, Ethan Rublee, Vincent Rabaud,
   Kurt Konolige, Gary Bradski, 2011. [OpenCV 공식 설명](https://docs.opencv.org/4.13.0/d1/d89/tutorial_py_orb.html).
   FAST 기반 위치 검출과 방향을 반영한 BRIEF 계열 이진 기술자를 결합한다.
   입력은 영상이며 조명/시점 변화와 반복 패턴에 대한 데이터별 한계는 별도 검증 대상이다.
   현재 ORB 호출은 이 방법을 라이브러리로 사용하며 직접 구현한 것이 아니다.
2. **BF Hamming / cross-check**, OpenCV 공식 문서, 특정 신규 논문으로 취급하지 않음.
   [문서](https://docs.opencv.org/4.13.0/dc/dc3/tutorial_py_matcher.html).
   이진 기술자를 비교해 상호 최근접 대응을 유지한다. 상호 최근접이라는 조건이 실제 같은 3D 점임을 보증하지는 않는다.
3. **Essential/recoverPose 및 PnP**, OpenCV calib3d 공식 문서.
   [문서](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html).
   현재 두 영상 대응으로 회전과 translation direction을 얻는다.
   제안인 PnP는 3D-2D 대응으로 pose를 추정하므로 metric 3D 입력이 선행되어야 한다.
4. **ORB-SLAM2: an Open-Source SLAM System for Monocular, Stereo and RGB-D Cameras**,
   Raul Mur-Artal, Juan D. Tardos, arXiv 2016 / T-RO 2017.
   [논문](https://arxiv.org/abs/1610.06475), [저자 코드](https://github.com/raulmur/ORB_SLAM2).
   tracking, mapping, loop closing을 결합하며 stereo/RGB-D에서는 실제 스케일을 사용할 수 있다.
   입력은 보정된 카메라 영상이다. 현재의 frame-to-frame baseline과 구조적 차이가 크다.
5. **VINS-Mono: A Robust and Versatile Monocular Visual-Inertial State Estimator**,
   Tong Qin, Peiliang Li, Shaojie Shen, arXiv 2017 / T-RO 2018.
   [논문](https://arxiv.org/abs/1708.03852).
   영상 관측과 IMU preintegration을 함께 최적화하는 추정기다.
   시간 정렬, extrinsics, bias/noise 모델, 초기화가 필요하다. IMU 파일 보유만으로 실행 가능한 상태는 아니다.

아래 표의 공수/실시간성은 우리 환경 실측이 아닌 설계 판단이다. 논문의 수치를 우리 성능으로 인용하지 않았다.

| 방법 | 필요 데이터 | 보유 | 추가 추출 | 연산/실시간성 | 결합 난이도 | 판단 |
|---|---|---|---|---|---|---|
| ORB + BF + E | 연속 영상, K | 있음 | 없음 | 현재 latency 미측정 | 낮음 | 기존 baseline 유지 |
| 매칭 gate/grid 분산 | 영상/descriptor/매칭 | 있음 | 공간 점유·거리 통계 | [가정] 낮은 추가 비용 | 낮음 | 오매칭 실험 가능, scale 문제는 해결 못 함 |
| Stereo + PnP | 좌우 영상, P0/P1, 시간 대응 | 있음 | disparity, metric 3D, temporal 2D | [미확인] 실측 필요 | 중간 | 다음 연구 우선 후보 |
| ORB-SLAM2 구조 | keyframe/map/BA/loop 인프라 | 일부만 | 상태/지도 관리 필요 | [미확인] 로컬 벤치마크 없음 | 높음 | 단계적 학습 참조 |
| VINS-Mono 구조 | 카메라+IMU+calibration | 파일 있음, 정렬 안 됨 | 이상 시간 처리/동기화/bias 초기화 | [미확인] | 높음 | 시간축 검증 이후 |

바로 적용 가능한 것은 관측/매칭 통계 개선이다. Stereo 깊이를 추가 추출하면 PnP가 가능하다.
현재 검증 수준에서 즉시 VIO 융합은 부적절하다. 선택은 **회고를 마치고 사용자에게 Stereo 연구와 IMU 정렬 연구 중 선택권을 제공**하는 것이며 구현 착수는 하지 않는다.
