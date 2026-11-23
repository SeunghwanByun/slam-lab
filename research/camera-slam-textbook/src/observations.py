"""Actual OpenCV observations with masks retaining original candidate indices."""
import cv2
import numpy as np
from common import CFG
from geometry import project


def stereo(left, right, K, baseline, p0, p1):
    orb = cv2.ORB_create(nfeatures=CFG['orb_features'])
    kl, dl = orb.detectAndCompute(left, None)
    kr, dr = orb.detectAndCompute(right, None)
    lp = np.float32([k.pt for k in kl]).reshape(-1, 2)
    rp = np.float32([k.pt for k in kr]).reshape(-1, 2)
    pairs = [] if dl is None or dr is None or len(dr) < 2 else cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(dl, dr, k=2)
    pairs = [pair for pair in pairs if len(pair) == 2]
    li = np.array([a.queryIdx for a, b in pairs], dtype=int)
    ri = np.array([a.trainIdx for a, b in pairs], dtype=int)
    d1 = np.array([a.distance for a, b in pairs])
    d2 = np.array([b.distance for a, b in pairs])
    a, b = lp[li], rp[ri]
    ratio = d1 / np.maximum(d2, 1)
    dy, disparity = a[:, 1] - b[:, 1], a[:, 0] - b[:, 0]
    ratio_mask = d1 < CFG['ratio'] * d2
    hamming_mask = ratio_mask & (d1 <= CFG['hamming'])
    y_mask = hamming_mask & (np.abs(dy) <= CFG['epipolar_px'])
    gate = y_mask & (disparity > CFG['disparity_min_px'])
    X = np.full((len(a), 3), np.nan)
    reproj = np.full(len(a), np.nan)
    if gate.any():
        homogeneous = cv2.triangulatePoints(p0, p1, a[gate].T.astype(float), b[gate].T.astype(float))
        X[gate] = (homogeneous[:3] / homogeneous[3]).T
        xr = X[gate] - np.array([baseline, 0, 0])
        reproj[gate] = np.maximum(np.linalg.norm(project(K, X[gate]) - a[gate], axis=1),
                                  np.linalg.norm(project(K, xr) - b[gate], axis=1))
    valid = gate & np.isfinite(X).all(axis=1) & (X[:, 2] > 0) & (X[:, 2] <= CFG['depth_max_m']) & (reproj <= CFG['reprojection_max_px'])
    cross = [] if dl is None or dr is None else cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(dl, dr)
    cross_a = np.float32([kl[m.queryIdx].pt for m in cross]).reshape(-1, 2)
    cross_b = np.float32([kr[m.trainIdx].pt for m in cross]).reshape(-1, 2)
    return dict(all_left=lp, all_right=rp, left=a, right=b, left_index=li, right_index=ri,
                d1=d1, d2=d2, ratio=ratio, dy=dy, disparity=disparity, ratio_mask=ratio_mask,
                hamming_mask=hamming_mask, y_mask=y_mask, gate=gate, valid=valid, X=X,
                reprojection_px=reproj, cross_left=cross_a, cross_right=cross_b)


def track(previous, current, points):
    a = np.asarray(points, np.float32).reshape(-1, 1, 2)
    if len(a) == 0:
        return dict(current=np.empty((0, 2)), backward=np.empty((0, 2)), fb=np.empty(0),
                    forward_valid=np.zeros(0, bool), valid=np.zeros(0, bool), lk_error=np.empty(0),
                    status_forward=np.zeros(0, bool), status_backward=np.zeros(0, bool))
    kwargs = dict(winSize=(CFG['lk_window'],) * 2, maxLevel=CFG['lk_levels'],
                  criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, .01))
    b, s1, err = cv2.calcOpticalFlowPyrLK(previous, current, a, None, **kwargs)
    back, s2, _ = cv2.calcOpticalFlowPyrLK(current, previous, b, None, **kwargs)
    b, back = b.reshape(-1, 2), back.reshape(-1, 2)
    fb = np.linalg.norm(back - a.reshape(-1, 2), axis=1)
    h, w = current.shape
    finite = np.isfinite(b).all(axis=1)
    inside = (b[:, 0] >= 0) & (b[:, 0] < w) & (b[:, 1] >= 0) & (b[:, 1] < h)
    forward = (s1.ravel() != 0) & inside & finite
    valid = forward & (s2.ravel() != 0) & np.isfinite(back).all(axis=1) & (fb <= CFG['fb_px'])
    # OpenCV leaves err undefined when status=0; never serialize uninitialized bytes.
    s1, s2 = s1.ravel()!=0, s2.ravel()!=0
    err=err.ravel().copy()
    err[~s1]=np.nan
    b[~s1]=np.nan
    back[~(s1&s2)]=np.nan
    fb[~(s1&s2)]=np.inf
    return dict(current=b, backward=back, fb=fb, forward_valid=forward, valid=valid, lk_error=err,
                status_forward=s1,status_backward=s2)


def dense(left, right, K, baseline):
    n, b = CFG['sgbm_disparities'], CFG['sgbm_block']
    def matcher(minimum):
        return cv2.StereoSGBM_create(minDisparity=minimum, numDisparities=n, blockSize=b,
            P1=8*b*b, P2=32*b*b, disp12MaxDiff=1, uniquenessRatio=CFG['sgbm_uniqueness'],
            speckleWindowSize=100, speckleRange=2, preFilterCap=31, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
    raw = matcher(0).compute(left, right)
    raw_right = matcher(-n).compute(right, left)
    disp, rd = raw.astype(float)/16, raw_right.astype(float)/16
    yy, xx = np.indices(disp.shape)
    xr = np.rint(xx-disp).astype(int)
    inside = (xr >= 0) & (xr < disp.shape[1])
    sampled = rd[yy, np.clip(xr, 0, disp.shape[1]-1)]
    lr = np.abs(disp + sampled)
    positive = disp > CFG['disparity_min_px']
    right_valid = sampled > -n
    consistent = positive & inside & right_valid & (lr <= CFG['sgbm_lr_px'])
    depth = np.full_like(disp, np.nan)
    depth[positive] = K[0, 0]*baseline/disp[positive]
    valid = consistent & (depth <= CFG['depth_max_m'])
    return dict(raw_disparity_fixed16=raw, raw_right_fixed16=raw_right, disparity=disp,
                depth_m=depth, positive=positive, lr_error=lr, consistent=consistent, valid=valid)
