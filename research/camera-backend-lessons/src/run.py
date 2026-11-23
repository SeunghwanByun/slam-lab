"""Reproduce all synthetic lesson artifacts and nine original figures."""

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

# Keep all generated caches inside the explicitly owned directory.
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ.setdefault("MPLCONFIGDIR", ".cache/matplotlib")
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy.spatial.transform import Rotation

from backend import (JointBA, ba_errors, centers, depths, gauge_transform, graph_cases,
                     make_ba, make_graph, project, solver_info, wrap)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def savefig(name, fig):
    fig.suptitle("SYNTHETIC LESSON | " + name.replace("_", " "), fontsize=14)
    fig.savefig(ROOT / "figures" / (name + ".png"), dpi=160)
    plt.close(fig)


def rmse(x):
    return float(np.sqrt(np.mean(np.asarray(x)**2)))


def run_ba(cfg, seed):
    data = make_ba(cfg, seed)
    folder = ROOT / "artifacts/ba"
    folder.mkdir(parents=True, exist_ok=True)
    states = {"initial": (data["initial_poses"], data["initial_points"])}
    metrics, models = {}, {}
    arrays = dict(data)
    for name, observation, loss in [("clean_ls", "observations", "linear"),
                                    ("outlier_ls", "corrupt", "linear"),
                                    ("outlier_robust", "corrupt", "soft_l1")]:
        model = JointBA(data[observation], data["K"], cfg["baseline_m"], data["poses_gt"][0])
        x0 = model.pack(*states["initial"])
        result = model.solve(x0, cfg, loss)
        poses, points = model.unpack(result.x)
        states[name], models[name] = (poses, points), model
        prediction = project(poses, points, data["K"], cfg["baseline_m"])
        residual = prediction - data[observation]
        metrics[name] = dict(**ba_errors(poses, points, data), solver=solver_info(result),
                             observation_coordinate_rmse_px=rmse(residual),
                             truth_coordinate_rmse_px=rmse(prediction-data["truth"]),
                             inlier_coordinate_rmse_px=rmse(residual[~data["outlier_mask"]]),
                             min_depth_m=float(depths(poses, points).min()),
                             pose_parameter_update_norm=float(np.linalg.norm(result.x[:model.pose_size]-x0[:model.pose_size])),
                             point_update_norm_m=float(np.linalg.norm(points-data["initial_points"])),
                             initial_objective=float(0.5*np.sum(model.residual(x0)**2)) if loss == "linear" else
                             float(cfg["robust_f_scale_px"]**2 * np.sum(np.sqrt(1+(model.residual(x0)/cfg["robust_f_scale_px"])**2)-1)))
        arrays[name+"_poses"], arrays[name+"_points"] = poses, points
        arrays[name+"_projections"], arrays[name+"_residuals"] = prediction, residual
        print(name, json.dumps(metrics[name]), flush=True)
    initial_prediction = project(*states["initial"], data["K"], cfg["baseline_m"])
    arrays["initial_projections"] = initial_prediction
    metrics["initial"] = dict(**ba_errors(*states["initial"], data),
                             observation_coordinate_rmse_px=rmse(initial_prediction-data["observations"]),
                             min_depth_m=float(depths(*states["initial"]).min()))
    metrics["contract"] = dict(cameras=cfg["cameras"], points=cfg["points"],
                               scalar_residuals=int(data["truth"].size),
                               anchored_parameters=int(models["clean_ls"].pack(*states["initial"]).size),
                               outlier_observations=int(data["outlier_mask"].sum()),
                               camera_rmse_excludes_anchor=True,
                               gt_alignment="none; fixed first pose defines GT frame",
                               initialization="synthetic GT perturbation; not a frontend",
                               residual_unit="pixel", robust_unit="scalar coordinate, not 2D block")
    np.savez_compressed(folder / "module.npz", **arrays)
    save_json(folder / "metrics.json", metrics)

    # Compare gauge spectra at one common GT state, not solver-modified robust J.
    free = JointBA(data["observations"], data["K"], cfg["baseline_m"], data["poses_gt"][0], False)
    fixed = models["clean_ls"]
    sf = np.linalg.svd(free.jacobian(free.pack(data["poses_gt"], data["points_gt"])), compute_uv=False)
    sa = np.linalg.svd(fixed.jacobian(fixed.pack(data["poses_gt"], data["points_gt"])), compute_uv=False)
    Q = Rotation.from_rotvec([0.2, -0.3, 0.1]).as_matrix()
    transformed = gauge_transform(data["poses_gt"], data["points_gt"], Q, np.array([1., -2., 0.5]))
    invariance = project(*transformed, data["K"], cfg["baseline_m"]) - data["truth"]
    scales = np.linspace(0.6, 1.5, 19)
    stereo_error, mono_error = [], []
    for scale in scales:
        p = data["poses_gt"].copy()
        p[:, 3:] *= scale
        diff = project(p, data["points_gt"]*scale, data["K"], cfg["baseline_m"])-data["truth"]
        stereo_error.append(rmse(diff))
        mono_error.append(rmse(diff[:, 0]))
    gauge = dict(rigid_transform_max_abs_px=float(np.max(np.abs(invariance))),
                 relative_svd_rank_tolerance=1e-10,
                 free_nullity=int(np.sum(sf < sf[0]*1e-10)),
                 fixed_nullity=int(np.sum(sa < sa[0]*1e-10)),
                 free_smallest_singular_values=sf[-8:].tolist(),
                 fixed_smallest_singular_values=sa[-8:].tolist(),
                 mono_max_scale_rmse_px=float(max(mono_error)),
                 stereo_scale_1_5_rmse_px=float(stereo_error[-1]),
                 spectrum_units="mixed pixel/radian and pixel/meter columns; not a coordinate-free condition number")
    gf = ROOT / "artifacts/gauge"
    gf.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(gf / "module.npz", free_singular_values=sf, fixed_singular_values=sa,
                        Q=Q, d=[1., -2., .5], transformed_poses=transformed[0],
                        transformed_points=transformed[1], projection_difference=invariance,
                        scales=scales, stereo_rmse_px=stereo_error, mono_rmse_px=mono_error)
    save_json(gf / "metrics.json", gauge)

    fig, axes = plt.subplots(1, 2, figsize=(11, 6), layout="constrained")
    ax = axes[0]
    ax.scatter(data["points_gt"][:, 0], data["points_gt"][:, 2], s=25, label="GT points")
    ax.scatter(states["initial"][1][:, 0], states["initial"][1][:, 2], marker="x", label="Initial points")
    ax.scatter(states["clean_ls"][1][:, 0], states["clean_ls"][1][:, 2], s=36, facecolors="none", edgecolors="green", label="Joint BA points")
    for name, p in [("GT", data["poses_gt"]), ("Initial", states["initial"][0]), ("Joint BA", states["clean_ls"][0])]:
        C = centers(p)
        ax.plot(C[:, 0], C[:, 2], "o-", label=name+" left centers")
        axes[1].plot(C[:, 0], C[:, 2], "o-", label=name+" left centers")
    from backend import rotation
    C = centers(data["poses_gt"])
    right = np.array([c + rotation(p[:3]).T @ [cfg["baseline_m"], 0, 0]
                      for c, p in zip(C, data["poses_gt"])])
    axes[1].scatter(right[:, 0], right[:, 2], marker="s", color="black", label="GT right centers")
    for left, r in zip(C, right):
        axes[1].plot([left[0], r[0]], [left[2], r[2]], "k:", lw=2)
    ax.set(xlabel="World x [m]", ylabel="World z [m]", aspect="equal", title="Scene (x-z view)")
    axes[1].set(xlabel="World x [m]", ylabel="World z [m]", aspect="equal", title="Camera zoom: baseline = 0.24 m")
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=9, ncol=3, loc="outside lower center")
    axes[1].legend(fontsize=8, loc="upper left", bbox_to_anchor=(0, -.28))
    savefig("01_stereo_scene", fig)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    for side in range(2):
        for col, name in enumerate(["initial", "clean_ls"]):
            ax = axes[side, col]
            pred = project(*states[name], data["K"], cfg["baseline_m"])[-1, side]
            obs = data["observations"][-1, side]
            ax.scatter(obs[:, 0], obs[:, 1], s=23, label="Noisy observed")
            ax.scatter(pred[:, 0], pred[:, 1], marker="+", color="darkorange", label="Predicted")
            for a, b in zip(obs, pred):
                ax.plot([a[0], b[0]], [a[1], b[1]], color="0.5", lw=.65)
            ax.set(xlim=(0, cfg["width_px"]), ylim=(cfg["height_px"], 0),
                   xlabel="u [px]", ylabel="v [px]", title=f"Camera 3 / {'left' if side == 0 else 'right'} / {name}", aspect="equal")
            ax.legend(fontsize=8)
    savefig("02_initial_final_projections", fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), layout="constrained")
    limit = np.ceil(np.abs(initial_prediction-data["observations"]).max())
    bins = np.linspace(-limit, limit, 71)
    for name in ["initial", "clean_ls"]:
        r = project(*states[name], data["K"], cfg["baseline_m"])-data["observations"]
        axes[0].hist(r.ravel(), bins=bins, histtype="step", lw=2, label=name)
    final_names = ["clean_ls", "outlier_ls", "outlier_robust"]
    limit = np.ceil(max(np.abs((project(*states[name], data["K"], cfg["baseline_m"])
                               - data["observations"])[~data["outlier_mask"]]).max()
                        for name in final_names))
    for name in final_names:
        r = project(*states[name], data["K"], cfg["baseline_m"])-data["observations"]
        axes[1].hist(r[~data["outlier_mask"]].ravel(), bins=np.linspace(-limit, limit, 61), histtype="step", lw=2, label=name)
    for ax, title in zip(axes, ["Clean observations: initial / final", "Uncorrupted observations only"]):
        ax.set(xlabel="Predicted - observed coordinate [px]", ylabel="Count", title=title)
        ax.legend()
    savefig("03_residual_histograms", fig)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), layout="constrained")
    names = list(states)
    for ax, key, unit in zip(axes, ["camera_center_rmse_m", "camera_rotation_rmse_deg", "point_rmse_m"], ["m", "deg", "m"]):
        ax.bar(range(4), [metrics[n][key] for n in names], color=["gray", "seagreen", "indianred", "royalblue"])
        ax.set(xticks=range(4), xticklabels=["Initial", "Clean LS", "Outlier LS", "Robust"], ylabel=f"RMSE [{unit}]", title=key.replace("_rmse_"+unit, "").replace("_", " "))
        ax.tick_params(axis="x", rotation=20)
    savefig("04_gt_error_ablation", fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    axes[0].semilogy(np.arange(len(sf)), sf, ".-", label="Unfixed: 6 rigid gauges")
    axes[0].semilogy(np.arange(len(sa)), sa, ".-", label="First pose fixed")
    axes[0].set(xlabel="Descending singular-value index", ylabel="Singular value [mixed units]", title="Analytic reprojection Jacobian at GT")
    axes[0].legend()
    axes[1].plot(scales, stereo_error, "o-", label="Stereo, fixed baseline")
    axes[1].plot(scales, mono_error, "s-", label="Left image only")
    axes[1].set(xlabel="Scale applied to points + translations", ylabel="Projection change RMSE [px]", title="Scale is not a stereo gauge")
    axes[1].legend()
    savefig("05_gauge_and_scale", fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    for name in ["outlier_ls", "outlier_robust"]:
        residual = project(*states[name], data["K"], cfg["baseline_m"])-data["corrupt"]
        axes[0].plot(np.sort(np.linalg.norm(residual[~data["outlier_mask"]], axis=1)), label=name)
        axes[1].scatter(np.linalg.norm(residual[data["outlier_mask"]], axis=1),
                        np.linalg.norm((project(*states[name], data["K"], cfg["baseline_m"])-data["truth"])[data["outlier_mask"]], axis=1), label=name, alpha=.7)
    axes[0].set(xlabel="Sorted inlier observation index", ylabel="2D observed residual [px]", title="Robust loss protects inliers")
    axes[1].set(xlabel="2D corrupted-observation residual [px]", ylabel="2D synthetic-GT projection error [px]", title="Fitting corruption is not accuracy")
    for ax in axes:
        ax.legend()
    savefig("06_outlier_tradeoff", fig)
    return metrics, gauge


def run_graph(cfg, seed):
    data = make_graph(cfg, seed+1)
    cases = graph_cases(data, cfg)
    states, metrics = {}, {}
    arrays = dict(data)
    for name, model in cases.items():
        result = model.solve(data["initial"], cfg)
        poses = model.unpack(result.x)
        states[name] = poses
        position = np.linalg.norm(poses[:, :2]-data["poses_gt"][:, :2], axis=1)
        angles = wrap(poses[:, 2]-data["poses_gt"][:, 2])
        metrics[name] = dict(position_rmse_m=rmse(position[1:]),
                             rotation_rmse_deg=float(np.rad2deg(rmse(angles[1:]))),
                             endpoint_distance_m=float(np.linalg.norm(poses[-1, :2]-poses[0, :2])),
                             whitened_residual_rmse=rmse(model.residual(result.x)),
                             initial_objective=float(.5*np.sum(model.residual(data["initial"][1:].ravel())**2)),
                             solver=solver_info(result))
        arrays[name+"_poses"] = poses
        arrays[name+"_edges"] = model.edges
        arrays[name+"_measurements"] = model.measurements
        arrays[name+"_sigmas"] = model.sigmas
        arrays[name+"_raw_residuals"] = model.raw_residual(poses)
        arrays[name+"_whitened_residuals"] = model.residual(result.x).reshape(-1, 3)
        print(name, json.dumps(metrics[name]), flush=True)
    metrics["loop_verification"] = dict(correct_measurement=cases["correct_loop"].measurements[-1].tolist(),
                                       false_measurement=cases["false_loop"].measurements[-1].tolist(),
                                       correct_loop_gt_residual=cases["correct_loop"].raw_residual(data["poses_gt"])[-1].tolist(),
                                       false_loop_gt_residual=cases["false_loop"].raw_residual(data["poses_gt"])[-1].tolist(),
                                       verification="synthetic GT check only; no operational loop detector or rejection gate")
    folder = ROOT / "artifacts/pose_graph"
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder / "module.npz", **arrays)
    save_json(folder / "metrics.json", metrics)

    fig, axes = plt.subplots(1, 3, figsize=(14, 5), layout="constrained")
    for ax, (name, poses) in zip(axes, states.items()):
        ax.plot(data["poses_gt"][:, 0], data["poses_gt"][:, 1], "k--", label="Synthetic GT")
        ax.plot(poses[:, 0], poses[:, 1], "o-", ms=3, label=name)
        ax.scatter([0], [0], marker="s", s=70, color="red", label="Fixed first pose")
        if name != "odometry":
            ax.plot([poses[-1, 0], 0], [poses[-1, 1], 0], "r:", lw=2, label="Loop endpoints")
        ax.set(xlabel="x [m]", ylabel="y [m]", title=name, aspect="equal", xlim=(-6, 5), ylim=(-2, 10))
        ax.legend(fontsize=8)
    savefig("07_se2_loop_paths", fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    for name, poses in states.items():
        axes[0].plot(np.linalg.norm(poses[:, :2]-data["poses_gt"][:, :2], axis=1), "o-", ms=3, label=name)
        axes[1].plot(np.rad2deg(np.abs(wrap(poses[:, 2]-data["poses_gt"][:, 2]))), "o-", ms=3, label=name)
    for ax, unit, title in zip(axes, ["m", "deg"], ["Position error", "Heading error"]):
        ax.set(xlabel="Pose index", ylabel=f"Error [{unit}]", title=title)
        ax.legend()
    savefig("08_se2_gt_errors", fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    for name in ["correct_loop", "false_loop"]:
        normalized = arrays[name+"_whitened_residuals"]
        axes[0].plot(np.linalg.norm(normalized, axis=1), "o-", label=name)
    axes[0].set(xlabel="Edge index (last = loop)", ylabel="Whitened residual norm [dimensionless]", title="Constraint tension after optimization")
    axes[0].legend()
    names = list(states)
    axes[1].bar(range(3), [metrics[n]["position_rmse_m"] for n in names], color=["gray", "seagreen", "indianred"])
    axes[1].set(xticks=range(3), xticklabels=["Odometry", "Correct loop", "False loop"], ylabel="Position RMSE [m]", title="A loop can improve or damage the map")
    savefig("09_loop_constraint_tension", fig)
    return metrics


def main():
    cfg_path = ROOT / "configs/lesson.json"
    cfg = json.loads(cfg_path.read_text())
    (ROOT / "figures").mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": .22})
    ba, gauge = run_ba(cfg["ba"], cfg["seed"])
    graph = run_graph(cfg["graph"], cfg["seed"])
    files = sorted(list((ROOT / "src").glob("*.py")) + list((ROOT / "configs").glob("*")))
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
    manifest = dict(synthetic_only=True, seed=cfg["seed"], graph_seed=cfg["seed"]+1,
                    config=cfg, source_sha256=hashes,
                    artifact_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in sorted(list((ROOT / "artifacts").glob("*/module.npz"))
                                                     + list((ROOT / "artifacts").glob("*/metrics.json"))
                                                     + list((ROOT / "figures").glob("*.png")))
                                     if p.parent.name != "tests"},
                    git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                    python=sys.version, executable=sys.executable, platform=platform.platform(),
                    dependencies={m.__name__: m.__version__ for m in [np, scipy, cv2, matplotlib]},
                    solver="SciPy TRF dense exact trust-region subproblem; not Schur BA or LM",
                    acceptance_observations={
                        "clean_reprojection_improved": ba["clean_ls"]["observation_coordinate_rmse_px"] < ba["initial"]["observation_coordinate_rmse_px"],
                        "robust_point_error_below_ls": ba["outlier_robust"]["point_rmse_m"] < ba["outlier_ls"]["point_rmse_m"],
                        "rigid_gauge_verified": gauge["rigid_transform_max_abs_px"] < 1e-9,
                        "correct_loop_improves": graph["correct_loop"]["position_rmse_m"] < graph["odometry"]["position_rmse_m"],
                        "false_loop_damages": graph["false_loop"]["position_rmse_m"] > graph["odometry"]["position_rmse_m"]})
    save_json(ROOT / "artifacts/manifest.json", manifest)
    print(json.dumps(manifest["acceptance_observations"], indent=2), flush=True)


if __name__ == "__main__":
    main()
