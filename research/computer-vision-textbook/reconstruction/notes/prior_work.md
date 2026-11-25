# 재구성 선행연구

## 표현과 등록은 무엇을 추정하는가
### Takeaway
표면의 거리, 공간의 점유, 영상의 외관은 서로 다른 출력이다.
### Cited Findings
- Brian Curless, Marc Levoy (1996), A Volumetric Method for Building Complex Models from Range Images. 거리장의 누적 가중 결합. [저자](https://graphics.stanford.edu/papers/volrange/)
- Szymon Rusinkiewicz, Marc Levoy (2001), Efficient Variants of the ICP Algorithm. 초기 근사와 선택/대응/최적화의 분리. [저자](https://graphics.stanford.edu/papers/fasticp/)
- Helen Oleynikova, Zachary Taylor, Marius Fehr, Roland Siegwart, Juan Nieto (2017), Voxblox: Incremental 3D Euclidean Signed Distance Fields for On-Board MAV Planning. TSDF와 거리 질의의 분리. [원문](https://helenol.github.io/publications/iros_2017_voxblox.pdf)
### Inferences
- 거리장 단면과 평면 ICP의 rank 결핍을 작은 합성 예로 분리 검증한다.
### Gaps
- 완전한 Voxblox/OctoMap 재현과 실시간 통합은 수행하지 않는다.

## 렌더링과 동적 추정은 어떤 가정이 필요한가
### Takeaway
광도 설명과 기하 정확도는 같은 검사가 아니다.
### Cited Findings
- Robert J. Woodham (1980), Photometric Method for Determining Surface Orientation from Multiple Images. 조명 변화의 표면 방향 추정. [저자 목록](https://www.cs.ubc.ca/~woodham/publications.html)
- Ben Mildenhall, Pratul P. Srinivasan, Matthew Tancik, Jonathan T. Barron, Ravi Ramamoorthi, Ren Ng (2020), NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis. [프로젝트](https://www.matthewtancik.com/nerf)
- Bernhard Kerbl, Georgios Kopanas, Thomas Leimkühler, George Drettakis (2023), 3D Gaussian Splatting for Real-Time Radiance Field Rendering. [원문](https://arxiv.org/abs/2308.04079)
- Berta Bescos, José M. Fácil, Javier Civera, José Neira (2018), DynaSLAM: Tracking, Mapping and Inpainting in Dynamic Scenes. [원문](https://arxiv.org/abs/1806.05620)
- Christian Forster, Luca Carlone, Frank Dellaert, Davide Scaramuzza (2017 journal; 2015 preprint), On-Manifold Preintegration for Real-Time Visual-Inertial Odometry. [원문](https://arxiv.org/abs/1512.02363)
### Inferences
- 광선 합성과 Gaussian 투영은 신경망 학습 없이 검증 가능하다. IMU 수치 예는 중력 제거와 회전 순서에 초점을 맞춘다.
### Gaps
- NeRF/3DGS 훈련, DynaSLAM inference, 완전한 VIO는 수행하지 않는다.

## 적용 및 평가 경계
### Takeaway
보유 자료로 가능한 검사와 원 논문의 주장 재현을 구분한다.
### Cited Findings
- KITTI 공식 odometry는 고정 파라미터로 시퀀스를 평가한다. [공식](https://www.cvlibs.net/datasets/kitti/eval_odometry.php)
- TUM VI는 관성/시각 평가용 데이터이다. [원문](https://arxiv.org/abs/1804.06120)
### Inferences
| 접근 | 데이터/feature | 보유/추출 | 실시간/결합 | 판단 |
|---|---|---|---|---|
| 수치 TSDF/ICP | 합성 점과 법선 | 생성 가능 | CPU 소형/독립 | 즉시 교육용 적용 |
| StereoSGBM | rectified 흑백 stereo | 보유 | CPU 측정/독립 | 실제 단일프레임 예 |
| photometric stereo | 알려진 조명 | 합성만 가능 | CPU 선형해 | 합성 명시 |
| 신경장/3DGS 학습 | 다중 시점 RGB/pose | 현재 실험 미구성 | 학습비용/결합 큼 | 수식만 부분 검증 |
| VIO | raw IMU/동기화 | 검증 안 됨 | 연동 계약 미완료 | 합성 사전적분만 |
### Gaps
- 실제 안전성, 배포 지연, 지도 진실성, 모델 일반화는 이 소형 실험으로 주장할 수 없다.
