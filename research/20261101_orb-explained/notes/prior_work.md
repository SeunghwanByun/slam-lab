# 확인한 원문과 적용 판단

- ORB: Rublee/Rabaud/Konolige/Bradski, ICCV2011. 공식 OpenCV ORB tutorial/API에서 이름과 구성 확인. 원 논문 PDF는 검색 결과는 확인했으나 안정적인 본문 열람 실패; 원문 전체 재현 주장 없음.
- FAST: Rosten/Drummond, ECCV2006. 저자 PDF https://www.edwardrosten.com/work/rosten_2006_machine.pdf 본문 확인. 초기 FAST12와 이번 FAST9_16 구분.
- Harris: Harris/Stephens, 1988. 학회 https://www.bmva-archive.org.uk/bmvc/1988/avc-88-023.html 및 공식 OpenCV 수식 확인.
- BRIEF: Calonder/Lepetit/Strecha/Fua, ECCV2010. 공식 OpenCV 설명/서지 확인. 본 실험은 random-test 교육 예시, 학습 rBRIEF 미재현.
- SuperPoint: DeTone/Malisiewicz/Rabinovich, CVPR workshop2018, https://arxiv.org/abs/1712.07629.
- LightGlue: Lindenberger/Sarlin/Pollefeys, ICCV2023, https://arxiv.org/abs/2306.13643.

| 방법 | 데이터/보유 | 추가 필요 | 비용/결합 | 판단 |
|---|---|---|---|---|
| 단계 시각화 | 로컬 영상/기존 NPZ 있음 | 없음 | CPU, 낮음 | 이번 선택 |
| 실제 ORB 계측 | cv2 있음 | 없음 | CPU, 낮음 | 이번 선택 |
| rBRIEF 재학습 | 단일 장면은 부족 | 다양한 patch corpus | 중간 | 미실시 |
| SuperPoint | 영상 있음 | weights/런타임/평가 | 중간 | 후속 선택지 |
| LightGlue | 호환 feature 필요 | weights/descriptor 계약 | 중간 | ORB에 무조건 직접 연결 불가 |

한계에서 후속 접근을 소개하되 이번 데이터에서 성능 개선됐다고 주장하지 않는다.
