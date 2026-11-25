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
