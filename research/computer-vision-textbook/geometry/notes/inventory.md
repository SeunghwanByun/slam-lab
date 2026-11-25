# Geometry inventory

- 범위: D13 사영/보정, D14 두 시점, D15 밀집 대응, D16 SfM/희소 최적화. 원본 교재와 운영 코드는 읽기 전용이다.
- 문제: 식을 외워도 좌표/잡음/게이지를 혼동하는 학습자가 solver의 실패를 진단할 수 있게 한다.
- 성공 기준: 네 장의 유도·수치 예·실패 실험, 12개 이상 검증, 12개 자체 그림, 재실행 manifest. 정확도 benchmark나 새 SLAM 성능 주장은 범위 밖이다.
- 기존 docs/report.md:1558 C2는 F/E/H 및 삼각측량 개요, C6에는 기존 BA/Schur 입문이 있다. 이를 교체하지 않고 DLT nullspace, calibration observability, cost-volume recurrence, elimination과 marginalization 차이를 심화한다. 행 번호는 조사 시점이며 통합 후 바뀐다.
- 입력: data/kitti/dataset/sequences/00/image_{0,1}/000000.png, uint8 grayscale. 해당 장면 disparity GT는 사용하지 않는다. 실제 stereo 출력은 정확도 주장이 아닌 사례다.
- 합성 입력: 고정 seed로 알려진 카메라/3D 점/체커보드/시차 구간/선형 최소제곱. GT와 관측 분리.
- Python: research/20261031_vo-lo-study/.venv/bin/python; NumPy/SciPy/OpenCV/Matplotlib/Pillow. GPU/추가 모델 불필요.
- 기준 커밋: 75f7140d0dec421971c9b13d088e1967ebe124d5. 현재 브랜치와 다른 연구자의 변경을 보존하며 fetch/branch 변경은 위임 범위 밖으로 수행하지 않는다.
- Quick-win: 새 geometry solver보다 기존 OpenCV 추정기 + 작은 대수 검산 + 독립 교육 실험이 적합하다. 제작 코드는 production 대체물이 아니다.
- 부족: 실제 stereo GT, 일반 장면 MVS 정답, 전체 SfM 실행 평가. 해당 성능은 미수행으로 명시한다.
