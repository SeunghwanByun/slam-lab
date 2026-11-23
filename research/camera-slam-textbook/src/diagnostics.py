"""Quick-win observations and gate ablations, without depth/flow ground truth."""
import cv2
import numpy as np
from common import CFG, calibration, image, directory, save_json, save_csv
from observations import stereo, track, dense
from odometry import estimate_pnp


def run(frame):
    K, baseline, p0, p1 = calibration()
    left, right, current = image(frame), image(frame, 1), image(frame+1)
    s = stereo(left, right, K, baseline, p0, p1)
    out = directory('stereo')
    np.savez_compressed(out/f'{frame:06d}.npz', **s, K=K, baseline_m=baseline,
                        P0=p0, P1=p1, left_image=left, right_image=right)
    rows = []
    for method, mask in [('nearest', np.ones(len(s['left']), bool)), ('ratio', s['ratio_mask']),
                         ('ratio_hamming', s['hamming_mask']), ('ratio_hamming_y', s['y_mask']),
                         ('positive_disparity', s['gate']), ('triangulated_valid', s['valid'])]:
        dy = np.abs(s['dy'][mask])
        rows.append(dict(method=method, count=int(mask.sum()), median_abs_dy_px=float(np.median(dy)) if len(dy) else None,
                         fraction_abs_dy_le_1_5=float(np.mean(dy<=CFG['epipolar_px'])) if len(dy) else None))
    cross_dy = np.abs(s['cross_left'][:, 1]-s['cross_right'][:, 1])
    rows.append(dict(method='crosscheck', count=len(cross_dy), median_abs_dy_px=float(np.median(cross_dy)),
                     fraction_abs_dy_le_1_5=float(np.mean(cross_dy<=CFG['epipolar_px']))))
    save_csv(out/f'{frame:06d}_ablation.csv', rows)
    t = track(left, current, s['all_left'])
    np.savez_compressed(directory('tracking')/f'{frame:06d}.npz', previous=s['all_left'], **t,
                        previous_image=left, current_image=current)
    d = dense(left, right, K, baseline)
    np.savez_compressed(directory('dense')/f'{frame:06d}.npz', **d)
    valid = s['valid']
    ids = s['left_index'][valid]
    X, b = s['X'][valid], t['current'][ids]
    good = t['valid'][ids]
    p = estimate_pnp(X[good], b[good], K, CFG['seed']+frame+1)
    np.savez_compressed(directory('reprojection')/f'{frame:06d}.npz', X_previous=X[good], current_pixels=b[good], **p)
    summary = dict(kind='actual KITTI; geometric consistency, not GT correspondence accuracy', frame=frame,
        shape=list(left.shape), baseline_m=float(baseline), stereo_ablation=rows,
        stereo_depth_median_m=float(np.median(s['X'][valid,2])),
        stereo_reprojection_median_px=float(np.median(s['reprojection_px'][valid])),
        lk_forward=int(t['forward_valid'].sum()), lk_fb=int(t['valid'].sum()),
        lk_fb_rejected=int((t['forward_valid'] & ~t['valid']).sum()),
        dense_positive_fraction=float(d['positive'].mean()), dense_lr_fraction=float(d['consistent'].mean()),
        dense_valid_fraction=float(d['valid'].mean()), dense_valid_count=int(d['valid'].sum()),
        dense_depth_median_m=float(np.median(d['depth_m'][d['valid']])),
        pose_only_initial_rmse_px=float(np.sqrt(np.mean(p['before']**2))) if len(p['before']) else None,
        pose_only_refined_rmse_px=float(np.sqrt(np.mean(p['after']**2))) if len(p['after']) else None)
    save_json(out/f'{frame:06d}_summary.json', summary)
    for module, values in [('tracking', {k:v for k,v in summary.items() if k.startswith('lk_')}),
                           ('dense', {k:v for k,v in summary.items() if k.startswith('dense_')}),
                           ('reprojection', {k:v for k,v in summary.items() if k.startswith('pose_')})]:
        save_json(directory(module)/f'{frame:06d}_summary.json', dict(kind='actual KITTI', frame=frame, **values))
        save_csv(directory(module)/f'{frame:06d}_summary.csv', [dict(frame=frame, **values)])
    return summary
