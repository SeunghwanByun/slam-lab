# Reconstruction 인계

## 통합 대상
- `notes/chapters.md`: D21-D24 전체 원고. 121,340 UTF-8 bytes, 1,737줄, H2 4개, H3 50개, 고유 앵커 54개, 완전 해설 16문제. 수식은 fenced text이며 LaTeX 미사용.
- 각 H2 앵커는 `d21`, `d22`, `d23`, `d24`; 하위는 `d21-1` 같은 고유 형식.
- 이미지 14개가 모두 `../research/computer-vision-textbook/reconstruction/figures/...` 형식으로 docs/ 기준 링크됨. 경로 재작성 불필요.
- 캡션은 각 장에서 순차 번호이며 source/units/synthetic-vs-real/제한을 포함함. 그림 파일 번호와 본문 순서는 D23/D24에서 다를 수 있으므로 본문 순서 유지.
- `notes/sources.md`: 확인된 1차 출처 12개. 본문 inline citation 이미 포함. 논문 성능 수치 가져오지 않음.

## 파일 목록
- notes/inventory.md, notes/prior_work.md, notes/architecture.md: 구현 전 조사/선행연구/계약.
- configs/default.json: seed 21024, 190dpi, 7inch, 거리/시차/시간 파라미터.
- src/run.py: 14개 교육 실험 그림 및 중간값 생성.
- src/test_numerics.py: 42개 unit/property/수치 예제 검사, JSON 결과 기록.
- src/check_artifacts.py: 링크/앵커/규격/유한값/해시 검사와 contact sheet 생성.
- artifacts/manifest.json: 실제 결과, source/config/data/figure SHA256, dependency versions, platform, commit, wall time.
- artifacts/{geometry,rendering,timing,evaluation,stereo}/arrays.npz: 5개 모듈 중간 배열.
- artifacts/tests/results.json: 42 run, 0 failure, 0 error.
- artifacts/qa/checks.json: 원고·그림·해시·숫자 검사 결과.
- artifacts/qa/contact_1.png ... contact_4.png: 시각 QA용 중간 자료, 원고에 삽입하지 않음.
- figures/d21_01_tsdf.png, d21_02_esdf.png, d21_03_registration.png, d21_04_kitti.png.
- figures/d22_01_raster.png, d22_02_photometric.png, d22_03_compositing.png, d22_04_gaussian.png.
- figures/d23_01_timing.png, d23_02_dynamic.png, d23_03_alignment.png.
- figures/d24_01_latency.png, d24_02_bias.png, d24_03_ablation.png.

## 재실행
저장소 루트에서 실행:

```text
research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/reconstruction/src/run.py
research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/reconstruction/src/test_numerics.py
research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/reconstruction/src/check_artifacts.py
```

## 확인된 결과
- 평면 ICP toy J rank=3; 20% 오염의 이동 평균=0.1200614m, Huber=0.0426860m (truth=0.04m).
- 광도 관측 한 개 오염 시 법선 각도 오류=18.6282191deg.
- 합성 alpha RGB=[0.575,0.2,0.375], projected Gaussian cov=[[120.25,6.75],[6.75,402.25]]px2.
- KITTI 실제 흑백 00 frame000000 SGBM: valid fraction=0.7255966, plotted points=9414. 정확도/GT 검증 아님.
- 합성 FIFO 평균 service28ms인데 p95 latency167.3333ms, deadline miss0.6.
- 14그림 전부 1330px 폭, 190dpi. 전체 contact sheet 육안 확인 후 제목 잘림/광도 단위 수정, 수정한 원본 재확인.
- `git diff --check` 통과. artifacts/ 및 figures/는 자체 .gitignore로 ignored임을 git check-ignore 확인.

## 인계 경계
정본 docs/report.md/pdf, tools, production code, 다른 연구 폴더를 수정하지 않았고 커밋/브랜치 변경/대형 다운로드/학습/드론 운용 없음.
최종 PDF 렌더와 페이지수/네비게이션 QA는 통합 담당자의 작업이다. 이 부분에서는 하지 않았음.
전체 ICP/VIO/NeRF/3DGS 재현이 아니라 명확히 표시된 교육용 부분 모델이다.
원고 SHA256: 77faefb2676d222bad9441e0373bc60dd6cb06b89354977f16563f7d3823e893.
