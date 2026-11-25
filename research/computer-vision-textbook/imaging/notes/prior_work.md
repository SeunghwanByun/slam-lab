# Imaging 원문 조사

## 관측과 색 부호화는 무엇을 보존하는가

### Takeaway
PNG의 숫자를 radiance로 바로 해석할 근거가 없으며 측정 모델과 표시 모델을 분리해야 한다.

### Cited Findings
- EMVA, 2021, *EMVA Standard 1288 Release 4.0 Linear*: 선형 센서의 광자·dark·양자화 잡음 측정 계약. [원문](https://www.emva.org/wp-content/uploads/EMVA1288Linear_4.0Release.pdf)
- ICC, IEC 61966-2-1:1999 기반 *sRGB*: 선형 성분과 저장 성분 간 구간별 전달 함수. [등록부](https://registry.color.org/rgb-registry/srgb)
- Paul E. Debevec, Jitendra Malik, 1997, *Recovering High Dynamic Range Radiance Maps from Photographs*: 노출이 다른 정적 장면으로 응답과 상대 radiance를 연결한다. [저자](https://www.pauldebevec.com/Research/HDR/)
- Henrique S. Malvar, Li-wei He, Ross Cutler, 2004, *High-quality linear interpolation for demosaicing of Bayer-patterned color images*. [연구기관 원문](https://www.microsoft.com/en-us/research/publication/high-quality-linear-interpolation-for-demosaicing-of-bayer-patterned-color-images/)
- KITTI의 gray/color 센서는 별도다. [공식 setup](https://www.cvlibs.net/datasets/kitti/setup.php)

### Inferences
- 현재 gray PNG에 Bayer와 sRGB 역함수를 무조건 적용하는 것은 계약 위반이다. 색 그림은 합성 교육 자료로 한정한다.

### Gaps
- 해당 PNG의 실제 광전자 수·노출·응답·camera ISP는 검증되지 않았다.

## 표본화와 잡음 제거의 가정은 무엇인가

### Takeaway
평활화는 잃은 정보를 복구하지 못하며 지표는 명시적 정답과 같은 값 공간에서만 비교한다.

### Cited Findings
- OpenCV *Image Filtering*: filter2D는 correlation이며 border와 ddepth가 연산 계약이다. [공식 문서](https://docs.opencv.org/4.x/d4/d86/group__imgproc__filter.html)
- SciPy *fft*: 기본 forward 비정규화, inverse 1/N. [공식 문서](https://docs.scipy.org/doc/scipy/reference/generated/scipy.fft.fft.html)
- Carlo Tomasi, Roberto Manduchi, 1998, *Bilateral Filtering for Gray and Color Images*: 공간과 밝기 거리를 결합한다. [저자 원문](https://users.cs.duke.edu/~tomasi/papers/tomasi/tomasiIccv98.pdf) 검색 원문은 확인했고 직접 fetch는403이었다.
- Zhou Wang, Alan C. Bovik, Hamid R. Sheikh, Eero P. Simoncelli, 2004, *Image Quality Assessment: From Error Visibility to Structural Similarity*. [저자 구현·논문](https://www.cns.nyu.edu/~lcv/ssim/)
- Antoni Buades, Bartomeu Coll, Jean-Michel Morel, 2011, *Non-Local Means Denoising*. [저널과 코드](https://www.ipol.im/pub/art/2011/bcm_nlm/)

### Inferences
- Gaussian·median·bilateral은 기존 라이브러리로 즉시 적용 가능. NLM은 후속 방향 설명만 한다. noise-free KITTI를 보유하지 않으므로 원 PNG 대비 인위 열화 복원만 평가한다.

### Gaps
- 실제 잡음 종류와 계수, 다른 시퀀스의 일반화 및 후속 SLAM 개선 미측정.

## 경계와 영역을 어떻게 검증하는가

### Takeaway
미분 크기, 가는 edge, 이진 영역, 의미 물체는 서로 다른 출력이다.

### Cited Findings
- David Marr, Ellen Hildreth, 1980, *Theory of edge detection*, Proc. Royal Society B207,187–217. [원문](https://www.med.harvard.edu/bss/neuro/bornlab/qmbc/beta/day4/marr-hildreth-edge-prsl1980.pdf)
- John Canny, 1986, *A Computational Approach to Edge Detection*, PAMI8(6),679–698. [원문](https://www.cse.ust.hk/~quan/comp5421/notes/canny1986.pdf)
- Nobuyuki Otsu, 1979, *A Threshold Selection Method from Gray-Level Histograms*, SMC9(1),62–66. [원문](https://skynet.ecn.purdue.edu/~ace/vip/A_Threshold_Selection_Method_from_Gray-Level_Histograms_otsu.pdf)

### Inferences
- Canny는 실제 KITTI에 적용하되 정확도는 GT 있는 합성 도형으로만 계산한다. Otsu는 조명 기울기와 밝은 배경에서 실패시킨다.

### Gaps
- KITTI의 의미 경계 GT는 이 실험에서 사용하지 않았다. 연산 시간은 작은 로컬 실험이지 실시간성 보증이 아니다.

적용 판단: OpenCV filter/Canny/threshold/morphology 즉시 사용, 합성 photon/Bayer/NMS는 교육용 추가 추출, 실제 EMVA 보정·HDR 응답 보정은 필요 raw/exposure 부재로 불가. 원문 요약은 짧게 유지하고 장의 긴 계산·예제는 자체 구성한다.
