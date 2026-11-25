"""Validate manuscript links and scientific figure files; make QA contact sheets."""
import hashlib
import json
from pathlib import Path
import re
import numpy as np
from PIL import Image, ImageDraw

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE.parents[2]
text=(BASE/"notes/chapters.md").read_text()
anchors=re.findall(r'<a id="([^"]+)"></a>',text)
assert len(anchors)==len(set(anchors))
assert all(re.fullmatch(r'd2[1-4](?:-\d+)?',a) for a in anchors)
assert re.findall(r'^## (D\d+)\.',text,re.M)==['D21','D22','D23','D24']
links=re.findall(r'!\[[^\]]*\]\(([^)]+)\)',text)
assert len(links)==14 and len(set(links))==14
assert text.count('**문제 D')==16 and text.count('**풀이.**')==16
assert text.count('```')%2==0
manifest=json.loads((BASE/"artifacts/manifest.json").read_text())
tests=json.loads((BASE/"artifacts/tests/results.json").read_text())
assert tests['successful'] and tests['run']>=40
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE/'configs/default.json')==manifest['config_hash']
for path,digest in manifest['source_hashes'].items():
    assert sha(ROOT/path)==digest,path
for path,digest in manifest['data_hashes'].items():
    assert sha(ROOT/path)==digest,path
checks=[]
images=[]
for link in links:
    p=(ROOT/'docs'/link).resolve()
    assert p.is_relative_to(BASE/'figures') and p.exists(),p
    with Image.open(p) as im:
        assert im.width==1330,(p,im.size)
        assert im.info.get('dpi',(0,0))[0]>=180
        assert np.asarray(im.convert('RGB')).std()>10
        assert sha(p)==manifest['figures'][p.name]
        checks.append({'name':p.name,'shape':list(im.size),'dpi':im.info['dpi']})
        thumb=im.convert('RGB');thumb.thumbnail((665,665));images.append((p.name,thumb))
qa=BASE/'artifacts/qa';qa.mkdir(exist_ok=True)
for page in range(4):
    sheet=Image.new('RGB',(1330,1410),'white');draw=ImageDraw.Draw(sheet)
    for index,(name,thumb) in enumerate(images[page*4:page*4+4]):
        x=(index%2)*665;y=(index//2)*705
        draw.text((x+10,y+5),name,fill='black')
        sheet.paste(thumb,(x,y+30))
    sheet.save(qa/f'contact_{page+1}.png')
for module in ['geometry','rendering','timing','evaluation','stereo']:
    with np.load(BASE/f'artifacts/{module}/arrays.npz') as data:
        assert len(data.files)>0
        for name in data.files:
            assert np.isfinite(data[name]).all(),(module,name)
result={'chapters':4,'anchors':len(anchors),'figures':checks,'solved_exercises':16,'numerical_tests':tests,'manuscript_bytes':len(text.encode()),'manuscript_lines':len(text.splitlines()),'npz_modules':5,'sha256':sha(BASE/'notes/chapters.md')}
(qa/'checks.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='figures'},indent=2))
