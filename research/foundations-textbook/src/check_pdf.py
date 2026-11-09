"""Check textbook content and render every PDF page for visual inspection."""
import json
import re
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[1]
OUT = STUDY / 'artifacts' / 'pdf-check'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = (ROOT / 'docs/report.md').read_text()
    assert len(re.findall(r'^### A\d+\.', source, re.M)) == 12
    assert len(re.findall(r'\*\*문제 A\d+-\d\.', source)) == 24
    assert len(re.findall(r'\*\*해설 A\d+-\d\.', source)) == 24
    assert len(re.findall(r'!\[.*?\]\(../research/foundations-textbook/figures/', source)) == 15
    numerical = json.loads((STUDY / 'artifacts/summary.json').read_text())
    assert len(numerical['checks']) == 25
    pdf = pdfium.PdfDocument(ROOT / 'docs/report.pdf')
    pages, thumbs, starts = [], [], {}
    for index in range(len(pdf)):
        page = pdf[index]
        textpage = page.get_textpage()
        text = textpage.get_text_range()
        compact = re.sub(r'\s+', '', text)
        assert len(compact) > 20, f'Unexpected almost-empty page: {index+1}'
        pages.append(text)
        for lesson in range(1, 13):
            if f'A{lesson}.' in compact and lesson not in starts:
                starts[lesson] = index + 1
        bitmap = page.render(scale=0.45)
        thumb = bitmap.to_pil().convert('RGB')
        thumbs.append(thumb)
        bitmap.close()
        textpage.close()
        page.close()
    full = re.sub(r'\s+', '', '\n'.join(pages))
    assert 'v2.0.0' in full
    assert len(starts) == 12
    for lesson in range(1, 13):
        for exercise in (1, 2):
            assert f'문제A{lesson}-{exercise}.' in full
            assert f'해설A{lesson}-{exercise}.' in full
    (OUT / 'text.txt').write_text('\n\n'.join(pages))
    sheets = []
    width, height = thumbs[0].size
    for start in range(0, len(thumbs), 12):
        sheet = Image.new('RGB', (3 * width, 4 * (height + 22)), '#d8dde1')
        draw = ImageDraw.Draw(sheet)
        for offset, thumb in enumerate(thumbs[start:start+12]):
            x, y = (offset % 3)*width, (offset // 3)*(height+22)
            draw.text((x+8, y+4), f'Page {start+offset+1}', fill='black')
            sheet.paste(thumb, (x, y+22))
        path = OUT / f'contact-{start//12+1:02d}.png'
        sheet.save(path)
        sheets.append(str(path))
    # Full-size lesson starts plus real-data projection and ending pages.
    selected = set(starts.values()) | {1, len(pdf)}
    for index, text in enumerate(pages):
        if any(label in re.sub(r'\s+', '', text) for label in ('그림A3-2.', '그림A7.', '그림A9.', '그림A11-2.')):
            selected.add(index + 1)
    for number in sorted(selected):
        page = pdf[number-1]
        bitmap = page.render(scale=1.5)
        bitmap.to_pil().save(OUT / f'page-{number:03d}.png')
        bitmap.close()
        page.close()
    result = {'pages': len(pdf), 'lesson_start_pages': starts,
              'exercises': 24, 'solutions': 24, 'new_figures': 15,
              'numerical_checks': 25, 'contact_sheets': sheets,
              'detail_pages': sorted(selected)}
    (OUT / 'checks.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    pdf.close()


if __name__ == '__main__':
    main()
