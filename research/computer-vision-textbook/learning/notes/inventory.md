# Learning 자원 조사

## 문제와 성공 기준
기존 교재의 학습 모델 소개를 D17–D20 계산 가능한 독립 교재로 심화한다. [가정] 성공 기준은 네 장, 신규 그림 12개 이상, 완전 풀이 16개 이상, 수치 검사 10개 이상, 실험 전체 재현이다. 생산 모델 정확도나 실시간성을 목표로 삼지 않는다. canonical 파일은 통합 작성자의 소유이며 이 연구자는 수정하지 않는다.

## 보유 자원
- 실행 환경: research/20261031_vo-lo-study/.venv/bin/python; NumPy/SciPy/OpenCV/Matplotlib/Pillow. 버전은 실행 manifest에 기록한다.
- KITTI odometry 00 image_0/000000.png: uint8 단일 채널 실제 입력. 이 연구의 검출/분할/깊이 정답은 없다. 실제 모델 예측 실험은 수행하지 않는다.
- research/20261031_vo-lo-study/src/common.py:28 image, :34 calibration, :54 finish가 기존 로더/그림 관례다. 생산 경로 의존 없이 cv2.imread로 동일 입력을 읽는다.
- docs/report.md: 현재 C 장의 학습 경계와 기하학을 반복하지 않고 확률/미분/평가/표현 계약을 보강한다.
- 기준 커밋 75f7140d0dec421971c9b13d088e1967ebe124d5; 코드/설정/실제 이미지 SHA256은 manifest.json으로 기록.
- 라벨/학습 데이터는 seed 고정 합성 자료. checkpoint, GPU, 대용량 다운로드, 외부 학습 프레임워크는 사용하지 않는다.

## Quick-win 및 범위
고정 선형 분류기, NumPy 작은 MLP, SciPy 할당 및 OpenCV 필터면 핵심 오류를 재현할 수 있다. 새 production 알고리즘이 필요 없다. 합성 데이터의 수치는 합성 분포에만 적용되며 KITTI 성능으로 외삽하지 않는다. git fetch/브랜치/커밋은 공동 작업 경계를 바꾸므로 이 연구에서는 수행하지 않는다.
