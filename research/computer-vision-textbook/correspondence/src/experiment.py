"""Reproducible teaching experiments, not production CV or neural reproductions."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import sys
import time

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
CFG = json.loads((BASE / "configs/experiment.json").read_text())
plt.rcParams.update({"font.size": 9, "axes.titlesize": 10,
                     "axes.labelsize": 9, "legend.fontsize": 8})


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def artifact(module, **arrays):
    path = BASE / "artifacts" / module
    path.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path / "arrays.npz", **arrays)


def finish(fig, name):
    fig.tight_layout()
    path = BASE / "figures" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=CFG["dpi"], facecolor="white")
    plt.close(fig)


def project(H, xy):
    q = np.c_[xy, np.ones(len(xy))] @ np.asarray(H).T
    if np.any(np.abs(q[:, 2]) < 1e-12):
        raise ValueError("point mapped to infinity")
    return q[:, :2] / q[:, 2:3]


def normalize_points(xy):
    xy = np.asarray(xy, dtype=float)
    center = xy.mean(axis=0)
    mean_distance = np.linalg.norm(xy - center, axis=1).mean()
    if mean_distance < 1e-12:
        raise ValueError("coincident points")
    s = np.sqrt(2) / mean_distance
    T = np.array([[s, 0, -s*center[0]], [0, s, -s*center[1]], [0, 0, 1.]])
    return project(T, xy), T


def dlt(src, dst, normalize=True):
    """Small educational DLT; actual robust fit uses cv2.findHomography."""
    src, dst = np.asarray(src, float), np.asarray(dst, float)
    if len(src) < 4 or src.shape != dst.shape:
        raise ValueError("need >=4 corresponding points")
    if np.linalg.matrix_rank(src - src.mean(0)) < 2:
        raise ValueError("collinear source")
    if np.linalg.matrix_rank(dst - dst.mean(0)) < 2:
        raise ValueError("collinear destination")
    if normalize:
        a, T1 = normalize_points(src)
        b, T2 = normalize_points(dst)
    else:
        a, b, T1, T2 = src, dst, np.eye(3), np.eye(3)
    rows = []
    for (x, y), (u, v) in zip(a, b):
        rows += [[-x, -y, -1, 0, 0, 0, u*x, u*y, u],
                 [0, 0, 0, -x, -y, -1, v*x, v*y, v]]
    A = np.array(rows)
    _, singular, vt = np.linalg.svd(A, full_matrices=True)
    if np.linalg.matrix_rank(A) < 8:
        raise ValueError("rank deficient DLT")
    H = np.linalg.inv(T2) @ vt[-1].reshape(3, 3) @ T1
    H /= H[2, 2]
    return H, singular, A


def rootsift(desc):
    desc = np.asarray(desc, np.float32)
    return np.sqrt(desc / np.maximum(desc.sum(axis=1, keepdims=True), 1e-12))


def sinkhorn(kernel, rows, cols, steps=100):
    """Positive-kernel toy; not SuperGlue logits or trained output."""
    p = np.asarray(kernel, float).copy()
    rows, cols = np.asarray(rows), np.asarray(cols)
    history = []
    for _ in range(steps):
        p *= (rows / p.sum(1))[:, None]
        p *= (cols / p.sum(0))[None, :]
        history.append(max(np.abs(p.sum(1)-rows).max(),
                           np.abs(p.sum(0)-cols).max()))
    return p, np.array(history)


def ransac_trials(w, sample=4, confidence=.99):
    if not 0 < w <= 1:
        raise ValueError("inlier fraction must be positive")
    if w == 1:
        return 1
    return int(np.ceil(np.log1p(-confidence)/np.log1p(-w**sample)))


def huber_weights(r, delta=1.0):
    return np.minimum(1., delta / np.maximum(np.abs(r), 1e-12))


def softmax(x, axis=-1):
    e = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e/e.sum(axis=axis, keepdims=True)


def keypoints(img, method):
    if method == "ORB":
        detector = cv2.ORB_create(nfeatures=CFG["features"])
    else:
        detector = cv2.SIFT_create(nfeatures=CFG["features"])
    kp, desc = detector.detectAndCompute(img, None)
    if method == "RootSIFT":
        desc = rootsift(desc)
    return kp, desc


def xy(kp):
    return np.array([p.pt for p in kp], np.float64)


def matching(k1, d1, k2, d2, H, method):
    norm = cv2.NORM_HAMMING if method == "ORB" else cv2.NORM_L2
    bf = cv2.BFMatcher(norm)
    pairs = bf.knnMatch(d1, d2, k=2)
    reverse = bf.match(d2, d1)
    rev = {m.queryIdx: m.trainIdx for m in reverse}
    pairs = [p for p in pairs if len(p) == 2]
    a = np.array([p[0].queryIdx for p in pairs])
    b = np.array([p[0].trainIdx for p in pairs])
    dist = np.array([[p[0].distance, p[1].distance] for p in pairs])
    ratio = np.divide(dist[:, 0], dist[:, 1], out=np.ones(len(dist)), where=dist[:, 1] > 0)
    err = np.linalg.norm(project(H, xy(k1)[a]) - xy(k2)[b], axis=1)
    mutual = np.array([rev[j] == i for i, j in zip(a, b)])
    return dict(a=a, b=b, dist=dist, ratio=ratio, err=err, mutual=mutual)


def feature_experiment(img):
    h, w = img.shape
    results, arrays, first = [], {}, {}
    sift_cache = {}
    for method in ["SIFT", "RootSIFT", "ORB"]:
        t = time.perf_counter()
        if method == "RootSIFT":
            k1, raw1 = sift_cache["source"]
            d1 = rootsift(raw1)
        else:
            k1, d1 = keypoints(img, method)
            if method == "SIFT":
                sift_cache["source"] = (k1,d1)
        extraction_ms = (time.perf_counter()-t)*1000
        for case in CFG["warp_cases"]:
            H = np.vstack([cv2.getRotationMatrix2D((w/2, h/2), case["angle"], case["scale"]), [0, 0, 1]])
            target = cv2.warpPerspective(img, H, (w, h))
            if case["blur"]:
                target = cv2.GaussianBlur(target, (0, 0), case["blur"])
            if method == "RootSIFT":
                k2, raw2 = sift_cache[case["name"]]
                d2 = rootsift(raw2)
            else:
                k2, d2 = keypoints(target, method)
                if method == "SIFT":
                    sift_cache[case["name"]] = (k2,d2)
            m = matching(k1, d1, k2, d2, H, method)
            q = project(H, xy(k1))
            visible = (q[:, 0] >= 16) & (q[:, 0] < w-16) & (q[:, 1] >= 16) & (q[:, 1] < h-16)
            near, _ = cKDTree(xy(k2)).query(q[visible])
            keep = (m["ratio"] < .75) & visible[m["a"]]
            good = m["err"] < CFG["geometry_threshold_px"]
            result = dict(method=method, case=case["name"], n1=len(k1), n2=len(k2),
                          visible=int(visible.sum()), repeatability=float((near<3).mean()),
                          selected=int(keep.sum()), correct=int((keep & good).sum()),
                          precision=float(good[keep].mean()) if keep.any() else None,
                          median_error_px=float(np.median(m["err"][keep])) if keep.any() else None,
                          diagnostic_ms=extraction_ms,
                          timing_scope="RootSIFT normalization only" if method=="RootSIFT" else "single detector call",
                          timing_is_benchmark=False)
            results.append(result)
            prefix = method + "_" + case["name"]
            arrays.update({prefix+"_"+key: val for key, val in m.items()})
            arrays[prefix+"_visible"] = visible
            arrays[prefix+"_kp0"] = xy(k1)
            arrays[prefix+"_kp1"] = xy(k2)
            if case["name"] == "rotate25":
                first[method] = (k1, d1, k2, d2, H, target, m, visible)
    artifact("features", **arrays)
    save_json(BASE/"artifacts/features/metrics.json", results)

    harris = cv2.goodFeaturesToTrack(img, 500, .01, 7, useHarrisDetector=True)
    shi = cv2.goodFeaturesToTrack(img, 500, .01, 7)
    fast = cv2.FastFeatureDetector_create(20, True).detect(img)
    fig, axes = plt.subplots(4, 1, figsize=(7, 8.2))
    for ax, points, name in zip(axes, [harris[:, 0], shi[:, 0], xy(fast), xy(first["SIFT"][0])],
                                ["Harris (cap 500)", "Shi-Tomasi (cap 500)", "FAST-9", "SIFT (cap 1200)"]):
        ax.imshow(img, cmap="gray", vmin=0, vmax=255)
        ax.scatter(points[:, 0], points[:, 1], s=3, c="#21bfa5", alpha=.6)
        ax.set_title(f"{name}: {len(points)} points; KITTI 00/000000")
        ax.set(xlabel="x [px]", ylabel="y [px]")
    finish(fig, "d9_01_detectors.png")

    sigmas = np.array([1.6*2**(i/3) for i in range(6)])
    smooth = [cv2.GaussianBlur(img.astype(float)/255, (0, 0), s) for s in sigmas]
    dogs = np.diff(np.array(smooth), axis=0)
    fig, axes = plt.subplots(2, 3, figsize=(7, 3.8))
    for i, ax in enumerate(axes[0]):
        level = cv2.pyrDown(img) if i == 1 else (cv2.pyrDown(cv2.pyrDown(img)) if i == 2 else img)
        ax.imshow(level, cmap="gray", extent=(0, level.shape[1], level.shape[0], 0))
        ax.set(xlim=(0, w), ylim=(h, 0), xlabel="level x [px]", ylabel="level y [px]")
        ax.set_title(f"Octave {i}: {level.shape}")
    for i, ax in enumerate(axes[1]):
        view = dogs[i, 75:155, 300:440]
        im = ax.imshow(view, cmap="coolwarm", vmin=-.09, vmax=.09, extent=(300,440,155,75))
        ax.set_title(f"DoG {sigmas[i]:.2f}->{sigmas[i+1]:.2f}")
        ax.set(xlabel="original x [px]", ylabel="original y [px]")
    fig.subplots_adjust(hspace=.85, wspace=.58, right=.98, left=.09, bottom=.30, top=.96)
    # A dedicated colorbar axis stays outside the data axes after layout changes.
    cax = fig.add_axes([.35,.14,.35,.025])
    fig.colorbar(im, cax=cax, orientation="horizontal", label="intensity difference [0-1]")
    fig.savefig(BASE/"figures/d9_02_scale_space.png", dpi=CFG["dpi"], facecolor="white")
    plt.close(fig)
    artifact("scale_space", sigmas=sigmas, dogs=dogs, harris=harris, shi=shi, fast=xy(fast))

    fig, axes = plt.subplots(3, 1, figsize=(7, 7.2))
    for method, color in [("SIFT", "#007f77"), ("RootSIFT", "#6a4c93"), ("ORB", "#cd502a")]:
        r = [v for v in results if v["method"] == method]
        for ax, field in zip(axes, ["repeatability", "precision", "correct"]):
            ax.plot([v["case"] for v in r], [v[field] for v in r], "o-", label=method, color=color)
    for ax, label in zip(axes, ["Directional repeatability", "Match precision (ratio < .75)", "Correct matches [count]"]):
        ax.set_ylabel(label); ax.grid(alpha=.2); ax.legend()
    finish(fig, "d9_03_feature_ablation.png")
    return first, results


def match_experiment(first, img):
    metrics, arrays = [], {}
    fig, axes = plt.subplots(2, 2, figsize=(7, 6.4))
    for method, color in [("SIFT", "#007f77"), ("RootSIFT", "#6a4c93"), ("ORB", "#cd502a")]:
        k1, d1, k2, d2, H, target, m, visible = first[method]
        for mutual in [False, True]:
            count, precision = [], []
            for ratio in CFG["ratios"]:
                keep = (m["ratio"] < ratio) & visible[m["a"]]
                if mutual:
                    keep &= m["mutual"]
                count.append(int(keep.sum()))
                precision.append(float((m["err"][keep] < 3).mean()) if keep.any() else None)
                metrics.append(dict(method=method, mutual=mutual, ratio=ratio,
                                    count=count[-1], precision=precision[-1]))
            axes[0, 0].plot(CFG["ratios"], precision, "--" if mutual else "-", color=color,
                            label=method + (" +mutual" if mutual else ""))
            axes[0, 1].plot(CFG["ratios"], count, "--" if mutual else "-", color=color)
    for ax, method in zip(axes[1], ["SIFT", "ORB"]):
        m = first[method][6]; visible = first[method][7][m["a"]]
        for good, color in [(True, "#007f77"), (False, "#cd502a")]:
            take = visible & ((m["err"] < 3) == good)
            ax.hist(m["ratio"][take], bins=np.linspace(0,1,21), color=color, alpha=.6,
                    label="GT <3px" if good else "GT >=3px")
        ax.set(xlabel="d1 / d2 (unitless)", ylabel="candidate count", title=method)
        ax.legend()
    axes[0,0].set(xlabel="ratio threshold", ylabel="precision"); axes[0,0].legend(fontsize=6.5)
    axes[0,1].set(xlabel="ratio threshold", ylabel="retained count")
    finish(fig, "d10_01_matching_gates.png")

    k1, d1, k2, d2, H, target, m, visible = first["SIFT"]
    exact = np.array([v.trainIdx for v in cv2.BFMatcher().match(d1,d2)])
    flann_rows = []
    for checks in [1, 8, 32, 128]:
        t = time.perf_counter()
        flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=4), dict(checks=checks))
        found = flann.knnMatch(d1,d2,k=2)
        ms = (time.perf_counter()-t)*1000
        indices = np.array([v[0].trainIdx for v in found])
        approx_ratio = np.array([v[0].distance/max(v[1].distance,1e-12) for v in found])
        flann_rows.append(dict(checks=checks, exact_index_agreement=float((indices==exact).mean()),
                               build_plus_query_ms=ms,
                               ratio_decision_disagreement=int(((approx_ratio<.75)!=(m["ratio"]<.75)).sum())))
    save_json(BASE/"artifacts/matching/metrics.json", dict(ratio=metrics, flann=flann_rows))
    for key, value in m.items():
        arrays[key] = value
    artifact("matching", **arrays)

    q = np.array([[1.,0.],[0.,1.]])
    keys = np.array([[1.,0.],[0.,1.],[1.,1.]])
    values = np.array([[2.,0.],[0.,2.],[1.,1.]])
    weights = softmax(q @ keys.T / np.sqrt(2))
    kernel = np.array([[8.,2.,1.],[2.,8.,1.],[1.,1.,4.]])
    transport, history = sinkhorn(kernel,[1,1,2],[1,1,2])
    fig, axes = plt.subplots(1, 3, figsize=(7, 3.2))
    for ax, mat, title in zip(axes[:2], [weights,transport], ["Toy attention weights", "Toy transport mass"]):
        ax.imshow(mat, cmap="YlGnBu")
        for (i,j), v in np.ndenumerate(mat):
            ax.text(j,i,f"{v:.3f}",ha="center",va="center",fontsize=9,
                    color="white" if v > mat.max()*.65 else "black")
        ax.set(title=title, xlabel="target index", ylabel="source index")
    axes[2].semilogy(np.maximum(history,1e-16)); axes[2].set(title="Marginal error",xlabel="iteration",ylabel="max abs error")
    finish(fig,"d10_02_attention_transport.png")

    take = np.where((m["ratio"] < .75) & visible[m["a"]])[0]
    canvas = np.hstack([img,target])
    fig, ax = plt.subplots(figsize=(7, 3.4)); ax.imshow(canvas,cmap="gray")
    for index in take[::max(1,len(take)//45)]:
        p, r = xy(k1)[m["a"][index]], xy(k2)[m["b"][index]]
        ax.plot([p[0],r[0]+img.shape[1]],[p[1],r[1]],linewidth=.6,
                color="#007f77" if m["err"][index]<3 else "#ff4020",alpha=.8)
    ax.set(title="SIFT: selected sample, known 25-degree synthetic warp",xlabel="joined canvas x [px]",ylabel="y [px]")
    finish(fig,"d10_03_match_overlay.png")
    artifact("toys", attention=weights, messages=weights@values, kernel=kernel,
             transport=transport, marginal_history=history)
    return dict(attention=weights.tolist(),messages=(weights@values).tolist(),transport=transport.tolist())


def alignment_experiment(img, rng):
    h,w = img.shape
    Hgt = np.array([[1.02,.03,12.],[-.015,.98,6.],[.00005,-.00008,1.]])
    src = rng.uniform([30,30],[w-30,h-30],size=(100,2))
    truth = project(Hgt,src)
    noise = rng.normal(0,.5,truth.shape)
    observed = truth + noise
    observed[:30] = rng.uniform([0,0],[w,h],size=(30,2))
    Hls, sn, An = dlt(src,observed)
    Hr, mask = cv2.findHomography(src,observed,cv2.RANSAC,3,maxIters=10000,confidence=.999)
    grid = np.stack(np.meshgrid(np.linspace(30,w-30,25),np.linspace(30,h-30,12)),axis=-1).reshape(-1,2)
    els = np.linalg.norm(project(Hls,grid)-project(Hgt,grid),axis=1)
    er = np.linalg.norm(project(Hr,grid)-project(Hgt,grid),axis=1)
    _, sr, Ar = dlt(src,truth+noise,False)
    _, sn_clean, _ = dlt(src,truth+noise,True)
    near = np.c_[np.linspace(20,w-20,100),100+rng.normal(0,.05,100)]
    Hnear, snear, _ = dlt(near,project(Hgt,near)+rng.normal(0,.5,near.shape))
    enear = np.linalg.norm(project(Hnear,grid)-project(Hgt,grid),axis=1)
    fig, axes = plt.subplots(1,2,figsize=(7,3.6))
    for ax,s,title in [(axes[0],sr,"Unnormalized DLT"),(axes[1],sn_clean,"Normalized DLT")]:
        ax.semilogy(np.arange(1,len(s)+1),s,"o-"); ax.set(title=title,xlabel="singular-value index",ylabel="singular value")
        ax.grid(alpha=.2)
    finish(fig,"d11_01_dlt_conditioning.png")
    fig, axes = plt.subplots(2,1,figsize=(7,6.2))
    axes[0].scatter(observed[30:,0],observed[30:,1],s=8,c="#007f77",label="70 noisy GT correspondences")
    axes[0].scatter(observed[:30,0],observed[:30,1],s=12,c="#d65029",label="30 replaced targets")
    axes[0].set(xlabel="target x [px]",ylabel="target y [px]",ylim=(h,0)); axes[0].legend()
    axes[1].boxplot([els,er,enear],tick_labels=["DLT: 30% outliers","RANSAC","Nearly collinear"],showfliers=False)
    axes[1].set(yscale="log",ylabel="held-out grid warp error [px]")
    finish(fig,"d11_02_robust_degenerate.png")

    Hsmall = np.array([[1.,0.,3.],[0.,1.,-2.],[0.,0.,1.]])
    moved = cv2.warpPerspective(img,Hsmall,(w,h))
    bright = np.clip(.7*moved.astype(float)+30,0,255).astype(np.uint8)
    warp = np.eye(2,3,dtype=np.float32)
    ecc, warp = cv2.findTransformECC(img,bright,warp,cv2.MOTION_TRANSLATION,
                                   (cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,100,1e-7))
    aligned = cv2.warpAffine(bright,warp,(w,h),flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP)
    ys,xs = np.mgrid[:h,:w]; interior = (xs>20)&(xs<w-20)&(ys>20)&(ys<h-20)
    before = np.abs(img.astype(float)-bright)
    after = np.abs(img.astype(float)-aligned)
    fit = np.linalg.lstsq(np.c_[img[interior],np.ones(interior.sum())],aligned[interior],rcond=None)[0]
    corrected = (aligned.astype(float)-fit[1])/fit[0]
    corrected_error = np.abs(img.astype(float)-corrected)
    checker = img.copy(); pick=((xs//32+ys//32)%2==0); checker[pick]=np.clip(corrected[pick],0,255).astype(np.uint8)
    fig,axes=plt.subplots(3,1,figsize=(7,7.4))
    axes[0].imshow(checker,cmap="gray",vmin=0,vmax=255); axes[0].set_title("ECC aligned checkerboard; synthetic translation + gain/bias")
    for ax,data,title in [(axes[1],after,"After geometry only: absolute photometric residual"),
                          (axes[2],corrected_error,"After geometry + fitted gain/bias")]:
        im=ax.imshow(data,cmap="magma",vmin=0,vmax=50); ax.set_title(title)
        fig.colorbar(im,ax=ax,label="DN",fraction=.025,pad=.02)
    for ax in axes: ax.set(xlabel="x [px]",ylabel="y [px]")
    finish(fig,"d11_03_ecc_photometric.png")
    metrics=dict(ransac_inliers=int(mask.sum()),grid_median_dlt_px=float(np.median(els)),
                 grid_median_ransac_px=float(np.median(er)),grid_median_near_collinear_px=float(np.median(enear)),
                 raw_singular_ratio=float(sr[0]/sr[-1]),normalized_singular_ratio=float(sn_clean[0]/sn_clean[-1]),
                 ecc=float(ecc),ecc_translation=warp[:,2].tolist(),gain_bias=fit.tolist(),
                 photometric_mae_before=float(before[interior].mean()),
                 photometric_mae_geometry=float(after[interior].mean()),
                 photometric_mae_corrected=float(corrected_error[interior].mean()))
    artifact("alignment",src=src,observed=observed,truth=truth,Hgt=Hgt,Hls=Hls,Hransac=Hr,
             grid=grid,grid_error_ls=els,grid_error_ransac=er,grid_error_near=enear,
             singular_raw=sr,singular_normalized=sn_clean,near_points=near,
             ecc_warp=warp,ecc_aligned=aligned,ecc_corrected=corrected,interior=interior)
    save_json(BASE/"artifacts/alignment/metrics.json",metrics)
    return metrics


def lk_pair(img,target,p,level):
    args=dict(winSize=(CFG["lk_window"],)*2,maxLevel=level,
              criteria=(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,CFG["lk_iterations"],CFG["lk_epsilon"]))
    q,st,_=cv2.calcOpticalFlowPyrLK(img,target,p,None,**args)
    back,sb,_=cv2.calcOpticalFlowPyrLK(target,img,q,None,**args)
    fb=np.linalg.norm(back[:,0]-p[:,0],axis=1)
    return q[:,0],st[:,0].astype(bool)&sb[:,0].astype(bool),fb


def motion_experiment(img,next_img):
    h,w=img.shape
    p=cv2.goodFeaturesToTrack(img,700,.01,8)
    rows,arrays=[],{}
    for shift in CFG["flow_translations_px"]:
        H=np.array([[1.,0.,shift],[0.,1.,2.],[0.,0.,1.]])
        target=cv2.warpPerspective(img,H,(w,h))
        truth=project(H,p[:,0])
        interior=(truth[:,0]>25)&(truth[:,0]<w-25)&(truth[:,1]>25)&(truth[:,1]<h-25)
        for level in CFG["flow_levels"]:
            q,status,fb=lk_pair(img,target,p,level)
            e=np.linalg.norm(q-truth,axis=1)
            valid=status&interior
            keep=valid&(fb<1)
            rows.append(dict(shift=shift,level=level,n_visible=int(interior.sum()),
                             n_status=int(valid.sum()),n_fb=int(keep.sum()),
                             median_status_epe=float(np.median(e[valid])),mean_status_epe=float(e[valid].mean()),
                             median_fb_epe=float(np.median(e[keep])),
                             mean_fb_epe=float(e[keep].mean()),good_visible_fraction=float((valid&(e<1)).sum()/interior.sum())))
            arrays[f"shift{shift}_level{level}_epe"]=e
            arrays[f"shift{shift}_level{level}_valid"]=valid
            arrays[f"shift{shift}_level{level}_fb"]=fb
    fig,axes=plt.subplots(2,1,figsize=(7,6))
    for level,color in [(0,"#cd502a"),(3,"#007f77")]:
        r=[v for v in rows if v["level"]==level]
        axes[0].plot([v["shift"] for v in r],[v["mean_status_epe"] for v in r],"o-",color=color,label=f"maxLevel={level}, status")
        axes[0].plot([v["shift"] for v in r],[v["mean_fb_epe"] for v in r],"x--",color=color,label=f"maxLevel={level}, FB<1px")
        axes[1].plot([v["shift"] for v in r],[v["good_visible_fraction"] for v in r],"o-",color=color,label=f"maxLevel={level}")
    axes[0].set(ylabel="mean endpoint error [px]",yscale="log")
    axes[1].set(ylabel="visible points with valid EPE<1px",xlabel="known horizontal translation [px]")
    for ax in axes: ax.legend(); ax.grid(alpha=.2)
    finish(fig,"d12_01_lk_pyramid_ablation.png")

    H=np.array([[1.,0.,8.],[0.,1.,2.],[0.,0.,1.]])
    target=cv2.warpPerspective(img,H,(w,h))
    occluded=target.copy(); occluded[70:165,330:455]=127
    flow=cv2.calcOpticalFlowFarneback(img,target,None,**CFG["farneback"])
    occflow=cv2.calcOpticalFlowFarneback(img,occluded,None,**CFG["farneback"])
    ys,xs=np.mgrid[:h,:w]
    interior=(xs>30)&(xs<w-40)&(ys>30)&(ys<h-30)
    visible=interior & ~((xs+8>=330)&(xs+8<455)&(ys+2>=70)&(ys+2<165))
    epe=np.linalg.norm(flow-np.array([8,2]),axis=2)
    occ_epe=np.linalg.norm(occflow-np.array([8,2]),axis=2)
    grad=cv2.Sobel(img,cv2.CV_32F,1,0)**2+cv2.Sobel(img,cv2.CV_32F,0,1)**2
    low=interior&(grad<100)
    dense=dict(clean_mean_epe=float(epe[interior].mean()),clean_median_epe=float(np.median(epe[interior])),
               low_gradient_mean_epe=float(epe[low].mean()),occlusion_visible_mean_epe=float(occ_epe[visible].mean()),
               clean_pixels=int(interior.sum()),occlusion_visible_pixels=int(visible.sum()))
    fig,axes=plt.subplots(3,1,figsize=(7,7.5))
    axes[0].imshow(occluded,cmap="gray",vmin=0,vmax=255); axes[0].set_title("Synthetic occluder (gray rectangle), target frame")
    for ax,data,title in [(axes[1],epe,"Clean warp: Farneback EPE"),(axes[2],np.where(visible,occ_epe,np.nan),"Occluded target: visible-only EPE")]:
        im=ax.imshow(data,cmap="magma",vmin=0,vmax=10); ax.set_title(title)
        fig.colorbar(im,ax=ax,label="px",fraction=.025,pad=.02)
    for ax in axes: ax.set(xlabel="x [px]",ylabel="y [px]")
    finish(fig,"d12_02_dense_flow_failure.png")

    q,status,fb=lk_pair(img,next_img,p,3)
    keep=status&(fb<1)&(q[:,0]>0)&(q[:,0]<w)&(q[:,1]>0)&(q[:,1]<h)
    temporal_flow=cv2.calcOpticalFlowFarneback(img,next_img,None,**CFG["farneback"])
    fig,axes=plt.subplots(2,1,figsize=(7,5.7))
    axes[0].imshow(img,cmap="gray"); pp=p[:,0][keep]; diff=q[keep]-pp
    axes[0].quiver(pp[:,0],pp[:,1],diff[:,0],diff[:,1],angles="xy",scale_units="xy",scale=1,color="#f4d842",width=.002)
    axes[0].set_title(f"Real KITTI 00: 000000 -> 000001, {keep.sum()} FB-kept tracks")
    magnitude=np.linalg.norm(temporal_flow,axis=2)
    im=axes[1].imshow(magnitude,cmap="viridis",vmin=0,vmax=20)
    fig.colorbar(im,ax=axes[1],label="px / frame pair",fraction=.025,pad=.02)
    axes[1].set_title("Real temporal flow magnitude: no GT error claim")
    for ax in axes: ax.set(xlabel="x [px]",ylabel="y [px]")
    finish(fig,"d12_03_real_temporal.png")
    arrays.update(points=p,flow=flow,occluded_flow=occflow,epe=epe,occluded_epe=occ_epe,
                  dense_interior=interior,dense_visible=visible,temporal_flow=temporal_flow,
                  temporal_points=q,temporal_fb=fb,temporal_keep=keep)
    artifact("motion",**arrays)
    metrics=dict(lk=rows,farneback=dense,temporal=dict(candidate_count=len(p),fb_kept=int(keep.sum()),
                median_fb_px=float(np.median(fb[keep])),gt_flow_available=False))
    save_json(BASE/"artifacts/motion/metrics.json",metrics)
    return metrics


def tracking_toy():
    motion=np.array([[.1,.2],[.11,.9]])
    appearance=np.array([[.05,.9],[.8,.02]])
    a,b=linear_sum_assignment(motion)
    c,d=linear_sum_assignment(motion+appearance)
    x=np.array([10.,2.]); P=np.diag([4.,1.]); F=np.array([[1.,1.],[0.,1.]])
    Q=np.diag([.25,.25]); C=np.array([[1.,0.]]); R=np.array([[1.]])
    xp=F@x; Pp=F@P@F.T+Q
    innovation=np.array([13.])-C@xp; S=C@Pp@C.T+R
    K=Pp@C.T@np.linalg.inv(S); post=xp+(K@innovation)
    Ppost=(np.eye(2)-K@C)@Pp@(np.eye(2)-K@C).T+K@R@K.T
    fig,axes=plt.subplots(1,3,figsize=(7,3.4))
    for ax,mat,title,r,col in [(axes[0],motion,"Motion cost",a,b),(axes[1],motion+appearance,"Motion + appearance",c,d)]:
        ax.imshow(mat,cmap="YlGnBu",vmin=0,vmax=1.3)
        for (i,j),v in np.ndenumerate(mat): ax.text(j,i,f"{v:.2f}",ha="center",va="center")
        ax.scatter(col,r,s=300,facecolors="none",edgecolors="#d65029",linewidth=2)
        ax.set(title=title,xlabel="detection index",ylabel="track index",xticks=[0,1],yticks=[0,1])
    axes[2].errorbar([0,1,2],[xp[0],13,post[0]],yerr=np.sqrt([Pp[0,0],1,Ppost[0,0]]),fmt="o",capsize=4)
    axes[2].set(xticks=[0,1,2],xticklabels=["prior","measure","post"],ylabel="x [px]",title="1D position toy")
    finish(fig,"d12_04_assignment_kalman.png")
    vals=dict(motion=motion.tolist(),appearance=appearance.tolist(),assignment_motion=b.tolist(),
              assignment_combined=d.tolist(),predicted=xp.tolist(),Ppredicted=Pp.tolist(),
              gain=K.tolist(),posterior=post.tolist(),Pposterior=Ppost.tolist(),
              normalized_innovation_squared=float(innovation@np.linalg.solve(S,innovation)))
    artifact("tracking",motion_cost=motion,appearance_cost=appearance,predicted=xp,Ppredicted=Pp,
             gain=K,posterior=post,Pposterior=Ppost)
    save_json(BASE/"artifacts/tracking/metrics.json",vals)
    return vals


def main():
    start=time.perf_counter(); cv2.setNumThreads(1); cv2.setRNGSeed(CFG["seed"])
    rng=np.random.default_rng(CFG["seed"])
    original=cv2.imread(str(ROOT/CFG["frame0"]),cv2.IMREAD_GRAYSCALE)
    nxt=cv2.imread(str(ROOT/CFG["frame1"]),cv2.IMREAD_GRAYSCALE)
    assert original is not None and nxt is not None
    height=round(original.shape[0]*CFG["width"]/original.shape[1])
    img=cv2.resize(original,(CFG["width"],height),interpolation=cv2.INTER_AREA)
    nxt=cv2.resize(nxt,(CFG["width"],height),interpolation=cv2.INTER_AREA)
    first,features=feature_experiment(img)
    toys=match_experiment(first,img)
    alignment=alignment_experiment(img,rng)
    motion=motion_experiment(img,nxt)
    tracking=tracking_toy()
    metrics=dict(features=features,toys=toys,alignment=alignment,motion=motion,tracking=tracking)
    save_json(BASE/"artifacts/summary.json",metrics)
    inputs=[ROOT/CFG["frame0"],ROOT/CFG["frame1"]]
    source=list((BASE/"src").glob("*.py"))+list((BASE/"configs").glob("*.json"))
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs+source}
    manifest=dict(seed=CFG["seed"],git_head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                  python=sys.version,platform=platform.platform(),versions=dict(numpy=np.__version__,scipy=scipy.__version__,
                  opencv=cv2.__version__,matplotlib=matplotlib.__version__),opencv_threads=cv2.getNumThreads(),
                  original_shape=list(original.shape),working_shape=list(img.shape),
                  realized_resize_xy=[img.shape[1]/original.shape[1],img.shape[0]/original.shape[0]],
                  sha256=hashes,runtime_seconds=time.perf_counter()-start,
                  command="research/20261031_vo-lo-study/.venv/bin/python research/computer-vision-textbook/correspondence/src/experiment.py",
                  learned_models_run=False,mot_benchmark_run=False,
                  timing_note="Single calls under concurrent workers; no warmup/repeats; not a speed ranking. RootSIFT reuses actual SIFT keypoints/descriptors.")
    save_json(BASE/"artifacts/manifest.json",manifest)
    print(json.dumps(dict(figures=len(list((BASE/"figures").glob("*.png"))),runtime_seconds=manifest["runtime_seconds"],
                         summary=str(BASE/"artifacts/summary.json"))))


if __name__ == "__main__":
    main()
