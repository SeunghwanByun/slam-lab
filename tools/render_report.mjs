import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const directory=path.join(root,'docs');
const deps=process.env.REPORT_PDF_DEPS || '/tmp/kitti-report-pdf/node_modules';
const {marked}=await import(pathToFileURL(path.join(deps,'marked/lib/marked.esm.js')));
const {chromium}=await import(pathToFileURL(path.join(deps,'playwright/index.mjs')));
const markdown=await fs.readFile(path.join(directory,'report.md'),'utf8');
const tokens=marked.lexer(markdown);
const localImages=[];
let expectedDiagrams=0;
marked.walkTokens(tokens,t=>{
  if(t.type==='code' && t.lang==='mermaid')expectedDiagrams++;
  if(t.type==='image' && !/^(?:[a-z][a-z\d+.-]*:|#)/i.test(t.href))localImages.push(t.href);
});
for(const href of localImages)await fs.access(path.resolve(directory,href));
if(!expectedDiagrams || !localImages.length)throw Error('Expected study diagrams and figures');
let content=marked.parser(tokens);
content=content.replace(/<h3>(A\d+\.)/g,'<h3 style="break-before:page">$1');
content=content.replace('<a id="foundations"></a>','<section class="foundations"><a id="foundations"></a>');
content=content.replace('<a id="orb"></a>','</section><a id="orb"></a>');
content=content.replace(/<p><strong>문제 (A\d+-\d\.)/g,'<p style="break-after:avoid"><strong>문제 $1');
content='<style>body img{max-height:170mm}.foundations img{max-height:85mm;display:block;margin:0 auto}.foundations pre{break-inside:avoid}.foundations p:has(>img){break-after:avoid}</style>'+content;
content=content.replace(/<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/g,'<pre class="mermaid">$1</pre>');
const html=`<!doctype html><html lang="ko"><meta charset="utf-8"><title>SLAM Lab 통합 보고서</title>
<style>@page{size:A4;margin:18mm 15mm}body{font-family:'Apple SD Gothic Neo','Noto Sans CJK KR',sans-serif;font-size:10pt;line-height:1.65;color:#18242b}h1{font-size:23pt}h2{font-size:17pt;border-bottom:1px solid #a9b8bf;padding-bottom:5px;break-before:page}h3{font-size:14pt;margin-top:24px}h4{font-size:12pt}h1,h2,h3,h4{break-after:avoid}p,li{orphans:3;widows:3}table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:8pt;margin:12px 0}th,td{border:1px solid #c9d3d8;padding:5px;vertical-align:top;overflow-wrap:anywhere}th{background:#eef3f5}thead{display:table-header-group}tr{break-inside:avoid}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f4f5;padding:10px;font-size:8pt}code{font-family:Menlo,monospace;font-size:.88em;overflow-wrap:anywhere}img{max-width:100%;max-height:210mm;object-fit:contain}a{color:#08677b;text-decoration:none}svg{max-width:100%;height:auto}pre.mermaid{background:white;break-inside:avoid}</style><body>${content}</body></html>`;
const htmlPath=path.join(directory,'report.print.html');
await fs.writeFile(htmlPath,html);
const browser=await chromium.launch({executablePath:process.env.REPORT_CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
try{
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(htmlPath).href);
 await page.addScriptTag({path:path.join(deps,'mermaid/dist/mermaid.min.js')});
 await page.evaluate(async()=>{mermaid.initialize({startOnLoad:false,theme:'neutral'});await mermaid.run();await document.fonts.ready;await Promise.all([...document.images].map(i=>i.decode()));});
 const diagrams=await page.locator('.mermaid svg').count();
 if(diagrams!==expectedDiagrams)throw Error(`Diagrams: ${diagrams}/${expectedDiagrams}`);
 const invalidAnchors=await page.evaluate(()=>[...document.querySelectorAll('a[href^="#"]')].filter(a=>!document.getElementById(decodeURIComponent(a.hash.slice(1)))).map(a=>a.hash));
 if(invalidAnchors.length||errors.length)throw Error(JSON.stringify({invalidAnchors,errors}));
 if(!process.argv.includes('--check-only'))await page.pdf({path:path.join(directory,'report.pdf'),format:'A4',printBackground:true,displayHeaderFooter:true,headerTemplate:'<span></span>',footerTemplate:'<div style="font-size:9px;width:100%;text-align:center;color:#777">SLAM Lab · <span class="pageNumber"></span> / <span class="totalPages"></span></div>',preferCSSPageSize:true});
 console.log(JSON.stringify({pdf:path.join(directory,'report.pdf'),images:localImages.length,diagrams,invalidAnchors,errors,checkOnly:process.argv.includes('--check-only')}));
}finally{await browser.close();}
