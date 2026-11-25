# Learning 통합 인계

## 원고
- `notes/chapters.md`: D17–D20, 약 116KB/2,000줄. H2 explicit anchors `d17`, `d18`, `d19`, `d20`만 사용. H3는 D17.1–D17.14, D18.1–D18.15, D19.1–D19.16, D20.1–D20.20.
- 16개 완전 풀이. 13개 신규 PNG, docs 기준 상대 링크 13개 확인. 실제 KITTI 고정 필터/patch 평균 2그림, 나머지 합성 교육 실험. pretrained inference 없음.
- 최종 페이지 수는 측정하지 않음: canonical PDF 렌더는 통합 작성자 소유. 원고·그림은 통합 가능 상태.
- canonical docs/report.md/pdf, tools, production code 수정 없음. 커밋 없음.

## 파일
- 선행 조사: `notes/inventory.md`, `notes/prior_work.md`, `notes/architecture.md`.
- 설정: `configs/default.json`.
- 실행: `src/experiment.py`, 검사: `src/test_experiment.py`, 링크·이미지·해시 QA: `src/qa.py`.
- 모듈별 배열: `artifacts/{learning,convolution,evaluation,attention}/arrays.npz`.
- 결과: `artifacts/results.json`, provenance: `artifacts/manifest.json`, 검사: `artifacts/tests.json`, 통합 QA: `artifacts/qa.json`, 시각 QA: `artifacts/contact_sheet.png`.
- artifacts 경로 git-ignore 확인. PNG는 figures/ 아래이며 원고 포함을 위해 보존.

## 재실행
저장소 루트에서 다음 명령을 각각 실행한다.

```sh
research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/learning/src/experiment.py
research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/learning/src/test_experiment.py
research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/learning/src/qa.py
```

24 numeric tests 통과. QA는 4 anchors, 13개 고유 그림과 경로, 16개 풀이, 190dpi/7인치 이상, 코드·설정·KITTI·그림 해시, 코드 fence 균형을 검사한다. contact sheet 전체와 attention/PR 확대를 시각 확인했다. 사용자 QA 반영: 동일 갱신 후 train/heldout/linear loss, PR raw/envelope 구분, attention 글자 대비/정수 tick 수정.

## 주요 실제 실행 숫자
- MLP 훈련 BCE 0.4313124, heldout 0.4544735, 선형 훈련 0.6919885. 모두 최종 갱신 직후.
- 중앙 차분 epsilon1e-5 최대 절대 오차 1.0118e-11.
- 합성 calibration T2.9971062, heldout NLL0.697609→0.490104.
- aliasing 평균0.5 대비 MSE0.25→6.56548e-7.
- 합성 box IoU0.6, NMS keep[0,2]. AP all-points0.755556, 순서 변경0.6.
- 합성 mask IoU0.672996, Dice0.804540. SciPy assignment cost4.
- attention 첫 행[0.66976155,0.33023845], 출력[1.33952310,1.32095380].
- 합성 역깊이 oracle affine[a,b]=[0.5,-0.05]. 모든 숫자는 벤치마크 성능 아님.

## 원문 근거
`notes/prior_work.md`와 본문 inline 링크에 제목/저자/연도 보존. 확인한 주요 원문은 Adam, BatchNorm, Dropout, Calibration, ResNet, U-Net, FPN, R-CNN, Faster R-CNN, 원래 YOLO, Focal Loss, DETR, Mask R-CNN, Panoptic, Attention, ViT, MAE, SimCLR, CLIP, SAM, MiDaS, DPT, RAFT, DROID-SLAM, Deep Compression, Integer Quantization, Distillation. VOC2010 공식 HTML과 COCO 공식 evaluator의 평가 규약도 확인. VOC2012 PDF는 접근 실패를 기록하고 VOC2010 공식 HTML로 AP 변경 근거를 대체했다.

## 제한
실제 pretrained 모델 비교·학습·데이터셋 AP·metric depth 정확도·GPU latency는 수행하지 않음. toy MLP/박스/attention은 명시적 교육 구현. 필터는 OpenCV, 최적 할당/온도 적합은 SciPy, least-squares는 NumPy 사용. 기존 운영 SLAM 성능 개선이나 통합 완료로 서술하지 말 것.
