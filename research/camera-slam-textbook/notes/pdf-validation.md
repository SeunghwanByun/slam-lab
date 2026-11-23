# PDF 검증 도구 인계

## 범위와 결과

- 도구 담당 범위: `tools/render_report.mjs`, `tools/check_camera_textbook.py`, 이 노트.
- `docs/report.md`, `docs/report.pdf`, 기존 수학·실험 소스·그림은 수정하지 않았다. 커밋하지 않았다.
- 기존 원본 v2.1.0 / 85쪽을 먼저 최소 페이지 제한 없이 검사했다. 로컬 이미지 47개, 빈 본문 페이지 및 깨진 로컬 링크/앵커 오류 0개. 기존 PDF에는 북마크가 없으므로 경고만 발생했다.
- 변경 렌더러는 별도 `artifacts/pdf-check/renderer-test`에 출력했다. 이미지 47개, Mermaid 4개, 잘못된 앵커와 브라우저 오류 0개. 결과 85쪽, PDF 북마크 177개, 태그 구조 있음.
- 원래 PDF와 변경 렌더러 PDF의 85쪽 전체를 PDFium scale=0.5로 비교한 결과 픽셀 차이 페이지 0개. 글꼴·여백·CSS·기존 수식 처리는 변경하지 않았다.
- `--chapter-pattern '^A1\.'`로 자동 단원 검색을 시험했고 9쪽을 찾았다. 첫쪽·9쪽·마지막쪽 고해상도 PNG와 전체 8개 접촉 시트가 생성됐다. 첫 접촉 시트와 9쪽 고해상도 이미지를 직접 확인했다. 모든 접촉 시트의 수동 검토를 완료했다는 뜻은 아니다.
- 음성 테스트: 기존 85쪽에 `--require-100-pages --expected-version v99.0.0` 적용 시 두 조건 모두 오류로 보고하고 종료 코드 1을 반환했다. 정상 검사 종료 코드는 0이다.

## 최종 작성자 실행 순서

저장소 루트에서 원본·그림 작성이 모두 끝난 후 실행한다. 아래 첫 명령만 최신 PDF를 갱신하며, QA는 입력 원본/PDF를 읽기만 한다.

```sh
node tools/render_report.mjs
research/20261031_vo-lo-study/.venv/bin/python tools/check_camera_textbook.py --require-100-pages --require-navigation
```

명시한 버전을 요구하려면 두 번째 명령에 `--expected-version v3.0.0`처럼 **실제 최종 버전**을 추가한다. 생략해도 원본의 `문서 버전: vX.Y.Z`와 PDF 첫쪽 버전이 일치하는지 검사한다.

- 결과: `research/camera-slam-textbook/artifacts/pdf-check/validation.json`.
- 전 페이지 축소본: `contact-001.jpg`부터 12쪽씩. 마지막 시트의 미사용 칸은 회색이며 PDF 빈 페이지가 아니다.
- 고해상도: `page-NNN.png`, 144 DPI. 첫쪽·마지막쪽과 새 단원 표제가 검출된 모든 페이지를 선택한다.
- 기본 표제 선택: Markdown 제목 안의 C1, C2 등 단원 번호, `camera`, 또는 `카메라`와 `교재/파트/부` 조합. 표제는 PDF 추출 텍스트와 공백을 제거해 대조한다. 별도 목차에 동일 제목이 있으면 해당 페이지도 선택될 수 있다.
- 제목 규칙이 다르면 `--chapter-pattern '원하는 정규식'`, 추가 확인 페이지는 `--pages 20,21,22`를 지정한다.
- 실행마다 `validation.json`에 적힌 이미지 목록만 현재 결과로 취급한다. 이전 실행에서 남은 이미지는 자동 삭제하지 않는다.
- 최종 담당자는 모든 접촉 시트와 선택된 고해상도 페이지를 열어 한글, 그림, 표·코드 잘림, 겹침, 페이지 경계를 확인한다. 필요한 페이지는 `--pages`로 추가 출력한다.

## 원본을 건드리지 않는 렌더러 회귀 검사

```sh
REPORT_PDF_OUTPUT=research/camera-slam-textbook/artifacts/pdf-check/renderer-test node tools/render_report.mjs
research/20261031_vo-lo-study/.venv/bin/python tools/check_camera_textbook.py --pdf research/camera-slam-textbook/artifacts/pdf-check/renderer-test/report.pdf --output research/camera-slam-textbook/artifacts/pdf-check/renderer-test --require-navigation --chapter-pattern '^A1\.'
```

`REPORT_PDF_OUTPUT`은 PDF와 중간 HTML 출력 위치만 변경한다. HTML의 base URL을 기존 `docs/`로 유지하여 그림 상대경로를 보존한다. 기본 실행 경로와 `--check-only` 동작은 유지한다.

## 의존성 및 근거

실제 사용한 패키지는 `/tmp/kitti-report-pdf/node_modules`의 marked 18.1.3, playwright 1.65.0, mermaid 12.3.0이다. 처음에는 디렉터리만 있고 모듈 파일이 빠져 있어 다음 명령으로 오프라인 복구했다.

```sh
npm install --offline --prefix /tmp/kitti-report-pdf marked@18.1.3 playwright@1.65.0 mermaid@12.3.0
```

QA Python 환경에는 `pypdfium2`, `Pillow`, `markdown_it`가 이미 설치되어 있었다. 새로운 수학 렌더링 패키지는 추가하지 않았다. 기본 브라우저는 기존 Google Chrome이며 `REPORT_CHROME`, `REPORT_PDF_DEPS` 환경변수도 그대로 지원한다.

- API 근거: `/tmp/kitti-report-pdf/node_modules/playwright-core/types/types.d.ts:4203`의 `outline`, `:4239`의 `tagged` 옵션. 실제 생성 PDF에서 PDFium 북마크 열거 및 `FPDFCatalog_IsTagged`로 확인했다.
- `tools/check_camera_textbook.py`는 MarkdownIt와 HTMLParser로 이미지·링크를 추출한다. 로컬 파일 존재, 동일 문서 명시적 앵커, 래스터 이미지 디코딩, 첫쪽 버전, 페이지 수, 렌더링 본문 잉크를 검사한다. 원본/PDF SHA-256과 실행 중 입력 변경 여부도 기록한다.
- 외부 URL은 목록만 기록하고 네트워크로 검증하지 않는다. 다른 파일 내부의 fragment, 참고문헌의 학술적 타당성, 모든 내용의 최신 PDF 반영은 보증하지 않는다. 버전이 같다는 사실만으로 원본과 PDF의 내용 전체가 같음을 증명할 수 없다.
- 빈 페이지 검사는 바깥 여백과 페이지 번호 영역을 제외한 저해상도 픽셀 기준이다. 거의 빈 페이지, 잘림·겹침, 한글 글리프 오류를 완전히 판정하지 못하므로 시각 검토를 대체하지 않는다. 태그 존재 검사는 PDF/UA 접근성 인증이 아니다.
- 아직 100쪽 이상 신규 교재는 작성 중이므로 그 최종 결과는 미검증이다. 최종 작성자가 위 명령으로 다시 확인해야 한다.

## 최종 QA 기록: v3.0.0 / 192쪽

2026-11-24 최종 확인. 위의 작성 중·최종 미검증 기록은 당시 상태이며, 아래 결과로 갱신한다.

- 근거: `research/camera-slam-textbook/artifacts/pdf-check/validation.json`. `--require-100-pages --require-navigation --expected-version v3.0.0` 검사 통과, 오류·경고 0개. 원본과 PDF의 현재 해시도 기록값과 일치한다.
- 원본 SHA-256: `4afbc8ec22bad886f53bf20e20166a8a75f0a3830c21b48e69919c5308a1e990`.
- PDF SHA-256: `2b92c3b5918477b2bfe116cf319c47762a20b70b025e241fbddbacc94b3e9a73`.
- 이미지 삽입 93회(고유 이미지 92개), Mermaid 5개, PDF 북마크 350개, 태그 구조 정상. 빈 본문 페이지·로컬 참조·이미지 검사 통과.
- 최종 시각 검토 분담: 1–96쪽은 main 담당자가 새 접촉 시트 005–008 및 고해상도 50·62·90쪽을 포함해 확인했다고 전달했다. 97–192쪽은 이 도구 담당자가 새 접촉 시트 009–016 전체와 장 시작·의심 경계 고해상도 페이지를 확인했다. 중대한 잘림·겹침·한글 깨짐·표 배치 문제는 남아 있지 않았다.
- 캡션 분리 수정: 이미지 문단에 `break-inside:avoid; break-after:avoid`만 적용했다. 최종 C4-11 82쪽, C5-01 85쪽, C6-05 102쪽, C12-08 136쪽, C12-16 144쪽에서 그림과 캡션이 같은 페이지에 있음을 확인했다. 기존 화면 그림의 캡션도 183쪽에서 확인했다. 글꼴·여백·강제 페이지 추가 없이 해결했으며, main이 도구 변경을 커밋했다고 전달했다.
- 검증 경계: 앞서 기존 85쪽 정상 검사와 페이지 수·버전 불일치 음성 테스트를 수행했다. 알고리즘 읽기 전용 검토에서 발견한 합성 회전 오차의 hold/성공 조건부 통계 혼합은 Bacon이 분리 수정했고, main이 19번째 회귀 테스트 통과 및 설명 보완을 확인했다고 전달했다. 이는 PDF QA에서 알고리즘 실험 전체를 재실행했다는 뜻이 아니다. 외부 참고문헌 검증·PDF/UA 인증도 이 검토 범위 밖이다.
- 이 최종 기록 추가 작업에서는 이 노트만 수정했다. PDF 재렌더링, `docs/`·도구 변경, 추가 커밋은 하지 않았다.
