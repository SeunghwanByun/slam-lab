# 학습 교재 리소스와 문제 정의

- 문제: 통합 보고서 v1.1.1의 수학 로드맵은 상세 학습용 유도·그림·연습문제가 부족하다. 알고리즘 정확도 개선 요청이 아니다.
- 기준 코드: 178ec59724069e60b991f1f4b967b1d63fc3617c. 기존 PDF와 알고리즘 장은 보존한다.
- 성공 기준 [가정]: 12개 기초 단원, 각 2개 문제와 해설, 신규 15개 그림, 계산 검증 25개, PDF 렌더 및 링크 검사.
- 데이터: KITTI Odometry 00 frame120의 image_0, velodyne, calib.txt. 시퀀스 카메라/점군 각각 4541프레임. 신규 그림 중 실제 데이터 사용은 투영 그림 하나다. GT를 신규 추정 입력으로 사용하지 않는다.
- feature: 이 작업에서 특징점 성능 실험은 하지 않는다. 기존 ORB/매칭/LO 중간 그림은 통합 문서에 유지한다.
- 환경: 기존 연구 venv의 OpenCV, NumPy, SciPy, Matplotlib. PDF는 tools/render_report.mjs의 Chrome/marked/mermaid. 검사는 pypdfium2 5.14.0.
- 재사용: src/generate.py의 frames, camera, estimation, linearization, graph_imu는 교육용 수치 실험이다. 실제 VO/LO 모듈을 교체하지 않는다.
- 부족한 것: 검증된 IMU 시간 정렬, 실제 루프 제약 추정, 전체 SLAM/BA 구현. 이번 범위 밖이다.
- 접근: 교육용 계산과 시각화 추가가 가장 작은 해결책이다. 신규 SLAM 알고리즘 선택·성능 비교는 하지 않는다.
