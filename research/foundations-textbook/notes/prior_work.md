# 확인한 원문과 사용 범위

- Lynch, Park, Modern Robotics, 3.3.1 Homogeneous Transformation Matrices: https://modernrobotics.northwestern.edu/nu-gm-book-resource/3-3-1-homogeneous-transformation-matrices/ — 변환 표기 및 합성.
- Dellaert, Factor Graphs and GTSAM: A Hands-on Introduction: https://gtsam.org/tutorials/intro.html — 변수/인자/사전 제약/최적화 개념.
- Solà, Deray, Atchuthan, A micro Lie theory for state estimation in robotics (2018): https://arxiv.org/abs/1812.01537 — 국소 상태 증분의 입문 연결.
- Forster, Carlone, Dellaert, Scaramuzza, On-Manifold Preintegration for Real-Time Visual-Inertial Odometry (2015 제출, 2016 개정): https://arxiv.org/abs/1512.02363 — IMU 사전적분의 후속 학습. 이번에 구현하지 않음.
- OpenCV calibration reference: https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html — 카메라 투영과 Rodrigues API 참고. 설치된 실제 버전은 summary.json 별도 기록.

논문의 그림이나 표를 복제하지 않았다. 15개 그림과 계산 예는 저장된 설정으로 생성한 독립 교육 자료다. 실측 성능 수치를 논문에서 가져오지 않았다. 새 알고리즘 선정이 아닌 교재 작업이므로 대규모 선행연구 비교/ablation은 해당하지 않는다.
