// One-time mechanical Markdown migration. Future edits belong in docs/report.md.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = path.join(root, 'docs/report.md');
const deps = process.env.REPORT_PDF_DEPS || '/tmp/kitti-report-pdf/node_modules';
const fence = '`'.repeat(3);
const {marked} = await import(pathToFileURL(path.join(deps, 'marked/lib/marked.esm.js')));
await fs.mkdir(path.dirname(out), {recursive:true});
try { await fs.access(out); throw new Error('docs/report.md already exists: edit it directly; do not overwrite from archives.'); }
catch(e) { if(e.code !== 'ENOENT') throw e; }

async function extract(directory, wanted) {
  const source = path.join(root, 'research', directory, 'report.md');
  const tokens = marked.lexer(await fs.readFile(source, 'utf8'));
  let active = false, parentSelected = false;
  const result=[];
  for(const token of tokens) {
    if(token.type==='heading' && token.depth<=3) {
      const key=token.text.match(/^(\d+(?:\.\d+)?)(?:\.|\s)/)?.[1];
      if(token.depth===2) { parentSelected=wanted.includes(key || token.text); active=parentSelected; }
      else active=parentSelected || wanted.includes(key);
    }
    if(!active)continue;
    if(token.type==='heading') {
      result.push('#'.repeat(Math.min(token.depth+1,6))+' '+token.text.replace(/^\d+(?:\.\d+)*\.?\s*/, '')+'\n\n');
      continue;
    }
    let raw=token.raw;
    marked.walkTokens([token], t=>{
      if(!['image','link'].includes(t.type) || !t.href || /^(?:[a-z][a-z\d+.-]*:|#|\/)/i.test(t.href))return;
      const absolute=path.resolve(path.dirname(source), t.href);
      const href=path.relative(path.dirname(out), absolute).split(path.sep).join('/');
      raw=raw.replace(t.raw,t.raw.replace(t.href,href));
    });
    result.push(raw);
  }
  if(!result.length)throw new Error(`Empty source selection: ${directory}`);
  return result.join('');
}

const chapters=[
  {id:'orb',title:'2. ORB: 픽셀부터 descriptor와 매칭까지',dir:'20261101_orb-explained',parts:['3','4','5','7','8','9','부록: 재현 경계와 참고문헌'],note:'기존 요약보다 상세한 설명을 우선한다. 피라미드 그림은 공통 픽셀 축으로 보완한 최신 자료다.'},
  {id:'vo-lo',title:'3. VO 기하와 LiDAR Odometry: 구현·비교·한계',dir:'20261031_vo-lo-study',parts:['4.6','4.7','4.8','4.9','5','6','7','8','9','10','부록'],note:'첫 200프레임 실험이다. 화면 구성은 5장의 통합 재생이 최신이다. 이 장의 실행 당시 커밋·측정 조건은 역사적 실험 출처로 보존한다.'},
  {id:'loops',title:'4. SLAM과 재방문: 데이터가 있는가, 무엇이 아직 없는가',dir:'20261031_loop-readiness',parts:['2','3','4','5','7','8','9','10','부록'],note:'GT를 사용한 후보 분석이며 자동 loop closure 구현 결과가 아니다.'},
  {id:'playback',title:'5. 좌우 카메라·VO·LO 통합 재생',dir:'20261101_unified-playback',parts:['2','3','4','5','7','8','9','10','부록'],note:'오른쪽 영상은 표시용이다. 단안 VO를 stereo VO로 바꾸지 않았다.'},
  {id:'audit',title:'6. 초기 데이터·IMU 감사 기록과 과거 baseline',dir:'20261030_progress-review',parts:['3','7','8','부록'],note:'이 장만은 초기 상태의 보관 기록이다. 여기의 LO 미구현·ATE 미측정·옛 main 코드 지적은 당시 상태이며 현재 상태가 아니다. 현재 LO 구현 및 측정값은 3장, 현재 재생은 5장이 우선한다. 과거 실패·미확인 사항을 삭제하지 않기 위해 보존했다.'}
];

let document=`# Visual SLAM Lab 통합 학습·연구 보고서

**문서 버전: v1.0.0**<br>
**최종 갱신: 2026-11-02**<br>
**고정 경로: docs/report.md → docs/report.pdf**<br>
**통합 기준 코드: 681582f (origin/main)**

## 읽는 순서와 문서 정책

이 파일이 유일한 최신 보고서 원본이다. PDF는 같은 원본에서 생성한다. 이후 설명 보완·실험 결과·그림 수정은 이 문서 안에서 갱신하고 마지막 변경 이력의 버전을 올린다. 날짜나 버전이 붙은 새 report 파일은 만들지 않는다. 변경 전 내용은 Git 이력으로 확인한다.

기존 날짜별 연구 디렉터리는 코드·설정·실험 산출물과 과거 보고서 보관소다. 오래된 PDF를 최신 설명으로 사용하지 않는다. 자료를 합치면서 ORB의 구형 자동 확대 피라미드 설명은 상세 교정본으로 대체했고, 과거 감사는 역사적 기록으로 표시했다. 기존 파일을 삭제하거나 실행 경로를 이동하지 않았다.

- [1. 현재 상태](#current)
- [2. ORB 상세 학습](#orb)
- [3. VO 기하·LiDAR Odometry·성능 비교](#vo-lo)
- [4. SLAM·재방문 후보](#loops)
- [5. 통합 재생](#playback)
- [6. 초기 감사와 IMU 기록](#audit)
- [7. 재현 및 문서 갱신](#reproduce)
- [8. 버전 변경 이력](#versions)

<a id="current"></a>

## 1. 현재 상태

- 입력: KITTI Odometry grayscale stereo, 00 LiDAR, GT와 calibration. Raw OXTS도 있으나 시간 정렬은 검증되지 않았다.
- VO: ORB→BF Hamming cross-check→Essential RANSAC→recoverPose. 단안 이동 방향을 누적하며 metric scale 복원은 없다.
- LO: KISS-ICP 기반 첫 200프레임 연구 구현. 전역 loop detection·pose graph 최적화는 미구현이다.
- 화면: 좌우 원본, 왼쪽 ORB·시간 매칭, LiDAR 투영·BEV, GT/VO/LO를 동기 재생한다.
- 평가: GT 사후 Sim(3) 형상 비교와 미터 단위 LO 평가를 구분한다. 좋은 모양이 실제 VO 거리 정확도를 뜻하지 않는다.

이 문서의 버전과 알고리즘 성능 버전은 다르다. v1.0.0 통합 자체는 새 정확도 실험이나 알고리즘 변경이 아니다. 주제별 과거 실험에서 사용하는 상대 경로 'src/', 'artifacts/', 'configs/'는 각 장에 명시한 원 실험 디렉터리를 기준으로 읽는다. 쉘 실행 명령은 별도 지시가 없으면 레포 루트 기준이다.

`;
for(const c of chapters) {
  document+=`<a id="${c.id}"></a>\n\n## ${c.title}\n\n${c.note}\n\n**원 실험 디렉터리:** \`research/${c.dir}/\`\n\n`;
  document+=await extract(c.dir,c.parts)+'\n\n';
}
document+=`<a id="reproduce"></a>

## 7. 재현 및 문서 갱신

### 최신 문서 갱신 절차
1. docs/report.md의 해당 주제를 직접 수정한다. 새 날짜별 보고서를 만들지 않는다.
2. 같은 문서 맨 위 버전과 아래 변경 이력을 함께 갱신한다. 오탈자는 patch, 설명/결과 확장은 minor, 구조·평가 계약의 큰 변경은 major를 올린다.
3. 그림은 실험 디렉터리의 실제 산출물을 상대경로로 연결하고 출처·설정·코드 버전을 기록한다.
4. 다음 명령으로 docs/report.pdf를 덮어쓴다. 원본과 PDF를 같은 기능 커밋에 포함한다.

${fence}sh
node tools/render_report.mjs
${fence}

초기 통합에 사용한 tools/consolidate_reports.mjs는 일회성 이관 도구다. 최신 원본이 있으면 실패하도록 되어 있으며 평소에는 실행하지 않는다. 각 장에 보존한 옛 PDF 생성 명령은 과거 재현 정보일 뿐 현재 문서 갱신에는 사용하지 않는다.

### 알고리즘 산출물 재현

${fence}sh
# 기존 연구 환경과 데이터가 있을 때 전체 VO/LO 실험
research/20261031_vo-lo-study/.venv/bin/python research/20261031_vo-lo-study/src/run.py --stage all

# 기존 결과로 통합 playback과 재방문 viewer만 갱신
research/20261031_vo-lo-study/.venv/bin/python research/20261031_vo-lo-study/src/run.py --stage playback

# ORB 상세 그림/수치 재현 (기존 orb/pyramid.npz 필요)
env MPLCONFIGDIR=.cache/matplotlib XDG_CACHE_HOME=.cache research/20261031_vo-lo-study/.venv/bin/python research/20261101_orb-explained/src/analyze.py

# 통합 재생 검증
node research/20261031_vo-lo-study/src/check_playback.mjs

# 최신 PDF
node tools/render_report.mjs

# PDF 렌더 검증 결과 재확인
node tools/render_report.mjs --check-only

${fence}

PDF 환경은 macOS Chrome, marked/playwright/mermaid다. 기본 의존성 경로는 /tmp/kitti-report-pdf/node_modules이고 REPORT_PDF_DEPS로 바꿀 수 있다. 설치 경로가 없으면 해당 패키지를 설치해야 한다. 다른 OS는 REPORT_CHROME으로 Chrome 실행 경로를 지정한다. 연구 Python 환경은 기존 requirements-lock.txt를 유지한다.

### Git 작업 규칙

병합된 feature 브랜치에 다음 작업을 이어 붙이지 않는다. 최신 main에서 새 feat/ 브랜치를 만든다. pull 실패를 해결하려고 데이터나 작업 파일을 지우지 않는다. 고유한 로컬 커밋이 있는지 먼저 확인한다.

${fence}sh
git fetch origin --prune
git switch main
git pull --ff-only origin main
git switch -c feat/<next-task>
${fence}

이번 로컬 main의 divergence 원인은 이미 원격에 동일 내용으로 존재하는 초기 session-summary 커밋의 해시 차이였다. backup/main-before-sync-20261101을 만든 뒤 rebase로 중복을 제거하여 681582f와 일치시켰다. 이 방법을 내용이 다른 로컬 커밋에도 무조건 적용한다는 뜻은 아니다. 전역 pull 설정은 변경하지 않았다.

<a id="versions"></a>

## 8. 버전 변경 이력

| 버전 | 갱신일 | 내용 | 알고리즘 변경 |
|---|---|---|---|
| v1.0.0 | 2026-11-02 | 날짜별 5개 보고서의 상세 설명·실험·그림을 주제별 고정 문서로 통합. ORB는 최신 교정본 우선, 초기 감사는 역사적 기록으로 구분. 고정 PDF 빌드와 링크/다이어그램 검증 추가. | 없음 |

과거 연구의 날짜·커밋·가정·미확인은 각 장에 보존했다. 추후 변경은 같은 파일과 Git 이력에 남긴다.
`;
await fs.writeFile(out, document);
console.log(`Migrated ${chapters.length} topic chapters to ${out}. Edit this file directly from now on.`);
