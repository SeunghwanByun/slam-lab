import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const dependencies = process.env.REPORT_PDF_DEPS || '/tmp/kitti-report-pdf/node_modules';
const {marked} = await import(pathToFileURL(path.join(dependencies, 'marked/lib/marked.esm.js')));
const {chromium} = await import(pathToFileURL(path.join(dependencies, 'playwright/index.mjs')));
const directory = path.resolve(process.argv[2] || 'research/20261030_progress-review');
let content = marked.parse(await fs.readFile(path.join(directory, 'report.md'), 'utf8'));
content = content.replace(/<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/g, '<pre class="mermaid">$1</pre>');
const html = `<!doctype html><html lang="ko"><meta charset="utf-8"><title>KITTI 연구 보고서</title>
<style>
@page{size:A4;margin:18mm 15mm}body{font-family:'Apple SD Gothic Neo','Noto Sans CJK KR',sans-serif;font-size:10pt;line-height:1.65;color:#18242b}h1{font-size:23pt}h2{font-size:16pt;border-bottom:1px solid #a9b8bf;padding-bottom:5px;margin-top:24px}h3{font-size:12pt}h1,h2,h3{break-after:avoid}p,li{orphans:3;widows:3}table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:8pt;margin:12px 0}th,td{border:1px solid #c9d3d8;padding:5px;vertical-align:top;overflow-wrap:anywhere}th{background:#eef3f5}thead{display:table-header-group}tr{break-inside:avoid}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f4f5;padding:10px;font-size:8pt}code{font-family:Menlo,monospace;font-size:.88em;overflow-wrap:anywhere}img{max-width:100%;max-height:210mm;object-fit:contain}a{color:#08677b;text-decoration:none}svg{max-width:100%;height:auto}pre.mermaid{background:white;break-inside:avoid}
</style><body>${content}</body></html>`;
const htmlPath = path.join(directory, 'report.print.html');
await fs.writeFile(htmlPath, html);
const browser = await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
try {
 const page = await browser.newPage();
 await page.goto(pathToFileURL(htmlPath).href);
 await page.addScriptTag({path:path.join(dependencies,'mermaid/dist/mermaid.min.js')});
 await page.evaluate(async()=>{mermaid.initialize({startOnLoad:false,theme:'neutral'});await mermaid.run();await document.fonts.ready;await Promise.all([...document.images].map(i=>i.decode()));});
 if(await page.locator('.mermaid svg').count()!==1)throw Error('Missing architecture diagram');
 await page.pdf({path:path.join(directory,'report.pdf'),format:'A4',printBackground:true,displayHeaderFooter:true,headerTemplate:'<span></span>',footerTemplate:'<div style="font-size:9px;width:100%;text-align:center;color:#777"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',preferCSSPageSize:true});
 console.log(path.join(directory,'report.pdf'));
} finally {await browser.close();}
