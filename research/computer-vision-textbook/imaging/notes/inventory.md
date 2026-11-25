# Imaging 리소스와 문제 계약

## 문제와 성공 기준

관측 PNG를 이상적인 광량으로 취급하거나 필터 이름만 암기하면 기하 추정 이전의 정보 손실을 진단할 수 없다. D1–D4는 측정, 표본화, 복원, 경계의 계약을 수치 예와 독립 실험으로 연결한다. [가정] 성공 기준은 4개 장, 원본 PNG 10–14개, 수치·불변량 검사 10개 이상, 장별 실패 사례 1개 이상이다. 실제 센서 보정·SLAM 성능 향상은 범위 밖이다.

## 사용 가능 리소스

- 현재 기반 커밋: `75f7140d0dec421971c9b13d088e1967ebe124d5`. 공유 작업으로 브랜치·commit·fetch 조작하지 않는다.
- 실제 입력: `data/kitti/dataset/sequences/00/image_0/000000.png`, 우측 `image_1/000000.png`. 데이터 크기·dtype·SHA256는 실행 manifest로 확인한다. 이 실험에서 GT pose는 사용하지 않는다.
- `research/20261031_vo-lo-study/src/orb_stages.py:15`: OpenCV cornerHarris, `:37`: GaussianBlur 사용. 기존 모듈은 재사용하지 않고 라이브러리를 직접 호출해 독립 산출물을 만든다.
- `docs/report.md:905`: Sobel 간단 정의, `:940`: Gaussian 평활화 소개. 이를 복사하지 않고 관측과 주파수·확률 유도를 새로 쓴다.
- 인터프리터: `research/20261031_vo-lo-study/.venv/bin/python`; numpy/scipy/cv2/matplotlib/Pillow 사용 가능. 설치·모델 다운로드·GPU 훈련 없음.
- 추출 가능: 히스토그램, ROI, 잡음 잔차, Fourier 스펙트럼, gradient/NMS/연결요소.
- 미보유: 원시 광전자, exposure metadata, camera response, Bayer raw, 잡음 없는 실제 정답 영상. 이들을 KITTI PNG에서 추정했다고 주장하지 않는다.

## Quick-win과 전달 경계

생산 코드 변경 없이 작은 OpenCV/SciPy 실험만으로 개념 검증 가능하다. 독립적인 손계산·Canny NMS는 교육용으로 표시하고 OpenCV 내부 구현 재현으로 부르지 않는다. 정본 `docs/report.md/pdf`와 tools는 통합 담당자만 수정한다. 담당 경로 밖에 쓰지 않는다. 모든 artifacts는 로컬 ignore한다.
