# 확인한 원문과 선택 근거

확인일: 2026-11-24. 논문 재현을 주장하지 않는 API 기반 소규모 수업 실험이다.
아래는 온라인 원문을 직접 열어 확인한 공식 문서이다.

| 원문 | 핵심 확인 사항 | 적용/한계 |
|---|---|---|
| [SciPy `least_squares` 공식 문서](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html), SciPy community, 열람 시 v1.18.0 | residual vector, callable/3-point Jacobian, TRF, loss와 f_scale, 종료 상태 | 즉시 적용. 설치 버전 1.17.1과 문서 버전 차이가 있어 실제 호출·수치미분 테스트도 수행 |
| [OpenCV camera calibration / projectPoints 공식 문서](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html), OpenCV contributors, 열람 시 4.13.0으로 연결 | world-to-camera rvec/tvec, pinhole 투영, Jacobian의 rotation/translation 열 | 즉시 적용. 설치 cv2 5.0.0에서는 직접 pinhole 비교와 중앙차분 대조로 사용 부분 확인 |

SciPy 1.17.1 지정 버전 웹 페이지도 열려고 했으나 도구가 접근 오류를 반환했다.
따라서 그 페이지를 읽었다고 주장하지 않는다. 온라인 문서와 설치 버전의 완전한 동일성은 [미확인].
실제 import 버전과 성공한 API 호출, 테스트는 별도의 실행 근거다.

## 채택 방법 비교

| 방법 | 필요한 데이터/보유 여부 | 계산·결합 판단 | 결정 |
|---|---|---|---|
| OpenCV projection + dense analytic joint J | K, baseline, pose, 점 / 합성으로 보유 | 576 residual, 126변수; 외부 frontend 필요 없음 | 주 실험 |
| 같은 모델 + 3-point numerical J | 같은 데이터 / 보유 | 계산량 증가, 미분 구현 독립 비교 가능 | 작은 문제 테스트 |
| pose-only 최적화 | 고정 3D점 / 보유 | 점 불확실성 갱신 불가 | 요청된 joint 수업의 대체 아님 |
| Schur complement 전용 BA | sparse block solver 필요 | 이 크기에서 추가 복잡도 이점 검증 안 함 | 미구현 |
| scalar soft-L1 | 동일 noisy 관측 / 보유 | 추가 feature 없이 loss만 변경 | outlier ablation |
| 2D SE(2) relative-coordinate graph | 상대 측정, sigma / 생성 | 일반 solver 사용; full Lie-log residual 아님 | 루프 수업 |
| 영상 기반 루프 검증 | 영상·후보·기하 검증 필요 / 미사용 | 별도 실제 파이프라인이 필요 | 범위 밖 |

TRF는 Trust Region Reflective의 약자다. 이 실험의 `tr_solver="exact"`는 작은 dense
부분문제 풀이 선택이며, 전역 최적해 보장이나 정확한 Schur 구현이라는 뜻이 아니다.
LM(Levenberg-Marquardt) solver를 사용했다고도 쓰지 않는다.
BA(Bundle Adjustment)는 여러 관측 광선 묶음과 카메라·점 기하를 함께 맞추는 최적화다.
기존 SLAM 시스템이나 특정 논문의 완전 재현으로 해석하지 않는다.
