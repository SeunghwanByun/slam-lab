"""Validate every output contract; optionally repeat full estimation independently."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from PIL import Image
from common import ROOT, STUDY, ART, FIG, CFG, initialize, directory, save_json, sha
from odometry import run_segment


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repeat',action='store_true',help='Re-estimate all 298 transitions in a separate artifact directory')
    args=parser.parse_args();initialize()
    manifest=json.loads((FIG/'figure_manifest.json').read_text())
    assert len(manifest)>=20
    for figure in manifest:
        path=STUDY/figure['file']
        with Image.open(path) as im:
            assert im.width>=1500 and im.height>=700
            assert np.asarray(im).std()>10
        for source in figure['sources']:
            assert (ROOT/source if source.startswith('data/') else STUDY/source).exists(),source
    checked=0;repeats={}
    for start,stop in CFG['segments']:
        name=f'{start:06d}_{stop:06d}'
        out=ART/f'odometry/{name}'
        poses=np.load(out/'poses.npz')
        with (out/'frames.csv').open() as f:rows=list(csv.DictReader(f))
        assert len(rows)==stop-start-1
        for method in ('stereo_fb','stereo_forward','mono_unit'):
            p=poses[method]
            assert p.shape==(stop-start,4,4) and np.isfinite(p).all()
            np.testing.assert_allclose(p[:,:3,:3].transpose(0,2,1)@p[:,:3,:3],np.broadcast_to(np.eye(3),(len(p),3,3)),atol=1e-8)
            np.testing.assert_allclose(np.linalg.det(p[:,:3,:3]),1.,atol=1e-8)
        for row in rows:
            frame=int(row['frame'])
            a=np.load(out/f'{frame:06d}.npz')
            assert len(a['fb_mask'])==len(a['X_previous'])==len(a['current_pixels'])
            assert np.all(a['fb_mask']<=a['forward_mask'])
            assert len(a['pnp_inlier_indices'])==int(row['pnp_inliers'])
            t=np.linalg.norm(a['mono_T'][:3,3])
            np.testing.assert_allclose(t,1 if row['mono_status']=='tracked_unit_step' else 0,atol=1e-8)
            checked+=1
        if args.repeat:
            destination=f'reproducibility/{name}'
            run_segment(start,stop,destination)
            repeated=np.load(ART/destination/'poses.npz')
            differences={method:float(np.max(np.abs(poses[method]-repeated[method]))) for method in ('stereo_fb','stereo_forward','mono_unit')}
            for diff in differences.values():assert diff==0.,differences
            compared_arrays=0
            for row in rows:
                frame=int(row['frame'])
                original=np.load(out/f'{frame:06d}.npz')
                repeat=np.load(ART/destination/f'{frame:06d}.npz')
                assert original.files==repeat.files
                for key in original.files:
                    np.testing.assert_array_equal(original[key],repeat[key],err_msg=f'{name}/{frame}/{key}')
                    compared_arrays+=1
            repeats[name]=dict(max_absolute_pose_difference=differences,stage_arrays_identical=compared_arrays)
    summary=json.loads((ART/'summary.json').read_text())
    assert all(summary['success_criteria'].values())
    result=dict(figures_verified=len(manifest),stage_frames_verified=checked,repeat_requested=args.repeat,
                repeat_results=repeats,success=True,
                reproducibility_scope='Same machine, dependencies, OpenCV single thread, exact arrays; runtime is not deterministic')
    save_json(directory('tests')/'artifact_verification.json',result)
    # Refresh source provenance after development, without changing scientific results.
    from run import provenance
    provenance()
    hashes={str(p.relative_to(STUDY)):sha(p) for folder in (ART,FIG) for p in sorted(folder.rglob('*'))
            if p.is_file() and p.name!='artifact_hashes.json'}
    save_json(directory('provenance')/'artifact_hashes.json',hashes)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
