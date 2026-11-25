# 수학 D5-D8 통합 인계

통합 대상은 `notes/chapters.md` 하나다. H2 anchor는 `d5`, `d6`, `d7`, `d8`이며 순서대로 정렬되어 있다. 4개 장, H3 58개, 약 108KB/2047줄, 해설 문제 17개. 정규 docs/report.md/pdf, tools, 생산 모듈 수정 없음. 커밋 없음. PDF 렌더링과 최종 쪽수 검증은 main writer의 통합 단계에 남아 있다.

## 파일

- notes/inventory.md, prior_work.md, architecture.md: 구현 전 작성한 계약·출처·설계.
- notes/chapters.md: 출판용 한국어 본문. 모든 그림 경로는 docs/ 기준.
- configs/experiment.json: seed=20261125, 600시행×60step, 200dpi/7in.
- src/experiments.py: NumPy/SciPy 기반 교육용 합성 실험.
- src/test_experiments.py: 26개 수치 계약 검사.
- src/qa.py: 검사 로그, 장 순서, 그림 상대경로·화소·dpi·비공백 검증.
- artifacts/d5/arrays.npz 및 metrics.json: 조건수/기저/PCA.
- artifacts/d6/arrays.npz 및 metrics.json: 차분/최적화/희소 구조.
- artifacts/d7/arrays.npz 및 metrics.json: Huber/상관/EM.
- artifacts/d8/arrays.npz 및 metrics.json: KF/RTS/UT/NIS/NEES/게이트.
- artifacts/provenance.json: 소스/config/NPZ SHA256, 버전, 실행 커밋, runtime.
- artifacts/qa/summary.json, tests.txt: QA 요약과 전체 테스트 결과.
- figures/d5_basis.png, d5_condition.png, d5_pca.png.
- figures/d6_derivatives.png, d6_optimization.png, d6_sparsity.png.
- figures/d7_robust.png, d7_correlation.png, d7_em.png.
- figures/d8_unscented.png, d8_smoothing.png, d8_kf_bands.png, d8_consistency.png, d8_gating.png.

## 실행과 실제 결과

```text
research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/mathematics/src/experiments.py
research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/mathematics/src/test_experiments.py
research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/mathematics/src/qa.py
```

26 tests PASS. 그림 14개 모두 1400px 폭/200dpi, 개별 visual inspection 완료. 생성 전체 약 4.78s(실시간 성능 주장 아님). 최초 테스트에서 EM의 이론적 0을 atol=0으로 비교해 1.39e-16 반올림에 실패했고, 명시적 atol=1e-14로 수정한 후 통과. 숨기지 않고 과정 기록.

정상 KF: NIS=1.0024, NEES=2.0140, 위치 RMSE=0.4927m. R을 실제의 4%로 보고: NIS=16.4022, NEES=30.5845, RMSE=0.5856m. 같은 데이터와 prior 사용. 시각별 600회 ensemble 구간과 전체 평균 기술통계를 구분.

상관 0.9인 두 센서 평균 분산 이론 0.95m², 표본 0.9550m², 독립 오가정 0.5m². 80정상+20이상치에서 평균 0.7838m vs Huber 0.1078m. GN full step 비용 12.1→1171.28. EM 동일 초기 평균은 -0.3856m에서 두 성분이 분리되지 않음. 모두 합성 교육 결과, 실제 SLAM/VIO 수치가 아님.

## 출처 확인의 경계

정식 서지·링크는 chapters.md D8.21과 prior_work.md. LAPACK 공식 문서, Baydin JMLR, More 기관 기록, Julier/Uhlmann 원문 PDF, EM 원문 스캔, Dellaert/Kaess 저자 페이지 확인. Kalman은 검색 원문 확인 후 direct fetch timeout. Huber 원문은 iframe 제한, RTS publisher는403이므로 원문 상세 정리/성능 보증을 읽었다고 주장하지 않음. 자체 유도와 테스트로 교육 수식을 검증했다. EM 본문1-22쪽과 토론 포함 스캔1-38쪽의 차이도 기록.

최초 조사 HEAD 75f7140..., 최종 실행 HEAD 9f42aa0...는 공유 저장소의 외부 변경이다. 본 작업자는 브랜치·커밋을 만들지 않았다. 생성 NPZ hash 네 개는 두 실행에서 동일.
