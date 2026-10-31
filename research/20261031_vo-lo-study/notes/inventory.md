# Phase 1-2: 문제 정의와 리소스

문제: 이전 보고서는 ORB/추정 과정의 교육적 설명과 단계별 산출물이 부족했고 LO가 없었다.
입력: KITTI 00 image_0와 velodyne의 동일 인덱스 0~199, calib.txt, 평가 전용 poses/00.txt.
출력: ORB 단계 그림/배열, VO/LO pose와 중간 산출물, 공정한 평가 표, PDF 보고서.

성공 기준: 200개 프레임 인덱스가 보존되는 VO/LO 로그; 대표 프레임별 단계 그림;
좌표 변환/스케일 정책이 명시된 위치 RMSE와 상대 회전 오차; 실패와 시간 통계 기록.
[가정] 개선은 baseline 대비 같은 구간의 지표로 판단한다. 목표 정확도/실시간 요구사항은 지정되지 않았다.
VO보다 LO가 좋아야 한다는 결과 조건은 두지 않는다.
범위 밖: full ORB 학습 재현, 신규 learned matcher 학습, VIO/LIO, loop closure, 제품 코드 통합.

| 자원 | 상태/근거 | 활용 |
|---|---|---|
| 좌우 grayscale | data/kitti/dataset/sequences/00/image_0,image_1 각 4541 | 이번에는 기존 단안 VO 유지 |
| LiDAR | velodyne 4541 bin, XYZI | LO; intensity는 시각화용만 |
| 컬러 | image_2/3 없음 | 컬러 ablation 불가; 설명과 한계 명시 |
| IMU | raw OXTS 45700 측정 | 시간축 이상 확인된 별도 자원, 이번 미사용 |
| GT/calibration | poses/00.txt, P0/Tr | GT는 평가 전용, Tr은 LO->camera 변환 |
| 특징점/매칭 | src/vo/features.py:4,8,13 | ORB/BF API 재사용 패턴 |
| 추정 | src/vo/two_view.py:11, src/vo/run_kitti.py:12 | baseline 재현; 제품 코드 수정 안 함 |
| 환경 | Python3.11 arm64, OpenCV/NumPy/Matplotlib | 연구 전용 venv에 KISS-ICP/SciPy 추가 |
| 부족 | per-point time, 컬러, GT correspondence label, 다중 조건 평가 | deskew off, synthetic GT로 feature만 부분 평가 |

## Phase 3: Quick-win

매칭 ratio gate는 작은 비교 실험으로 실행하되 scale 한계를 해결하지 못한다.
신규 LO와 단계별 교육 모듈은 기존 파라미터 조정으로 만들 수 없으므로 Phase 4-5가 필요하다.
