# 리소스 및 문제 정의

- 문제: ORB 구성 요소의 약자·작동 원리·연결이 빠져 있고 피라미드의 자동 확대가 해상도 차이를 감춘다.
- baseline: ../20261031_vo-lo-study/src/orb_stages.py:7~13은 원본에서 4단계 resize 후 각 축에 자동 fit한다.
- 실제 VO: ../20261031_vo-lo-study/src/vo.py의 ORB_create는 nfeatures만 지정한다. 실행 환경 getter로 nlevels=8, scaleFactor~1.2, patchSize=31, FAST threshold=20, WTA_K=2 확인.
- 데이터: 00 image_0 120,121번; 기존 artifacts/orb/pyramid.npz; calibration 및 VO 연구 출력.
- 사용 feature: 실제 ORB 위치/angle/size/octave/response/32-byte descriptor. 교육용 FAST ring/Harris response/moment/random BRIEF 추가 생성.
- 환경: 기존 연구 venv OpenCV5.0.0/NumPy/Matplotlib; 기존 PDF renderer와 Chrome.
- 성공 기준: 기존 4개 배열 동일 재현, 8레벨 원시 배열 및 shape/hash 기록, L1~7 복원 MAE>0, FAST9 조건 검사, XOR popcount 일치, 그림9개와 모든 주요 용어 설명.
- 부족: OpenCV5.0.0 binary의 정확한 빌드 소스, ORB 내부 피라미드 buffer 직접 추출, rBRIEF 재학습 데이터. 4.13 source를 5.0 동일 구현 증거로 사용하지 않는다.
- Quick-win: 기존 데이터로 시각화·교육용 실험만 추가한다. 생산 VO/LO 알고리즘 변경 없음.
