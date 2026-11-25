# 출판 인프라 변경과 검증 기록

2026-11-25, 기존 v3.0.0 정본을 읽기 전용 fixture로 사용했다. 이 작업의 소유 범위는 `tools/check_camera_textbook.py`와 루트 `notes/{inventory.md,architecture.md,publication-qa.md}`다. 확정된 geometry 원고, 다른 연구자 폴더, canonical Markdown/PDF, `render_report.mjs`는 변경하지 않았다. 커밋·브랜치 변경도 수행하지 않았다.

## 변경 계약

- `--min-pages N`: 양의 정수 N을 받아 PDF 페이지 수가 작으면 실패한다. 생략하면 기존처럼 별도 하한이 없다.
- `--require-100-pages`: 기존 의미 유지. 두 옵션을 함께 쓰면 `max(N,100)`을 적용하며 JSON에 `min_pages`, `effective_min_pages`를 기록한다.
- 기본 chapter 정규식: C1–C24/D1–D24와 기존 camera/한국어 교재 키워드. D25/D240/D01이나 다른 영숫자 접두어를 잘못 부분 매칭하지 않는다. `--chapter-pattern` override 유지.
- `--source-coverage`: 선택적 JSON 및 stdout 통계. UTF-8 `source_bytes`, `source_lines`, 고유 H2 `new_d_chapter_count`/ID, 누락/중복 D ID, `image_occurrences`, `image_unique`를 제공한다.
- D장은 H2만 세므로 목차·본문 언급·H3·fenced code를 장으로 세지 않는다. 로컬 이미지 경로는 resolve한 경로로 중복 제거하며 외부 이미지는 URL identity로 센다. 외부 reference는 기존처럼 fetch하지 않는다.
- 기존 `local_images`와 링크/버전/빈 페이지/navigation/입력변경 검사는 유지했다. 원본 bytes는 산문 품질·신규 내용 증가의 자동 증명이 아니라 필요조건 통계다.
- 새 기본 출력은 `research/computer-vision-textbook/artifacts/pdf-check`다. 이전 camera-slam-textbook QA 디렉터리에 결과를 쓰지 않는다.

## 실제 PDF 통합 시험

작업 디렉터리는 저장소 루트다. 실행 Python은 아래와 같으며 `markdown_it`, `PIL`, `pypdfium2` import를 확인했다.

```text
research/20261031_vo-lo-study/.venv/bin/python tools/check_camera_textbook.py --min-pages 192 --source-coverage --require-navigation --expected-version v3.0.0
```

결과: exit 0, `ok=true`, 192쪽, effective minimum=192, errors/warnings 모두 빈 배열. 모든 192쪽을 raster 검사하고 16개 contact sheet를 생성했다. JSON은 새 기본 경로의 `validation.json`이다. source 통계는 434160 bytes, 5655행, D장 0, 이미지 93회·고유 92개였다. D장 24개 누락은 현재 확장 전 fixture의 정상 통계이며 자동 오류로 삼지 않는다.

```text
research/20261031_vo-lo-study/.venv/bin/python tools/check_camera_textbook.py --min-pages 384 --require-100-pages --source-coverage --require-navigation --expected-version v3.0.0 --output research/computer-vision-textbook/artifacts/pdf-check/min384
```

결과: 의도한 exit 1, `ok=false`, effective minimum=384. 유일한 오류는 `Page count 192 < 384`, warnings는 없다. 이전 옵션과 함께 써도 100으로 하한이 약화되지 않는다. 결과는 `artifacts/pdf-check/min384/validation.json`에 별도 보존해 성공 fixture 결과를 덮어쓰지 않았다.

```text
research/20261031_vo-lo-study/.venv/bin/python tools/check_camera_textbook.py --min-pages 0
```

결과: 의도한 exit 2, argparse 오류 `must be a positive integer`. 입력을 읽거나 결과 폴더를 생성하기 전 거부한다.

```text
research/20261031_vo-lo-study/.venv/bin/python tools/check_camera_textbook.py --require-100-pages --min-pages 50 --require-navigation --expected-version v3.0.0 --output research/computer-vision-textbook/artifacts/pdf-check/legacy100
```

결과: exit 0, `ok=true`, effective minimum=100, errors/warnings 모두 빈 배열. `--source-coverage`를 생략했으므로 JSON에 선택적 통계 key가 없음을 확인했다.

## 12개 회귀 시험

Python unittest로 12개 test method를 실행했고 모두 통과했다. 추가 테스트 파일을 소유 범위 밖에 만들지 않고 stdin에서 검사기를 import했다.

| 시험 | 정확한 assertion |
|---|---|
| default_min | `minimum_pages()==0` |
| legacy | `minimum_pages(None,True)==100` |
| lower_combined | `minimum_pages(50,True)==100` |
| higher_combined | `minimum_pages(384,True)==384` |
| min_only | `minimum_pages(192)==192` |
| positive | `positive_int('192')==192` |
| nonpositive | `'0'`, `'-1'` 모두 ArgumentTypeError |
| chapters | C/D 각 1–24의 48개 제목 모두 default regex 매칭 |
| chapter_boundaries | C0,D25,D240,AC1,CD13,D01 모두 매칭하지 않음 |
| legacy_camera | `Camera textbook`, `카메라 교재` 매칭 유지 |
| coverage | H2 D1,D24,D1중복; H3 D2/H2 C1/H2 D25/code D3 제외; 2고유장·중복D1·22누락; 이미지3회/2고유 |
| empty_coverage | 빈 입력: D0개, 이미지0개, 누락24개 |

coverage fixture는 다음 원본을 MarkdownIt commonmark(html=True)로 parse/render한 결과다. 로컬 경로 중복 제거와 외부 이미지를 함께 확인한다. source path는 `/tmp/docs/report.md`를 쓰되 실제 이미지 파일은 필요 없는 순수 통계 시험이다.

```markdown
## D1. 시작
## D24. 끝
### D2. 소절
## C1. 과거
## D1. 중복
## D25. 제외
~~~
## D3. 코드
~~~
![a](../a.png)
![b](.././a.png)
![c](https://example.com/a.png)
```

실행 fixture의 code fence는 backtick fence였고 위 표시용 fixture는 같은 CommonMark 의미의 tilde fence다. UTF-8 byte 수와 splitlines 행 수도 원본에서 계산한 값과 일치하는지 검사했다.

## 승인 범위

이번 결과는 검사기 변경의 회귀/fixture 검사다. 24장 통합, 384쪽 이상, 실질 원고 868320 bytes 이상, 신규48그림/72풀이, 통합 PDF 전체 시각 검토는 다른 게이트이며 아직 완료라고 선언하지 않는다. 새 글꼴·페이지 padding·여백 변경은 없다. 생성한 contact sheet만으로 glyph·잘림·겹침 검토를 승인하지 않는다. 통합 후에는 버전과 분량을 새 정본으로 다시 검사해야 한다.

최종 상태: 12개 회귀 시험, 실제 PDF 성공/의도적 실패/legacy 호환 3회, invalid 인자 거부 1회 완료. 세 validation JSON의 source/PDF hash가 모두 같고, baseline 192페이지 기록·16 contact sheet·선택 key 생략·의도한 단일 오류를 포함한 artifact 일관성 assertion 7개도 통과했다. 변경 파일의 `git diff --check`는 오류가 없었다.

## 최종 v4.0.0 PDF v2 검사와 145–300쪽 시각 검토

2026-11-25 추가 기록. 위 192쪽 fixture 시험과 이 최종 검사를 구분한다. 최초 455쪽 렌더에서는 standalone anchor paragraph 때문에 빈 페이지가 생겨 검토를 중단했다. 주 담당자가 anchor를 다음 heading의 id로 옮기는 renderer 수정을 적용하고 커밋 `b05400c`를 통보했다. 최종 검사 대상은 453쪽 수정본이며, 이전 `pdf-final-check`의 페이지 번호나 검토 결과를 그대로 승계하지 않는다.

검사 산출물 경로는 `research/computer-vision-textbook/artifacts/pdf-final-check-v2/`다. 다음은 같은 검사 조건을 재현하는 명령이다. 이번 분담 검토자는 검사기를 다시 돌리지 않고 주 담당자가 생성한 `validation.json`과 PNG/JPG를 읽었다.

```text
research/20261031_vo-lo-study/.venv/bin/python tools/check_camera_textbook.py --min-pages 384 --source-coverage --require-navigation --expected-version v4.0.0 --output research/computer-vision-textbook/artifacts/pdf-final-check-v2
```

JSON 직접 확인 결과: `ok=true`, v4.0.0, 453쪽, effective minimum 384, 원본 1186817 UTF-8 bytes/18042행, 고유 D장 24개(누락/중복 없음), 이미지 172회/고유171개, bookmarks721개, tagged=true, errors/warnings 모두 빈 배열, contact sheet38개다. raw byte 기준과 페이지 하한은 통과했으나 bytes 자체가 산문 품질을 증명한다는 뜻은 아니다.

```text
source SHA256:
fffc6e7d95ddf7de40e0dd268b3c89bb79f08e24acf57f784be938743b956524
PDF SHA256:
2287619cb307287af60f0ec29f12d7cac76bbf194bbaa1e1867c3dd51c077af5
```

**이 분담자의 직접 시각 검토 범위:** `view_image`로 v2의 `contact-013.jpg`부터 `contact-025.jpg`까지 13개를 빠짐없이 열어 145–300쪽 전체 156페이지를 확인했다. 이어 `page-162.png`, `172`, `182`, `192`, `210`, `219`, `228`, `243`, `244`, `247`, `259`, `269`, `280`, `298`의 고해상도 14페이지를 직접 열었다. 이 목록의 생략된 숫자는 모두 같은 경로의 `page-NNN.png`다. 텍스트 추출만으로 시각 검토를 대체하지 않았다.

- D1–D4 시작 페이지의 단위표·문단·수식과 수정 후192쪽 D4 정상 시작을 확인했다.
- D5 조건수 그림(210), D6 최적화 경로(219), D7 상관 분포(228), D8 NIS/NEES 그림·결과표(243), Mahalanobis gate와 캡션(244)을 확대 확인했다.
- D9–D12 시작 페이지(247/259/269/280)의 표·기호·코드 블록과 contact sheet상의 특징점·피라미드·대응·정합·광류 그림/캡션 배치를 확인했다. 298쪽 사영 격자와 캡션도 확대 확인했다.
- **발견 사항:** 담당 범위에서 출판을 막는 중대한 페이지 경계 잘림, 본문/표/그림 겹침, 그림과 캡션의 페이지 분리, 한글 glyph 손상을 발견하지 못했다. 장말의 여백과 다음 페이지로 이어지는 문장/수식은 보이나 내용 소실로 판정할 증거는 없었다.

**다른 분담의 상태:** 주 담당자는 1–144쪽 contact-001–012 전체와 고해상도1/96쪽에 문제가 없다고 통보했다(이 분담자가 대신 확인했다고 주장하지 않음). 301–453쪽의 별도 검토 결과는 이 기록 작성 시점에 수신하지 않아 **대기**로 남긴다. 전체 출판 승인은 주 담당자가 세 범위를 합쳐 확정한다. 이번 추가 작업은 이 QA 노트만 수정했으며 canonical Markdown/PDF, renderer, 확정 연구 원고와 다른 작업자의 파일은 변경하지 않았다.

## 최종 통합 승인

위 대기 상태 이후 301–453쪽 검토가 완료되었다. 해당 검토자는 contact-026–038 전체 13장과 고해상도 304, 306, 313, 322, 330, 342, 347, 350, 357, 358, 365, 372, 373, 375, 385, 394, 403, 453쪽을 확인했으며 중대한 잘림·겹침·고립 캡션을 발견하지 못했다. 세 범위를 합쳐 453쪽 전체의 contact sheet 38장과 선택 고해상도 34쪽을 시각 검토했다. 이는 모든 문장과 수치의 무오류 인증이 아니라 출판 배치 검토다.

정본은 기존 192쪽 대비 453쪽(2.3594배), UTF-8 원본 434160 bytes 대비 1186817 bytes(2.7336배)다. 글꼴 크기나 여백을 늘리지 않았다. 신규 D24장, 그림79개, 완전 풀이106문제와 여섯 파트 수치시험180개를 추가했다. 신규 그림79개는 Git에 포함했고 데이터/venv/중간 artifacts는 포함하지 않았다. 기존 운영 VO/LO 코드는 변경하지 않았다. 정본과 PDF는 위 SHA256의 검사본이며 단일 최신 경로를 유지한다.

최종 재현 순서는 저장소 루트에서 `node tools/render_report.mjs`, 위 `check_camera_textbook.py` 명령, 각 파트 handoff 또는 정본에 수록된 실험·검사 명령이다. 렌더러 수정은 빈 anchor 문단의 id를 다음 제목으로 옮겨 공백 페이지를 없앴으며, 내부 링크 검사와 721개 책갈피 검사를 통과했다. `git diff --check`도 통과했다. 연구 결과와 출판물의 재현 범위를 승인하며, 추가 알고리즘 개선·실제 SLAM/VIO 통합은 수행하지 않고 사용자 판단을 기다린다.
