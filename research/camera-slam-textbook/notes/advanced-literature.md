# 고급 카메라 SLAM: 지도 수명주기에서 관성·밀집 지도·학습으로

작성 기준: 2026-11-24. 후속 집필자를 위한 독립 연구 노트이며 정식 보고서가 아니다.
수정 범위는 이 파일 하나다. `docs/report.md`, `docs/report.pdf`, 구현 파일과 Git은 변경하지 않는다.
이 자료는 기존 교재의 확장 재료다. 85쪽에서 130쪽 이상으로 늘어날 수 있다는 집필 방향은 이해하되, 실제 페이지 수는 통합·렌더링 전에는 확정하지 않는다.
논문 내용은 아래 Cited Findings에 출처를 붙이고, 자체 유도·수업 설계·적용 판단은 Inferences에 명시적으로 분리한다.
숫자 예제는 모두 교육용 가정이다. 실제 KITTI/Astra 측정값이나 논문 벤치마크 점수가 아니다.
현재 연구에서 구현, 학습, 데이터셋 실행, GPU 측정, 센서 촬영, 그림 렌더링은 수행하지 않았다.
그림과 배열 설명은 미래 집필·실습용 명세이며 생성 완료를 뜻하지 않는다.

기존 문서 중복 경계:
- `docs/report.md:284`의 A3 투영과 `:337`의 A4 스테레오를 선행 단원으로 사용한다.
- `docs/report.md:375`의 A5 최소제곱과 `:535`의 A9 미분을 반복하지 않고 블록 최적화로 확장한다.
- `docs/report.md:574`의 A10 Lie 군과 `:615`의 A11 factor graph를 재투영 Jacobian·gauge에 연결한다.
- `docs/report.md:659`의 A12 IMU 기초 뒤에 사전적분·관측가능성·초기화를 배치한다.
- `docs/report.md:751`의 ORB 검출·기술자 설명은 다시 쓰지 않는다.
- `docs/report.md:1052`의 SuperPoint/LightGlue 개요는 본문의 입출력 계약과 실패 진단으로 확장한다.
- `docs/report.md:1461`의 재방문 감사는 검증된 loop edge와 구별한다.
- `docs/report.md:1817`의 Astra 준비 절은 현재 상태의 근거다. 장치 모델과 스트림은 그 기록에서도 미확인이다.
- 위 행 번호는 이번 읽기 시점 기준이며 통합 시 절 이름을 기준으로 다시 연결한다.

독자가 마지막에 할 수 있어야 하는 일:
1. 프레임에서 지도까지 어떤 상태와 관측이 남고 사라지는지 설명한다.
2. 하나의 재투영 잔차에서 pose/landmark Jacobian과 Schur complement를 계산한다.
3. 장소 검색 점수와 기하 검증된 루프 제약을 구분한다.
4. 직접법·특징점법·VIO가 같은 상태를 서로 다른 관측으로 추정함을 설명한다.
5. TSDF·ESDF·occupancy·신경 표현 중 목적에 맞는 지도를 고른다.
6. 학습 기반 대응점, SLAM, 렌더링, VLM, VLA의 출력 경계를 구분한다.

## 1. 장기 카메라 SLAM은 무엇을 기억하고 어떻게 함께 보정하는가?

### Takeaway

장기 SLAM의 핵심은 프레임마다 이동을 추정하는 것만이 아니라, 유용한 관측을 보존하고 재방문에서 과거 상태를 일관되게 고치는 것이다.
키프레임·랜드마크·재투영 최적화·장소 검색은 서로 다른 역할이며 하나의 알고리즘 이름으로 묶어 이해하면 실패 원인을 놓친다.

### Cited Findings

- Georg Klein, David Murray, 2007, **Parallel Tracking and Mapping for Small AR Workspaces**, ISMAR: 추적과 지도 작성을 분리한 키프레임 기반 AR 시스템이다. 논문과 이후 배포 구현의 초기화·재위치추정 구성이 항상 같지는 않다. [논문](https://www.robots.ox.ac.uk/~gk/publications/KleinMurray2007ISMAR.pdf), [저자 프로젝트](https://www.robots.ox.ac.uk/~gk/PTAM/)
- Raul Mur-Artal, J. M. M. Montiel, Juan D. Tardos, 2015, **ORB-SLAM: a Versatile and Accurate Monocular SLAM System**, IEEE T-RO: ORB 특징을 추적·지도 작성·재위치추정·루프 처리에 사용하며 키프레임과 점을 선택적으로 유지한다. [원문](https://arxiv.org/abs/1502.00956)
- Raul Mur-Artal, Juan D. Tardos, 2017, **ORB-SLAM2: an Open-Source SLAM System for Monocular, Stereo and RGB-D Cameras**, IEEE T-RO: 단안 외에 stereo/RGB-D 관측을 지원하고 지도 재사용과 루프 후 최적화를 다룬다. arXiv 최초 공개는 2016년이다. [원문](https://arxiv.org/abs/1610.06475), [저자 서지](https://webdiis.unizar.es/~raulmur/)
- Carlos Campos, Richard Elvira, Juan J. Gomez Rodriguez, Jose M. M. Montiel, Juan D. Tardos, 2021, **ORB-SLAM3: An Accurate Open-Source Library for Visual, Visual-Inertial and Multi-Map SLAM**, IEEE T-RO: 관성 초기화를 MAP 추정으로 다루고 여러 지도를 유지·병합한다. 최초 프리프린트는 2020년이다. [원문](https://arxiv.org/html/2007.11898v2)
- Bill Triggs, Philip McLauchlan, Richard Hartley, Andrew Fitzgibbon, 2000, **Bundle Adjustment - A Modern Synthesis**: 공동 카메라·구조 추정, 희소 최적화, 강건 비용과 gauge를 체계화한다. 1999 워크숍과 2000 출판 연도를 혼동하지 않는다. [저자 보관 원문](https://thoth.inrialpes.fr/people/triggs/pubs/Triggs-hdr-papers.pdf)
- Dorian Galvez-Lopez, Juan D. Tardos, 2012, **Bags of Binary Words for Fast Place Recognition in Image Sequences**, IEEE T-RO: 이진 기술자 vocabulary tree와 장소 검색, 기하 대응 가속을 다룬다. DBoW2는 해당 계열의 라이브러리이며 SLAM 전체가 아니다. [저자 서지](https://doriangalvez.com/publications), [공식 구현과 인용 정보](https://github.com/dorian3d/DBoW2)

### Inferences

아래는 위 문헌에서 출발해 작성한 독자적 교육 설명과 유도다.
논문별 고정 임계값·코드 분기·실행 시간의 완전 재현을 주장하지 않는다.

#### 1.1 먼저 시스템을 상태·관측·결정으로 나눈다

질문은 "매칭이 몇 개 나왔는가?"가 아니라 "어떤 관측이 어떤 상태를 제약했는가?"다.
프레임은 시각 t의 영상과 보정값을 담는 입력 단위다.
키프레임은 이후에도 최적화와 재방문 검색에 사용하기 위해 남긴 프레임이다.
랜드마크는 여러 영상의 관측을 하나의 물리적 장면점으로 묶은 지도 상태다.
관측은 `(keyframe_id, landmark_id, pixel, uncertainty)`라는 연결이다.
동일한 2D 특징이 검출되었다고 곧바로 동일한 3D 점이라는 뜻은 아니다.
지도점 ID를 공유하게 만드는 data association이 잘못되면 BA도 잘못된 문제를 푼다.
이때 최적화 성공 메시지는 데이터 연결이 옳다는 증거가 아니다.

교육용 상태 흐름은 다음과 같다.

```text
영상 + 보정 + timestamp
  -> 기존 지도에 현재 pose 정합
  -> 추적 품질 판단
  -> 새 시점의 정보가 충분하면 키프레임 삽입
  -> 삼각측량 또는 깊이 역투영으로 지도점 후보 생성
  -> 다중 관측 검증 / 중복점 병합 / 불량점 제거
  -> 지역 BA
  -> 장소 후보 검색
  -> 기하 검증
  -> 루프 제약 또는 지도 병합
  -> 전역 보정 및 파생 지도 갱신
```

추적 실패와 지도 실패를 구분한다.
현재 프레임 추적 실패 후 기존 지도에서 재위치추정에 성공할 수 있다.
추적이 계속되더라도 잘못된 점 연결이 누적되어 지도가 왜곡될 수 있다.
새 지도를 만드는 것은 실패를 없앤 것이 아니라 불확실한 연속성을 끊은 것이다.
나중에 지도 병합을 하려면 두 지도의 대응과 상대 변환을 다시 검증해야 한다.

#### 1.2 키프레임은 시간 간격이 아니라 정보와 계산량의 절충이다

매 프레임을 남기면 반복 관측이 많아지고 최적화 비용이 커진다.
너무 드물게 남기면 시점 사이 대응이 끊기고 새 영역을 삼각측량하기 어렵다.
교육용 판단 변수는 공통 지도점 수, 새로운 영역, 시차, 시간 간격, 추적 잔차와 mapper 처리 여유다.
이 변수들은 논문마다 결합 방식이 다르므로 보편적인 한 임계값을 제시하지 않는다.
시차는 카메라 사이 위치 차이 자체가 아니라 같은 점을 보는 광선 방향의 차이다.
먼 점은 같은 이동에서도 작은 시차를 보인다.
회전만으로 픽셀이 많이 움직여도 깊이를 위한 기하적 baseline이 생기지 않을 수 있다.
따라서 픽셀 이동량을 그대로 삼각측량 가능성으로 해석하지 않는다.

수업용 예로 깊이 5 m인 점과 baseline 0.1 m를 생각한다.
작은 각도 근사에서 시차는 약 `0.1/5 = 0.02 rad`다.
같은 baseline에서 깊이 50 m이면 약 `0.002 rad`다.
이는 특정 카메라의 검출 기준이 아니라 baseline/depth 비율의 설명이다.
새 키프레임 선택에서 멀리 있는 점만 많이 보존하면 가까운 구조의 관측이 부족해질 수 있다.
반대로 가까운 점만 택하면 급격한 시점 변화에서 가림이 커질 수 있다.

예상 중간 산출물 `keyframe_decisions`의 한 행에는 다음이 필요하다.
- frame ID, timestamp[s], 후보 키프레임 ID.
- 공통점 수와 전체 후보점 수, 영상 내 분포.
- 회전 보정 전/후 시차 요약, 깊이 범위와 단위.
- 삽입 또는 거절 사유, 당시 mapper 대기열 길이.
- 추적 성공·실패와 새 지도 생성 여부.

그림 명세 K1은 같은 구간의 모든 프레임 위치를 회색, 선택 키프레임을 색으로 표시한다.
그림 아래에는 시차와 추적점 수의 시계열을 같은 시간축으로 놓는다.
촘촘한 키프레임 구간이 어려운 운동 때문인지 정책 오류 때문인지 설명해야 한다.
이 노트에서는 K1을 생성하지 않았다.

#### 1.3 랜드마크의 수명주기

생성 직후 점은 충분히 검증된 고정 진실이 아니다.
처음에는 두 시점 삼각측량이나 한 시점 깊이 센서 측정으로 후보를 얻는다.
양의 깊이 조건, 재투영 잔차, 시차와 관측 가시성을 검사한다.
새 관측이 들어오면 위치·대표 descriptor·관측 목록을 갱신할 수 있다.
점이 예측상 보이는 상황에서 반복해서 매칭되지 않으면 잘못된 점일 가능성이 있다.
하지만 실제 가림이나 조명 변화도 있기 때문에 한 번의 실패로 단정하면 안 된다.
오래된 점의 삭제와 키프레임 삭제는 서로 다른 연산이다.
키프레임이 삭제되어도 다른 관측이 남으면 점은 유지할 수 있다.
점이 삭제되면 그 점을 참조하는 관측과 그래프 통계도 함께 정리해야 한다.
중복점을 병합할 때에는 모든 관측이 실제로 같은 물체의 같은 점인지 검증한다.
ID만 합치고 충돌하는 관측을 남기면 같은 프레임에서 같은 점이 두 픽셀에 나타나는 모순이 생긴다.

지도 유지 상태를 `candidate -> active -> weak -> removed`로 표현하는 것은 교육용 추상화다.
원 논문·라이브러리가 반드시 이 네 enum을 사용하는 것은 아니다.
상태 전이의 근거를 기록해야 지도점 수 감소가 품질 개선인지 추적 붕괴인지 해석할 수 있다.
관측 횟수만 많아도 동일 위치에서 찍은 거의 같은 영상이면 깊이 정보는 약할 수 있다.
관측 횟수와 관측 기하를 함께 본다.

#### 1.4 그래프는 하나가 아니다

공동가시성 그래프의 노드는 키프레임이고 연결은 공유 지도점 관계를 나타낸다.
공유점 수는 이웃 선택에 도움이 되지만 센서 오차 공분산 그 자체는 아니다.
spanning tree는 연결성을 보존하는 뼈대로 사용할 수 있다.
pose graph의 edge는 두 pose 사이 상대 변환과 그 신뢰도를 나타낸다.
BA factor graph에는 pose뿐 아니라 지도점 변수와 각 재투영 관측이 있다.
장소 검색 데이터베이스는 외형 유사도를 위한 색인이다.
이 네 구조를 한 그림에서 같은 종류의 edge로 그리면 의미를 오해하기 쉽다.
권장 그림은 공동가시성 선, 측정 factor, 검색 후보 화살표를 다른 선 종류로 구별한다.

#### 1.5 BA의 입출력 계약부터 고정한다

BA는 Bundle Adjustment, 여러 카메라에서 나오는 관측 광선 묶음의 일관성을 조정하는 문제다.
이 절에서는 보정된 pinhole 카메라, 정적 점, 알려진 내부행렬 K를 가정한다.
왜곡이 남으면 아래 Jacobian 뒤에 왜곡 함수의 미분을 합성해야 한다.
세계점 `P_j^W`는 3차원 열벡터다.
`T_i = T_CiW = (R_i,t_i)`는 세계 좌표를 i번 카메라 좌표로 보낸다.
`p_ij = R_i P_j^W + t_i = (X,Y,Z)^T`다.
`z_ij = (u_obs,v_obs)^T`는 관측 픽셀이다.
잔차 부호는 일관되게 `r_ij = pi(p_ij) - z_ij`로 둔다.
이것은 예측 빼기 관측이며 반대 정의를 쓰는 코드의 Jacobian과 섞지 않는다.
미터 축척이 알려진 예제에서 X,Y,Z,t,P의 단위는 m다.
순수 단안 초기 지도라면 같은 식의 길이 단위는 임의 지도 단위다.
초점거리와 주점, u,v의 단위는 px다.

```text
pi(X,Y,Z) = [fx X/Z + cx, fy Y/Z + cy]^T
E = 1/2 sum_(i,j observed) rho(r_ij^T Sigma_ij^(-1) r_ij)
Sigma_ij : 2x2 pixel covariance [px^2]
s_ij = r_ij^T Sigma_ij^(-1) r_ij : dimensionless
```

관측되지 않은 `(i,j)` 조합에는 잔차를 만들지 않는다.
N개의 카메라와 M개의 점이 있다고 N*M개의 대응이 자동으로 생기는 것이 아니다.
픽셀 covariance의 비대각항은 두 픽셀 성분 오차의 상관을 뜻한다.
단순히 각 축 표준편차를 같은 값으로 두는 것은 모델 가정이다.
강건 손실을 쓴다고 잘못된 관측 노이즈 모델이 사라지는 것은 아니다.

#### 1.6 재투영 Jacobian을 단계별로 유도한다

먼저 3D 점을 픽셀로 보내는 미분을 구한다.
분모 Z를 미분하면 `d(X/Z)/dZ = -X/Z^2`가 나온다.
따라서 다음 2x3 행렬을 얻는다.

```text
J_pi = [ fx/Z       0      -fx X/Z^2
           0     fy/Z      -fy Y/Z^2 ]
```

J_pi의 각 원소 단위는 px/m다.
pose 증분은 `delta_xi = (delta_rho, delta_phi)` 순서의 6차원 벡터로 둔다.
병진 증분 delta_rho의 단위는 m, 회전 증분 delta_phi는 rad다.
업데이트는 왼쪽 곱 `T_new = Exp(delta_xi^) T`로 고정한다.
작은 증분에 대해 `p_new ~= p + delta_rho + delta_phi cross p`다.
외적의 순서를 바꾸면 `delta_phi cross p = -[p]_x delta_phi`다.
여기서 `[p]_x q = p cross q`를 만족하는 3x3 반대칭행렬을 쓴다.
연쇄법칙으로 pose와 점 Jacobian은 다음과 같다.

```text
J_pose = J_pi [ I_3 | -[p]_x ]             # 2x6
J_point = J_pi R_i                         # 2x3
J_pose_translation : px/m
J_pose_rotation    : px/rad
J_point            : px/m
```

회전 성분을 rad로 구분하는 것은 구현상의 단위 실수를 잡기 위해서다.
수학적으로 rad는 무차원으로 취급할 수 있지만 degree 입력과 혼용하면 안 된다.
오른쪽 곱 업데이트는 증분 좌표계가 달라지므로 같은 J_pose를 그대로 쓸 수 없다.
카메라 pose를 `T_WC`로 저장하는 경우에도 역변환의 미분을 반영해야 한다.
내부 보정까지 추정한다면 fx,fy,cx,cy에 대한 추가 열이 필요하다.
예를 들어 `du/dfx = X/Z`, `du/dcx = 1`이다.

교육용 수치로 `p=(1,2,5)m`, `fx=fy=500px`를 넣는다.

```text
J_pi = [100,   0, -20
          0, 100, -40]
J_pose = [100,   0, -20,  -40, 520, -200
            0, 100, -40, -580,  40,  100]
```

`delta_rho_x=0.01m`만 주면 예측 픽셀은 u 방향으로 1px 증가한다.
`delta_phi_z=0.001rad`만 주면 1차 예측은 `(-0.2,+0.1)px`다.
이 예제에서는 z축 작은 회전이 `(X,Y)`를 `(-Y,X)` 방향으로 바꾸는 것도 직접 확인할 수 있다.
숫자가 작다고 유효한 관측인 것은 아니다. Z가 0에 가까우면 투영 자체가 불안정하다.
카메라 뒤의 점 `Z<=0`을 정상적인 재투영 관측으로 최적화하지 않는다.

검증용 산출물 B1은 analytic J와 manifold 중앙차분 J를 나란히 저장한다.
중앙차분은 `r(Exp(+eps e_k^)T)`와 `r(Exp(-eps e_k^)T)`로 계산해야 한다.
회전행렬 원소 하나에 eps를 더하는 검사는 같은 미분이 아니다.
eps를 여러 크기로 바꾸며 절대/상대 오차를 본다.
이 노트의 행렬은 손계산 유도이며 B1 배열을 실행해 생성한 것은 아니다.

#### 1.7 Whitening과 강건 손실은 서로 다른 연산이다

Sigma가 양의 정부호이면 `L^T L = Sigma^(-1)`인 whitening 행렬 L을 잡는다.
`r_bar=Lr`, `J_bar=LJ`로 두면 잔차를 측정 노이즈 기준으로 비교할 수 있다.
L의 단위는 1/px이므로 r_bar는 무차원이다.
다른 센서 잔차를 함께 더하기 전에 이 단위 정리가 필요하다.
픽셀 잔차 제곱과 미터 잔차 제곱을 아무 가중치 없이 더하지 않는다.

여기서는 Huber 손실을 잔차 norm q에 대해 정의한다.

```text
q = ||r_bar||
h_delta(q) = 0.5 q^2                         if q <= delta
             delta(q - 0.5 delta)            otherwise
w(q) = 1                                    if q <= delta
       delta/q                              otherwise
```

이 정의는 `0.5*rho(q^2)` 표현과 맞춰 사용할 수 있다.
IRLS는 Iteratively Reweighted Least Squares, 반복 재가중 최소제곱이다.
현재 q에서 얻은 w로 `sqrt(w)r_bar`와 `sqrt(w)J_bar`를 함께 재가중한다.
잔차만 곱하고 Jacobian은 그대로 두면 다른 정상방정식을 만들게 된다.
교육용으로 q=10, delta=2이면 w=0.2이며 sqrt(w)는 약 0.447214다.
제곱 손실은 50이지만 위 Huber 손실은 `2*(10-1)=18`이다.
큰 잔차의 영향을 줄였을 뿐 관측을 완전히 삭제한 것은 아니다.
같은 잘못된 물체에 수백 개의 대응이 모이면 각각의 가중치를 줄여도 잘못된 운동이 우세할 수 있다.
따라서 강건 손실은 기하 검증이나 동적 물체 분리를 대신하지 않는다.

#### 1.8 Schur complement: 점을 먼저 없애도 pose 정보를 잃지 않는 이유

현재 선형화점에서 `r(x+delta) ~= r + J delta`로 근사한다.
측정 가중행렬을 Lambda로 써서 `H=J^T Lambda J`, `g=J^T Lambda r`라 두면 `H delta=-g`다.
pose 증분을 delta_c, 점 증분을 delta_p로 나눈다.

```text
[ U      W_cp ] [delta_c] = -[g_c]
[ W_cp^T V    ] [delta_p]    [g_p]
```

W_cp는 pose와 point 사이의 블록 교차행렬이며 측정 가중행렬 Lambda와 다르다.
둘째 식은 `V delta_p = -g_p - W_cp^T delta_c`다.
이를 첫째 식에 대입하면 pose만의 식이 된다.

```text
S = U - W_cp V^(-1) W_cp^T
S delta_c = -g_c + W_cp V^(-1) g_p
delta_p = -V^(-1)(g_p + W_cp^T delta_c)
```

서로 다른 점을 직접 연결하는 factor가 없으면 V는 점별 블록 대각이다.
그래서 작은 점 블록을 풀고 비교적 작은 pose 시스템을 풀 수 있다.
`V^(-1)`는 유도를 위한 표기이며 실제 수치 계산은 분해·선형해법으로 수행한다.
관측이 부족한 점은 해당 V 블록이 특이하거나 나쁘게 조건화될 수 있다.
감쇠나 제거 정책 없이 무조건 역행렬을 만들면 안 된다.
Levenberg-Marquardt 감쇠를 넣었다면 감쇠가 포함된 블록 시스템을 일관되게 소거한다.

교육용 스칼라 블록 예제는 `U=6, W_cp=2, V=4, g_c=-8, g_p=-4`다.
`S=6-2*(1/4)*2=5`다.
우변은 `8+2*(1/4)*(-4)=6`이다.
따라서 `delta_c=1.2`, `delta_p=-(1/4)*(-4+2*1.2)=0.4`다.
첫 식에 넣으면 `6*1.2+2*0.4=8`이다.
둘째 식에 넣으면 `2*1.2+4*0.4=4`다.
이 예제의 변수는 무차원이며 실제 카메라 pose와 점의 혼합 단위를 표현한 것이 아니다.

Schur 단계에서 점을 제거해도 같은 선형 문제의 최적 pose 해를 얻는다.
그 다음 점 증분을 복원하므로 지도를 영구히 버린 것이 아니다.
이 점이 다음 절의 시간 marginalization과 중요하게 다르다.

#### 1.9 Gauge: 숫자 부족과 좌표 기준의 자유를 구분한다

순수 단안 관측에서 모든 세계점과 카메라 중심을 같은 비율로 늘려도 투영은 같다.
관측은 상대 구조를 보지만 절대 원점·축 방향·길이 기준은 정하지 않는다.
일반적인 비퇴화 단안 BA에는 전역 translation 3, rotation 3, scale 1의 gauge가 있다.
미터 baseline을 아는 stereo/RGB-D에서는 scale 자유가 제거되어 보통 6개 전역 gauge가 남는다.
이 개수는 연결된 지도와 충분한 기하라는 전제에서 말하는 것이다.
순수 회전, 공선 점, 단절된 지도에는 추가적인 비관측 방향이 생길 수 있다.
첫 pose를 고정하면 6개 기준 자유를 정하지만 단안 scale까지 자동으로 정해지지는 않는다.
단안에서는 한 거리나 baseline 등 별도의 scale 규약이 필요하다.
이 규약은 미터를 관측했다는 뜻이 아니다.

예로 카메라 중심 두 개가 0과 1, 점이 `(1,1,5)`인 임의 단위를 생각한다.
중심과 모든 점을 10배하면 normalized projection은 변하지 않는다.
이때 t도 같은 좌표 규칙으로 바꿔야 한다.
점만 10배하고 카메라 translation을 고정하면 동일한 문제가 아니다.
시각적으로 같은 재투영을 가지는 여러 해는 solver 고장이 아니라 관측 모델의 성질이다.

강한 임의 prior로 H를 가역으로 만들 수는 있다.
그러나 임의 prior가 준 정보를 센서가 준 정보로 해석하면 covariance를 과신한다.
평가에서 Sim(3) 정렬을 사용하면 scale 오차를 정렬 과정에서 제거한다.
따라서 metric 성능을 주장할 때는 scale 정렬 허용 여부를 반드시 적는다.

#### 1.10 Marginalization: 오래된 상태를 버리면서 남기는 정보

실시간 sliding window에서는 모든 과거 프레임을 계속 최적화할 수 없다.
오래된 상태 m을 제거하고 남는 상태 r에 prior를 만든다고 하자.
현재 선형화에서 quadratic cost를 `0.5 delta^T H delta + g^T delta + const`로 쓴다.
블록 소거 결과는 다음과 같다.

```text
H_prior = H_rr - H_rm H_mm^(-1) H_mr
g_prior = g_r  - H_rm H_mm^(-1) g_m
E_prior(delta_r) = 0.5 delta_r^T H_prior delta_r
                   + g_prior^T delta_r + const
```

적절한 비특이 Gaussian 선형 문제에서 적분하여 얻은 marginal과 최적화 소거는 남은 변수의 같은 quadratic 정보를 준다.
정규화 상수는 달라질 수 있지만 상태 최적점에는 영향을 주지 않는다.
비선형 문제에서는 제거 시점의 선형 근사를 보존한 prior다.
원래 영상 관측 전체를 저장한 것과 같지 않다.
상태가 멀리 이동하면 과거 선형화의 유효성이 약해질 수 있다.
Schur BA는 한 iteration 안에서 점을 다시 복원하지만 window marginalization은 상태를 활성 집합에서 영구히 뺀다.
prior는 어떤 기준 상태 x0와 tangent 좌표에서 생성했는지 함께 보존해야 한다.
pose 차이를 단순 quaternion 원소 뺄셈으로 취급하면 prior 의미가 깨진다.
변수 순서나 기준 pose를 바꾸면 prior의 좌표도 일관되게 변환해야 한다.

수업용 두 상태 cost를 `0.5*x0^2 + 0.5*(x1-x0-1)^2`로 둔다.
전개하면 `H=[[2,-1],[-1,1]]`, `g=[1,-1]`다.
x0를 제거하면 `H_prior=1-1/2=0.5`다.
`g_prior=-1-(-1)*(1/2)*1=-0.5`다.
남은 최적점은 `x1=1`이다.
분산은 이 선형 Gaussian 예제에서 `1/H_prior=2`다.
처음 prior variance 1과 상대 관측 variance 1이 합쳐진 결과와 같다.
만약 첫 x0 prior를 없애면 남은 x1에 절대 위치 정보를 만들 수 없다.
이는 marginalization이 없는 정보를 발명해서는 안 된다는 간단한 검산이다.

예상 산출물 B2는 제거 전/후 변수 목록, x0, H_prior, g_prior, rank와 eigenvalue 요약이다.
관측을 prior에 포함한 뒤 같은 관측을 활성 factor로 다시 넣지 않는지 확인한다.
그렇지 않으면 같은 데이터를 두 번 믿는 double counting이 된다.
일관성 유지를 위한 선형화 고정 정책은 사용 추정기별로 검토해야 한다.
본 노트는 특정 FEJ 구현의 정확성을 검증했다고 주장하지 않는다.

#### 1.11 PTAM에서 배울 것과 배울 수 없는 것

PTAM은 Parallel Tracking and Mapping이라는 이름 그대로 두 작업의 주기가 다를 수 있음을 보여준다.
학습 목표는 빠른 현재 pose 추정과 느린 지도 개선을 같은 연산으로 취급하지 않는 것이다.
소규모 AR에서 키프레임과 점을 유지하는 설계는 대규모 장거리 시스템을 이해하는 출발점이 된다.
그러나 "추적과 지도 작성을 분리했다"는 이유만으로 장기 다중 세션 SLAM이 완성되지는 않는다.
지도 검색, 메모리 관리, 재초기화, 전역 일관성은 추가 문제다.
읽고 그릴 중간 그림은 tracker가 읽는 지도 snapshot과 mapper가 갱신하는 상태의 관계다.
병렬화는 계산 성능뿐 아니라 상태 소유권과 일관성 문제를 만든다는 점을 토론한다.

#### 1.12 ORB-SLAM 세대를 기능 축으로 비교한다

ORB-SLAM1이라는 이름은 보통 최초 ORB-SLAM 논문을 후속 버전과 구분하는 통칭이다.
정식 최초 제목에는 숫자 1이 없다.
ORB-SLAM의 수업 축은 특징 재사용, 지역 지도, 키프레임 선택, 장소 인식과 루프다.
ORB-SLAM2의 축은 센서 관측 모델 확장이다.
같은 점을 stereo에서는 좌우 영상으로, RGB-D에서는 픽셀과 깊이로 제약할 수 있다.
깊이가 있으면 scale을 얻기 쉬워지지만 깊이 센서 오차와 invalid pixel 처리가 추가된다.
ORB-SLAM3의 축은 관성 상태와 여러 지도의 수명주기다.
추적 상실 후 다른 지도를 시작하고 이후 장소 인식으로 병합하는 흐름을 배운다.
시스템 제목이 나열하는 센서와 카메라 모델의 모든 조합이 모든 코드 버전에서 동일하게 지원된다는 뜻은 아니다.
실제 재현에서는 선택 버전의 입력 예제와 calibration schema를 별도 확인한다.

세대가 올라간다는 이유만으로 모든 환경에서 더 작은 오차를 보장하지 않는다.
단안 영상만 있는 문제에는 관성 기능이 직접 정보를 추가하지 않는다.
나쁜 시간 동기화의 IMU를 더하면 추정이 악화될 수 있다.
추가 기능은 새 실패 경로와 설정 부담을 함께 만든다.
비교표의 첫 열은 연도가 아니라 입력 센서와 평가 목표여야 한다.

#### 1.13 BoW와 DBoW2: 지도 검색의 입력과 출력

BoW는 Bag of Words, 영상의 local descriptor들을 시각 단어 빈도로 요약하는 표현이다.
여기서 word는 자연어 단어가 아니라 descriptor 공간의 군집 ID다.
vocabulary는 학습 descriptor들을 계층적으로 나눈 색인 구조다.
질의 descriptor는 트리를 따라 가까운 대표 노드로 내려가 word ID를 얻는다.
이진 descriptor 비교에는 Hamming 거리가 자연스럽지만 실수 descriptor용 어휘와 그대로 호환되지는 않는다.
새 SuperPoint descriptor를 기존 ORB vocabulary에 그냥 넣는 것은 올바른 교체가 아니다.
inverted index는 특정 word가 등장한 키프레임을 찾아 전체 비교를 줄인다.
direct index는 영상 안의 feature와 트리 노드 관계를 보존해 후보 사이 대응 탐색을 돕는다.
검색 결과는 `(candidate_id, similarity_score)`이며 상대 pose가 아니다.

교육용 TF-IDF를 다음처럼 정한다.

```text
tf_w = count_w / total_descriptors
idf_w = log(N / n_w)
v_w = tf_w * idf_w
v <- v / ||v||_1
score(a,b) = 1 - 0.5 ||a-b||_1
```

N은 어휘 통계에 쓰인 영상 수, n_w는 word w를 포함한 영상 수다.
구현에는 smoothing과 weighting 선택지가 있으므로 위 식을 모든 DBoW2 설정의 유일한 식이라고 하지 않는다.
희귀한 단어는 더 큰 가중치를 가질 수 있지만 조명·가림·양자화 오류에도 민감할 수 있다.
예로 정규화된 `a=(0.6,0.3,0.1)`, `b=(0.5,0.2,0.3)`이면 L1 차이는 0.4다.
점수는 0.8이다.
이 값은 같은 장소일 확률 80%라는 뜻이 아니다.
반복 복도는 word 비율이 비슷하면서 다른 실제 장소일 수 있다.

#### 1.14 Loop verification은 독립된 기하 문제다

검색 단계에서는 최근 이웃 프레임을 제외하고 과거 후보를 찾을 수 있다.
최근 영상과 닮았다는 것은 당연하며 장기 재방문 발견과 다르다.
후보에 대해 실제 feature 대응과 지도점 대응을 만든다.
2D-2D면 essential/fundamental 모델, 2D-3D면 PnP, 3D-3D면 상대 정합 등을 검토한다.
선택은 사용 가능한 상태와 scale 관측 여부에 달려 있다.
RANSAC은 무작위 부분집합에서 가설을 만들고 전체 대응의 일치도를 검사한다.
inlier 개수 외에 영상 내 분포, 시차, 양의 깊이, residual 분포와 temporal consistency를 확인한다.
한 작은 반복 무늬에 몰린 많은 inlier는 전체 pose를 안정적으로 정하지 못할 수 있다.
추정된 상대변환은 재투영 또는 양방향 정합으로 추가 검증한다.
검증을 통과한 뒤에만 graph edge를 만든다.

교육용 단계별 로그는 다음을 분리해야 한다.
- 검색 후보 수와 각 BoW 점수.
- descriptor 대응 수와 geometric inlier 수.
- 상대변환 모델 종류: SE(3), Sim(3), PnP 등.
- scale, translation, rotation과 각각의 단위.
- 잔차의 중앙값/상위 분위수, 영상 공간 분포.
- 승인/거절 사유와 최종 graph edge ID.

기하 검증이 실패한 후보를 루프 성공으로 집계하지 않는다.
GT가 가깝다는 사실은 평가 label로 쓸 수 있지만 자동 검증기의 입력으로 섞지 않는다.
검색 recall과 verified-loop precision은 다른 지표다.
검색 임계값을 낮추면 후보가 늘 수 있지만 검증 계산량과 오검출 위험도 함께 바뀐다.

#### 1.15 SE(3)와 Sim(3)를 선택하는 이유

SE(3)는 rotation과 translation으로 거리를 보존한다.
Sim(3)는 Similarity transformation group으로 양의 scale s를 추가한다.
`p' = s R p + t`에서 s는 무차원이다.
단안 지도는 구간마다 scale drift가 생길 수 있어 상대 scale 보정이 필요할 수 있다.
metric scale이 관측된 stereo/RGB-D 지도에서는 임의 scale 변경을 허용하면 센서의 길이 기준을 훼손할 수 있다.
그러므로 모델 선택은 "자유도가 많으면 좋다"가 아니라 센서가 제약하는 자유도에 맞춘다.
Sim(3) inverse는 `p = (1/s) R^T (p'-t)`다.
translation을 단순히 -t로 바꾸는 것은 일반적으로 inverse가 아니다.

교육용으로 `s=2, R=I, t=(1,0,0)`이면 `(1,1,1)`은 `(3,2,2)`가 된다.
inverse를 적용하면 `0.5*((3,2,2)-(1,0,0))=(1,1,1)`이다.
여기서 scale 2는 보정 예제의 가정이며 실제 단안 궤적에서 측정한 값이 아니다.

#### 1.16 Pose graph residual의 방향을 검산한다

이 절에서만 설명 편의를 위해 `G_i=T_WCi`를 사용한다.
G_i는 앞 BA의 T_i와 inverse 관계다.
관측 `Z_ij`는 j 카메라 좌표를 i 카메라 좌표로 보내는 상대변환으로 정의한다.
예측 상대변환은 `G_i^(-1)G_j`다.

```text
e_ij = Log(Z_ij^(-1) G_i^(-1) G_j)
E_graph = 1/2 sum e_ij^T Omega_ij e_ij
```

관측과 예측이 같으면 Log의 입력은 항등변환이고 e=0이다.
SE(3)에서는 e가 6차원, Sim(3)에서는 log-scale을 포함해 7차원이다.
Omega는 이 tangent 좌표와 단위에 맞는 information matrix다.
회전과 병진의 covariance를 아무 좌표 변환 없이 다른 edge 방향에 복사하면 안 된다.
BoW 점수를 Omega의 모든 대각 원소로 넣는 규칙은 정당화된 측정 모델이 아니다.
상대변환이 같은 지도 관측에서 계산되었다면 다른 edge와 상관이 있을 수 있다.
독립 edge 가정은 실용적 근사이지 항상 정확한 확률 모델이 아니다.

pose graph를 고친 뒤 landmark와 dense map이 그대로면 서로 다른 좌표 상태가 된다.
희소점은 소속 키프레임의 보정에 따라 옮기거나 추가 BA를 수행한다.
TSDF는 과거 잘못된 pose에서 적분된 값이므로 단순히 최신 camera pose만 바꿔서는 복원되지 않는다.
재적분·변형·submap 이동 같은 별도 전략이 필요하다.
이 연결은 2절의 밀집 지도에서 다시 다룬다.

#### 1.17 풀이형 연습문제: 지도와 최적화

**문제 1.** `p=(1,2,5)m`, f=500px에서 x translation 2cm가 만드는 1차 픽셀 변화는?
**풀이.** J_pose의 첫 열은 `(100,0)^T px/m`다.
0.02m를 곱해 `(2,0)px`다.
이는 세계 카메라 중심 이동이 아니라 앞서 정의한 왼쪽 pose 증분의 결과다.
중심 이동으로 문제를 바꾸면 변환 방향부터 다시 정해야 한다.

**문제 2.** 같은 점에 z축 회전 0.002rad만 적용하면?
**풀이.** 회전 z 열 `(-200,100)^T`에 0.002를 곱한다.
`(-0.4,0.2)px`다.
큰 각도에서 이 결과를 그대로 누적하지 않고 Exp와 재선형화를 사용한다.

**문제 3.** 관측 표준편차가 2px이고 잔차가 `(6,8)px`다. q와 delta=2 Huber weight는?
**풀이.** whitening 후 `(3,4)`, q=5다.
가중치 w=2/5=0.4다.
sqrt(w)는 약 0.632456이며 잔차와 J 모두에 곱한다.
Huber 비용은 `2*(5-1)=8`이다.

**문제 4.** U=6, W_cp=2, V=4, g_c=-8, g_p=-4의 Schur 해를 구하라.
**풀이.** S=5, 축약 우변=6이므로 delta_c=1.2다.
역대입하면 delta_p=0.4다.
두 원래 방정식을 만족하므로 부호를 확인할 수 있다.

**문제 5.** 단안 BA에서 첫 pose를 고정했으니 미터 scale을 얻었다는 주장에 답하라.
**풀이.** 첫 pose 고정은 원점과 축을 정한다.
첫 중심을 기준으로 다른 중심과 점을 함께 scale해도 단안 투영은 같다.
미터 baseline·깊이·관성 운동 등 추가 정보가 없으면 metric scale은 관측되지 않는다.

**문제 6.** 3개 word의 a=(0.6,0.3,0.1), b=(0.5,0.2,0.3)의 점수가 0.8이면 loop edge를 추가해도 되는가?
**풀이.** L1 차이 0.4이므로 점수 계산 자체는 맞다.
그러나 상대 pose와 기하 일치가 없으므로 후보일 뿐이다.
기하 검증을 통과하지 않은 상태에서 edge를 추가하면 지도 전체를 왜곡할 수 있다.

**문제 7.** `0.5*x0^2+0.5*(x1-x0-1)^2`에서 x0를 marginalize하라.
**풀이.** H_prior=0.5, g_prior=-0.5다.
상수항을 제외한 cost는 `0.25*x1^2-0.5*x1`이다.
미분 `0.5*x1-0.5=0`에서 x1=1이며 variance는 2다.
상수를 더해 `0.25*(x1-1)^2`로 표현할 수 있다.

### Gaps

- 논문의 정확한 키프레임 임계값이나 해당 저장소 버전의 세부 구현은 이 연구에서 재실행·검증하지 않았다.
- BA 수치 예제는 교육용 계산이며 실제 KITTI 관측에서 생성한 Jacobian 배열이 아니다.
- 원문에 보고된 정확도·속도 수치는 하드웨어와 설정을 재현하지 않았으므로 이 노트의 우열 근거로 인용하지 않았다.
- 루프 검증기의 실제 false-positive율과 지도 병합 성공률은 미측정이다.
- 병렬 tracker/mapper의 구체적인 lock 정책은 구현 과제가 아니므로 설계 쟁점만 남겼다.

## 2. 직접법·관성 융합·RGB-D는 어떤 관측과 지도 표현을 추가하는가?

### Takeaway

특징점·밝기·IMU·깊이는 서로 다른 물리량을 측정하므로 잔차와 단위를 먼저 구별해야 한다.
좋은 pose, 좋은 표면, 충돌 검사에 적합한 지도는 관련되어 있지만 동일한 산출물은 아니다.

### Cited Findings

- Jakob Engel, Thomas Schops, Daniel Cremers, 2014, **LSD-SLAM: Large-Scale Direct Monocular SLAM**, ECCV: 직접 영상 정합, 반밀집 깊이와 Sim(3) 키프레임 그래프를 사용한다. [저자 프로젝트](https://cvg.cit.tum.de/research/vslam/lsdslam)
- Jakob Engel, Vladlen Koltun, Daniel Cremers, 2018, **Direct Sparse Odometry**, IEEE TPAMI; 프리프린트 2016: 광도 보정을 포함한 희소 직접 최적화로 pose와 inverse depth 등을 함께 추정한다. 이름 그대로 원 기본 시스템은 VO다. [원문](https://arxiv.org/pdf/1607.02565), [출판 연도 확인용 저자 서지](https://www.cvg.cit.tum.de/publications?key=Engel-et-al-pami2018)
- Xiang Gao, Rui Wang, Nikolaus Demmel, Daniel Cremers, 2018, **LDSO: Direct Sparse Odometry with Loop Closure**, IROS: DSO 계열에 루프 탐지와 pose graph 최적화를 추가한다. [원문](https://arxiv.org/abs/1808.01111)
- Anastasios I. Mourikis, Stergios I. Roumeliotis, 2007, **A Multi-State Constraint Kalman Filter for Vision-aided Inertial Navigation**, ICRA: 여러 카메라 pose 관측의 제약을 사용하되 모든 3D feature를 EKF 상태에 넣지 않는다. [저자 원문](https://intra.ece.ucr.edu/~mourikis/papers/MourikisRoumeliotis-ICRA07.pdf)
- Christian Forster, Luca Carlone, Frank Dellaert, Davide Scaramuzza, 2017, **On-Manifold Preintegration for Real-Time Visual-Inertial Odometry**, IEEE T-RO: 회전 군에서 사전적분·noise·bias 보정과 factor graph 결합을 유도한다. 프리프린트는 2015년, DOI에는 2016이 들어간다. [저자 원문](https://dellaert.github.io/files/Forster16tro.pdf), [기관 서지](https://infoscience.epfl.ch/entities/publication/a90bb09d-35a8-4d0b-9640-0e64b3fca64d/articledetails)
- Tong Qin, Peiliang Li, Shaojie Shen, 2018, **VINS-Mono: A Robust and Versatile Monocular Visual-Inertial State Estimator**, IEEE T-RO: 초기화, tightly coupled 최적화, 재위치추정과 4DoF pose graph를 결합한다. 프리프린트는 2017년이다. [원문](https://arxiv.org/pdf/1708.03852), [저자 서지](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/master/support_files/paper_bib.txt)
- Tong Qin, Shaojie Shen, 2018, **Online Temporal Calibration for Monocular Visual-Inertial Systems**, IROS: 시간 offset을 pose·feature 상태와 공동 추정한다. [원문](https://arxiv.org/abs/1808.00692)
- Brian Curless, Marc Levoy, 1996, **A Volumetric Method for Building Complex Models from Range Images**, SIGGRAPH: 정렬된 거리 영상을 가중 signed-distance volume으로 누적하고 등위면을 추출한다. [저자 원문 페이지](https://graphics.stanford.edu/papers/volrange/)
- Richard A. Newcombe, Shahram Izadi, Otmar Hilliges, David Molyneaux, David Kim, Andrew J. Davison, Pushmeet Kohli, Jamie Shotton, Steve Hodges, Andrew Fitzgibbon, 2011, **KinectFusion: Real-Time Dense Surface Mapping and Tracking**, ISMAR: depth 기반 추적과 volumetric fusion을 결합한다. 같은 해 제목이 다른 KinectFusion 논문과 구별한다. [저자 논문 사본](https://www.cs.jhu.edu/~misha/ReadingSeminar/Papers/Newcombe11.pdf), [Microsoft Research 출판 목록](https://www.microsoft.com/en-us/research/project/kinectfusion-project-page/publications/)
- Armin Hornung, Kai M. Wurm, Maren Bennewitz, Cyrill Stachniss, Wolfram Burgard, 2013, **OctoMap: An Efficient Probabilistic 3D Mapping Framework Based on Octrees**, Autonomous Robots: occupied/free/unknown 공간을 확률적으로 표현한다. [저자 원문](https://www.ipb.uni-bonn.de/wp-content/papercite-data/pdf/hornung13auro.pdf)
- Helen Oleynikova, Zachary Taylor, Marius Fehr, Roland Siegwart, Juan Nieto, 2017, **Voxblox: Incremental 3D Euclidean Signed Distance Fields for On-Board MAV Planning**, IROS: TSDF에서 ESDF를 증분 구성하여 장애물 거리 질의를 지원한다. 여기 저자 순서는 열린 저자 PDF 표지 기준이다. [저자 원문](https://helenol.github.io/publications/iros_2017_voxblox.pdf)
- KITTI 공식 Raw/Odometry 설명은 영상·보정·LiDAR·GPS/IMU 등 제공 항목과 benchmark 구성을 구별한다. 등록된 실내 RGB-D 스트림을 제공하는 카메라와 같은 입력은 아니다. [Raw](https://www.cvlibs.net/datasets/kitti/raw_data.php), [Odometry](https://www.cvlibs.net/datasets/kitti/eval_odometry.php)
- Orbbec 공식 SDK 자료는 제품별 지원을 나눈다. Astra라는 이름만으로 정확한 모델·프로토콜·호스트 지원을 확정할 수 없다. [공식 SDK](https://github.com/orbbec/OrbbecSDK)

### Inferences

다음 식은 문헌의 문제 구조를 설명하기 위해 표기와 숫자를 새로 정한 교육용 유도다.
제품 사양이나 논문의 실행 결과를 대신하지 않는다.

#### 2.1 직접법의 질문: 대응 픽셀 좌표 대신 밝기를 맞추면 무엇이 달라지는가?

특징점법은 먼저 대응점을 만든 뒤 그 좌표의 기하 오차를 최소화한다.
직접법은 현재 깊이와 pose로 픽셀을 warp하고 대응 위치의 밝기를 비교한다.
"직접"은 모든 픽셀을 사용한다는 뜻이 아니다.
선택한 소수 픽셀만 사용하는 sparse direct 방법도 가능하다.
반대로 dense flow를 먼저 추정한 뒤 좌표 오차를 최적화하면 dense지만 광도 직접법과는 다르다.
밀도 축과 잔차 종류 축을 별도로 분류해야 한다.

기준 영상 i의 픽셀 p와 inverse depth d를 둔다.
depth는 `Z=1/d`이고 d의 단위는 metric 지도에서 1/m다.
`q=K^(-1) p_tilde`이며 마지막 성분이 1인 normalized ray다.
`P_i=q/d`, `P_j=R_ji P_i+t_ji`로 변환한다.
새 픽셀은 `p'=pi(P_j)`다.
단안 임의 scale 지도에서는 d도 그 지도 단위의 역수다.
영상 밖으로 나간 p'나 가려진 점은 정상 밝기 대응이 아니다.

#### 2.2 광도 모델과 노출

원시 밝기를 raw image I_raw라고 하자.
카메라 응답함수의 inverse G^(-1), vignetting V(p), 노출시간 tau를 구분한다.
설명용 보정 영상은 `I(p)=G^(-1)(I_raw(p))/V(p)`로 정의한다.
이 정의에서는 노출시간은 아직 나누지 않았으므로 잔차에서 tau 비율을 사용한다.
노출까지 이미 나눈 영상에 다시 tau 비율을 적용하면 중복 보정이다.
영상 i와 j의 affine brightness 상태를 `(a_i,b_i)`, `(a_j,b_j)`라 둔다.

```text
alpha_ji = (tau_j / tau_i) * exp(a_j-a_i)
r_photo = [I_j(p') - b_j] - alpha_ji [I_i(p) - b_i]
```

a와 alpha는 무차원이고 b와 r_photo는 사용 보정 영상의 intensity 단위다.
tau 단위는 s이며 비율에서는 소거된다.
서로 다른 문헌의 I 정의가 같지 않으므로 식만 복사하지 말고 보정 순서를 확인한다.
패치 여러 위치의 잔차를 합치면 한 픽셀보다 정보를 늘릴 수 있다.
그러나 한 패치가 서로 다른 깊이 경계를 가로지르면 같은 기하 모델이 깨질 수 있다.
밝기 변화가 단순 affine가 아닌 반사·그림자·포화는 이 모델에 남는 오차다.

교육용으로 I_i=100, I_j=120, tau_i=tau_j, a_i=a_j=0, b_i=0, b_j=20을 둔다.
보정 잔차는 `(120-20)-1*(100-0)=0`이다.
b_j를 0으로 고정하면 잔차는 20이다.
optimizer가 이 20을 pose 이동으로만 줄이려 하면 실제 운동과 밝기 변화가 섞일 수 있다.

#### 2.3 광도 Jacobian과 aperture problem

영상 미분을 `grad I_j = (dI/du,dI/dv)`라고 하자.
단위는 intensity/px다.
warp의 pose 미분은 앞 절의 J_pi와 `[I|-P_j cross]`를 조합한다.

```text
J_photo_pose = grad I_j(p') * J_pi(P_j) * [I | -[P_j]_x]
dP_i/dd = -q/d^2
J_photo_depth = grad I_j(p') * J_pi(P_j) * R_ji * (-q/d^2)
```

pose translation 열 단위는 intensity/m다.
inverse depth 열 단위는 intensity/(1/m)다.
밝기가 일정한 영역은 grad I가 0에 가까워 pose를 거의 제약하지 못한다.
직접법이 코너만 요구하지 않는다는 사실과 완전히 무텍스처에서 운동을 알아낸다는 주장은 다르다.
수직 경계 하나는 주로 경계 법선 방향 이동에 민감하다.
경계 접선 방향 이동은 밝기를 거의 바꾸지 않아 aperture problem이 생긴다.
서로 다른 방향의 gradient를 가진 픽셀들을 공간적으로 분산시키는 이유다.

작은 예로 gradient가 `(4,0) intensity/px`, warp 변화가 `(0.5,2)px`라면 밝기 변화는 2다.
수직 2px 변화는 이 국소 1차 모델에서 보이지 않는다.
최적화 iteration 수를 늘려도 없는 gradient 정보를 새로 만들 수는 없다.
피라미드는 큰 이동을 작은 이동으로 만드는 데 도움을 주지만 깊이·조명 가정의 오류까지 없애지는 않는다.

#### 2.4 LSD-SLAM과 DSO는 목적과 유지 정보가 다르다

LSD-SLAM의 학습 질문은 반밀집 inverse depth와 scale-aware 전역 그래프를 어떻게 연결하는가다.
DSO의 질문은 활성 window 안에서 geometry·pose·밝기 등을 함께 어떻게 정교하게 추정하는가다.
DSO 결과를 누적해 경로를 그렸다고 자동으로 루프가 닫힌 것은 아니다.
LDSO는 그 부족한 장기 제약을 추가하는 후속 분기다.
따라서 "LSD-SLAM이 오래되었으니 DSO가 모든 기능을 대체했다"는 설명은 틀리다.
직접법 실습에서 기대할 출력은 원본/warp 영상, 광도 잔차, gradient 선택 mask, inverse-depth uncertainty다.
재투영 좌표 오차만 저장하면 photometric calibration 실패를 설명하기 어렵다.
흑백 intensity를 사용했다는 사실만으로 RGB 채널의 모든 정보가 사용되었다고 말하지 않는다.

#### 2.5 VIO의 상태와 센서 계약

VIO는 Visual-Inertial Odometry, 시각-관성 오도메트리다.
VINS는 Visual-Inertial Navigation System, 시각-관성 항법 시스템을 뜻한다.
최소 교육 상태는 `x_i=(R_WBi,p_WBi,v_WBi,b_gi,b_ai)`다.
R은 body에서 world로의 회전, p는 위치[m], v는 속도[m/s]다.
b_g는 자이로 bias[rad/s], b_a는 가속도 bias[m/s^2]다.
센서 외부변환 `T_BC`와 시간 offset t_d[s]를 고정하거나 추정 상태에 포함할 수 있다.
"외부 보정"은 센서 간 고정 변환이고 매 시점의 세계 pose와 다르다.
내부 카메라 보정, IMU noise density, bias random walk, timestamp clock domain도 필요하다.
이 값들이 없으면 영상과 IMU 숫자를 함께 읽는 것만으로 재현 가능한 VIO 입력이 되지 않는다.

세계 중력은 예를 들어 `g_W=(0,0,-9.81)m/s^2`로 정한다.
측정 가속도는 비력이며 `a_m=R_WB^T(a_W-g_W)+b_a+n_a`다.
회전 측정은 `omega_m=omega+b_g+n_g`다.
정지한 수평 IMU에서 축 정의에 따라 중력 반대 방향의 비력이 나오는 이유를 먼저 확인한다.
g를 두 번 더하거나 빼는 오류는 정지 테스트로 잡을 수 있다.
noise density와 discrete sample variance는 단위와 샘플 간격을 통해 변환해야 한다.
데이터시트의 수치를 단위 확인 없이 covariance 대각에 복사하지 않는다.

#### 2.6 MSCKF: 점을 상태에 넣지 않고 점의 정보를 쓰는 방법

MSCKF는 Multi-State Constraint Kalman Filter다.
현재 IMU 상태와 여러 과거 카메라 pose clone을 유지한다.
한 정적 feature의 여러 관측을 쌓으면 선형화된 식을 얻는다.

```text
r = H_x delta_x + H_f delta_f + n
```

delta_f는 해당 3D 점 위치의 불확실한 증분이다.
그 점을 영구 상태로 추가하지 않고 제거하고 싶다.
H_f의 left nullspace basis N을 구하면 `N^T H_f=0`이다.
양변에 N^T를 곱한다.

```text
r_o = N^T r = N^T H_x delta_x + N^T n
R_o = N^T R N
```

점 증분은 없어졌지만 여러 pose의 상대 기하 정보는 남는다.
noise가 isotropic이고 N 열이 orthonormal이면 noise 처리가 단순해진다.
일반 covariance에서 projection 후 noise를 원래와 같다고 놓으면 안 된다.
5개 영상에서 한 점을 관측하면 픽셀 잔차는 10차원이다.
H_f rank가 3이면 left nullspace 차원은 7이다.
이는 남는 식 수를 뜻하며 pose의 모든 자유도를 독립적으로 관측했다는 뜻은 아니다.
rank가 다른 퇴화 상황에서는 차원과 정보량을 별도 해석한다.
영구 landmark map을 유지하지 않는 구조와 장소 재방문 기능의 존재는 별도 문제다.
MSCKF라는 이름만으로 loop closure까지 구현되었다고 가정하지 않는다.

#### 2.7 사전적분은 IMU를 버리는 것이 아니라 상대 factor로 압축하는 것이다

카메라 i와 j 사이에 고주파 IMU 샘플이 여러 개 있다고 하자.
매 optimization iteration마다 모든 샘플을 세계 좌표에서 재적분하면 계산이 반복된다.
사전적분은 시작 body 좌표에서 상대 회전·속도·위치 변화를 요약한다.
이 절은 구간 내 bias가 일정하다는 1차 교육 모델을 사용한다.
정밀 구현에서는 covariance와 bias Jacobian을 함께 전파한다.

```text
DeltaR_ij = R_i^T R_j
Deltav_ij = R_i^T (v_j-v_i-g_W DeltaT)
Deltap_ij = R_i^T (p_j-p_i-v_i DeltaT-0.5 g_W DeltaT^2)
```

DeltaR은 회전, Deltav는 m/s, Deltap는 m다.
이 식은 참 상태가 만족할 상대량의 정의다.
실제 IMU에서 계산한 hat-Delta와 상태에서 예측한 Delta를 비교해 residual을 만든다.
교육용 discrete 적분은 다음 순서로 설명할 수 있다.

```text
Deltap_next = Deltap + Deltav*dt + 0.5*DeltaR*(a_m-b_a)*dt^2
Deltav_next = Deltav + DeltaR*(a_m-b_a)*dt
DeltaR_next = DeltaR * Exp((omega_m-b_g)*dt)
```

세 식 우변은 같은 이전 step의 DeltaR,Deltav를 사용한다고 정의한다.
실제 midpoint 적분과는 차이가 있는 교육용 전진 모델이다.
샘플 dt가 균일하다고 가정하지 않고 timestamp 차이를 사용한다.
camera interval의 경계에 걸린 IMU 샘플은 보간·분할 정책을 명시한다.

회전 residual은 예를 들어 `r_R=Log(hat_DeltaR^T R_i^T R_j)`로 둔다.
속도 residual은 `r_v=R_i^T(v_j-v_i-g DeltaT)-hat_Deltav`다.
위치 residual도 위 정의에서 hat_Deltap를 뺀다.
이 세 residual의 차원은 각각 3이고, bias 변화 residual을 더하면 흔히 15차원 factor를 구성한다.
회전·속도·위치 오차에는 상관이 생기므로 대각 covariance만 쓰는 것은 추가 근사다.
각 residual을 covariance로 whitening한 뒤 시각 residual과 결합한다.

#### 2.8 Bias 보정은 왜 필요한가?

사전적분은 기준 bias b0에서 수행된다.
최적화가 bias를 바꾸면 같은 측정의 해석도 달라진다.
작은 delta_b에서는 저장한 Jacobian으로 1차 보정할 수 있다.

```text
Deltav(b0+delta_b) ~= Deltav(b0) + J_v_bg delta_bg + J_v_ba delta_ba
Deltap(b0+delta_b) ~= Deltap(b0) + J_p_bg delta_bg + J_p_ba delta_ba
DeltaR(b0+delta_bg) ~= DeltaR(b0) Exp(J_R_bg delta_bg)
```

큰 bias 변화에서는 이 근사가 부족해 재적분이 필요할 수 있다.
사전적분을 한 번 했으니 bias를 바꾸어도 그대로 써도 된다는 뜻이 아니다.
bias Jacobian은 센서 축과 회전 perturbation 정의에 종속된다.
다른 논문에서 가져온 Jacobian을 좌표계 확인 없이 혼합하지 않는다.

단순 1D 예제로 중력을 이미 제거한 가속도 2m/s^2, dt=0.1s를 두 번 적분한다.
시작 속도와 위치가 0이면 최종 속도는 0.4m/s다.
최종 위치는 `0.5*2*(0.2)^2=0.04m`다.
이는 3D 사전적분을 완전 재현한 것이 아니라 단위와 시간 항의 검산이다.
회전과 bias가 있으면 가속도 방향도 바뀌므로 단순 스칼라 합으로 대체할 수 없다.

#### 2.9 VINS 초기화: 한꺼번에 모든 미지수를 푸는 문제가 아니다

단안 영상만으로 만든 초기 구조는 scale이 정해지지 않는다.
IMU에는 중력·속도·bias와 외부 보정의 불확실성이 있다.
초기화의 목표는 이 서로 다른 정보를 일관된 metric 상태로 연결하는 것이다.
교육 흐름은 시각 상대 구조 확보, 자이로 bias 검토, scale·중력·속도 정합, 중력 크기 제약과 비선형 refinement다.
이는 이해를 위한 단계화이며 모든 VIO 시스템이 동일한 순서와 식을 쓰는 것은 아니다.
ORB-SLAM3처럼 초기화를 MAP 추정 관점에서 구성하는 분기도 있다.
초기화 성공 여부는 solver return code만으로 판단하지 않는다.
양의 scale, 합리적인 gravity magnitude, bias 크기, residual와 condition을 함께 점검한다.

이를 수식으로 보려면 시각 카메라 중심을 임의 단위의 c_i, scale을 s[m/시각 단위]로 둔다.
외부 lever arm이 0이고 시각 회전이 세계축과 정렬된 교육용 단순화를 가정한다.
그러면 IMU 위치는 `p_i=s*c_i`로 쓸 수 있다.
앞 절의 사전적분 정의를 위치와 속도 갱신식으로 다시 정리한다.

```text
s*(c_j-c_i) = v_i*DeltaT + 0.5*g*DeltaT^2 + R_i*hat_Deltap_ij
v_j-v_i     = g*DeltaT + R_i*hat_Deltav_ij
```

위 식에서 c_i와 회전, 사전적분값을 잠시 고정하면 s, 각 v_i, g에 대해 선형인 부분 문제가 된다.
여러 시간 구간을 쌓아 풀고 gravity 크기 제약을 추가하여 refinement하는 직관을 얻는다.
실제 camera-IMU translation이 있으면 `p_C=p_B+R_WB*t_BC`를 사용해 lever arm을 포함한다.
그때 시각 중심 c와 IMU 위치를 같은 값으로 놓으면 회전 중 위치 오차를 만든다.
bias가 바뀌면 hat-Delta도 보정해야 하므로 이 선형 부분 문제만으로 전체 초기화가 끝나는 것은 아니다.
가속도·자세 변화가 빈약하면 scale과 속도·중력·bias를 구분하는 열들이 약하게 제약될 수 있다.
이것이 초기화 성공 여부를 조건수와 residual로 확인해야 하는 이유다.

별도 검산 예제로 중력이 제거된 1D에서 c_j-c_i=0.5 시각 단위, DeltaT=1s라 하자.
v_i=0m/s가 독립적으로 알려졌고 사전적분 위치 변화가 1m이면 s=2m/시각 단위다.
하지만 v_i도 미지수이면 식은 `0.5*s=v_i+1`뿐이다.
예를 들어 `(s,v_i)=(2,0)`과 `(4,1)`이 모두 성립하므로 이 한 구간만으로 scale을 정할 수 없다.
여러 관측을 추가하는 이유를 "식이 많아진다"보다 "혼동되던 상태를 구분한다"로 설명한다.

운동 excitation은 미지 상태를 구분할 수 있게 충분히 다양한 관측을 만드는 움직임이다.
계속 정지해 있으면 중력 방향 일부를 관찰할 수 있어도 단안 translation scale은 얻기 어렵다.
등속 직선 이동은 다양한 가속 운동에 비해 scale과 bias 분리가 약해질 수 있다.
회전만으로 외부 rotation을 제약할 수 있어도 translation scale의 모든 정보가 생기지는 않는다.
카메라-IMU lever arm이 있으면 회전이 유발하는 운동까지 고려해야 하므로 모든 순수 회전 상황을 같은 식으로 단정하지 않는다.
안전한 소규모 실험에서는 여러 방향의 완만한 회전·이동을 제공하고 excitation 지표를 기록한다.
불충분한 구간을 억지로 초기화하기보다 관측을 더 기다리는 정책도 필요하다.

이상적인 충분한 excitation의 VIO는 metric scale과 gravity 방향을 제약할 수 있다.
외부 절대 위치·방위 정보가 없으면 전역 translation과 gravity축 yaw는 보통 남는다.
gravity alignment 후 4DoF 전역 그래프를 설명하는 배경이다.
여전히 관측되지 않는 자유도를 제거한 covariance를 절대 위치 신뢰도로 해석하지 않는다.

#### 2.10 시간 보정은 위치 보정과 다르다

카메라 시각 t_C와 대응 IMU 시각을 `t_I=t_C+t_d`로 정의한다.
t_d의 부호는 이 정의에 묶이며 반대 정의의 구현에 그대로 입력하면 안 된다.
normalized feature q의 시간 미분 q_dot를 알고 있다면 작은 offset에서 `q(t+t_d) ~= q(t)+q_dot*t_d`다.
픽셀 좌표로 쓰면 q_dot 대신 pixel velocity[px/s]를 쓴다.
시간 offset residual Jacobian에는 이 시간 미분이 들어간다.
정지 영상은 시간 이동을 주어도 거의 달라지지 않아 offset을 식별하기 어렵다.
일정한 단순 운동에서는 외부변환이나 bias와 강하게 결합될 수 있다.
따라서 시간 calibration도 관측가능성 문제다.

교육용 feature의 pixel velocity가 `(80,-20)px/s`이고 t_d=0.01s라면 보간 변화는 `(0.8,-0.2)px`다.
예측된 pixel p0와 관측 z에 대해 `r=p0+v_pixel*t_d-z`로 두면 `dr/dt_d=v_pixel`이다.
이 Jacobian의 단위는 px/s다.
앞서 정의한 offset 부호를 바꾸면 보간식과 Jacobian 부호도 함께 바꿔야 한다.
같은 pixel velocity에서 허용 보간 오차 norm을 0.5px로 정한 교육용 기준은 `|t_d|<=0.5/sqrt(80^2+20^2)`다.
약 0.00606s이며 특정 센서의 동기화 합격 기준이 아니라 운동에 따른 예시다.

노출시간, timestamp 기준 시점, rolling shutter row readout, 전송 지연, clock drift는 서로 다르다.
상수 t_d 하나로 모든 시간 오류를 설명하지 못할 수 있다.
하드웨어 동기화가 가능하면 먼저 그것을 검증하고 온라인 추정은 잔여 오차 모델로 본다.
GT 궤적을 가장 잘 맞추는 offset을 고른 뒤 이를 무감독 온라인 성능으로 보고하지 않는다.
그런 정렬은 oracle 또는 calibration 단계로 분리해야 한다.

#### 2.11 RGB-D reconstruction의 목표부터 고른다

RGB-D는 color와 depth 관측을 제공하지만 결과 지도 형식은 따로 선택해야 한다.
점군은 관측된 3D 점의 집합이다.
surfel은 위치·법선·크기·색 등 국소 표면 요소다.
mesh는 정점과 면 연결로 표면을 표현한다.
TSDF는 표면 근처의 signed distance를 voxel에 누적한다.
occupancy는 공간이 점유되었을 확률과 관측 여부를 표현한다.
ESDF는 가까운 장애물/표면까지의 유클리드 거리를 제공한다.
같은 입력으로 여러 지도 레이어를 만들 수 있으며 각 레이어의 목적이 다르다.
"밀집 지도"라는 말만으로 충돌 검사, 렌더링, 치수 측정에 모두 적합하다고 말하지 않는다.

#### 2.12 Depth 역투영과 RGB 정렬

깊이가 카메라 optical axis의 Z라면 `P_C=Z*K^(-1)p_tilde`다.
센서가 광선을 따른 range를 준다면 ray를 unit length로 정규화해야 한다.
이 두 의미를 혼동하면 영상 가장자리에서 깊이 편향이 생긴다.
raw depth를 m로 바꾸는 scale은 메타데이터로 확인한다.
invalid depth 0, NaN, saturated 값은 실제 표면 0m와 구분한다.
depth와 RGB 해상도가 같아도 시점과 광선이 같지는 않다.
depth 좌표의 점을 `T_color_depth`로 보낸 뒤 color K로 투영해야 색을 붙일 수 있다.
가림 때문에 여러 depth 점이 같은 color pixel로 갈 수 있으므로 z-buffer 같은 visibility 처리가 필요하다.
등록 과정에서 생긴 hole을 임의 보간한 값은 원래 센서 측정과 구분한다.
움직이는 장면에서는 공간 calibration만으로 시간 어긋남을 해결하지 못한다.

예제로 fx=500px, cx=320px, u=420px, Z=2m이면 X=0.4m다.
Z를 range로 오해해 동일 식을 사용하면 원래 정의와 다른 좌표가 된다.
교재에서는 중심 픽셀과 가장자리 픽셀을 둘 다 보여 이 차이를 확인한다.

#### 2.13 KinectFusion식 연결: 추적한 pose가 다음 지도를 만든다

depth로 만든 현재 vertex/normal과 기존 지도에서 raycast한 표면을 정합한다고 하자.
point-to-plane residual은 `r=n^T(T p-q)`다.
p는 현재 점, q는 예측 표면점, n은 q의 단위 법선이다.
좌표를 m로 두면 residual도 m다.
추정 pose로 현재 depth를 volume에 통합하고 다음 프레임에서 그 volume을 예측에 사용한다.
잘못된 pose가 지도에 들어가면 이후 tracking의 reference도 잘못될 수 있다.
그러므로 tracking 품질이 낮은 프레임은 integration을 보류하는 정책을 검토한다.
특징이 없는 평면은 depth가 있어도 평면 내 이동이나 회전 일부에 약한 기하를 만들 수 있다.
깊이가 있다는 사실이 모든 6DoF를 항상 관측한다는 뜻은 아니다.

중간 산출물 D1은 depth validity, vertex map, normal map, correspondence mask, ICP residual이다.
결과 mesh만 보여주면 추적이 망가진 순간을 찾기 어렵다.
관측 범위와 voxel 크기에 따른 세부 형상 소실도 별도로 기록한다.

#### 2.14 TSDF의 정의와 가중 적분

TSDF는 Truncated Signed Distance Function이다.
이 절의 부호는 카메라와 관측 표면 사이가 양수, 표면 뒤쪽이 음수다.
voxel 중심 x를 현재 카메라로 보낸 위치의 z를 z_x라 하자.
해당 투영 pixel의 유효 depth가 D(u)이면 projective distance는 `s=D(u)-z_x`다.
truncation 길이 mu[m]를 정한다.

```text
f_obs = clip(s/mu, -1, +1)
F_new = (W_old F_old + w_obs f_obs)/(W_old+w_obs)
W_new = W_old+w_obs
```

F는 이 정규화 정의에서 무차원이다.
미터 단위 TSDF를 저장하는 구현도 있으므로 저장 형식을 확인한다.
s가 -mu보다 훨씬 작은 가려진 표면 뒤 영역을 모든 ray에서 무조건 음수로 갱신하지 않는다.
valid band와 free-space carving 정책을 별도로 정한다.
W는 관측 신뢰도의 누적이며 선택한 weight 모델에 따라 의미가 달라진다.
모든 프레임을 독립 동일 noise 관측으로 보는 것은 실용적 근사다.
최대 weight cap을 쓰면 오래된 지도 적응성이 달라지고 단순 순서 독립성도 달라질 수 있다.

교육용으로 F_old=0.5, W_old=2, f_obs=-0.25, w_obs=1이면 F_new=0.25다.
W_new=3이다.
mu=0.1m라면 같은 정규화 단위의 값 0.25는 0.025m에 대응한다.
하지만 이것을 모든 방향에서의 정확한 최근접 표면거리라고 읽으면 안 된다.
projective signed distance와 Euclidean distance는 기울어진 표면에서 다를 수 있다.
여러 관측의 융합과 truncation도 그 해석에 영향을 준다.

#### 2.15 TSDF에서 표면을 꺼내는 의미

F=0의 등위면이 표면 후보가 된다.
이웃 voxel의 부호 변화와 interpolation으로 표면 위치를 얻는다.
예로 위치 x0=0m에서 F0=0.2, x1=0.1m에서 F1=-0.3이면 선형 zero crossing은 x=0.04m다.
계산은 `x0+(x1-x0)*F0/(F0-F1)`이다.
이는 해당 두 값 사이 선형 근사이지 원래 실제 표면이 반드시 0.04m라는 보장은 아니다.
메시를 촘촘하게 추출해도 입력 depth 해상도와 pose 정확도가 늘어나는 것은 아니다.
W=0인 미관측 voxel에서 임의 F=0을 표면으로 추출하면 가짜 면이 생긴다.
따라서 값과 observation mask를 함께 저장한다.

그림 D2는 동일 단면에서 F, W, 유효 관측 mask, zero crossing을 나란히 보여준다.
F만 색칠하면 unknown과 실제 표면이 혼동될 수 있다.
voxel 축은 m로 표시하고 voxel size와 mu를 캡션에 적는다.

#### 2.16 Occupancy와 log-odds

occupancy는 특정 voxel이 점유되었을 확률 p를 표현한다.
확률을 log-odds `l=log(p/(1-p))`로 바꾸면 증거 누적을 덧셈으로 표현할 수 있다.
사전확률 p0의 log-odds를 l0라 하자.

```text
l_t = l_(t-1) + logit(p(m|z_t)) - l0
p_t = 1/(1+exp(-l_t))
```

이 식은 선택한 inverse sensor model과 조건부 독립 근사에 의존한다.
광선 끝점 근처에는 occupied 증거, 그 앞 통과 공간에는 free 증거를 준다.
반환점 뒤는 보지 못했으므로 일반적으로 unknown을 유지한다.
센서 무반환을 무한 거리 free-space 증거로 해석할지는 센서 모델에 따라 달라진다.
검은 물체나 유리에서 무효 depth가 나왔다고 그곳이 비어 있다고 결론내리지 않는다.
Octree는 공간을 8개 자식으로 나누는 계층 표현이다.
occupied 확률의 의미와 공간 압축 구조는 별개의 설계 축이다.

교육용 p0=0.5, hit 모델 0.7이면 log-odds 증분은 약 0.847298이다.
독립 hit를 두 번 받으면 odds는 `(0.7/0.3)^2=49/9`다.
확률은 `49/58 ~= 0.844828`이다.
연속 영상의 비슷한 depth는 상관되어 있으므로 이 숫자를 실제 confidence로 그대로 믿지 않는다.
clamping은 수치 포화와 적응 속도를 조절하지만 상관 문제의 완전한 해결책은 아니다.

#### 2.17 ESDF는 로봇이 표면에서 얼마나 떨어졌는지 묻는다

ESDF는 Euclidean Signed Distance Field다.
장애물 경계 집합 S에 대해 외부 점의 이상적 거리는 `d(x)=min_(y in S)||x-y||`다.
단위는 m이며 내부/외부를 정의할 수 있을 때 부호를 붙인다.
trajectory optimizer는 이 거리와 gradient를 사용해 장애물에서 떨어지게 만들 수 있다.
TSDF는 표면 reconstruction에 편리하고 ESDF는 거리 질의에 편리하다.
두 표현을 같은 배열이라고 취급하지 않는다.
Voxblox의 학습 핵심은 표면 부근 정보에서 넓은 공간의 distance field를 갱신하는 연결이다.
unknown 영역의 distance를 안전한 양수 거리로 취급하지 않는 정책이 필요하다.

교육용 로봇 반지름 r=0.3m, 여유 margin=0.1m, ESDF 거리 0.35m라면 clearance는 -0.05m다.
공식은 `d-r-margin`이다.
양수가 아니므로 이 단순 구형 모델에서는 요구 여유를 만족하지 못한다.
실제 로봇은 형상·자세·동적 장애물·지도 오차를 포함해야 한다.
이 계산은 비행 제어 안전성을 인증하는 기준이 아니다.

#### 2.18 루프 보정 이후 dense map의 수명주기

희소 SLAM은 과거 pose를 수정할 수 있다.
TSDF는 과거 pose로 투영된 depth를 이미 평균에 섞어 두었다.
이때 마지막 pose만 바꾸면 벽의 이중 표면은 그대로 남는다.
원 관측과 적분 정보를 보존했다면 이전 기여 제거 후 새 pose로 재적분할 수 있다.
압축·weight cap·비선형 필터 때문에 정확한 역적분이 항상 간단한 것은 아니다.
다른 선택은 작은 local submap을 만들고 global graph에서는 submap transform을 최적화하는 것이다.
이때 submap 내부 drift와 경계 불일치가 별도 문제가 된다.
표면 deformation은 빠르게 시각적 정합을 고칠 수 있지만 metric 거리와 topology를 다시 확인해야 한다.
각 선택은 저장량, 보정 비용, 원 관측 재사용 가능성의 절충이다.

지도 export에는 world frame ID, scale, 생성 pose 버전, integration 설정을 함께 남긴다.
보정 전 mesh와 보정 후 trajectory를 한 장면에 겹치면 시각화 자체가 거짓 비교가 된다.
같은 지도 버전의 산출물끼리 연결되어야 한다.

#### 2.19 실내 Astra와 실외 KITTI의 실험 질문은 다르다

현재 저장소 기록에서 Astra 정확한 모델과 RGB-D streaming은 미확인이다.
따라서 이 노트는 거리 범위·정확도·fps·실외 동작 가능성을 제품 실측값처럼 제시하지 않는다.
실내 depth camera 실험에서는 단위·registration·짧은 거리의 표면·가림·반사·무효값을 먼저 본다.
능동 광학 방식이라면 주변 조명과 표면 반사 특성의 영향을 제품별로 확인해야 한다.
모든 Astra 제품이 같은 기술과 같은 sunlight 내성을 가진다고 가정하지 않는다.
KITTI 실외 영상에서는 먼 깊이, 전진 운동, 자동차·보행자, 노출 변화와 stereo disparity 불확실성이 중요하다.
LiDAR 투영 depth는 보통 희소하며 카메라와 위치·시각·가림이 다를 수 있다.
희소 투영을 채워 만든 dense depth는 원래 센서가 모든 pixel을 측정한 것이 아니다.
센서 유래 depth, stereo 추정 depth, 학습 추정 depth, GT depth를 별도 표시한다.

KITTI Odometry 영상 번호와 Raw OXTS를 이름만 보고 결합하지 않는다.
정렬 검증 전에는 입력 IMU라고 주장할 수 없다.
OXTS fused GPS/INS pose를 IMU acceleration처럼 넣으면 평가 정보가 유입될 수 있다.
보유 파일 존재와 알고리즘에 사용할 수 있는 관측 계약 완성은 다른 상태다.
실내 한 방 reconstruction 성능을 실외 자동차 SLAM 성능으로 일반화하지 않는다.

#### 2.20 지도와 사실적인 디지털 트윈의 차이

사진처럼 보이는 표면은 visual inspection에 도움이 된다.
하지만 metric 치수, 관통하지 않는 collision mesh, 물리 재질, 관절, 질량, 센서 모델은 별도 요구사항이다.
디지털 트윈이라는 용어를 사용할 때 이 교재는 무엇을 검증한 복제인지 범위를 명시한다.
예를 들어 "시각화용 장면 복원"과 "충돌 검사 가능한 metric 지도"를 다른 결과로 표기한다.
렌더링의 빈틈을 줄이기 위한 보간이 실제 측정된 자유 공간을 늘리는 것은 아니다.
그럴듯한 벽 뒤 geometry는 로봇의 탐색 근거가 될 수 없다.
기하 관측 layer와 시각적 보완 layer를 분리하면 이런 혼동을 줄일 수 있다.

#### 2.21 풀이형 연습문제: 직접법·관성·밀집 지도

**문제 8.** gradient `(4,0)`에 warp displacement `(0.5,2)px`가 주어졌다. 1차 밝기 변화는?
**풀이.** 내적 `4*0.5+0*2=2` intensity 단위다.
두 번째 이동 성분은 이 관측 하나로 제약하지 못한다.
두 성분 모두를 추정하려면 다른 gradient 방향 등의 추가 정보가 필요하다.

**문제 9.** 5개 영상의 2D 관측을 쌓은 MSCKF 잔차에서 H_f rank가 3이면 projection 후 최대 잔차 차원은?
**풀이.** 원래 10차원에서 3을 제거하여 7차원이다.
7차원이라는 사실만으로 pose state rank가 7이 되는 것은 아니다.
남은 H_x와 운동 기하를 확인해야 한다.

**문제 10.** 중력을 제거한 2m/s^2 가속도를 0.2s 적분하라. 초기 속도는 0이다.
**풀이.** 속도는 0.4m/s, 위치 변화는 0.04m다.
가속도 bias가 추가로 0.1m/s^2였다면 같은 단순 모델의 위치 오차는 0.002m다.
이는 3D 회전 오차로 중력이 누출되는 경우를 포함하지 않는다.

**문제 11.** F_old=0.5, W_old=2, f_obs=-0.25, w=1의 TSDF를 갱신하라.
**풀이.** 분자는 1-0.25=0.75, 분모는 3이다.
F_new=0.25, W_new=3이다.
mu=0.1m이면 정규화 값의 환산은 0.025m지만 ESDF로 해석하지 않는다.

**문제 12.** prior 0.5인 occupancy cell에 독립 hit probability 0.7을 두 번 적용하라.
**풀이.** log-odds가 두 번 더해져 odds=49/9다.
p=49/58=0.844828이다.
같은 depth frame을 두 번 넣었다면 독립 관측이 아니므로 이 confidence 증가는 정당화되지 않는다.

**문제 13.** ESDF d=0.35m, 로봇 반지름 0.3m, margin 0.1m의 clearance는?
**풀이.** 0.35-0.3-0.1=-0.05m다.
요구한 margin을 5cm 부족하게 만족하지 못한다.
지도 오차를 무시한 구형 로봇 교육 모델이라는 한계도 함께 답해야 한다.

**문제 14.** depth가 2m, fx=500px, cx=320px, u=420px일 때 X를 구하라.
**풀이.** optical-axis depth 가정에서 X=(420-320)*2/500=0.4m다.
range depth이면 ray 정규화를 먼저 해야 하므로 같은 공식을 무조건 적용하지 않는다.

### Gaps

- MSCKF 저자 PDF는 검색에서 본문이 확인되었으나 직접 열기 요청 한 번이 timeout이었다. 세부 구현 재현까지 완료한 것으로 표기하지 않는다.
- KinectFusion Microsoft 논문 페이지의 추정 URL은 404였다. 검증 가능한 논문 사본과 공식 연구 데모를 연결했고 다른 제목의 논문과 혼합하지 않았다.
- Astra 모델·firmware·실제 depth scale·수집 해상도·host SDK 조합은 미확인이다.
- Raw OXTS와 Odometry 정렬은 기존 문서의 미완료 상태를 유지한다.
- 광도 calibration 파일, IMU noise calibration, 실내 GT, dense reconstruction GT는 이 연구에서 조사·생성하지 않았다.
- TSDF/ESDF/occupancy 예제는 알고리즘 실행 결과가 아니라 손계산 모델이다.
- 환경별 최적 voxel size, mu, depth threshold, VIO 초기화 성공률은 후속 실험 항목이다.

## 3. 학습·의미·신경 지도는 무엇을 바꾸며 어떻게 공부하고 검증해야 하는가?

### Takeaway

학습은 특징 검출·매칭·반복 추정·지도 표현·의미 해석·행동 정책 중 서로 다른 층에 들어간다.
더 사실적인 렌더링이나 더 좋은 매칭만으로 metric SLAM, 충돌 안전성, 언어 기반 행동이 함께 해결되지는 않는다.

### Cited Findings

- Daniel DeTone, Tomasz Malisiewicz, Andrew Rabinovich, 2018, **SuperPoint: Self-Supervised Interest Point Detection and Description**, CVPR Workshops; 프리프린트 2017: 영상에서 interest point와 descriptor를 공동 추정하고 homographic adaptation으로 학습 신호를 만든다. [학회 원문](https://openaccess.thecvf.com/content_cvpr_2018_workshops/w9/html/DeTone_SuperPoint_Self-Supervised_Interest_CVPR_2018_paper.html)
- Paul-Edouard Sarlin, Daniel DeTone, Tomasz Malisiewicz, Andrew Rabinovich, 2020, **SuperGlue: Learning Feature Matching with Graph Neural Networks**, CVPR; 프리프린트 2019: attention 기반 문맥과 optimal transport를 사용해 두 영상 feature의 부분 대응을 추정한다. [원문](https://arxiv.org/abs/1911.11763)
- Philipp Lindenberger, Paul-Edouard Sarlin, Marc Pollefeys, 2023, **LightGlue: Local Feature Matching at Light Speed**, ICCV: 매칭 난이도에 맞춘 적응적 계산을 사용한다. [원문](https://arxiv.org/abs/2306.13643), [공식 구현](https://github.com/cvg/LightGlue/blob/main/README.md)
- Zachary Teed, Jia Deng, 2021, **DROID-SLAM: Deep Visual SLAM for Monocular, Stereo, and RGB-D Cameras**, NeurIPS: recurrent update와 dense bundle adjustment layer를 결합한다. [학회 원문](https://papers.neurips.cc/paper_files/paper/2021/hash/89fcd07f20b6785b92134bd6c1d0fa42-Abstract.html), [공식 구현](https://github.com/princeton-vl/DROID-SLAM)
- Zihan Zhu, Songyou Peng, Viktor Larsson, Weiwei Xu, Hujun Bao, Zhaopeng Cui, Martin R. Oswald, Marc Pollefeys, 2022, **NICE-SLAM: Neural Implicit Scalable Encoding for SLAM**, CVPR; 프리프린트 2021: 계층적 지역 표현과 사전학습 geometry prior를 이용한 신경 implicit SLAM이다. [원문](https://arxiv.org/abs/2112.12130), [공식 구현](https://github.com/cvg/nice-slam)
- Bernhard Kerbl, Georgios Kopanas, Thomas Leimkuhler, George Drettakis, 2023, **3D Gaussian Splatting for Real-Time Radiance Field Rendering**, ACM TOG: explicit Gaussian 표현을 최적화해 빠른 novel-view rendering을 수행한다. 원 논문 자체는 미지 camera pose를 실시간 추적하는 완결 SLAM 시스템이 아니다. [저자 프로젝트와 논문](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)
- Hidenobu Matsuki, Riku Murai, Paul H. J. Kelly, Andrew J. Davison, 2024, **Gaussian Splatting SLAM**, CVPR; 프리프린트 2023: Gaussian 표현을 tracking과 mapping에 연결하는 구체적인 SLAM 확장이다. [학회 원문](https://openaccess.thecvf.com/content/CVPR2024/html/Matsuki_Gaussian_Splatting_SLAM_CVPR_2024_paper.html), [저자 프리프린트](https://arxiv.org/abs/2312.06741)
- John McCormac, Ankur Handa, Andrew Davison, Stefan Leutenegger, 2017, **SemanticFusion: Dense 3D Semantic Mapping with Convolutional Neural Networks**, ICRA; 프리프린트 2016: 여러 시점의 semantic prediction을 dense map에 융합한다. [저자 원문](https://www.imperial.ac.uk/media/imperial-college/research-centres-and-groups/dyson-robotics-lab/mccormac_etal_icra2017.pdf)
- Berta Bescos, Jose M. Facil, Javier Civera, Jose Neira, 2018, **DynaSLAM: Tracking, Mapping and Inpainting in Dynamic Scenes**, IEEE RA-L: 동적 요소 검출을 통해 정적 지도를 만들고 배경 복원을 다룬다. [원문](https://arxiv.org/abs/1806.05620), [기관 서지](https://zaguan.unizar.es/record/71183/export/hx)
- Brianna Zitkovich 외, 2023, **RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control**, CoRL: VLM을 행동 표현으로 확장해 robotic control을 학습한다. proceedings와 arXiv의 저자 나열 순서가 다르므로 여기서는 proceedings를 따른다. [학회 서지·원문](https://proceedings.mlr.press/v229/zitkovich23a.html), [Brohan 외 순서의 arXiv](https://arxiv.org/abs/2307.15818)
- Moo Jin Kim 외, 2024, **OpenVLA: An Open-Source Vision-Language-Action Model**: 시각·언어와 로봇 행동 학습을 연결하는 공개 모델이다. 학습 데이터와 행동 인터페이스가 필요하다는 경계 사례로 사용한다. [저자 원문과 전체 저자 목록](https://arxiv.org/abs/2406.09246)

### Inferences

이 절의 적용 판단과 resource checklist는 원 논문 성능의 재현 결과가 아니라 후속 실험 설계다.
2026년 모든 최신 방법을 포괄하는 leaderboard가 아니라 요청된 대표 분기들의 개념 지도다.

#### 3.1 학습이 들어갈 위치를 먼저 정한다

첫 층은 detector와 descriptor다.
둘째 층은 두 집합 사이 data association이다.
셋째 층은 여러 시점의 geometry와 pose를 반복 추정하는 구조다.
넷째 층은 map representation과 rendering이다.
다섯째 층은 object/semantic 해석이다.
여섯째 층은 주어진 목표를 행동으로 바꾸는 정책이다.
이 층들은 조합할 수 있지만 입출력 타입이 다르므로 이름만 바꿔 끼우면 안 된다.
논문을 읽을 때 "학습한다"보다 "무엇을 출력하는가?"를 먼저 적는다.

| 방법 | 입력 | 직접 출력 | 별도로 필요한 것 |
|---|---|---|---|
| SuperPoint | 한 영상 | 2D 점·score·descriptor | 대응, pose, map 관리 |
| SuperGlue/LightGlue | 두 영상의 점·descriptor | 대응 index·confidence | 기하 검증, BA, 루프 정책 |
| DROID-SLAM | 영상 시퀀스와 보정 등 | pose·depth 추정 | 환경별 검증, 출력 scale 계약 |
| NICE-SLAM | 선택 구성의 RGB-D 관측 등 | pose와 implicit scene | 실제 센서 정합·자원 검증 |
| 원 3DGS | 보정 영상과 초기 geometry/pose 등 | 장면 appearance 표현 | 미지 pose의 온라인 추적 |
| GS-SLAM 계열 | 시퀀스와 해당 센서 가정 | pose와 Gaussian map | 충돌·물리 모델 검증 |
| semantic mapping | 영상·geometry·분류기 | class 분포가 붙은 지도 | 동적 판정·행동 계획 |
| VLA | 시각·언어·상태 등 모델 입력 | 행동 표현 | actuator 변환·제약·폐루프 검증 |

위 표는 개념 계약이며 각 논문의 모든 입력 조합을 열거한 API 명세가 아니다.

#### 3.2 SuperPoint의 교체 범위

SuperPoint 출력 점은 여전히 이미지 좌표다.
descriptor가 학습되었다고 점의 metric depth가 자동 생성되는 것은 아니다.
homography augmentation은 대응 일관성 학습을 돕지만 실제 3D 장면의 모든 parallax를 표현하지는 않는다.
원 detector score는 검출 우선순위이며 pose covariance와 같은 확률량이 아니다.
전처리 resize가 있으면 keypoint를 원 영상 좌표로 되돌리거나 K를 같은 비율로 바꿔야 한다.
padding을 추가했다면 주점 offset도 맞춘다.
모델이 어느 해상도에서 출력하는지와 descriptor sampling 위치를 기록한다.
이 정보를 놓치면 좋은 matcher를 써도 PnP residual이 체계적으로 커질 수 있다.
기존 ORB의 binary descriptor와 실수 descriptor의 거리·저장량·검색 구조가 다르다.
descriptor 차원과 normalization 방식은 실제 checkpoint 계약으로 확인한다.

교육용 중간 산출물 L1은 detection heatmap, NMS 전/후 점, descriptor shape, resize transform이다.
비교할 때 점 수를 통제하지 않으면 detector 품질과 단순 관측 수 증가가 섞인다.
특징 개수 증가로 latency가 커졌는지도 함께 기록한다.

#### 3.3 SuperGlue의 핵심: 독립 최근접 비교에서 문맥적 부분 대응으로

단순 nearest-neighbor matching은 각 descriptor를 따로 비교한다.
문맥적 matcher는 한 영상 안 점들의 관계와 다른 영상의 관계를 함께 사용한다.
self-attention은 같은 집합의 문맥을, cross-attention은 두 집합 사이 정보를 전달하는 관점으로 이해한다.
attention score가 높다고 실제 3D 대응이 보장되지는 않는다.
가림·시야 밖·검출 누락 때문에 모든 점에 짝이 있어야 한다는 가정은 틀리다.
부분 대응 모델은 unmatched를 허용해야 한다.
optimal transport 기반 assignment는 대응의 전체적 일관성을 다루는 수단이다.
dummy 또는 dustbin 항목은 짝이 없는 가능성을 표현하는 데 사용된다.
이런 구조는 descriptor 거리 하나보다 풍부하지만 학습 분포와 반복 패턴의 한계는 남는다.

교육용 2x2 유사도 행렬을 생각한다.
첫 행은 `(0.9,0.8)`, 둘째 행은 `(0.89,0.1)`이다.
독립 argmax는 두 점 모두 첫 열을 선택한다.
일대일 대응 총점을 비교하면 대각 합은 1.0, 반대 대각 합은 1.69다.
공동 assignment가 독립 선택과 다를 수 있음을 보여준다.
이것은 실제 SuperGlue의 optimal transport 계산을 재현한 예제가 아니다.
unmatched 비용과 정규화가 추가되면 결과는 다시 달라질 수 있다.

#### 3.4 LightGlue: 계산량도 입력에 따라 달라진다

적응형 matcher는 쉬운 pair에 적은 계산, 어려운 pair에 더 많은 계산을 배분할 수 있다.
따라서 평균 latency 하나로 worst-case 동작을 설명하기 어렵다.
교재 실험에서는 point count, image overlap, 실행 layer 수, 제거된 point 수, latency를 같이 기록한다.
early exit threshold를 바꾸면 속도와 대응 품질이 함께 달라진다.
confidence가 낮은 점을 지우는 정책이 작은 정적 배경까지 없애지 않는지 확인한다.
어려운 장면에서 많이 pruning되었다고 계산이 똑똑하게 끝났다는 뜻만은 아니다.
유효 geometry가 부족해진 실패일 수도 있다.
학습 matching 후에도 essential/PnP/RANSAC과 residual 검증이 필요하다.
장소 검색과 tracking의 point 수·시간 예산은 다르므로 동일 설정을 무조건 공유하지 않는다.

#### 3.5 DROID-SLAM: 기하를 없애는 대신 학습 업데이트와 결합한다

DROID의 수업 목표는 "신경망이 pose를 직접 찍는다"는 단순화를 피하는 것이다.
영상 간 correspondence 관련 정보를 반복 갱신하고, geometry를 만족시키는 BA layer로 pose와 depth를 조정하는 구조를 읽는다.
교육용 목적함수를 다음처럼 추상화할 수 있다.

```text
E(T,d) = sum_(i,j,p) || warp(T_j T_i^(-1),p,d_i(p)) - qhat_ij(p) ||^2_(W_ij(p))
```

여기 T는 이 식 안에서 세계→카메라 변환으로 정의한다.
qhat은 학습 업데이트가 제안한 target coordinate이며 pixel 단위다.
W는 해당 residual의 가중치를 표현한다.
이 식은 전체 네트워크 architecture와 training loss의 완전 전사가 아니라 geometric layer의 교육용 추상화다.
학습 confidence와 통계적으로 calibration된 covariance를 동일시하지 않는다.
단안 입력의 물리적 scale 모호성이 네트워크 이름 때문에 없어지지 않는다.
학습 데이터의 크기 prior를 사용할 수 있다는 것과 새로운 환경에서 metric scale을 관측했다는 것은 다르다.
stereo/depth를 사용하는 구성과 순수 단안 구성을 평가에서 분리한다.

중간 산출물 L2는 frame graph, proposed correspondence, weight map, depth, BA 전후 residual이다.
깊이가 매끈해 보이는지뿐 아니라 depth discontinuity와 motion boundary에서 잔차를 본다.
신경망 출력이 좋지 않을 때 geometry layer가 복구할 수 있는 범위도 초기값과 관측에 제한된다.
저장소에 DROID 코드를 설치하지 않았으므로 KITTI에서 기존 VO보다 나을 것이라고 약속하지 않는다.

#### 3.6 신경 implicit 지도: 값은 어디에 저장되는가?

명시적 point map은 각 점 좌표를 직접 저장한다.
implicit representation은 위치 x를 넣으면 geometry/appearance 관련 값을 반환하는 함수로 장면을 표현한다.
함수의 parameter, local feature grid, decoder가 지도 저장 수단이 된다.
NICE-SLAM은 이런 표현에 지역성과 계층 구조를 넣는 분기로 읽는다.
"neural"이라고 해서 센서에서 본 것과 보지 않은 것을 자동으로 구분해 주지는 않는다.
학습 prior가 보이지 않은 면을 그럴듯하게 보완할 수 있지만 그 면은 관측된 truth가 아니다.
출력 함수가 occupancy-like 값인지 SDF인지 density인지 확인한다.
모든 neural field를 signed distance라고 부르면 gradient와 표면 해석이 틀어진다.
rendering을 통한 pose 최적화는 관측과 예측의 차이를 줄이지만 장면과 pose가 함께 틀리는 모호성도 있다.
지도 표현의 유연성이 커질수록 잘못된 pose를 appearance로 흡수할 가능성을 경계한다.

#### 3.7 3DGS의 기하와 렌더링

3DGS는 3D Gaussian Splatting이다.
각 Gaussian의 중심 mu는 3D 위치이며 metric 지도라면 m 단위다.
공분산 Sigma는 모양과 방향을 나타내는 3x3 행렬이고 m^2 단위다.
이는 pose 추정 오차 covariance와 다르다.
opacity alpha는 무차원이고 appearance에는 방향 의존 색 계수를 사용할 수 있다.
양의 공분산을 유지하기 위해 scale과 rotation으로 Sigma를 parameterize할 수 있다.
Gaussian 중심을 카메라로 옮기고 projection Jacobian J로 화면상 타원을 근사한다.

```text
Sigma_screen ~= J R Sigma_world R^T J^T
```

J의 단위가 px/m이므로 화면 covariance는 px^2다.
깊이 순서로 정렬된 Gaussian들의 pixel별 alpha를 사용하면 색 합성을 설명할 수 있다.

```text
C = sum_k T_k alpha_k c_k
T_k = product_(l<k) (1-alpha_l)
```

T_k는 앞 Gaussian들을 통과한 잔여 투과율이다.
배경색이 있으면 마지막 남은 투과율에 배경색을 곱해 더한다.
alpha_k에는 해당 pixel의 Gaussian footprint 영향이 포함된다고 정의한다.
이 식은 렌더링 색을 설명하며 TSDF zero level이나 occupancy 확률을 직접 주지 않는다.
Gaussian을 많이 넣어 이미지를 맞춘다고 충돌 면이 자동으로 닫히는 것은 아니다.
반사·투명체 appearance를 표현하는 성공과 실제 두께·재질의 물리적 복원은 다르다.

#### 3.8 3DGS와 Gaussian SLAM을 분리해서 읽는다

원 3DGS의 입력 준비에는 알려진 camera pose와 초기 구조가 중요한 역할을 한다.
SLAM에서는 그 pose 자체가 미지수이며 시간에 따라 추정해야 한다.
따라서 online tracking, keyframe selection, visibility, Gaussian 추가·제거와 pose/map 공동 갱신이 추가된다.
Gaussian Splatting SLAM은 이 연결을 연구한 하나의 구체적 시스템이다.
이름이 비슷한 모든 GS 기반 SLAM이 같은 loop closure나 map management를 갖는 것은 아니다.
논문마다 실제 포함된 장기 보정 기능을 읽어야 한다.
사진 같은 결과만으로 "최신이므로 모든 전통 SLAM보다 우수"라고 결론내리지 않는다.
trajectory 오류, geometry 오류, held-out rendering, 메모리와 latency를 각각 평가한다.
학습·최적화에 사용한 같은 시점의 rendering 품질은 novel-view 일반화와 구분한다.

#### 3.9 자원 요구를 사실과 계획으로 분리한다

공식 DROID-SLAM 구현은 GPU 중심 환경과 별도 연산 의존성을 안내한다. [공식 README](https://github.com/princeton-vl/DROID-SLAM)
2026-11-24 열람한 README의 요구사항은 demo inference에 GPU memory 11G 이상, training에 24G 이상이며 CUDA 설치를 요구한다.
이는 저자 배포 구성의 안내값이다. 모든 sequence의 충분조건이나 이 호스트에서의 실측값이 아니다. [요구사항](https://github.com/princeton-vl/DROID-SLAM#requirements)
공식 NICE-SLAM 구현도 환경 구성과 학습된 구성요소를 제공한다. [공식 구현](https://github.com/cvg/nice-slam)
LightGlue의 adaptive pruning 동작은 point 수와 하드웨어에 따라 달라진다고 공식 README가 설명한다. [공식 설명](https://github.com/cvg/LightGlue/blob/main/README.md)
이 확인은 현재 로컬 호스트에서 실행 가능성을 검증했다는 뜻이 아니다.
특히 CUDA 대상 코드를 macOS arm64에서 같은 속도로 실행할 수 있다고 가정하지 않는다.
CPU fallback이 존재하는지, custom kernel 대체가 있는지, 정확도와 memory 차이가 무엇인지 먼저 확인한다.
설치 가능성과 실시간성은 다른 합격 조건이다.

후속 연구가 남길 resource ledger 항목은 다음과 같다.
- 모델·코드 버전과 checkpoint 식별자, 라이선스.
- 학습 데이터 종류, 평가 데이터와의 중복 여부.
- 입력 해상도, image resize, crop, intrinsics 변환.
- GPU/CPU 모델, RAM/VRAM, precision, batch와 point 수.
- 추론만 실행했는지 학습·미세조정까지 했는지.
- 최초 로딩, warm-up, steady-state latency를 구분한 기록.
- front-end, backend, rendering, disk I/O의 개별 시간.
- peak memory, window와 frame graph 크기, 누적 map 크기.
- 실패 프레임, 재시작, OOM, frame drop과 fallback 정책.

정해진 해상도에서 N개 keypoint를 M개와 모두 비교하면 pair 수는 N*M이다.
교육용으로 N=M=2048이면 pair 수는 4,194,304다.
float32 한 행렬만 저장해도 16,777,216byte, 즉 16MiB다.
실제 네트워크 memory는 feature, 여러 layer, attention, workspace와 gradient 때문에 더 커질 수 있다.
이는 특정 matcher의 실측 VRAM이 아니라 단일 배열 크기 하한 예제다.
해상도나 point 수를 줄이면 자원을 아끼지만 작은 구조와 시야 overlap 정보도 줄어든다.

#### 3.10 Semantic SLAM과 dynamic SLAM은 다른 질문이다

semantic mapping은 각 위치나 object가 무엇인지 추정한다.
dynamic SLAM은 정적 장면 가정이 깨졌을 때 camera motion과 object motion을 구분한다.
"차량"이라는 class는 움직일 수 있다는 prior이지 현재 움직인다는 측정이 아니다.
주차 차량은 현재 정적일 수 있다.
반대로 움직이는 문이나 상자는 detector의 동적 class 목록에 없을 수 있다.
따라서 semantic mask와 geometric motion consistency를 함께 보는 것이 합리적이다.
SemanticFusion은 지도에 의미를 융합하는 분기이고 DynaSLAM은 동적 요소를 처리하는 분기로 배치한다.
하나를 다른 하나의 완전 대체라고 설명하지 않는다.

#### 3.11 정적 배경을 고를 때 발생하는 순환 의존

정확한 camera pose가 있어야 움직이는 점을 잘 찾는다.
하지만 움직이는 점을 빼야 camera pose를 잘 추정한다.
초기 pose, 강건 추정, semantic prior, 여러 운동 가설과 시간 일관성을 결합해 이 의존을 완화한다.
큰 이동 차량이 화면 대부분을 차지하면 RANSAC이 그 차량 운동을 선택할 수 있다.
inlier 비율이 높아도 정적 세계 기준 camera motion이 아닐 수 있다.
가림 경계와 depth hole을 동적 물체로 오인하는 경우도 있다.
모든 dynamic-class 픽셀을 삭제하면 static feature가 부족한 장면에서 tracking이 더 나빠질 수 있다.
삭제 정책은 남은 점 수와 공간 분포, pose 관측가능성을 함께 확인한다.

교육용 motion test는 예측 정적 flow와 관측 flow 차이를 비교하는 것이다.
`e_flow = flow_observed - flow_static(T,depth)`로 둔다.
두 항 모두 px/frame 또는 px/s 중 같은 단위를 사용해야 한다.
depth나 pose가 틀려도 이 잔차가 커지므로 큰 잔차를 즉시 실제 물체 운동이라고 확정하지 않는다.
object ID를 시간에 걸쳐 추적하면 단일 프레임 mask보다 풍부한 근거를 얻는다.
object-centric map을 선택하면 물체 pose·shape·수명주기라는 추가 상태가 필요하다.

#### 3.12 의미 확률을 합칠 때의 주의

지도점의 class 분포를 p(c)라 하자.
독립 관측이라는 교육용 가정에서 `p_new(c) proportional p_old(c)*p_obs(c)`로 설명할 수 있다.
두 class A,B에 prior `(0.5,0.5)`, 관측 `(0.8,0.2)`를 두 번 사용하면 비정규화 값은 `(0.32,0.02)`다.
정규화하면 `(16/17,1/17)`이다.
연속 영상의 거의 같은 network prediction은 독립이 아니므로 이 방식은 과신을 만들 수 있다.
잘못된 depth registration은 class를 다른 표면에 누적시키는 원인이 된다.
분류 confidence, geometry confidence, temporal consistency를 한 숫자로 무작정 곱하지 않는다.
학습되지 않은 class는 unknown으로 남길 수 있어야 한다.
배경 inpainting으로 채운 texture를 실제 관측된 표면으로 평가하지 않는다.

#### 3.13 VLM과 VLA의 경계

VLM은 Vision-Language Model, 시각과 언어를 연결하는 모델이다.
장면을 설명하거나 질문에 답하는 출력은 그 자체로 로봇 제어 명령이 아니다.
VLA는 Vision-Language-Action 모델로 행동 표현까지 다룬다.
하지만 action token의 의미는 학습 데이터의 로봇 embodiment와 제어 공간에 묶인다.
예를 들어 end-effector delta pose, 관절 목표값, gripper command는 서로 다른 action이다.
이들의 단위, reference frame, 실행 주기, 범위와 safety constraint가 명시되어야 한다.
언어로 "앞으로 가라"고 말할 수 있다는 이유만으로 motor command가 안전하게 정의되지는 않는다.
RT-2와 OpenVLA는 이 행동 학습 경계를 이해하기 위한 사례다.
SLAM은 상태와 지도를 제공할 수 있지만 VLA 학습에 필요한 행동 supervision을 대신하지 않는다.

VLM이 이미지에서 문을 찾는다고 문까지의 metric collision-free path가 검증되는 것은 아니다.
VLA가 행동을 출력한다고 장기 상태 추정의 모든 문제가 사라지는 것도 아니다.
실제 시스템은 perception, state estimation, planning/policy, control, safety monitoring의 책임을 정의해야 한다.
모든 VLA가 반드시 명시적 SLAM을 요구한다고 단정하는 것도 피한다.
중요한 것은 필요한 정보를 어느 구성요소가 제공하며 오류를 어떻게 검출하는가다.

#### 3.14 KITTI는 왜 VLA 학습 데이터와 같지 않은가?

여기서 말하는 KITTI는 공식 Raw/Odometry의 기본 배포 범위다.
영상·LiDAR·calibration·pose 또는 OXTS 자료가 있다고 language instruction/action trajectory가 자동으로 존재하지 않는다.
차량 궤적은 관측된 운동 상태이며 조향·가속 actuator 명령과 같은 것이 아니다.
동일한 이동은 서로 다른 제어·마찰·차량 동역학으로 발생할 수 있다.
따라서 pose 차이를 action label로 이름만 바꾸면 원래 제어 문제를 바꾼다.
후속 annotation 데이터셋이 있을 가능성과 현재 보유 자료의 label 존재는 별개다.
자연어 caption을 나중에 붙이는 것은 scene-language 실험에 도움이 될 수 있다.
그러나 원래 운전자의 목표와 수행 행동이 동기화된 demonstration을 복구하는 것과 같지 않다.
KITTI만으로 검증 가능한 주장은 관측·기하·일부 인식 과제의 범위에서 설정해야 한다.
언어 지시 성공률·행동 성공률은 해당 행동과 평가 환경 없이는 측정할 수 없다.

#### 3.15 평가 지표는 층마다 다르게 둔다

특징 층은 repeatability, match precision, 공간 분포, geometric inlier와 latency를 본다.
pose 층은 trajectory error와 실패율, 복구 시간, 정렬 정책을 본다.
map geometry는 표면 거리·완성도·치수·관측 영역을 본다.
occupancy는 free/occupied/unknown 구분 오류를 본다.
rendering은 관측에 쓰지 않은 시점의 appearance 품질을 본다.
semantic 지도는 class별 오류와 unknown 처리를 본다.
행동 정책은 실제 정의된 task 성공·충돌·제약 위반·복구를 본다.
한 층의 수치를 다른 층의 성공으로 보고하지 않는다.

ATE는 Absolute Trajectory Error, RPE는 Relative Pose Error다.
ATE는 지정한 alignment 이후 대응 pose 차이를 요약하며 RPE는 일정 간격의 상대 운동 오차를 본다.
time association, SE(3)/Sim(3) alignment, 실패 구간 처리와 단위를 명시해야 비교할 수 있다.
영상이 나빠 tracking을 잃은 구간을 삭제하면 평균 오차만 좋아질 수 있다.
완주율과 실패 후 재초기화 여부를 함께 공개한다.
학습 모델의 신뢰도는 in-distribution 평균뿐 아니라 illumination·motion·texture·dynamic 비율 변화로 평가한다.
이 노트에는 어떤 모델의 실제 ATE, FPS, GPU peak memory도 새 측정값으로 제시하지 않는다.

#### 3.16 학습 경로는 교체 사다리가 아니라 분기 그래프다

공통 시작점은 기존 A3/A5/A9/A10/A11과 이 노트의 재투영·Schur·gauge다.
그 다음 관심 있는 관측과 지도 목적에 따라 갈라진다.
한 분기의 최신 논문을 읽었다고 다른 분기의 기초 문제가 사라지는 것은 아니다.

```text
공통: projection -> residual -> Jacobian -> uncertainty -> gauge
  |
  +-- 희소 장기 지도: PTAM -> ORB-SLAM -> ORB-SLAM2 -> ORB-SLAM3
  |                    |        |
  |                    |        +-- BoW/DBoW2 -> geometric loop -> pose graph
  |                    +-- BA / Schur / map lifecycle
  |
  +-- 광도 관측: LSD-SLAM -> DSO -> LDSO
  |              |          |
  |              +-- Sim3   +-- photometric calibration / marginalization
  |
  +-- 관성 관측: MSCKF -----> nullspace / consistency
  |              Forster --> preintegration -> VINS-Mono / ORB-SLAM3
  |                                             +-- time calibration
  |
  +-- RGB-D 기하: Curless-Levoy -> KinectFusion -> TSDF surface
  |               OctoMap --------------------> occupancy
  |               Voxblox --------------------> ESDF planning distance
  |
  +-- 학습 대응: SuperPoint -> SuperGlue -> LightGlue
  +-- 학습 반복 추정: DROID-SLAM -> geometry + learned update 해석
  +-- 장면 표현: NICE-SLAM / 3DGS -> Gaussian Splatting SLAM
  +-- 의미와 운동: SemanticFusion / DynaSLAM
  +-- 별도 행동 학습: VLM 경계 -> RT-2 / OpenVLA
```

화살표는 이 교재의 읽기 의존성을 뜻하며 논문이 반드시 직접 계승 관계라는 뜻은 아니다.
MSCKF와 optimization VIO는 계산·선형화·상태 유지 방식이 다른 대안이다.
occupancy는 TSDF보다 오래되었다고 쓸모없어진 표현이 아니다.
photorealistic rendering이 필요 없는 navigation에는 ESDF/occupancy가 직접 목적에 맞을 수 있다.
신경 matcher를 쓰지 않는 baseline도 자원·해석 가능성·도메인 적합성 때문에 유효하다.

#### 3.17 단계별 읽기 질문과 통과 기준

1. **PTAM + ORB-SLAM:** 키프레임·관측·지도점의 관계를 직접 그린다.
   통과 기준은 frame 삭제와 landmark 삭제가 어떻게 다른지 설명하는 것이다.
2. **BA synthesis:** 재투영 J와 Schur 블록을 손으로 계산한다.
   통과 기준은 residual 부호와 perturbation 방향을 바꾸었을 때 무엇이 달라지는지 말하는 것이다.
3. **DBoW2 + ORB loop:** 검색 점수에서 relative pose까지 필요한 산출물을 나열한다.
   통과 기준은 반복 복도에서 score가 높아도 edge를 거절할 근거를 제시하는 것이다.
4. **LSD-SLAM + DSO + LDSO:** residual 종류와 active/global map을 비교한다.
   통과 기준은 direct와 dense가 다른 축이고 DSO와 loop-SLAM이 다른 범위임을 설명하는 것이다.
5. **MSCKF + Forster:** feature elimination과 IMU factor compression을 구분한다.
   통과 기준은 nullspace projection과 Schur complement의 공통점·차이를 말하는 것이다.
6. **VINS-Mono + temporal calibration + ORB-SLAM3:** 초기화와 observability를 읽는다.
   통과 기준은 정지 구간만으로 모든 calibration을 추정할 수 없는 이유를 설명하는 것이다.
7. **Curless-Levoy + KinectFusion + OctoMap + Voxblox:** 지도 목적을 분리한다.
   통과 기준은 같은 depth에서 TSDF와 occupancy가 어떤 다른 값으로 갱신되는지 계산하는 것이다.
8. **SuperPoint + SuperGlue + LightGlue:** 학습 front-end의 타입 계약을 읽는다.
   통과 기준은 resize와 K, descriptor와 vocabulary, confidence와 covariance를 구별하는 것이다.
9. **DROID + NICE-SLAM + 3DGS + GS-SLAM:** 학습 대상이 update인지 scene인지 식별한다.
   통과 기준은 trajectory·geometry·rendering 평가를 분리하는 것이다.
10. **SemanticFusion + DynaSLAM + RT-2/OpenVLA:** 의미·운동·행동의 경계를 읽는다.
    통과 기준은 KITTI pose를 action label로 대체할 수 없는 이유를 설명하는 것이다.

위 번호는 수업 진행 순서이며 알고리즘의 절대 성능 순위가 아니다.
관성 데이터가 없다면 5~6은 이론 학습으로 남기고 RGB-D 수집 계약을 먼저 검증할 수 있다.
GPU가 없다면 8~9는 입출력·논문 수식·실패 분석을 공부하고 실행 가능성을 별도 검토한다.
실습 자원이 없다는 이유로 미실행 결과를 성공으로 쓰지 않는다.

#### 3.18 후속 집필자를 위한 그림과 배열 계약

그림 A: 키프레임·지도점 수명주기와 삭제 사유를 같은 시간축으로 표현한다.
배열: frame_id, keyframe_id, landmark_id, observation_count, age, rejection_reason.
그림 B: 작은 BA의 J/H 희소 구조와 Schur 이후 pose coupling을 표시한다.
배열: variable_order, residual_order, J, H, g, fixed_dofs, perturbation convention.
그림 C: loop 후보→대응→inlier→보정 전후를 네 panel로 나눈다.
배열: retrieval_score, match_pairs, inlier_mask, relative_transform, graph_edge_status.
그림 D: 직접법 원본·warp·광도 잔차·gradient mask를 같은 intensity scale로 표시한다.
배열: exposure, affine_brightness, response_correction, inverse_depth, residual_image.
그림 E: VIO 초기화 구간의 운동·bias·scale·gravity와 condition을 같은 시간축으로 표시한다.
배열: timestamps, raw_imu_units, extrinsics, bias_reference, preintegration_covariance.
그림 F: 동일 공간 단면의 TSDF·weight·occupancy·ESDF·unknown mask를 비교한다.
배열: voxel_origin, voxel_size_m, truncation_m, field_units, observed_mask, map_version.
그림 G: 학습 feature의 입력 resize와 원 영상 대응 좌표를 overlay한다.
배열: resize_transform, keypoints, descriptor_shape, match_confidence, geometric_inliers.
그림 H: neural/GS 지도에서 training view와 held-out view, depth error를 분리한다.
배열: camera_split, pose_source, depth_source, render_settings, visible_region_mask.
모든 그림의 caption에는 교육용 모델/실측/라이브러리 내부 출력 중 어느 것인지 적는다.
여기 나열한 파일 이름은 제안 schema이며 이 연구에서 새 산출물 파일을 만들지 않았다.

#### 3.19 후속 실험 선택: 작은 질문부터 시작한다

현재 보고서의 ORB 기반 VO 결과를 ORB-SLAM 전체 baseline으로 이름 바꾸지 않는다.
첫 질문은 기존 correspondence의 오류가 geometry 때문인지 descriptor 때문인지다.
같은 이미지 pair와 같은 K, 같은 검증기로 matcher만 바꿔 비교할 수 있다.
다음 질문은 loop 후보가 geometry를 통과하는지이며 GT를 검증 입력에 넣지 않는다.
밀집 지도가 목표라면 먼저 RGB-D 단위·정렬·정지 depth 품질을 확인한다.
그 다음 알려진 pose 또는 외부 기준 pose에서 fusion을 시험하면 tracking 오류와 fusion 오류를 분리할 수 있다.
이때 알려진 pose 사용은 oracle mapping 실험이라고 표시한다.
VIO는 검증된 시간·좌표 계약을 확보한 뒤 시작한다.
학습 모델은 resource ledger와 최소 재현부터 확인하고 전 구간 benchmark는 그 다음이다.
새 방법의 우수성을 가정한 뒤 유리한 구간만 고르는 순서를 피한다.

#### 3.20 추가 풀이형 연습문제: 학습과 시스템 경계

**문제 15.** 1280x960 영상을 가로·세로 절반으로 줄였다. fx=800px, cx=640px는 어떻게 바꾸는가?
**풀이.** 단순 좌표 scale 정의에서 fx'=400px, cx'=320px다.
u=1000px의 점은 u'=500px다.
pixel-center convention과 crop offset이 있으면 해당 resize API의 정확한 변환을 적용한다.
이미지만 줄이고 원 K를 쓰면 normalized ray가 달라진다.

**문제 16.** 2048x2048 float32 대응 score 행렬 하나의 크기는?
**풀이.** 원소 수는 4,194,304다.
4byte를 곱하면 16,777,216byte, 16MiB다.
이 값은 네트워크 전체 VRAM이 아니며 실제 실행 메모리는 추가 항목이 필요하다.

**문제 17.** 두 Gaussian의 pixel alpha가 0.5와 0.4다. 첫 색은 빨강 `(1,0,0)`, 둘째는 파랑 `(0,0,1)`, 배경은 검정이다.
**풀이.** 첫 기여는 `(0.5,0,0)`이다.
둘째에 도달하는 투과율은 0.5이므로 둘째 기여는 `(0,0,0.2)`다.
합은 `(0.5,0,0.2)`이며 남은 투과율은 0.3이다.
이 색만으로 물체의 표면 깊이나 점유 확률을 확정할 수는 없다.

**문제 18.** 주차 차량의 semantic mask가 vehicle이다. 모든 feature를 제거해야 하는가?
**풀이.** class는 잠재 이동성의 prior이지 현재 운동 측정이 아니다.
시간·기하 일관성과 배경 관측 수를 확인해 정책을 정한다.
장기 정적 지도에서 제외할지 현재 tracking에 일시 사용할지도 구분할 수 있다.

**문제 19.** KITTI pose 차이를 action으로 부르고 영상에 자연어 caption을 붙였다. VLA demonstration이 완성되는가?
**풀이.** 아니다. pose 변화는 결과 상태 변화이지 actuator command가 아니다.
명령 공간·주기·차량 동역학·목표 지시와 실제 실행의 대응이 부족하다.
이 데이터는 별도로 정의한 예측 과제에 쓸 수 있지만 원래 VLA 제어 평가와 동일하지 않다.

**문제 20.** 신경 지도의 rendering이 개선되었지만 ATE와 surface error는 악화되었다. SLAM이 개선되었다고 할 수 있는가?
**풀이.** rendering 목표에서는 개선이라고 할 수 있다.
pose와 metric geometry 목표에서는 악화이며 합쳐서 우수하다고 단정할 수 없다.
학습에 사용하지 않은 시점인지, scale alignment가 같은지까지 확인한 뒤 목표별로 보고한다.

#### 3.21 통합 시 보존해야 할 주장 경계

논문에 있다는 사실과 이 저장소에 구현되어 있다는 사실을 분리한다.
논문 benchmark 우수성과 현재 센서에서의 실시간성을 분리한다.
후속 연구를 알고 있다는 사실과 실제 실행 환경을 검증했다는 사실을 분리한다.
학습 prior의 추정값과 센서가 직접 관측한 값을 분리한다.
지도점의 geometry covariance와 Gaussian appearance footprint를 분리한다.
loop 후보, 승인 edge, 실제 global optimization 완료를 분리한다.
정적 세계 지도와 움직이는 object state를 분리한다.
metric 치수, 보기 좋은 mesh, physics-ready digital twin을 분리한다.
VLM의 설명, VLA의 action output, 실제 actuator 실행을 분리한다.
이 구분을 유지하면 교재가 길어져도 기능의 경계와 실험 근거를 잃지 않는다.

연구 노트 점검 기록:
- 세 개의 핵심 질문마다 Takeaway/Cited Findings/Inferences/Gaps 구성을 확인했다.
- 풀이형 문제 20개와 닫힌 코드 블록을 구조 검사했다.
- Schur 해, Huber 예제, TSDF 평균, occupancy 갱신, clearance, zero crossing, 배열 용량은 일회성 산술 검사로 재확인했다.
- Jacobian 수치는 직접 유도했고 실제 센서 관측에 대한 유한차분 시험은 수행하지 않았다.
- 수식 검산은 알고리즘 구현·데이터셋 benchmark·장치 검증과 구분한다.

### Gaps

- 일부 CVF HTML은 검색에서 내용이 확인되었지만 직접 열기에서 403을 반환했다. 저자 arXiv와 공식 구현으로 서지·핵심 주장을 교차 확인했다.
- learned model checkpoint를 내려받거나 실행하지 않았다. 로컬 GPU/VRAM 적합성과 실제 FPS는 미확인이다.
- 3DGS/implicit map의 mesh 추출·충돌 기하·실제 치수 정확도는 미검증이다.
- KITTI 기반 행동 label 또는 언어 지시 자료를 새로 구축하지 않았다. 기본 배포 자료를 VLA 행동 데이터로 취급하지 않는다.
- semantic segmentation의 현재 환경 class coverage와 동적 물체 분리 정확도는 미측정이다.
- 원 3DGS, NICE-SLAM, Gaussian SLAM은 각각 다른 입력·목적·구성이다. 동일 데이터·설정의 직접 비교 결과는 없다.
- 후속 집필자는 이 노트를 정식 보고서에 통합할 때 기존 버전·변경 이력을 갱신하고 PDF를 렌더링해야 한다. 이번 범위에는 해당 작업이 포함되지 않는다.
