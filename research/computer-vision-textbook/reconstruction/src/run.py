"""Small teaching models, not implementations of the cited full SLAM systems."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import time

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import numpy as np
import scipy
import PIL
from scipy.ndimage import distance_transform_edt
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
CFG = json.loads((BASE / "configs/default.json").read_text())
plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "legend.fontsize": 9})


def fusion(values, weights):
    return float(np.dot(values, weights) / np.sum(weights))


def composite(alpha, colors, background):
    alpha = np.asarray(alpha)
    trans = np.r_[1., np.cumprod(1 - alpha)[:-1]]
    weights = trans * alpha
    return weights @ colors + np.prod(1 - alpha) * background, weights


def projection_jacobian(p, f):
    x, y, z = p
    return np.array([[f/z, 0, -f*x/z**2], [0, f/z, -f*y/z**2]])


def plane_jacobian(points, normals):
    return np.column_stack((np.cross(points, normals), normals))


def preintegrate(accels, gyros, dt):
    r, v, p = np.eye(3), np.zeros(3), np.zeros(3)
    positions = [p.copy()]
    for a, w in zip(accels, gyros):
        p = p + v*dt + 0.5*(r @ a)*dt**2
        v = v + (r @ a)*dt
        r = r @ Rotation.from_rotvec(w*dt).as_matrix()
        positions.append(p.copy())
    return r, v, p, np.asarray(positions)


def align_points(est, truth, scale=False):
    x, y = est-est.mean(0), truth-truth.mean(0)
    u, s, vt = np.linalg.svd(x.T @ y)
    d = np.eye(3)
    d[-1, -1] = np.linalg.det(u @ vt)
    r = u @ d @ vt
    k = np.sum(s*np.diag(d))/np.sum(x*x) if scale else 1.
    return k*x @ r + truth.mean(0), k


def queue_latency(service, period):
    finish = 0.
    latency = []
    for i, cost in enumerate(service):
        arrival = i*period
        finish = max(arrival, finish)+cost
        latency.append(finish-arrival)
    return np.asarray(latency)


def savefig(fig, name):
    fig.tight_layout()
    fig.savefig(BASE / "figures" / (name + ".png"), dpi=CFG["dpi"])
    plt.close(fig)


def artifact(module, **arrays):
    path = BASE / "artifacts" / module
    path.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path / "arrays.npz", **arrays)


def main():
    start = time.perf_counter()
    cv2.setRNGSeed(CFG["seed"])
    cv2.setNumThreads(1)
    (BASE / "figures").mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(CFG["seed"])
    metrics = {}
    z = np.linspace(1.6, 2.4, 241)
    depths = np.array([2.00, 2.03, 1.98])
    weights = np.array([1., 1., 4.])
    fs = np.clip((depths[:, None]-z)/CFG["tsdf_truncation_m"], -1, 1)
    fused = np.average(fs, axis=0, weights=weights)
    biased = np.mean(np.clip((np.array([2., 2.15])[:, None]-z)/0.12, -1, 1), axis=0)
    fig, ax = plt.subplots(2, 1, figsize=(7, 6))
    for i, row in enumerate(fs):
        ax[0].plot(z, row, label=f"depth={depths[i]:.2f} m, w={weights[i]:g}")
    ax[0].plot(z, fused, "k", lw=2, label="weighted TSDF")
    ax[0].axhline(0, c="gray", lw=.7)
    ax[0].set(xlabel="voxel z [m]", ylabel="normalized TSDF", title="Synthetic rays: positive in front of surface")
    ax[0].legend()
    ax[1].plot(z, biased, label="two poses: 0.15 m inconsistency")
    ax[1].axvline(2, c="k", ls="--", label="true surface")
    ax[1].axhline(0, c="gray", lw=.7)
    ax[1].set(xlabel="voxel z [m]", ylabel="normalized TSDF", title="Pose error survives fusion")
    ax[1].legend()
    savefig(fig, "d21_01_tsdf")
    metrics["weighted_depth_m"] = fusion(depths, weights)

    grid = np.zeros((80, 80), bool)
    grid[30:50, 30:50] = True
    sdf = (distance_transform_edt(~grid)-distance_transform_edt(grid))*.05
    fig, ax = plt.subplots(1, 2, figsize=(7, 3.7))
    im = ax[0].imshow(grid, origin="lower", extent=[0,4,0,4], cmap="gray_r")
    ax[0].set(title="Synthetic occupancy (known cells)", xlabel="x [m]", ylabel="y [m]")
    im = ax[1].imshow(sdf, origin="lower", extent=[0,4,0,4], cmap="coolwarm")
    ax[1].contour(np.linspace(0,4,80), np.linspace(0,4,80), sdf, levels=[.2,.5,1.], colors="black", linewidths=.6)
    ax[1].set(title="Grid-center signed distance", xlabel="x [m]", ylabel="y [m]")
    fig.colorbar(im, ax=ax[1], label="distance [m]", shrink=.7)
    savefig(fig, "d21_02_esdf")

    xy = rng.uniform(-1, 1, (400, 2))
    points = np.c_[xy, np.ones(400)]
    normals = np.tile([0.,0.,1.], (400,1))
    jac = plane_jacobian(points, normals)
    singular = np.linalg.svd(jac, compute_uv=False)
    measured = .04 + rng.normal(0,.003,400)
    measured[:80] += .4
    ls = float(np.mean(measured))
    robust = float(least_squares(lambda t: t-measured, [.0], loss="huber", f_scale=.01).x[0])
    tree = cKDTree(points)
    _, indices = tree.query(points, k=12)
    cov = np.cov(points[indices[0]].T)
    _, eigvec = np.linalg.eigh(cov)
    fig, ax = plt.subplots(1, 2, figsize=(7, 3.6))
    ax[0].bar(np.arange(6), singular)
    ax[0].set(xlabel="singular value index", ylabel="mixed-unit J singular value", title="Plane ICP: three null directions")
    ax[1].hist(measured, bins=25, color="gray")
    ax[1].axvline(ls, c="red", label=f"mean {ls:.4f} m")
    ax[1].axvline(robust, c="green", label=f"Huber {robust:.4f} m")
    ax[1].axvline(.04, c="k", ls="--", label="truth 0.04 m")
    ax[1].set(xlabel="normal displacement [m]", ylabel="count", title="Known correspondences; 20% outliers")
    ax[1].legend()
    savefig(fig, "d21_03_registration")
    metrics.update(icp_rank=int(np.linalg.matrix_rank(jac)), translation_mean_m=ls, translation_huber_m=robust)
    artifact("geometry", z=z, tsdf=fs, fused=fused, occupancy=grid, sdf=sdf, points=points, jacobian=jac, singular=singular, displacement=measured, estimated_normal=eigvec[:,0])

    seq = ROOT / "data/kitti/dataset/sequences/00"
    files = [seq / "image_0/000000.png", seq / "image_1/000000.png", seq / "calib.txt"]
    left, right = [cv2.imread(str(p), cv2.IMREAD_GRAYSCALE) for p in files[:2]]
    calib = {line.split(":")[0]: np.fromstring(line.split(":")[1], sep=" ") for line in files[2].read_text().splitlines()}
    p0, p1 = calib["P0"].reshape(3,4), calib["P1"].reshape(3,4)
    f, cx, cy = p0[0,0], p0[0,2], p0[1,2]
    baseline = -p1[0,3]/p1[0,0] + p0[0,3]/p0[0,0]
    block = CFG["stereo_block_size"]
    matcher = cv2.StereoSGBM_create(minDisparity=0, numDisparities=CFG["stereo_num_disparities"], blockSize=block, P1=8*block**2, P2=32*block**2, uniquenessRatio=10, speckleWindowSize=100, speckleRange=2)
    ts = time.perf_counter()
    disp = matcher.compute(left, right).astype(float)/16
    stereo_ms = 1000*(time.perf_counter()-ts)
    depth = f*baseline/np.maximum(disp, .001)
    valid = (disp > 1) & (depth < CFG["stereo_max_depth_m"])
    vv, uu = np.indices(left.shape)
    xyz = np.stack(((uu-cx)*depth/f, (vv-cy)*depth/f, depth), axis=-1)
    sample = valid & (uu%6 == 0) & (vv%6 == 0)
    cloud = xyz[sample]
    fig = plt.figure(figsize=(7,7))
    ax = fig.add_subplot(211)
    ax.imshow(left, cmap="gray")
    ax.set(title="KITTI 00 / 000000 left, actual grayscale", xlabel="u [px]", ylabel="v [px]")
    ax = fig.add_subplot(212, projection="3d")
    ax.scatter(cloud[:,0], cloud[:,2], -cloud[:,1], c=left[sample], cmap="gray", s=1)
    ax.set(xlabel="camera x [m]", ylabel="camera z [m]", zlabel="-camera y [m]", title="StereoSGBM depth: unvalidated geometry, not GT")
    ax.view_init(22, -70)
    savefig(fig, "d21_04_kitti")
    metrics.update(stereo_valid_fraction=float(valid.mean()), stereo_point_count=len(cloud), stereo_ms=stereo_ms, stereo_baseline_m=float(baseline))
    artifact("stereo", disparity=disp, valid=valid, cloud=cloud, gray=left[sample], P0=p0, P1=p1)

    # Pixel-center barycentric interpolation; illustrative rasterization only.
    xx, yy = np.meshgrid(np.linspace(0,1,101), np.linspace(0,1,101))
    lambdas = np.stack((1-xx-yy, xx, yy), axis=-1)
    mask = (lambdas >= 0).all(-1)
    vertex_z = np.array([1.,2.,4.])
    reciprocal = np.sum(lambdas/vertex_z, -1)
    correct_z = 1/np.maximum(reciprocal, 1e-8)
    wrong_z = lambdas @ vertex_z
    fig, ax = plt.subplots(1, 2, figsize=(7,3.7))
    for axis, val, title in zip(ax, [correct_z, wrong_z-correct_z], ["Perspective-correct depth", "Linear z minus correct depth"]):
        im=axis.imshow(np.where(mask,val,np.nan), origin="lower", extent=[0,1,0,1], cmap="viridis")
        axis.set(xlabel="screen x [normalized]", ylabel="screen y [normalized]", title=title)
        fig.colorbar(im, ax=axis, label="m", shrink=.7)
    savefig(fig, "d22_01_raster")

    lights = np.array([[0,0,1],[.6,0,.8],[0,.6,.8],[-.6,0,.8],[0,-.6,.8]])
    normal = np.array([.3,.4,np.sqrt(.75)])
    albedo = .7
    intensity = lights @ (albedo*normal)
    bad = intensity.copy(); bad[1] += .4
    clean_g = np.linalg.lstsq(lights,intensity,rcond=None)[0]
    bad_g = np.linalg.lstsq(lights,bad,rcond=None)[0]
    recovered = bad_g/np.linalg.norm(bad_g)
    photo_angle = np.degrees(np.arccos(np.clip(normal @ recovered,-1,1)))
    fig, ax = plt.subplots(1,2,figsize=(7,3.8))
    ax[0].plot(intensity,"o-",label="Lambertian synthetic")
    ax[0].plot(bad,"s--",label="one specular violation")
    ax[0].set(xlabel="light index",ylabel="linear intensity [relative units]",title="Photometric stereo inputs"); ax[0].legend()
    ax[1].bar(np.arange(3)-.16,normal,.32,label="true normal")
    ax[1].bar(np.arange(3)+.16,recovered,.32,label="least-squares normal")
    ax[1].set(xticks=[0,1,2],xticklabels=["nx","ny","nz"],ylabel="unitless",title=f"Specularity error {photo_angle:.2f} deg"); ax[1].legend()
    savefig(fig,"d22_02_photometric")
    metrics["photometric_corruption_angle_deg"] = float(photo_angle)

    alpha = np.array([.5,.25,.8]); colors=np.eye(3); bg=np.ones(3)
    rgb, w=composite(alpha,colors,bg)
    rgb_reverse,_=composite(alpha[::-1],colors[::-1],bg)
    fig,ax=plt.subplots(1,2,figsize=(7,3.7))
    ax[0].bar(np.arange(4),np.r_[w,np.prod(1-alpha)],color=["red","green","blue","gray"])
    ax[0].set(xticks=[0,1,2,3],xticklabels=["near","middle","far","background"],ylabel="termination weight",title="Front-to-back mass conservation")
    ax[1].imshow(np.array([[rgb,rgb_reverse]]),extent=[0,2,0,1])
    ax[1].set(xticks=[.5,1.5],xticklabels=["front to back","reversed"],yticks=[],title="Same samples, wrong ordering")
    savefig(fig,"d22_03_compositing")
    metrics["composite_rgb"] = rgb.tolist()

    mu=np.array([.3,.1,2.]); sigma=np.diag([.04**2,.08**2,.12**2]); j=projection_jacobian(mu,500)
    cov2=j @ sigma @ j.T
    vals,vecs=np.linalg.eigh(cov2)
    pts=rng.multivariate_normal(mu,sigma,4000)
    proj=500*pts[:,:2]/pts[:,2,None]
    center=500*mu[:2]/mu[2]
    fig,ax=plt.subplots(1,2,figsize=(7,3.7))
    ax[0].scatter(proj[:,0],proj[:,1],s=.7,alpha=.2)
    angle=np.degrees(np.arctan2(vecs[1,1],vecs[0,1]))
    ax[0].add_patch(Ellipse(center,4*np.sqrt(vals[1]),4*np.sqrt(vals[0]),angle=angle,fill=False,color="red",lw=2))
    ax[0].set(xlabel="u [px; principal point=0]",ylabel="v [px]",title="Projected synthetic 3D Gaussian")
    ax[0].set_aspect("equal")
    depths_g=np.linspace(.3,5,60)
    ax[1].plot(depths_g,[np.sqrt(np.trace(projection_jacobian([.3,.1,d],500) @ sigma @ projection_jacobian([.3,.1,d],500).T)) for d in depths_g])
    ax[1].set(xlabel="mean z [m]",ylabel="sqrt(trace covariance) [px]",title="Near camera: nonlinear footprint")
    savefig(fig,"d22_04_gaussian")
    metrics["gaussian_cov_px2"]=cov2.tolist()
    artifact("rendering", lambdas=lambdas, correct_z=correct_z, wrong_z=wrong_z, lights=lights, intensity=intensity, corrupted=bad, recovered_g=clean_g, alpha=alpha, weights=w, color=rgb, covariance=cov2, projected=proj)

    n=100; dt=CFG["imu_dt_s"]
    accel=np.tile([1.,0.,0.],(n,1)); gyro=np.tile([0.,0.,.2],(n,1))
    r,v,p,path=preintegrate(accel,gyro,dt)
    _,_,_,wrong=preintegrate(accel,np.zeros_like(gyro),dt)
    offsets=np.linspace(0,.05,100)
    fig,ax=plt.subplots(1,2,figsize=(7,3.7))
    ax[0].plot(path[:,0],path[:,1],label="rotated specific force")
    ax[0].plot(wrong[:,0],wrong[:,1],"--",label="ignore rotation")
    ax[0].set(xlabel="delta p x [m]",ylabel="delta p y [m]",title="Synthetic horizontal preintegration");ax[0].legend()
    ax[1].plot(offsets*1000,500*.5*offsets,label="500 px, 0.5 rad/s")
    ax[1].set(xlabel="time offset [ms]",ylabel="first-order image shift [px]",title="Timing error is geometric error");ax[1].legend()
    savefig(fig,"d23_01_timing")
    metrics["preintegrated_position_m"]=p.tolist()

    frac=np.linspace(0,.9,19); bias=.5*frac
    retained_static=1-frac
    fig,ax=plt.subplots(1,2,figsize=(7,3.7))
    ax[0].plot(frac,bias,label="least squares: 0.5 m dynamic offset")
    ax[0].plot(frac,np.zeros_like(frac),label="oracle dynamic mask")
    ax[0].set(xlabel="dynamic fraction",ylabel="translation bias [m]",title="Analytic mixture (no detector)");ax[0].legend()
    ax[1].plot(frac,retained_static,label="static retained fraction")
    ax[1].plot(frac,1/np.sqrt(np.maximum(retained_static,.01)),label="relative standard error")
    ax[1].set(xlabel="dynamic fraction",ylabel="ratio",title="Removing points also removes information");ax[1].legend()
    savefig(fig,"d23_02_dynamic")

    t=np.linspace(0,2*np.pi,120)
    truth=np.c_[3*np.cos(t),2*np.sin(t),.2*t]
    rot=Rotation.from_euler("z",25,degrees=True).as_matrix()
    estimate=1.2*truth @ rot.T + [5,-2,1]
    se3,_=align_points(estimate,truth); sim3,scale=align_points(estimate,truth,True)
    errs=[np.sqrt(np.mean(np.sum((x-truth)**2,axis=1))) for x in [estimate,se3,sim3]]
    fig,ax=plt.subplots(1,2,figsize=(7,3.7))
    ax[0].plot(truth[:,0],truth[:,1],label="truth")
    ax[0].plot(se3[:,0],se3[:,1],label="SE(3) aligned")
    ax[0].set(xlabel="x [m]",ylabel="y [m]",title="Synthetic scale bias remains");ax[0].legend()
    ax[1].bar(["raw","SE(3)","Sim(3)"],errs)
    ax[1].set(ylabel="position RMSE [m]",title="Alignment policy changes the question")
    savefig(fig,"d23_03_alignment")
    metrics.update(alignment_rmse_m=errs, oracle_scale=float(scale))
    artifact("timing", path=path, ignoring_rotation=wrong, gyro=gyro, accel=accel, offsets=offsets, dynamic_fraction=frac)

    service=np.full(120,20.);service[::20]=180.
    latency=queue_latency(service,CFG["queue_period_ms"])
    fig,ax=plt.subplots(2,1,figsize=(7,5.5))
    ax[0].plot(service,label="service time");ax[0].plot(latency,label="end-to-end FIFO latency")
    ax[0].axhline(CFG["queue_period_ms"],c="k",ls="--",label="arrival period")
    ax[0].set(xlabel="frame index",ylabel="ms",title="Synthetic queue, not hardware profile");ax[0].legend()
    ax[1].plot(np.sort(latency),np.arange(1,121)/120)
    ax[1].set(xlabel="latency [ms]",ylabel="empirical CDF",title="Tail latency cannot be replaced by mean service")
    savefig(fig,"d24_01_latency")
    metrics.update(service_mean_ms=float(service.mean()),latency_p95_ms=float(np.percentile(latency,95)),deadline_miss_fraction=float(np.mean(latency>CFG["queue_period_ms"])))

    groups=np.repeat(np.arange(20),20)
    group_error=rng.normal(0,1,20)
    observations=group_error[groups]+rng.normal(0,.1,len(groups))
    iid_means=np.mean(rng.choice(observations,(1000,len(observations))),axis=1)
    block_means=np.mean(rng.choice(group_error,(1000,len(group_error))),axis=1)
    fig,ax=plt.subplots(1,2,figsize=(7,3.7))
    ax[0].plot(observations,".",ms=2)
    ax[0].set(xlabel="frame index (20 per scene)",ylabel="synthetic error [m]",title="Within-scene correlation")
    ax[1].hist(iid_means,bins=30,alpha=.6,label="frame resampling")
    ax[1].hist(block_means,bins=30,alpha=.6,label="scene resampling")
    ax[1].set(xlabel="resampled mean [m]",ylabel="count",title="Frame vs scene resampling");ax[1].legend()
    savefig(fig,"d24_02_bias")
    metrics.update(frame_bootstrap_std_m=float(iid_means.std()),scene_bootstrap_std_m=float(block_means.std()))

    thresholds=np.linspace(.005,.5,100)
    errors=[]
    for threshold in thresholds:
        fit=least_squares(lambda q:q-measured,[.0],loss="huber",f_scale=threshold)
        errors.append(abs(fit.x[0]-.04))
    fig,ax=plt.subplots(1,2,figsize=(7,3.7))
    ax[0].plot(thresholds,errors)
    ax[0].set(xlabel="Huber transition [m]",ylabel="absolute translation error [m]",title="One frozen contamination scenario")
    ax[1].bar(["LS","Huber .01"],[abs(ls-.04),abs(robust-.04)])
    ax[1].set(ylabel="absolute translation error [m]",title="Paired ablation; not a benchmark score")
    savefig(fig,"d24_03_ablation")
    artifact("evaluation", truth=truth,estimate=estimate,se3=se3,sim3=sim3,service=service,latency=latency,observations=observations,frame_means=iid_means,scene_means=block_means,thresholds=thresholds,errors=errors)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest={"config":CFG,"metrics":metrics,"runtime_s":time.perf_counter()-start,"python":platform.python_version(),"platform":platform.platform(),"opencv_threads":cv2.getNumThreads(),"dependencies":{m.__name__:m.__version__ for m in [np,scipy,cv2,matplotlib,PIL]},"commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"source_hashes":{str(p.relative_to(ROOT)):sha(p) for p in sorted((BASE/"src").glob("*.py"))},"config_hash":sha(BASE/"configs/default.json"),"data_hashes":{str(p.relative_to(ROOT)):sha(p) for p in files},"figures":{p.name:sha(p) for p in sorted((BASE/"figures").glob("*.png"))},"limitations":["No stereo ground truth verification","No full ICP or VIO system","No NeRF or 3DGS training","Synthetic latency is not device profiling"]}
    (BASE/"artifacts/manifest.json").write_text(json.dumps(manifest,indent=2))
    print(json.dumps(metrics,indent=2))


if __name__ == "__main__":
    main()
