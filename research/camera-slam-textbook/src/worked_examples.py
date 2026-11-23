"""Numerically checked worked examples for the writer, not a new report."""
import numpy as np
from common import ART, directory, save_json, save_csv
from geometry import inverse, transform, project


def run():
    s=np.load(ART/'stereo/000000.npz')
    stage=np.load(ART/'odometry/000000_000200/000001.npz')
    valid=np.flatnonzero(s['valid'])
    i=int(valid[np.argmin(np.abs(s['disparity'][valid]-20))])
    K=s['K']; baseline=float(s['baseline_m']); X=s['X'][i]
    ideal_depth=float(K[0,0]*baseline/s['disparity'][i])
    current_from_previous=stage['pnp_T']
    start_from_current=inverse(current_from_previous)
    reconstructed=project(K,X[None])[0]
    left_residual=np.linalg.norm(reconstructed-s['left'][i])
    np.testing.assert_allclose(s['ratio'][i],s['d1'][i]/s['d2'][i])
    np.testing.assert_allclose(ideal_depth,19.30724,atol=1e-8)
    np.testing.assert_allclose(current_from_previous@start_from_current,np.eye(4),atol=1e-12)
    results=dict(kind='Actual saved KITTI observations; ideal rectified depth is an explicitly stated model',
        frame=0,candidate_index=i,left_pixel=s['left'][i],right_pixel=s['right'][i],
        nearest_hamming_bits=float(s['d1'][i]),second_hamming_bits=float(s['d2'][i]),
        ratio=float(s['ratio'][i]),dy_px=float(s['dy'][i]),disparity_px=float(s['disparity'][i]),
        baseline_m=baseline,ideal_same_row_depth_m=ideal_depth,actual_dlt_X_m=X,
        left_reprojection_pixel=reconstructed,left_reprojection_error_px=float(left_residual),
        actual_max_stereo_reprojection_px=float(s['reprojection_px'][i]),
        T_current_previous=current_from_previous,T_start_current=start_from_current,
        sigma_depth_20px_if_sigma_disparity_0_5px_m=float(K[0,0]*baseline/(20**2)*.5),
        units_note='Disparity and residual px, descriptor bits, depth and metric translation m; synthetic sigma assumed')
    out=directory('worked_examples')
    save_json(out/'summary.json',results)
    np.savez_compressed(out/'stages.npz',K=K,X=X,left=s['left'][i],right=s['right'][i],
                        T_current_previous=current_from_previous,T_start_current=start_from_current)
    save_csv(out/'scalars.csv',[dict(quantity=k,value=v) for k,v in results.items() if isinstance(v,(float,int))])
    return results
