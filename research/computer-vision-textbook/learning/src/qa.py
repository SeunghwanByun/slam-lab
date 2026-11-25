"""Check integration links, scientific image sizes, provenance, and source scope."""
import json
import re
from pathlib import Path
from PIL import Image, ImageDraw
from experiment import BASE, ROOT, digest


def main():
    source=BASE/'notes/chapters.md'
    text=source.read_text()
    images=re.findall(r'!\[[^\]]*\]\(([^)]+)\)',text)
    anchors=re.findall(r'<a id="([^"]+)"',text)
    assert anchors==['d17','d18','d19','d20'], anchors
    assert len(images)==13 and len(set(images))==13
    dims={}
    for link in images:
        p=(ROOT/'docs'/link).resolve()
        assert p.is_relative_to(BASE/'figures') and p.exists(), link
        with Image.open(p) as im:
            dpi=im.info['dpi'][0]
            assert dpi>=180 and im.width/dpi>=6.99
            assert im.convert('L').getextrema()[0]<200
            dims[p.name]={'pixels':im.size,'dpi':dpi}
    manifest=json.loads((BASE/'artifacts/manifest.json').read_text())
    for name,sha in manifest['input_sha256'].items():
        assert digest(ROOT/name)==sha,name
    for name,sha in manifest['figure_sha256'].items():
        assert digest(BASE/'figures'/name)==sha,name
    tests=json.loads((BASE/'artifacts/tests.json').read_text())
    assert tests['successful'] and tests['checks']>=24
    assert text.count('```')%2==0
    assert len(re.findall(r'\*\*문제 D\d+-[A-D]:',text))==16
    report={'source_bytes':source.stat().st_size,'source_lines':len(text.splitlines()),'chapters':anchors,'figures':dims,'solved_exercises':16,'numeric_checks':tests['checks'],'verified_hashes':True,'fences_balanced':True}
    (BASE/'artifacts/qa.json').write_text(json.dumps(report,indent=2)+'\n')
    sheet=Image.new('RGB',(1200,350*7),'white')
    draw=ImageDraw.Draw(sheet)
    for n,p in enumerate(sorted((BASE/'figures').glob('*.png'))):
        with Image.open(p) as im:
            im=im.convert('RGB');im.thumbnail((580,315))
            x=(n%2)*600;y=(n//2)*350
            sheet.paste(im,(x,y+25));draw.text((x+10,y+5),p.stem,fill='black')
    sheet.save(BASE/'artifacts/contact_sheet.png')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
