# 실험 진행 노트

## 사전 고정
2026-11-24: 문제/인벤토리/quick-win/아키텍처를 구현 전에 기록했다.
구간 [0,200)은 개발 관측, [400,500)은 같은 설정의 분리 holdout이다.
holdout은 다른 시퀀스가 아니므로 일반화 성능을 대표하지 않는다.
baseline 대비 성능 향상 목표 없음. 데이터 기반 척도와 평가 전용 정렬의 분리가 핵심이다.
아래는 실제 실행 뒤 저장된 JSON/CSV/NPZ에서 옮긴 결과이다. 문서 작성용 중간 노트이며 별도 보고서가 아니다.

## 핵심 결과 / 판정

| 구간 (끝 제외) | 방법 / 평가 정책 | ATE RMSE m | endpoint m | 1-frame RPE m | 회전 RPE deg |
|---|---|---:|---:|---:|---:|
| 0:200 | stereo FB, metric, 척도 적합 없음 | 1.7043379117964552 | 1.7155781111153412 | 0.03353653198260218 | 0.07253139337451359 |
| 0:200 | stereo forward only, metric | 1.6417975648517316 | 1.74624721614764 | 0.033950404701595424 | 0.0745482823380338 |
| 0:200 | mono unit-step, 평가 전용 GT Sim3 | 5.149899767979516 | 4.604658214359584 | 0.23085987319021134 | 0.42915732445988514 |
| 400:500 | stereo FB, metric, 척도 적합 없음 | 0.790699804727608 | 1.3388999681441516 | 0.028919082285049524 | 0.046586127524290415 |
| 400:500 | stereo forward only, metric | 0.7547449472853373 | 1.3274528252899191 | 0.02623927178109734 | 0.04715282335753963 |
| 400:500 | mono unit-step, 평가 전용 GT Sim3 | 3.130592768918678 | 4.64319386530858 | 0.22819106806535572 | 0.9029975356560023 |

- GT path length: 144.87855170702335m / 66.40044101005537m.
- mono 사후 fitted scale: 0.7242085489415547 / 0.7065476892909599 m per arbitrary unit.
- 각 방법의 hold=0/199, 0/99. 이는 이 두 구간의 결과일 뿐 robust tracking 인증이 아니다.
- FB는 두 구간 모두 ATE를 악화시켰다. 작은 잘못된 관측을 줄이는 게이트라도 최종 궤적 개선을 보장하지 않는다.
- stereo metric과 mono Sim3의 숫자를 공정한 정확도 순위로 해석하지 않는다. 관측과 정렬 조건이 다르다.
- 전체 숫자: `artifacts/summary.json`, 여섯 평가 행 `artifacts/metrics.csv`.
- 각 프레임의 잔차/오류/수: `artifacts/odometry/<segment>/frames.csv`, `artifacts/evaluation/<segment>/errors.csv`.

## Quick-win 실제 측정

| 프레임 | ratio 수 / y<=1.5px 비율 | cross-check 수 / y 비율 | 최종 sparse 3D 수 | LK forward → FB |
|---|---|---|---:|---|
| 0 | 657 / 0.8188736681887366 | 1217 / 0.7230895645028759 | 518 | 2495 → 2363 |
| 100 | 910 / 0.8615384615384616 | 1390 / 0.7985611510791367 | 731 | 2462 → 1539 |
| 400 | 1148 / 0.9233449477351916 | 1540 / 0.8941558441558441 | 897 | 2427 → 2417 |

ratio 뒤 Hamming<=64를 추가해도 세 프레임 모두 제거 수 0이었다. 이 ablation은 실제 무효한 추가 게이트도 공개한다.
ratio와 cross-check 비교는 정류 일관성/개수의 비교이며 정답 대응률이나 전체 VO 정확도 비교가 아니다.
y gate 뒤 y 비율=1은 게이트 정의에 의한 결과이므로 독립 검증 지표로 쓰지 않는다.
frame100의 큰 FB 제거 수는 관측 품질 변화의 신호지만, GT flow/가림 mask가 없어 원인을 확정하지 않는다.

| 프레임 | dense 양의 disparity 비율 | LR 일관 비율 | 깊이 유효 비율 / 수 | LM 전 → 후 RMSE px |
|---|---:|---:|---|---|
| 0 | 0.7452894885730451 | 0.6692998096936239 | 0.6599923706002366 / 307963 | 0.629673871177033 → 0.617612570430628 |
| 100 | 0.8176637749241347 | 0.7242850652356542 | 0.7173243094964596 / 334715 | 0.5515574929650505 → 0.47938525423266676 |
| 400 | 0.7027877312393918 | 0.5900162017590481 | 0.5835869322955064 / 272311 | 0.46494461449513425 → 0.4349973910936946 |

모든 dense 비율의 분모는 376*1241 전체 픽셀이다. 코드의 positive는 d>1px이며 수학적 d>0과 구분한다.
SGBM 깊이는 시각화/진단용이며 PnP 입력에 사용하지 않았다. PnP의 3D는 ORB stereo 삼각측량뿐이다.
LM 비교는 동일 RANSAC inlier의 in-sample 오차이다. 추가 일반화·joint BA 성능을 입증하지 않는다.

## 유용한 실패 진단

- 0:200의 최대 stereo 1-frame RPE는 frame1, 0.1907563355762054m. PnP 490/512 inlier에도 오차가 있다.
- 400:500의 최대값은 frame461, 0.08910900090936784m. PnP 435/466 inlier.
- 각 구간 상위 5개와 사후 Pearson 상관: `evaluation/<segment>/failures.json`, `worst_frames.csv`.
- feature 수/FB 오차와 RPE의 상관 부호가 구간별로 달라진다. 하나의 quality score로 오류 원인을 단정하지 않는다.
- 실패 프레임을 identity hold하더라도 다음 이미지로 진행하므로 실패 이동은 영구히 빠진다. 재추적 복구가 아니다.
- E가 여러 후보를 반환하면 첫 3x3만 사용한다. 이번 298 transition의 multi-E frame은 0개였다.
- 단안 성공 step=1은 속도 변화 표현 불가. 전체 Sim3가 맞더라도 국소 이동량은 틀릴 수 있다.
- 실제 loop closure, local map, keyframe selection, outlier semantic mask, 누적 BA 없음.

## 합성 실험 (KITTI 실측과 분리)

- 렌즈 계수 [-0.22,0.06,0.001,-0.0005,0]는 설명용 가정, 실제 KITTI 보정이 아니다.
- 가상 grid 최대 변위 83.7418847033159px, 알려진 모델 역변환 최대 오차 1.5956708065935117e-12px.
- disparity sigma=0.5px, 100m에서 선형 전파 sigma_Z=12.948510506939366m,
  깊이별 10000회 Monte Carlo 표준편차 14.182915498081321m. 비선형 변환 효과가 있다.
- 각 퇴화 조건 20회 E accepted: normal 20, pure_rotation 14, far_depth 9, planar 20, tiny_translation 9.
- pure_rotation에서 accepted 14회는 정상 이동 복원이 아니다. 번역이 없는데도 비영 이동을 추정하는 거짓 신뢰 사례다.
- planar accepted 20/20도 비퇴화 증명이 아니다. 방향/회전 오차 분포는 `synthetic/degeneracy.csv`를 함께 봐야 한다.
- 합성 PnP는 exact 3D를 받는다. 실제 stereo PnP 또는 단안과 공정한 성능 비교가 아니다.
- 합성 회전오차 summary는 `system_output_rotation_median_including_hold_deg`와
  `successful_estimate_rotation_median_deg`를 분리하고 `essential_accepted`/`essential_failed_hold`를 함께 기록한다.
  전자를 accepted만의 정확도로 인용하지 않는다. per-trial `E_accepted`도 CSV에 보존한다.

| 합성 조건 | 성공 / hold | 전체 출력 회전오차 중앙값 deg | 성공 추정만 중앙값 deg |
|---|---|---:|---:|
| normal | 20 / 0 | 0.34176524445491674 | 0.34176524445491674 |
| pure_rotation | 14 / 6 | 0.1086865994435105 | 0.08840049626513946 |
| far_depth | 9 / 11 | 1.470839686933306 | 0.15045471516789577 |
| planar | 20 / 0 | 0.9543423260825845 | 0.9543423260825845 |
| tiny_translation | 9 / 11 | 1.470839686933306 | 0.21541626935464123 |

전체 출력 통계는 실패 시 identity rotation의 오차를 포함한다. 성공 조건부 통계는 선택 편향이 있으므로 성공률과 함께 읽는다.
이 분리를 검증하는 회귀 테스트를 포함해 현재 19개 불변량 테스트가 통과한다.

## 작성자용 수식과 수치 연결

### 1. 목표는 픽셀에서 metric 이동 얻기
입력은 같은 시각의 좌/우 흑백 영상과 다음 시각의 왼쪽 영상이다. 출력은 시작 카메라에서 본 현재 카메라 자세이다.
기호 K는 내부행렬(px), X는 카메라 3D(m), p=(u,v)는 픽셀(px), b는 baseline(m), d=uL-uR는 disparity(px).
투영은 u=fx*X/Z+cx, v=fy*Y/Z+cy. Z는 optical-axis depth이며 카메라와 점 사이 Euclidean range가 아니다.
좌표 축은 x 오른쪽, y 아래, z 전방. `geometry.py:22`, `observations.py:8`.

### 2. 정류와 깊이
이미 정류된 P0=[K|0], P1=[K|(-fx*b,0,0)]를 읽는다. raw distortion을 추정하거나 raw 영상을 정류하지 않았다.
b=386.1448/718.856=0.5371657188644179m. 이상적인 같은 행 대응에서는 d=fx*b/Z, 즉 Z=fx*b/d.
실제 예제는 frame0의 candidate323: left=(956,161), right=(936,160), d=20px, dy=1px.
이상적 동일 행 모델 깊이는 19.30724m, 실제 OpenCV DLT 3D는
(9.368194026011457,-0.6638089660386813,19.306872628031506)m이다.
서로 다른 y 관측 때문에 DLT와 간단 공식의 마지막 자릿수가 다르며, 최대 양안 재투영 잔차는 0.5000097548414209px이다.
연습: disparity가 두 배이면 이상적 깊이는? 답: 절반 9.65362m. 코드 검증값은 `worked_examples/summary.json`.

### 3. ORB 관측과 descriptor 선택
ORB는 Oriented FAST and Rotated BRIEF의 약자다. FAST는 밝기 비교로 코너 후보를 찾고,
BRIEF는 patch 내 픽셀쌍 밝기 비교를 binary descriptor로 만든다. ORB는 방향 정규화 등을 결합한다.
이 실험은 OpenCV ORB의 실제 keypoint/descriptor 출력만 사용하며 내부 FAST/Harris/BRIEF 배열을 재현했다고 주장하지 않는다.
Hamming 거리는 XOR에서 서로 다른 bit의 수. candidate323의 최근접=32bit, 차근접=47bit,
ratio=32/47=0.6808510638297872<0.75이고 Hamming<=64, abs(dy)<=1.5, d>1을 통과한다.
ratio는 모호성, Hamming은 절대 descriptor 차이, y는 정류 기하를 검사하는 서로 다른 조건이다.
cross-check는 서로가 서로의 최근접인 쌍이다. ratio의 동의어가 아니며 이번에는 더 많은 쌍을 남기지만 y 일관성 비율은 낮다.
연습: y gate를 통과한 쌍의 y 합격률이 100%라면 정확도인가? 답: 아니다. 같은 조건의 자기검사다.

### 4. SGBM과 dense validity
SGBM은 Semi-Global Block Matching 계열 OpenCV 구현이다. 픽셀/블록 대응 비용과 disparity 변화 벌점을 여러 경로에서 결합한다.
교육적 목적 함수는 sum C(p,d_p)+P1*[이웃 disparity 차이=1]+P2*[차이>1] 형태지만,
이 실험은 OpenCV 내부 경로별 비용 배열을 추출하지 않았다. 저장된 raw는 실제 최종 fixed-point disparity다.
OpenCV disparity 정수 출력은 16으로 나누어 px로 변환한다. P1=8*5^2=200, P2=32*5^2=800,
disparities=128, block=5, uniqueness=10. 비용 벌점과 보정 projection P1은 이름만 같고 다른 기호다.
우측 매칭은 음수 disparity convention이라 LR residual=abs(dL+dR(uL-dL))이다.
영상 밖, 무효 우측 disparity, LR>1px, Z>100m를 제외한다. 무텍스처/가림/반사면 깊이는 여전히 틀릴 수 있다.

### 5. Temporal LK와 FB
LK는 Lucas-Kanade 광류. I_previous(p)≈I_current(p+delta)를 국소 선형화해
공간 밝기 gradient로 delta를 추정한다. pyramid는 큰 움직임의 국소 선형화 범위를 줄여 준다.
이 실험의 winSize=21, maxLevel=3, 최대 30회/epsilon0.01은 고정 설정이다.
FB는 norm(p_back-p_previous)<=1px. 순방향 status, 현재 영상 bounds, 역방향 status를 함께 검사한다.
단일 에지는 aperture ambiguity가 있고, 반복 무늬의 잘못된 대응도 왕복 일관성을 가질 수 있다.
status=0인 LK error는 OpenCV 계약상 미정의다. 이를 NaN으로 바꾸고 invalid 좌표/FB를 명시적으로 표시한다.
연습: FB=0이므로 true correspondence인가? 답: 아니며 GT flow 없이는 정답률을 측정할 수 없다.

### 6. E와 PnP의 다른 관측 가능성
정규화 bearing x=K^-1*[u,v,1]에 대해 x_current^T E x_previous=0, E=[t]_x R이다.
E를 상수배해도 같은 제약이므로 t의 크기를 얻지 못한다. recoverPose의 단위 t를 frame마다 누적하는 것이 mono_unit이다.
PnP(Perspective-n-Point)는 이전 frame의 metric X_i와 현재 pixel p_i에서
sum ||pi(K*(R*X_i+t))-p_i||^2를 최소화한다. RANSAC이 outlier를 거르고 LM이 고정 inlier의 자세만 보정한다.
스테레오 baseline에서 metric이 전달되며 GT 이동량은 절대 사용하지 않는다.
이전 X를 현재로 옮기는 T_current_previous를 누적 자세에 그대로 곱하면 방향이 틀린다.
T_start_current=T_start_previous*inverse(T_current_previous). frame0→1 t_z=-0.67222211은
카메라 전진과 양립하며, 카메라 위치는 역변환의 -R^T*t로 계산해야 한다.
연습: t의 부호만 바꾸면 inverse인가? 답: 일반적으로 아니고 회전 전치가 필요하다.

### 7. 평가와 정렬
GT는 각 구간의 첫 자세 역변환으로 시작 좌표계에 정규화한다. stereo에는 추가 fit을 하지 않는다.
ATE는 위치 오차 norm의 RMSE. relative D_i=inverse(T_i)*T_(i+1),
RPE residual=inverse(D_GT)*D_est이며 translation norm과 rotation angle을 각각 집계한다.
mono는 s,R,t로 위치의 제곱오차를 최소화한 Sim3를 평가에서만 사용한다. 한 가지 s는 가변 속도를 복원하지 못한다.
official KITTI 100..800m 구간 평가와 다르다. 구간이 짧고 동일 시퀀스라 광범위 성능 비교를 주장하지 않는다.

### 8. 불확실성과 한계
Z=fx*b/d에서 abs(dZ/dd)=fx*b/d^2=Z^2/(fx*b). 따라서 sigma_Z≈Z^2*sigma_d/(fx*b).
candidate323과 d=20px, 가정 sigma_d=0.5px이면 sigma_Z=0.482681m.
실제 ORB의 정수/피라미드 양자화, 대응 오답, calibration 오차는 이 Gaussian 모델에 포함되지 않는다.
순수 회전에서 t 방향은 물리적으로 정의되지 않는다. E accepted flag는 observability 판정이 아니다.

## 그림 / 배열 인계

그림 37개 = 실제 KITTI 33 + 합성 4. 전부 폭 7in, 220dpi, 축·단위·실제/합성 제목을 사용한다.
`figures/figure_manifest.json`에 파일, kind, 원본 NPZ/CSV, 한국어 caption을 저장했다.
- 01..09: 정류 입력, epipolar ECDF, ORB 공간 분포, ratio, Hamming-geometry, gate ablation, disparity-depth, sparse 3D, reprojection.
- 10..13: SGBM disparity/depth/validity/LR residual.
- 14..17: temporal LK/FB/patch error/pose-only LM.
- 각 구간 8개: metric trajectory, mono Sim3 trajectory, metric errors, inlier 수, step scale, RPE, FB ablation, worst frame.
- synthetic_* 4개: depth uncertainty, lens distortion, radius 관계, degeneracy acceptance.
- 그림 source 경로는 연구 디렉터리 기준, data/로 시작하는 원본만 repo 기준이다.
- original library 출력: ORB points/distances, LK flow/status, SGBM fixed16, E/PnP/DLT/LM.
  교육적 모델: 합성 왜곡/불확실성/퇴화. 두 종류를 섞어 library 내부 구현으로 인용하지 않는다.

## 재현 / 검증 / 시행착오

```sh
cd /Users/youth/Project/slam-lab
research/20261031_vo-lo-study/.venv/bin/python research/camera-slam-textbook/src/run.py
research/20261031_vo-lo-study/.venv/bin/python research/camera-slam-textbook/src/verify.py --repeat
research/20261031_vo-lo-study/.venv/bin/python -m unittest discover -s research/camera-slam-textbook/src -p test_invariants.py -v
```

`--reuse-estimates`는 기존 추정을 평가/그림만 재생성하는 선택지이며 fresh run으로 표기하지 않는다.
기본 full run은 두 구간 합계 300 poses/298 transitions를 처리한다. 반복 검증도 각각 최대 200frame이다.
프레임 runtime은 두 estimator+ablation 포함 처리 시간이며 NPZ 쓰기 이후 시간을 포함하지 않는다. 실시간 인증이 아니다.
의존성: Python 3.11, numpy2.4.6 scipy1.17.1 matplotlib3.11.1 opencv-python5.0.0.93(cv2=5.0.0).
seed37, OpenCV single thread. input/source/artifact SHA256, full dependencies, build 정보는 provenance에 저장한다.
원래 실험 base f09b08e와 실행 HEAD는 다를 수 있다. 후속 다른 담당자 커밋과 혼동하지 않는다.

실제로 발견/수정한 문제:
1. OpenCV5의 undistortPointsIter 부재. 로컬 docstring을 확인해 criteria 인자가 있는 undistortPoints를 사용하고 4.x 분기를 보존했다.
2. LK failed status의 err buffer 미정의. 초기 반복 검사에서 2500개 중 3개 err가 달랐지만 궤적은 동일했다.
   invalid error/좌표를 NaN, 왕복오차를 inf로 정규화하고 raw status를 저장하도록 수정했다.
3. FB 추가의 ATE 악화는 버그로 숨기지 않고 관측 결과로 기록했다. 개선을 위한 holdout 튜닝을 하지 않았다.

최종 검증 결과는 `artifacts/tests/summary.json` 및 `artifact_verification.json`을 기준으로 인용한다.
후자는 두 구간의 자세·모든 저장 stage 배열의 독립 재실행 equality를 검사한다. runtime은 equality 대상이 아니다.
운영 코드, docs/report.md/pdf, tools는 수정하지 않았고 커밋하지 않았다.

## 구현 위치 (현재 소스 줄 번호)
- 보정/영상 계약: `src/common.py:47` calibration.
- ORB matching/게이트/triangulation: `src/observations.py:8` stereo.
- LK/FB 및 undefined buffer 정규화: `src/observations.py:45` track.
- SGBM fixed16/LR/depth mask: `src/observations.py:73` dense.
- PnP RANSAC/pose-only LM: `src/odometry.py:10` estimate_pnp.
- 단안 E/첫 후보/unit translation: `src/odometry.py:38` estimate_essential.
- metric 누적 및 stage 저장: `src/odometry.py:62` run_segment; 실패 시 영상 진행 `:108`.
- GT 독립 읽기/정렬: `src/evaluation.py:22` evaluate; metric 정의 `:8`.
- 역변환/합성/Sim3: `src/geometry.py:14`, `:27`, `:31`.
- 실제 진단/ablation: `src/diagnostics.py:9`; 합성 모델 `src/synthetic.py:16`, hold 분리 집계 `:9`.
- 실제 수치 예제: `src/worked_examples.py:7`.
- 불변량 테스트: `src/test_invariants.py:17`; 독립 재실행 검증 `src/verify.py:12`.

## 최종 검증 / 인계 상태
2026-11-24: 19/19 테스트 통과, 37개 그림의 해상도·비어 있지 않음·source 경로 검사 통과.
298 transition의 독립 재실행에서 세 방법 모두 두 구간 자세의 최대 절대차=0.
stage 배열도 0:200에서 8557개, 400:500에서 4257개, 합계 12814개가 NaN 위치를 포함해 정확히 일치했다.
OpenCV 실패 버퍼 정규화 후의 결과이며 다른 하드웨어/의존성 버전의 bitwise 재현까지 보장하지 않는다.
최종 합성 통계 분리 뒤 19-test 재실행 및 요약/그림 재생성을 수행했다. KITTI metric 값은 변경되지 않았다.
`artifacts/summary.json`의 최신 run_mode=reuse estimates는 이 마지막 문서용 재집계 실행을 정직하게 나타낸다.
실제 추정과 독립 반복 실행은 이미 완료되었으며 `tests/artifact_verification.json`에 결과가 남아 있다.
본인 소유의 소스·config·그림·세 노트는 인계 준비 완료. 이후 변경/커밋은 main 담당자와 작성자가 관리한다.
