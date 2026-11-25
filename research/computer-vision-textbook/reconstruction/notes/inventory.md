# Reconstruction 리소스 조사

## 문제와 범위
기존 C11은 표현 개관이며 수치 융합, 렌더링, 시간 오차, 검증 계약의 유도가 부족하다. 목표는 D21-D24 원고, 독립적인 교육 실험 14개 그림, 10개 이상 검증이다. 새 SLAM 시스템이나 생산 코드 개선이 아니며 정본 수정/커밋/배포/비행은 범위 밖이다. 원고는 통합 담당자가 docs/report.md에 옮길 중간 자료다.

## 보유 자원
- 기준 커밋: 75f7140d0dec421971c9b13d088e1967ebe124d5. 공유 작업 트리에서 브랜치 변경/fetch/커밋은 수행하지 않는다.
- KITTI 00 image_0/000000.png, image_1/000000.png, calib.txt 존재. 흑백 uint8. 실험 입력은 두 영상과 보정 파일만 사용한다. GT와 IMU는 사용하지 않는다.
- research/20261031_vo-lo-study/.venv/bin/python: 사용자가 제공한 numpy/scipy/cv2/matplotlib/Pillow 환경.
- 기존 common.py:28 영상, :34 calibration, :50 transform; evaluate.py:8 sim3, :18 metrics; lo.py:8 실행 진입. 기존 구현은 수정하거나 호출하지 않고 데이터 형식만 참고한다.
- docs/report.md:3791 C11 지도 개관, :693 사전적분 개관. 새 원고는 개념 목록이 아니라 수치 유도와 조건부 실패를 보강한다.
- 미보유/미수행: 동기화 IMU 시퀀스 검증, 컬러 RGB-D, Astra 실측 보정, 드론 제어, 신경장 학습, 디지털 트윈 실측 검증.

## Quick-win
기존 단원 문구 추가만으로 관측가능성/렌더링/시간 동기화 계산을 검증할 수 없다. 최소 독립 실험으로 선형대수와 기존 SciPy/OpenCV를 사용한다. 훈련/대형 다운로드/새 production pipeline은 불필요하다.

## 성공 기준 [가정]
14 PNG (7 inch, 190 dpi), 설정/시드, NPZ 중간값, JSON 결과/해시/버전/시간, 수치 단위검사 20개 이상. 적어도 각 장 하나의 반례/ablation. 숫자와 원고 일치. 과학적 점수는 직접 실행한 toy 결과만 보고한다.
