# D21-D24 확인한 1차 출처

2026-11-25 웹에서 저자 프로젝트/논문 원문/공식 데이터셋을 확인했다. 본문은 핵심 아이디어만 짧게 인용하며 수치 유도·합성 예제는 자체 작성이다. 논문 성능 수치를 가져오지 않았다.

| ID | 확인한 서지 | 역할 / 원문 |
|---|---|---|
| R21-1 | Brian Curless, Marc Levoy. 1996. A Volumetric Method for Building Complex Models from Range Images. SIGGRAPH. | 거리 누적의 원전. https://graphics.stanford.edu/papers/volrange/ |
| R21-2 | Szymon Rusinkiewicz, Marc Levoy. 2001. Efficient Variants of the ICP Algorithm. 3DIM. | 대응/선택/최적화 단계 구분. https://graphics.stanford.edu/papers/fasticp/ |
| R21-3 | Helen Oleynikova, Zachary Taylor, Marius Fehr, Roland Siegwart, Juan Nieto. 2017. Voxblox: Incremental 3D Euclidean Signed Distance Fields for On-Board MAV Planning. IROS. | TSDF와 ESDF 질의 차이. https://helenol.github.io/publications/iros_2017_voxblox.pdf |
| R22-1 | Robert J. Woodham. 1980. Photometric Method for Determining Surface Orientation from Multiple Images. Optical Engineering. | 조명 변화와 법선. https://www.cs.ubc.ca/~woodham/publications.html |
| R22-2 | Ben Mildenhall, Pratul P. Srinivasan, Matthew Tancik, Jonathan T. Barron, Ravi Ramamoorthi, Ren Ng. 2020. NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis. ECCV. | 복사장과 알려진 pose. https://www.matthewtancik.com/nerf |
| R22-3 | Bernhard Kerbl, Georgios Kopanas, Thomas Leimkühler, George Drettakis. 2023. 3D Gaussian Splatting for Real-Time Radiance Field Rendering. ACM TOG. | Gaussian 표현. https://arxiv.org/abs/2308.04079 |
| R23-1 | Berta Bescos, José M. Fácil, Javier Civera, José Neira. 2018. DynaSLAM: Tracking, Mapping and Inpainting in Dynamic Scenes. IEEE RA-L. | 의미와 동적 기하. https://arxiv.org/abs/1806.05620 |
| R23-2 | Christian Forster, Luca Carlone, Frank Dellaert, Davide Scaramuzza. 2017 journal / 2015 preprint. On-Manifold Preintegration for Real-Time Visual-Inertial Odometry. IEEE TRO. | 사전적분, 실제 구현은 미실행. https://arxiv.org/abs/1512.02363 |
| R24-1 | KITTI authors' official odometry benchmark, Evaluation 2012 page. | 데이터/고정 파라미터 평가 계약. https://www.cvlibs.net/datasets/kitti/eval_odometry.php |
| R24-2 | David Schubert, Thore Goll, Nikolaus Demmel, Vladyslav Usenko, Jörg Stückler, Daniel Cremers. 2018. The TUM VI Benchmark for Evaluating Visual-Inertial Odometry. IROS. | 동기화와 GT 확보 범위. https://arxiv.org/abs/1804.06120 |
| R24-3 | Wenshan Wang, Delong Zhu, Xiangwei Wang, Yaoyu Hu, Yuheng Qiu, Chen Wang, Yafei Hu, Ashish Kapoor, Sebastian Scherer. 2020. TartanAir: A Dataset to Push the Limits of Visual SLAM. IROS. | 합성 데이터 목적. https://arxiv.org/abs/2003.14338 |
| R24-4 | Moo Jin Kim, Karl Pertsch, Siddharth Karamcheti et al. 2024. OpenVLA: An Open-Source Vision-Language-Action Model. | 로봇 행동 데이터/출력의 예. https://openvla.github.io/ |

접근 한계: TUM RGB-D tools 페이지와 Inria 3DGS 프로젝트 직접 열기는 timeout. 3DGS는 저자 arXiv 원문으로 확인했다. TUM RGB-D 도구의 현재 구현 세부사항은 본문 주장의 근거로 쓰지 않았다. ORB-SLAM3/DBoW2 검색은 확장 검토용이며 이번 본문에서 새로운 성능 주장의 출처로 사용하지 않았다.
