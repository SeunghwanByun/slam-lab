"""Verify the handoff, without writing the canonical report or renderer."""
import io
import json
import re
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
from experiments import BASE
from test_experiments import NumericContracts


def main():
    source=BASE/"notes/chapters.md"
    content=source.read_text()
    docs=BASE.parents[2]/"docs"
    anchors=re.findall(r'<a id="([^"]+)"></a>',content)
    assert anchors==["d5","d6","d7","d8"],anchors
    assert len(re.findall(r"^## ",content,re.M))==4
    assert content.count("```text")==content.count("```")//2
    links=re.findall(r"!\[[^\]]*\]\(([^)]+)\)",content)
    assert len(links)==14 and len(set(links))==14
    pictures=[]
    for link in links:
        path=(docs/link).resolve()
        assert path.is_relative_to(BASE)
        with Image.open(path) as im:
            assert im.width==1400
            assert min(im.info["dpi"])>=180
            assert np.asarray(im.convert("L")).std()>10
            pictures.append({"path":str(path.relative_to(BASE)),"size":list(im.size),"dpi":list(im.info["dpi"])})
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NumericContracts))
    output=BASE/"artifacts/qa"
    output.mkdir(exist_ok=True)
    (output/"tests.txt").write_text(stream.getvalue())
    summary={"tests":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"chapters":4,"h3_sections":len(re.findall(r"^### ",content,re.M)),"solved_exercises":len(re.findall(r"^문제 D[5-8]-\d+\.",content,re.M)),"lines":len(content.splitlines()),"bytes":source.stat().st_size,"figures":pictures,"canonical_modified":False,"visual_review":"14 figures viewed individually; PDF integration belongs to main writer"}
    (output/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False))
    print(json.dumps(summary,indent=2,ensure_ascii=False))
    assert result.wasSuccessful()


if __name__=="__main__":main()
