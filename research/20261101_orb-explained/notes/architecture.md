# 산출물 계약

모든 입력은 frame120 image_0 uint8 376x1241, 매칭만 frame121 추가. x 오른쪽/y 아래, 단위 pixel. 원본 픽셀과 level 픽셀의 scale 구분. 실시간 센서 업데이트/새 동기화 없음.

| 모듈 | 처리 | artifacts 산출물 | 단독 검사 |
|---|---|---|---|
| 피라미드 감사 | 원본에서 1/1.2^l resize | pyramid.npz,levels.csv,roi_level_*.npy | 기존4배열 동일/MAE/hash |
| 코너 검증 | FAST9/NMS/교육 Harris | fast_harris.npz,harris_toys.json | cyclic 9 조건/flat-edge-corner |
| 방향/descriptor demo | 원형 moment/steering/random 비교 | orientation_brief.npz | bit와 실제 밝기 비교 |
| 실제 ORB | detectAndCompute/BF | actual_orb.npz,matching.npz | dtype/shape/octave/XOR |
| 보고 | PNG+MD -> Chrome PDF | summary.json; figures/*.png;report.pdf | decode/레이아웃 |

기존 생산 모듈 재사용/수정 없음. 공통 연구 venv와 PDF renderer만 사용.
