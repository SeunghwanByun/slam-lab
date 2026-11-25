# Imaging D1-D4 SOURCE FREEZE

정본·tools·생산 코드·다른 연구 폴더를 수정하지 않았다. commit 없음. 통합용 원고와 실험은 아래 상태로 동결한다.

- 원고: `research/computer-vision-textbook/imaging/notes/chapters.md`
- UTF-8 111783 bytes, 1833 lines, H2 D1-D4, H3 58개, unique lowercase anchors62개.
- 완전 해설 연습문제20개. 각 장의 실험·실패·가정·후속 선택 포함.
- 원고 SHA256: `4c5b7d000a30346aa4ce755d48c7298be87fd850b7e544b5e632a0dd297090ca`
- 그림13개, `figures/01_photon_noise.png`부터 `13_otsu_topology.png`. 전부7inch·200dpi·1400px폭. 13개 시각 확인 완료. 수정한06/10/11은 재확인했다. 09 범례도 핵심 경계 중앙에서 이동했다.
- 요청된11의 Gaussian 제목: `Gaussian sigma=1.2 px; output [DN]`. DoG 제목도 공간sigma와출력DN을 분리했다. 교육NMS와OpenCV실제결과는 구분 유지.
- 계산: `src/imaging.py`, 실행: `src/run.py`, 수치검사: `src/test_imaging.py`, 통합전검사: `src/audit.py`, seed설정: `configs/default.json`.
- 중간 배열: `artifacts/d1/arrays.npz` ~ `artifacts/d4/arrays.npz`; 각 `metrics.json`; `artifacts/manifest.json`; `artifacts/audit.json`.
- artifacts는 담당 폴더의 `.gitignore`로 제외. manifest에 입력·설정·소스·그림·모듈산출물SHA256, 기반commit, 의존성, 실행시간 포함.
- 최종검사: unittest41/41, 구조·링크·그림dpi·hash·배열finite 등audit29/29 통과. manuscript와fences 및docs기준그림링크 확인. 담당경로 diff whitespace 검사 통과.
- 최종 그림생성 실행시간2.9339937500초(macOS arm64, CPU, OpenCV1thread). 실시간 알고리즘 benchmark 아님.

## 재현 명령

```text
research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/imaging/src/run.py
research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/imaging/src/audit.py
```

## 핵심 직접 실행 결과

- D1 PNG값2배clip: ROI255비율3.8719%→16.1938%; 실제노출보정 아님.
- D2 cosine0.7/0.3 alias 표본최대차2.19e-14;3x3가중합5;DFT4점 `[10,-2+2i,-2,-2-2i]`.
- D3 Gaussian SD15 DN에서bilateral29.5728dB/SSIM0.7993,충격잡음에서는15.8972dB/0.2512;같은설정의실패. 충격median27.8810dB/0.8693.
- D3 합성단순역-73.2667dB vsK0.01정규화역30.8606dB;관측29.0953dB. 주기합성모델이며실제PSF추정아님.
- D4 교육Canny threshold3/8,8/20,16/40 개수12389/3950/1735;별도OpenCV3957. 개수는정확도가아님.
- D4 합성Otsu T112, TP2809 FP10716 FN0 TN11051,precision/IoU0.207689,recall1. 밝은배경과물체혼동.

## 통합 주의

그림링크는 이미docs/기준 `../research/computer-vision-textbook/imaging/figures/...` 이므로 원고 전체를 그대로 통합한다. 별도날짜보고서로배포하지 않는다. 정본PDF렌더·페이지수·내비게이션 검사는 통합담당 범위이며 여기서는 수행하지 않았다. 원문은 prior_work와 각 장의 inline primary links에 있다: EMVA2021, ICCsRGB, Debevec-Malik1997, Malvar-He-Cutler2004, Tomasi-Manduchi1998, Wang외2004, Buades외2011, Marr-Hildreth1980, Canny1986, Otsu1979, KITTI공식setup, OpenCV/SciPy공식문서. 원문성능숫자를복사하지 않았으며 수치표는직접실험만 사용했다.
