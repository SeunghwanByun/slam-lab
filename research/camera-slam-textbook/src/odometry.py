"""Estimation ONLY: no pose files, GT, evaluation, or external scale input."""
import time
import cv2
import numpy as np
from common import CFG, calibration, image, directory, save_csv, save_json
from geometry import pose, accumulate, project, transform
from observations import stereo, track


def estimate_pnp(X, pixels, K, seed):
    cv2.setRNGSeed(seed)
    result = dict(T=np.eye(4), accepted=False, inliers=np.empty(0, int),
                  before=np.empty(0), after=np.empty(0), status='insufficient_correspondences')
    if len(X) < CFG['min_pose_inliers']:
        return result
    try:
        ok, r, t, inliers = cv2.solvePnPRansac(np.ascontiguousarray(X, np.float64),
            np.ascontiguousarray(pixels, np.float64), K, None, iterationsCount=CFG['pnp_iterations'],
            reprojectionError=CFG['pnp_px'], confidence=.999, flags=cv2.SOLVEPNP_EPNP)
        ids = np.empty(0, int) if inliers is None else inliers.ravel()
        result.update(inliers=ids, status='insufficient_inliers')
        if not ok or len(ids) < CFG['min_pose_inliers']:
            return result
        initial = pose(cv2.Rodrigues(r)[0], t)
        before = np.linalg.norm(project(K, transform(initial, X[ids]))-pixels[ids], axis=1)
        r, t = cv2.solvePnPRefineLM(X[ids].astype(float), pixels[ids].astype(float), K, None, r, t)
        T = pose(cv2.Rodrigues(r)[0], t)
        after = np.linalg.norm(project(K, transform(T, X[ids]))-pixels[ids], axis=1)
        if not np.isfinite(T).all() or np.any(transform(T, X[ids])[:, 2] <= 0):
            result['status'] = 'nonfinite_or_cheirality'
            return result
        result.update(T=T, accepted=True, before=before, after=after, status='tracked')
    except cv2.error:
        result['status'] = 'opencv_error'
    return result


def estimate_essential(a, b, K, seed):
    cv2.setRNGSeed(seed)
    result = dict(T=np.eye(4), accepted=False, mask=np.zeros(len(a), bool),
                  ransac_mask=np.zeros(len(a), bool), E=np.empty((0, 3)), candidate_count=0,
                  selected_candidate=0, status='insufficient_correspondences')
    if len(a) < CFG['min_pose_inliers']:
        return result
    try:
        E, mask = cv2.findEssentialMat(a, b, K, method=cv2.RANSAC, prob=.999, threshold=CFG['essential_px'])
        if E is None:
            result['status'] = 'no_essential'
            return result
        ransac = mask.ravel() != 0
        # Explicit baseline policy: first 3x3 candidate, not best-candidate selection.
        result['candidate_count'] = int(E.shape[0]//3)
        n, R, t, mask = cv2.recoverPose(E[:3], a, b, K, mask=mask)
        result.update(E=E[:3], mask=mask.ravel()!=0, ransac_mask=ransac, status='insufficient_cheirality')
        if n >= CFG['min_pose_inliers']:
            result.update(T=pose(R, t.ravel()/np.linalg.norm(t)), accepted=True, status='tracked_unit_step')
    except cv2.error:
        result['status'] = 'opencv_error'
    return result


def run_segment(start, stop, output_name=None):
    K, baseline, p0, p1 = calibration()
    out = directory(output_name or f'odometry/{start:06d}_{stop:06d}')
    sequences = {name: [np.eye(4)] for name in ('stereo_fb', 'stereo_forward', 'mono_unit')}
    rows = []
    previous = image(start)
    for frame in range(start+1, stop):
        began = time.perf_counter()
        current = image(frame)
        s = stereo(previous, image(frame-1, 1), K, baseline, p0, p1)
        temporal = track(previous, current, s['all_left'])
        selected = s['valid']
        ids = s['left_index'][selected]
        X = s['X'][selected]
        b = temporal['current'][ids]
        fb = temporal['valid'][ids]
        forward = temporal['forward_valid'][ids]
        seed = CFG['seed']+frame
        p = estimate_pnp(X[fb], b[fb], K, seed)
        ablation = estimate_pnp(X[forward], b[forward], K, seed)
        mask = temporal['valid']
        e = estimate_essential(s['all_left'][mask], temporal['current'][mask], K, seed)
        for name, result in [('stereo_fb', p), ('stereo_forward', ablation), ('mono_unit', e)]:
            sequences[name].append(accumulate(sequences[name][-1], result['T']))
        row = dict(frame=frame, orb=len(s['all_left']), stereo_candidates=len(s['left']),
            stereo_ratio=int(s['ratio_mask'].sum()), stereo_y=int(s['y_mask'].sum()), stereo_valid=int(selected.sum()),
            lk_forward=int(temporal['forward_valid'].sum()), lk_fb=int(mask.sum()),
            pnp_input=int(fb.sum()), pnp_inliers=len(p['inliers']), pnp_status=p['status'],
            pnp_forward_input=int(forward.sum()), pnp_forward_inliers=len(ablation['inliers']), pnp_forward_status=ablation['status'],
            essential_ransac=int(e['ransac_mask'].sum()), essential_inliers=int(e['mask'].sum()),
            essential_candidates=e['candidate_count'], mono_status=e['status'],
            stereo_step_m=float(np.linalg.norm(p['T'][:3, 3])),
            median_fb_px=float(np.median(temporal['fb'][temporal['forward_valid'] & np.isfinite(temporal['fb'])]))
                if (temporal['forward_valid'] & np.isfinite(temporal['fb'])).any() else None,
            reproj_before_rmse_px=float(np.sqrt(np.mean(p['before']**2))) if len(p['before']) else None,
            reproj_after_rmse_px=float(np.sqrt(np.mean(p['after']**2))) if len(p['after']) else None,
            seconds=time.perf_counter()-began)
        rows.append(row)
        np.savez_compressed(out/f'{frame:06d}.npz', **{f'stereo_{k}':v for k,v in s.items()},
            **{f'lk_{k}':v for k,v in temporal.items()}, X_previous=X, current_pixels=b,
            fb_mask=fb, forward_mask=forward, pnp_inlier_indices=p['inliers'],
            pnp_T=p['T'], forward_T=ablation['T'], mono_T=e['T'], E=e['E'],
            essential_mask=e['mask'], essential_ransac_mask=e['ransac_mask'],
            essential_candidates=e['candidate_count'], selected_essential_candidate=e['selected_candidate'],
            reproj_before=p['before'], reproj_after=p['after'])
        # A held pose still advances the image: the failed interval is permanently lost.
        previous = current
        if (frame-start) % 25 == 0:
            print(f'{start}:{stop} frame {frame} stereo={len(p["inliers"])} mono={e["mask"].sum()}', flush=True)
    np.savez_compressed(out/'poses.npz', frames=np.arange(start, stop), **{k:np.array(v) for k,v in sequences.items()})
    save_csv(out/'frames.csv', rows)
    summary = dict(start=start, stop_exclusive=stop, frames=stop-start, transitions=len(rows),
        stereo_held=sum(r['pnp_status']!='tracked' for r in rows),
        forward_held=sum(r['pnp_forward_status']!='tracked' for r in rows),
        mono_held=sum(r['mono_status']!='tracked_unit_step' for r in rows),
        median_seconds=float(np.median([r['seconds'] for r in rows])),
        p95_seconds=float(np.percentile([r['seconds'] for r in rows],95)))
    save_json(out/'summary.json', summary)
    return summary
