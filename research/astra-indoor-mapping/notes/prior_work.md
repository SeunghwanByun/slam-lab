# 공식 구현 조사 (2026-11-10)

| 방법 | 입력/적용 | 현 상태 | 판단 |
|---|---|---|---|
| Orbbec SDK | 모델·펌웨어·OS에 맞는 장치 | 모델 미확인 | 설치 보류 |
| RTAB-Map RGB-D | 정렬된 RGB·depth·보정·timestamp | 실측 입력 없음 | 첫 실내 지도 baseline 후보 |
| ORB-SLAM3 | RGB-D 또는 영상/IMU | 실측 입력 없음 | 추적·초기화·최적화 학습용 후속 |

Orbbec 지원표에서 Astra 2와 Astra Pro Plus는 SDK v2 지원이 다르다. 이름에 Astra가 들어간다는 이유만으로 같은 드라이버를 선택하지 않는다. macOS 제품 지원 목록도 별도로 확인해야 한다. 펌웨어를 자동 갱신하지 않는다.

- https://github.com/orbbec/OrbbecSDK (SDK/플랫폼 지원표)
- https://github.com/orbbec/OrbbecSDK_ROS2 (main과 v2-main 지원 차이)
- https://github.com/introlab/rtabmap_ros (RGB-D SLAM, ROS2 파이프라인)
- https://github.com/UZ-SLAMLab/ORB_SLAM3 (기존 학습에서 확인한 후속 프레임워크)

이 작업은 입력 준비 단계로 논문 재현·추정기 선정 실험·성능 비교를 수행하지 않는다. RTAB-Map의 실제 적용 가능성은 모델 확인 및 스트림 검증 이후 판단한다.
