# 컴퓨터 비전 교재 확장: 루트 조사 취합

이 루트 노트는 2026-11-25에 여섯 독립 연구 파트의 진행 중 자료와 사용자 계약을 취합한 기록이다. 모든 하위 연구보다 먼저 작성했다고 주장하지 않는다. 각 파트의 사전 조사·선행연구·설계는 해당 `notes/inventory.md`, `notes/prior_work.md`, `notes/architecture.md`가 소유한다.

## 문제와 Baseline

기존 v3.0.0 교재는 192쪽, UTF-8 원본 434160 bytes, 5655행이다. 사용자는 SLAM 개요를 넘어 컴퓨터 비전 기초에서 고급까지 더 깊은 유도·계산·실험을 요구했다. 분량은 목적 자체가 아니라 생략된 중간 계산과 실패 조건을 채우는 최소 용량이다. 원문을 복사하거나 기존 C장을 반복하지 않는다.

| 항목 | 목표/최소 기준 | 검증 방법 |
|---|---|---|
| 최종 PDF | 목표 400–550쪽; 최소 384쪽(기존의 2배) | checker `--min-pages 384`; 목표 초과는 편집 검토 |
| 실질 원고 분량 | 최소 868320 bytes 상당의 유의미한 원고; 폰트/여백/반복 부풀리기 금지 | raw source bytes 최소 868320을 필요조건으로 확인하고 편집자가 실질 산문·유도 증가를 별도 검사 |
| 신규 단원 | D1–D24, 24장 | H2 고유 ID·누락·중복 검사 |
| 신규 과학 그림 | 최소 48개 | 파트 figure 목록과 기존 92개 고유 이미지 baseline을 구분해 검토 |
| 신규 완전 풀이 | 최소 72개 | 문제와 정답·중간 계산 쌍을 편집 검토 |
| 구조 | 문제→계약/기호/단위→유도→예제→재현 그림→한계/후속→풀이 | 장별 편집 검토 |

raw UTF-8 bytes는 산문만의 byte 수가 아니다. 경로·링크·코드·공백도 포함하므로 자동 통계만으로 실질 확장을 인증하지 않는다. 신규 그림 수 역시 전체 이미지 occurrence 증가와 동일하지 않다. 기존 그림 중복 삽입은 신규 그림으로 세지 않는다. 페이지 수는 품질을 보장하지 않는다.

## 자원과 분담

| 파트/소유 경로 | 장 | 책임 |
|---|---|---|
| imaging/ | D1–D4 | 영상 형성·표본화·필터·복원·경계 |
| mathematics/ | D5–D8 | 수치 선형대수·미분/최적화·확률·추정 |
| correspondence/ | D9–D12 | 특징 검출·기술·대응·움직임 |
| geometry/ | D13–D16 | 사영/보정·다시점·stereo/MVS·SfM/BA |
| learning/ | D17–D20 | 학습 기반 비전의 계산·표현·추론 |
| reconstruction/ | D21–D24 | 복원 표현·융합·렌더링·시간/평가 계약 |

- 공통 Python: `research/20261031_vo-lo-study/.venv/bin/python`; NumPy/SciPy/OpenCV/Matplotlib/Pillow 사용. 파트마다 실제 dependency 버전과 source/config hash를 기록한다.
- 보유 데이터: KITTI Odometry 00 grayscale 좌우 영상. 사용한 프레임·경로·hash를 각 파트에 기록한다. 실제 disparity GT나 학습 모델의 성능을 보유했다고 가정하지 않는다.
- 합성 입력은 seed/config와 정답 생성식을 명시한다. 실제 KITTI와 합성 컬러/카메라/표면을 캡션에서 구분한다.
- 기존 출판 경로: `docs/report.md` → `node tools/render_report.mjs` → `docs/report.pdf`; 렌더러는 이 인프라 작업에서 변경하지 않는다.
- 검사기: `tools/check_camera_textbook.py`; PDF 렌더링·텍스트·버전·링크·navigation·빈 페이지 검사. contact sheet는 시각 검토 자료이지 자동 승인 증명서가 아니다.
- 코드 기준점: `75f7140d0dec421971c9b13d088e1967ebe124d5`; 현재 브랜치 `feat/computer-vision-textbook`. 이전 feature가 미병합이라 유지한다는 통합 작업의 결정에 따른다. 이 worker는 별도 fetch/merge/branch 변경이나 커밋을 수행하지 않는다.

## Quick-win과 범위

표현만 길게 늘리거나 기존 개요를 문장으로 덧붙이는 quick-win은 요구된 solver 수준 유도·재현·실패 검증을 충족하지 못한다. 기존 라이브러리를 재사용한 작은 독립 실험을 먼저 만들고, 여섯 파트에서 원고와 검증 산출물을 모아 편집한다. 새로운 production SLAM 구현, 대규모 모델 학습/GPU 다운로드, 문자 그대로 컴퓨터 비전 전체를 완결하는 백과사전은 범위 밖이다. 유한한 24장 교육과정을 깊게 다룬다.

최신 정본은 `docs/report.md`와 그 생성물 `docs/report.pdf` 한 쌍뿐이다. 버전·변경 이력은 같은 원본에 갱신하고 최종 전달은 PDF 하나다. 파트의 `chapters.md`는 통합 중간 자료이며 날짜별 최종 보고서를 만들지 않는다. 미완료 파트·시각 검토·통합 후 분량 목표는 완료로 표시하지 않는다.
