"""Only this module reads GT. Its outputs are never imported by estimation."""
import csv
import numpy as np
from common import DATA, CFG, directory, save_json, save_csv
from geometry import inverse, align_poses


def metrics(estimated, truth):
    error = np.linalg.norm(estimated[:, :3, 3]-truth[:, :3, 3], axis=1)
    estimated_relative = np.linalg.inv(estimated[:-1]) @ estimated[1:]
    truth_relative = np.linalg.inv(truth[:-1]) @ truth[1:]
    residual = np.linalg.inv(truth_relative) @ estimated_relative
    translation = np.linalg.norm(residual[:, :3, 3], axis=1)
    rotation = np.degrees(np.arccos(np.clip((np.trace(residual[:, :3, :3], axis1=1, axis2=2)-1)/2, -1, 1)))
    result = dict(ate_rmse_m=float(np.sqrt(np.mean(error**2))), endpoint_m=float(error[-1]),
                  rpe_1frame_translation_rmse_m=float(np.sqrt(np.mean(translation**2))),
                  rpe_1frame_rotation_rmse_deg=float(np.sqrt(np.mean(rotation**2))))
    assert all(np.isfinite(list(result.values())))
    return result, error, translation, rotation


def evaluate(start, stop):
    name = f'{start:06d}_{stop:06d}'
    out = directory(f'evaluation/{name}')
    gt = np.repeat(np.eye(4)[None], stop-start, axis=0)
    gt[:, :3] = np.loadtxt(DATA/'poses'/f'{CFG["sequence"]}.txt')[start:stop].reshape(-1, 3, 4)
    gt = inverse(gt[0]) @ gt
    poses = np.load(directory(f'odometry/{name}')/'poses.npz')
    results, arrays, rows = {}, dict(gt=gt, frames=poses['frames']), []
    for method in ('stereo_fb', 'stereo_forward', 'mono_unit'):
        estimated = poses[method]
        scale = 1.
        if method == 'mono_unit':
            estimated, scale, R, t = align_poses(estimated, gt[:, :3, 3])
            arrays.update(mono_alignment_R=R, mono_alignment_t=t)
        stat, error, translation, rotation = metrics(estimated, gt)
        stat.update(alignment='GT Sim3 position fit; evaluation only' if method=='mono_unit' else 'first pose only; no fitting',
                    evaluation_scale=scale, estimated_units='unit-step arbitrary' if method=='mono_unit' else 'm')
        results[method] = stat
        arrays.update({method:estimated, method+'_error_m':error, method+'_rpe_m':translation, method+'_rpe_deg':rotation})
        for i, frame in enumerate(poses['frames']):
            rows.append(dict(method=method, frame=int(frame), position_error_m=error[i],
                             rpe_translation_m=None if i==0 else translation[i-1], rpe_rotation_deg=None if i==0 else rotation[i-1]))
    results['gt_path_length_m'] = float(np.linalg.norm(np.diff(gt[:, :3, 3],axis=0),axis=1).sum())
    np.savez_compressed(out/'stages.npz', **arrays)
    save_json(out/'metrics.json', results)
    save_csv(out/'errors.csv', rows)
    return results
