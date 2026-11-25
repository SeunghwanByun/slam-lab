# Geometry primary sources

## 어떤 모델을 왜 사용하는가

### Takeaway
이 연구는 원 논문의 짧은 방법 요약을 출처로 붙이고, 자체 좌표 예·유도·합성 실험을 길게 개발한다. 기존 논문 그림이나 교과서 문장을 전사하지 않는다.

### Cited Findings
- Zhengyou Zhang, 2000, A Flexible New Technique for Camera Calibration: 평면을 여러 자세에서 관찰해 내부 파라미터 초기화 후 비선형 개선. 기술보고서 1998/1999와 저널 2000 구분. [저자 기관](https://www.microsoft.com/en-us/research/publication/a-flexible-new-technique-for-camera-calibration/), [원문](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr98-71.pdf).
- Richard I. Hartley, 1995 ICCV, In Defence of the 8-point Algorithm: 입력 정규화와 rank-2 강제. [저자 원문](https://users.cecs.anu.edu.au/~hartley/Papers/fundamental/ICCV-final/fundamental.pdf). 1997 PAMI 확장판 In Defense of the Eight-Point Algorithm과 구분.
- Richard I. Hartley, Peter Sturm, 1997, Triangulation: 영상 오차의 최적 삼각측량. [저자 원문](https://users.cecs.anu.edu.au/~hartley/Papers/triangulation/triangulation.pdf).
- Heiko Hirschmüller, 2008, Stereo Processing by Semiglobal Matching and Mutual Information: 여러 경로의 동적계획을 조합하는 SGM. [저자 기관](https://elib.dlr.de/55367/).
- Michael Bleyer, Christoph Rhemann, Carsten Rother, 2011 BMVC, PatchMatch Stereo - Stereo Matching with Slanted Support Windows: 개별 픽셀의 평면 가설과 전파. [저자 기관](https://www.microsoft.com/en-us/research/publication/patchmatch-stereo-stereo-matching-with-slanted-support-windows/).
- Johannes L. Schönberger, Jan-Michael Frahm, 2016, Structure-from-Motion Revisited: 증분 재구성 단계와 강건한 선택. [학회 원문](https://openaccess.thecvf.com/content_cvpr_2016/papers/Schonberger_Structure-From-Motion_Revisited_CVPR_2016_paper.pdf).
- Bill Triggs, Philip McLauchlan, Richard Hartley, Andrew Fitzgibbon, 2000, Bundle Adjustment - A Modern Synthesis: 희소 구조, gauge, 품질 관리. [저자 기관](https://lear.inrialpes.fr/people/triggs/pubs.html).
- Avishek Chatterjee, Venu Madhav Govindu, 2013, Efficient and Robust Large-Scale Rotation Averaging: 회전군에서 상대회전을 강건하게 통합. [학회 원문](https://openaccess.thecvf.com/content_iccv_2013/papers/Chatterjee_Efficient_and_Robust_2013_ICCV_paper.pdf).
- OpenCV 공식 calib3d 문서는 호출 계약/좌표/distortion/flag 확인에 사용. [공식 문서](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html).
- David Nistér, 2004, An Efficient Solution to the Five-Point Relative Pose Problem: 5개 보정 대응에서 다항식 후보를 구한다. [원문](https://engineering.purdue.edu/~jshan/publications/2023/An_efficient_solution_to_the_five-point_relative_pose_problem.pdf). 검색 인덱스에서 제목/저자/연도/원문 초록 확인; 별도 open 재시도는 timeout. 페이지 범위는 2차 서지의 충돌 때문에 기재하지 않는다.
- Ramin Zabih, John Woodfill, 1994 ECCV, Non-parametric Local Transforms for Computing Visual Correspondence: rank/census 변환. [저자 서지 확인](https://www.cs.cornell.edu/rdz/rdz-papers.html), [원문](https://courses.cs.duke.edu/spring06/cps296.1/handouts/Zabih%20Woodfill%201994.pdf).

### Inferences
| 선택 | 입력/보유 | 실시간성 | 결합 난이도 | 판단 |
|---|---|---|---|---|
| OpenCV calibration/triangulation | 합성 2D/3D 생성 가능 | 오프라인 | 낮음 | 즉시 교육 실험 |
| normalized eight-point | 합성 대응 | 작은 선형계 | 낮음 | toy 대수 검증 |
| SGBM | KITTI gray 보유 | 해상도/범위 의존 | 낮음 | 실제 그림; GT 평가 아님 |
| PatchMatch MVS | 여러 보정 뷰 추가 필요 | 미측정 | 중간 | 유도만; 완전 재현 아님 |
| full SfM | track/검증/BA 필요 | 미측정 | 높음 | 시스템 계약 설명, 작은 선형 실험 |

### Gaps
실제 KITTI dense GT 및 장기 SfM benchmark를 수행하지 않는다. 생산 성능이나 모든 조건에서 최적임을 주장하지 않는다. 임의의 문헌 benchmark 수치를 복사하지 않는다.
