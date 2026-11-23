"""Explicitly synthetic teaching models; never calibration of KITTI raw cameras."""
import cv2
import numpy as np
from common import CFG, calibration, directory, save_json, save_csv
from geometry import project, pose, transform
from odometry import estimate_essential, estimate_pnp


def rotation_summary(rows):
    successful=[r['E_rotation_error_deg'] for r in rows if r['E_accepted']]
    return dict(trials=len(rows),essential_accepted=len(successful),essential_failed_hold=len(rows)-len(successful),
        system_output_rotation_median_including_hold_deg=float(np.median([r['E_rotation_error_deg'] for r in rows])),
        successful_estimate_rotation_median_deg=float(np.median(successful)) if successful else None)


def run():
    rng = np.random.default_rng(CFG['seed'])
    K, baseline, _, _ = calibration()
    out = directory('synthetic')
    z = np.linspace(3, 100, 150)
    disparity = K[0, 0]*baseline/z
    sigma_d = .5
    first_order = z*z/(K[0, 0]*baseline)*sigma_d
    samples = disparity[:, None]+rng.normal(0, sigma_d, (len(z),10000))
    depth = K[0,0]*baseline/samples
    empirical = np.std(depth,axis=1)
    np.savez_compressed(out/'uncertainty.npz', z_m=z, disparity_px=disparity,
                        sigma_z_m=first_order, empirical_std_m=empirical, sigma_d_px=sigma_d,
                        quantile_depth_m=np.quantile(depth,[.05,.5,.95],axis=1))
    # Radial/tangential example coefficients are invented, not KITTI calibration.
    xx, yy = np.meshgrid(np.linspace(30,1210,25), np.linspace(20,350,12))
    ideal = np.c_[xx.ravel(), yy.ravel()]
    rays = np.c_[ideal, np.ones(len(ideal))] @ np.linalg.inv(K).T
    coeff = np.array([-.22,.06,.001,-.0005,0.])
    distorted = cv2.projectPoints(rays,np.zeros(3),np.zeros(3),K,coeff)[0].reshape(-1,2)
    criteria=(cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS,50,1e-12)
    if hasattr(cv2,'undistortPointsIter'):
        restored=cv2.undistortPointsIter(distorted.reshape(-1,1,2),K,coeff,None,K,criteria).reshape(-1,2)
    else:
        restored=cv2.undistortPoints(distorted.reshape(-1,1,2),K,coeff,P=K,criteria=criteria).reshape(-1,2)
    np.savez_compressed(out/'distortion.npz', ideal=ideal, distorted=distorted, restored=restored, coefficients=coeff, K=K)
    rows, arrays = [], {}
    for case in ('normal','pure_rotation','far_depth','planar','tiny_translation'):
        rotation = cv2.Rodrigues(np.array([.005,.025,-.003]))[0]
        translation = np.array([.25,.01,.5])
        X = np.c_[rng.uniform(-4,4,300),rng.uniform(-1.5,1.5,300),rng.uniform(8,30,300)]
        if case=='pure_rotation': translation[:] = 0
        if case=='tiny_translation': translation *= .001
        if case=='far_depth': X *= 100
        if case=='planar': X[:,2]=15
        target = pose(rotation,translation)
        a0, b0 = project(K,X), project(K,transform(target,X))
        case_rows=[]
        for trial in range(20):
            a, b = a0+rng.normal(0,.5,a0.shape), b0+rng.normal(0,.5,b0.shape)
            e = estimate_essential(a,b,K,CFG['seed']+trial)
            p = estimate_pnp(X,b,K,CFG['seed']+trial)
            err = np.degrees(np.arccos(np.clip((np.trace(e['T'][:3,:3].T@rotation)-1)/2,-1,1)))
            direction = None
            if np.linalg.norm(translation)>0 and e['accepted']:
                direction = float(np.degrees(np.arccos(np.clip(e['T'][:3,3]@translation/np.linalg.norm(translation),-1,1))))
            case_rows.append(dict(case=case,trial=trial,E_accepted=e['accepted'],E_inliers=int(e['mask'].sum()),
                E_rotation_error_deg=float(err), E_direction_error_deg=direction,
                PnP_accepted=p['accepted'], PnP_translation_error_m=float(np.linalg.norm(p['T'][:3,3]-translation)),
                note='PnP receives exact synthetic 3D; not stereo-derived'))
        rows.extend(case_rows)
        arrays.update({case+'_X':X,case+'_a':a0,case+'_b':b0,case+'_T':target})
    np.savez_compressed(out/'degeneracy.npz',**arrays)
    save_csv(out/'degeneracy.csv',rows)
    summary = dict(kind='SYNTHETIC; invented lens coefficients and Gaussian noise',
        distortion_max_px=float(np.max(np.linalg.norm(distorted-ideal,axis=1))),
        undistortion_max_error_px=float(np.max(np.linalg.norm(restored-ideal,axis=1))),
        sigma_disparity_px=sigma_d, uncertainty_at_100m_firstorder_m=float(first_order[-1]),
        uncertainty_at_100m_empirical_std_m=float(empirical[-1]),
        degeneracy={case:rotation_summary([r for r in rows if r['case']==case])
                    for case in ('normal','pure_rotation','far_depth','planar','tiny_translation')})
    save_json(out/'summary.json',summary)
    save_csv(out/'uncertainty.csv',[dict(depth_m=a,disparity_px=b,sigma_z_firstorder_m=c,sigma_z_empirical_m=d)
                                   for a,b,c,d in zip(z,disparity,first_order,empirical)])
    save_csv(out/'distortion.csv',[dict(u=a[0],v=a[1],distorted_u=b[0],distorted_v=b[1],restored_error_px=float(np.linalg.norm(c-a)))
                                  for a,b,c in zip(ideal,distorted,restored)])
    return summary
