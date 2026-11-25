"""Check handoff links, raster assets, numeric tests, and produce a QA contact sheet."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw

base=Path(__file__).resolve().parents[1]
root=base.parents[2]
doc=(base/'notes/chapters.md').read_text()
anchors=re.findall(r'<a id="([^"]+)"',doc)
assert len(anchors)==len(set(anchors))
assert re.findall(r'^## (D\d+)\.',doc,re.M)==['D13','D14','D15','D16']
links=re.findall(r'!\[[^\]]*\]\(([^)]+)\)',doc)
assert len(links)==12
images=[]
for link in links:
    path=(root/'docs'/link).resolve()
    assert path.exists(),path
    im=Image.open(path).convert('RGB')
    assert im.width>=1400 and im.height>=600
    assert np.asarray(im).std()>10
    images.append(im)
qa=base/'artifacts/qa'; qa.mkdir(parents=True,exist_ok=True)
sheet=Image.new('RGB',(1400,4*520),'white'); draw=ImageDraw.Draw(sheet)
for i,im in enumerate(images):
    im.thumbnail((450,470)); x=(i%3)*466; y=(i//3)*520
    sheet.paste(im,(x,y+25)); draw.text((x+5,y+5),Path(links[i]).name,fill='black')
sheet.save(qa/'contact.png')
test=subprocess.run([sys.executable,str(base/'src/test_geometry.py')],capture_output=True,text=True)
assert test.returncode==0,test.stderr
(qa/'tests.txt').write_text(test.stdout+test.stderr)
result={'chapters':4,'h3_sections':len(re.findall(r'^### ',doc,re.M)),
        'anchors':len(anchors),'figures':len(links),'solved_exercises':len(re.findall(r'^\*\*문제 \d+',doc,re.M)),
        'lines':len(doc.splitlines()),'bytes_utf8':len(doc.encode()),'tests':22,'tests_passed':True,
        'chapter_sha256':hashlib.sha256(doc.encode()).hexdigest(),
        'artifact_sha256':{str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in list((base/'figures').glob('*.png'))+list((base/'artifacts').glob('*/*.npz'))}}
(qa/'audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
