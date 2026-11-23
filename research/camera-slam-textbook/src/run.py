"""Bounded full reproduction. Run from any directory with the pinned interpreter."""
import argparse
import csv
import importlib.metadata
import io
import json
import platform
import subprocess
import sys
import time
import unittest
import cv2
import numpy as np
import scipy
import matplotlib
from common import ROOT, STUDY, DATA, SEQ, ART, FIG, CFG, initialize, directory, save_json, save_csv, sha


def provenance():
    inputs={}
    frames=set(CFG['diagnostic_frames']) | {f+1 for f in CFG['diagnostic_frames']}
    for start,stop in CFG['segments']:frames.update(range(start,stop))
    for frame in sorted(frames):
        for side in (0,1):
            path=SEQ/f'image_{side}'/f'{frame:06d}.png'
            inputs[str(path.relative_to(ROOT))]=sha(path)
    for path in (SEQ/'calib.txt',DATA/'poses'/f'{CFG["sequence"]}.txt'):
        inputs[str(path.relative_to(ROOT))]=sha(path)
    source={str(p.relative_to(ROOT)):sha(p) for folder in ('src','configs')
            for p in sorted((STUDY/folder).glob('*')) if p.is_file()}
    versions={d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
    result=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
        cv2=cv2.__version__,numpy=np.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__,
        dependencies=versions,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        experiment_base='f09b08eba08ae400b8c647c88a99a8b3ec874eb4',seed=CFG['seed'],opencv_threads=cv2.getNumThreads(),
        input_sha256=inputs,source_sha256=source,
        gt_access='GT poses file hash and evaluation only; never supplied to odometry')
    save_json(directory('provenance')/'manifest.json',result)
    (directory('provenance')/'opencv_build.txt').write_text(cv2.getBuildInformation())
    return result


def tests():
    suite=unittest.defaultTestLoader.discover(str(STUDY/'src'),pattern='test_invariants.py')
    buffer=io.StringIO()
    result=unittest.TextTestRunner(stream=buffer,verbosity=2).run(suite)
    (directory('tests')/'unittest.txt').write_text(buffer.getvalue())
    stat=dict(run=result.testsRun,failures=len(result.failures),errors=len(result.errors),successful=result.wasSuccessful())
    save_json(directory('tests')/'summary.json',stat)
    if not result.wasSuccessful():raise RuntimeError(buffer.getvalue())
    return stat


def failure_summary(start,stop):
    name=f'{start:06d}_{stop:06d}'
    with (ART/f'odometry/{name}/frames.csv').open() as f:rows=list(csv.DictReader(f))
    a=np.load(ART/f'evaluation/{name}/stages.npz')
    errors=a['stereo_fb_rpe_m']
    ids=np.argsort(errors)[-5:][::-1]
    worst=[dict(frame=int(rows[i]['frame']),rpe_m=float(errors[i]),pnp_inliers=int(rows[i]['pnp_inliers']),
                pnp_input=int(rows[i]['pnp_input']),median_fb_px=float(rows[i]['median_fb_px'])) for i in ids]
    correlations={}
    for key in ('pnp_inliers','pnp_input','median_fb_px','reproj_after_rmse_px','stereo_step_m'):
        v=np.array([float(r[key]) for r in rows])
        correlations[key]=float(np.corrcoef(v,errors)[0,1]) if np.std(v)>0 else None
    result=dict(worst_stereo_frames=worst,pearson_with_stereo_1frame_rpe=correlations,
        multie_frames=sum(int(r['essential_candidates'])>1 for r in rows),
        pnp_inliers_min=min(int(r['pnp_inliers']) for r in rows),
        mono_cheirality_min=min(int(r['essential_inliers']) for r in rows),
        median_pnp_input=float(np.median([int(r['pnp_input']) for r in rows])),
        interpretation='Post-hoc diagnostic correlations, not causal explanations; no dynamic-object GT')
    save_json(directory(f'evaluation/{name}')/'failures.json',result)
    save_csv(directory(f'evaluation/{name}')/'worst_frames.csv',worst)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reuse-estimates',action='store_true',help='Replot/evaluate existing estimates; do not claim a fresh estimation run')
    args=parser.parse_args()
    initialize();start_time=time.perf_counter()
    provenance()
    from diagnostics import run as diagnostic
    from odometry import run_segment
    from evaluation import evaluate
    from synthetic import run as synthetic
    from worked_examples import run as worked_examples
    import figures
    summary=dict(kind='isolated teaching experiments, NOT production SLAM',config=CFG,
        run_mode='reuse estimates' if args.reuse_estimates else 'full fresh estimation',tests=tests(),
        diagnostic={},segments={})
    for frame in CFG['diagnostic_frames']:
        summary['diagnostic'][str(frame)]=diagnostic(frame)
    for start,stop in CFG['segments']:
        name=f'{start:06d}_{stop:06d}'
        if not args.reuse_estimates:run_segment(start,stop)
        summary['segments'][name]=dict(estimation=json.loads((ART/f'odometry/{name}/summary.json').read_text()),
            evaluation=evaluate(start,stop),failures=failure_summary(start,stop))
    summary['worked_examples']=worked_examples()
    summary['synthetic']=synthetic()
    summary['figures']=figures.main()
    summary['actual_figures']=sum(m['kind']=='actual KITTI' for m in figures.MANIFEST)
    summary['elapsed_seconds']=time.perf_counter()-start_time
    summary['success_criteria']=dict(figures_at_least_20=summary['figures']>=20,
        actual_figures_at_least_20=summary['actual_figures']>=20,tests_at_least_8=summary['tests']['run']>=8,
        two_disjoint_segments=CFG['segments'][0][1]<=CFG['segments'][1][0],
        finite_stereo_metrics=all(np.isfinite(s['evaluation']['stereo_fb']['ate_rmse_m']) for s in summary['segments'].values()))
    summary['limitations']=[
        'GT depth/flow absent: consistency is not accuracy',
        'Identity hold advances previous image; failed motion is permanently lost',
        'Monocular unit steps cannot represent variable speed; Sim3 is evaluation-only',
        'Metric stereo and GT-Sim3 mono are not a fair accuracy ranking',
        'First essential candidate E[:3] used; not candidate selection',
        'Same-sequence holdout, not cross-sequence generalization',
        'Finite metrics and no holds do not establish robustness',
        'Pose-only LM fixed 3D, not joint BA; no loop closure',
        'Crosscheck/ratio comparison is one-pair consistency ablation, not full VO comparison',
        'Synthetic PnP receives exact 3D, not noisy stereo reconstruction']
    save_json(ART/'summary.json',summary)
    metric_rows=[]
    for segment,s in summary['segments'].items():
        for method in ('stereo_fb','stereo_forward','mono_unit'):
            metric_rows.append(dict(segment=segment,method=method,**s['evaluation'][method]))
    save_csv(ART/'metrics.csv',metric_rows)
    artifact_hashes={str(p.relative_to(STUDY)):sha(p) for folder in (ART,FIG) for p in sorted(folder.rglob('*'))
                     if p.is_file() and p.name!='artifact_hashes.json'}
    save_json(directory('provenance')/'artifact_hashes.json',artifact_hashes)
    print(json.dumps(dict(success=summary['success_criteria'],seconds=summary['elapsed_seconds'],metrics=metric_rows),indent=2))


if __name__=='__main__':main()
