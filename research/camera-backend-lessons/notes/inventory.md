# 합성 backend 실험 리소스

이 디렉터리는 주 작성자에게 전달하는 구현·중간 자료이며 별도 최신 보고서가 아니다.
사용자의 이번 범위 지시에 따라 `docs/report.md`, `docs/report.pdf`, 기존 모듈,
브랜치와 커밋은 변경하지 않는다. 실제 KITTI 실험과 결합하지 않는다.

## 문제와 기준

- 문제: pose-only 최적화와 공동 bundle adjustment를 구분하고, 좌표계 자유도와 잘못된 루프의 영향을 직접 확인한다.
- 입력: 생성된 calibrated stereo 관측과 대응점 ID, 고정 내부파라미터·baseline, 생성된 SE(2) 상대 pose 측정.
- 출력: 공동 pose·점 추정, graph pose 추정, 원본 배열, 지표, 그림 9개, 재현 가능한 테스트.
- [가정] 교육용 성공 기준: clean BA의 재투영 RMSE < 1 px 및 초기 대비 GT 오차 감소; 같은 오염 관측에서 robust의 pose·점 GT 오차가 LS보다 작음.
- [가정] 기하 검증 기준: 전역 강체변환 투영 변화 < 1e-9 px, 상대 특이값 기준 1e-10에서 free nullity=6 / anchor nullity=0.
- [가정] 루프 교육 기준: correct loop 위치 RMSE < odometry, false loop 위치 RMSE > odometry. 이 seed의 관찰이지 모든 그래프의 정리가 아니다.
- 범위 밖: real KITTI 성능, 특징 검출·매칭, 삼각측량 초기화, place recognition, 루프 승인 시스템, full 3D SLAM, Schur 전용 solver, 실시간성.

## 자원 확인

| 자원 | 상태와 용도 |
|---|---|
| `CODEX.md` | 작업 전 읽음; 연구 절차와 좌표/단위·근거 원칙 적용 |
| 지정 Python | `research/20261031_vo-lo-study/.venv/bin/python`; NumPy/SciPy/cv2/Matplotlib import 확인 |
| 기존 연구 src | `rg --files research/20261031_vo-lo-study/src`로 목록 확인; 이번 과제에서는 import/수정하지 않음 |
| 실제 영상·GT | 필요 없음, 읽지 않음; 프레임/시퀀스는 해당 없음 |
| 합성 GT | `src/backend.py:34`, `src/backend.py:155`에서 생성; 초기화와 평가에 사용 사실 공개 |
| 대응점 feature | 모든 카메라·좌우 영상에 동일한 36개 점 ID가 알려져 있다고 가정; 자동 매칭 아님 |
| outlier ID | 생성 시 29/288개 2D 관측 표시; 평가에만 사용, solver 입력 mask 아님 |
| pose graph | 25노드, 24 odometry edge, 선택적 1 loop edge; 측정 단위 m/rad |
| 현재 코드 버전 | 실행 시 HEAD와 새 소스 SHA-256을 `artifacts/manifest.json`에 저장 |
| 누락/미수행 | 실데이터, 다중 seed 통계, 런타임 benchmark, 실제 센서 캘리브레이션, 자동 loop rejection |

시작 시 다른 작업자의 수정(`tools/render_report.mjs` 등)이 존재했다. 이 작업에서는 읽거나 되돌리지 않았다.
공유 작업트리를 보존하려고 fetch/브랜치 생성/커밋을 수행하지 않았다.

## Quick-win 판단

파라미터 튜닝만으로 pose-only 구현이 joint BA가 되지는 않는다. 점 변수가 포함된
작은 목적함수를 새 연구 폴더에 정의하는 것이 교육 목적에 필요한 최소 변경이다.
새 최적화 알고리즘을 발명하지 않고 SciPy 일반 solver를 재사용한다.
outlier 처리의 quick-win은 같은 residual에 `linear` 대신 `soft_l1`을 적용하는 ablation이다.
false loop는 자동 제거하지 않고 그대로 최적화하여 실패를 관찰한다.
