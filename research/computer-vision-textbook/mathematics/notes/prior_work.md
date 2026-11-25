# 수학의 원문과 교육 범위

## 수치 계산은 무엇을 보장하는가

### Takeaway
라이브러리의 검증된 분해를 사용하고 수학적 존재와 유한정밀도 안정성을 구분한다.

### Cited Findings
- LAPACK Users' Guide, 1999, Linear Least Squares: full rank QR/LQ와 rank-deficient SVD 드라이버 구분. [원문](https://netlib.org/lapack/lug/node27.html)
- A. G. Baydin, B. A. Pearlmutter, A. A. Radul, J. M. Siskind, 2018, Automatic Differentiation in Machine Learning: a Survey: 프로그램 연산의 미분을 전파하는 AD 분류. [출판사](https://www.jmlr.org/papers/v18/17-468.html)
- J. J. More, 1977 기술보고서, Levenberg--Marquardt algorithm: implementation and theory: 변수 스케일과 감쇠 선택. 1978 책 장과 구분. [기관 저장소](https://digital.library.unt.edu/ark:/67531/metadc1448594/)

### Inferences
- QR/SVD 라이브러리 즉시 적용. AD는 작은 연산 그래프의 손계산만 사용, 범용 프레임워크 구현은 하지 않는다.

### Gaps
- 생산 시스템의 희소 분해 시간/메모리 벤치마크는 미수행.

## 확률과 추정은 어떤 가정에 의존하는가

### Takeaway
정확한 평균뿐 아니라 공분산의 계약과 상관을 검증한다.

### Cited Findings
- R. E. Kalman, 1960, A New Approach to Linear Filtering and Prediction Problems, Journal of Basic Engineering 82(1),35-45. 상태 공간과 오차 공분산 재귀. [원문](https://cs-www.cs.yale.edu/homes/yry/readings/general/Kalman1960.pdf), DOI 10.1115/1.3662552. 검색 원문 확인, 직접 fetch timeout.
- S. J. Julier, J. K. Uhlmann, 2004, Unscented Filtering and Nonlinear Estimation, Proceedings IEEE 92(3),401-422. 시그마점으로 비선형 변환의 모멘트를 근사. [원문](https://www.cs.ubc.ca/~murphyk/Papers/Julier_Uhlmann_mar04.pdf)
- A. P. Dempster, N. M. Laird, D. B. Rubin, 1977, Maximum Likelihood from Incomplete Data Via the EM Algorithm, JRSS B 39(1),1-22. 잠재 변수의 조건부 기대와 최대화. [출판사](https://academic.oup.com/jrsssb/article/39/1/1/7027539). 직접 fetch CDN 오류 뒤 [원문 스캔](https://jhanley.biostat.mcgill.ca/bios601/Likelihood/EM-DemsterLairdRubin1977.pdf) 확인 완료. 스캔은 토론 포함 1-38쪽.
- P. J. Huber, 1964, Robust Estimation of a Location Parameter, Annals of Mathematical Statistics 35(1),73-101. [DOI](https://doi.org/10.1214/aoms/1177703732). 원문 페이지 iframe 제한; 일반 Huber 손실 정의만 자체 수식으로 사용.
- F. Dellaert, M. Kaess, 2017, Factor Graphs for Robot Perception, Foundations and Trends in Robotics 6(1-2),1-139. 희소 확률 그래프와 소거 관점. [저자](https://www.cs.cmu.edu/~kaess/pub/Dellaert17fnt.html)

### Inferences
| 선택 | 입력/보유 | 계산/결합 | 판단 |
|---|---|---|---|
| 선형 KF | 합성 상태/관측 모두 생성 | 작은 dense 행렬 | 즉시 교육 적용 |
| UKF 모멘트 | 합성 Gaussian | 3개 점 | 변환 비교만 적용 |
| EM | 합성 scalar mixture | SciPy logsumexp | 교육용 소규모 반복 |
| 전체 VIO | IMU 정렬 미검증 | 다중 상태 manifold | 범위 밖 |

### Gaps
- 전체 UKF 추적기, 비선형 RTS, 실제 데이터 일관성은 미수행.
- RTS: H. E. Rauch, F. Tung, C. T. Striebel, 1965, Maximum likelihood estimates of linear dynamic systems, AIAA Journal 3(8),1445-1450, DOI 10.2514/3.3166. 서지는 교차 확인했으나 출판사 본문 403. 교재 후방식은 조건부 Gaussian으로 자체 유도하며 미열람 원문의 상세 내용을 주장하지 않는다.
