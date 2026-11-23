"""Synthetic stereo joint BA and planar pose graph; no dataset frontend."""

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


def rotation(rvec):
    return cv2.Rodrigues(np.asarray(rvec, dtype=float))[0]


def centers(poses):
    return np.array([-rotation(p[:3]).T @ p[3:] for p in poses])


def project(poses, points, K, baseline):
    """Return [camera, side(L=0/R=1), point, uv] in pixels."""
    result = np.empty((len(poses), 2, len(points), 2))
    for i, pose in enumerate(poses):
        for side in range(2):
            t = pose[3:] - np.array([side * baseline, 0.0, 0.0])
            result[i, side] = cv2.projectPoints(
                points, pose[:3], t, K, None
            )[0].reshape(-1, 2)
    return result


def depths(poses, points):
    return np.array([(points @ rotation(p[:3]).T + p[3:])[:, 2]
                     for p in poses])


def make_ba(cfg, seed):
    rng = np.random.default_rng(seed)
    n, m = cfg["cameras"], cfg["points"]
    K = np.array([[cfg["fx_px"], 0, cfg["cx_px"]],
                  [0, cfg["fy_px"], cfg["cy_px"]], [0, 0, 1.]])
    poses = np.zeros((n, 6))
    for i in range(n):
        poses[i, :3] = [0.008 * i, -0.025 * i, 0.006 * i]
        C = np.array([0.30 * i, 0.035 * np.sin(i), 0.025 * i])
        poses[i, 3:] = -rotation(poses[i, :3]) @ C
    points = rng.uniform([-1.3, -1.0, 4.5], [1.7, 1.0, 8.0], (m, 3))
    truth = project(poses, points, K, cfg["baseline_m"])
    observations = truth + rng.normal(0, cfg["noise_px"], truth.shape)
    corrupt = observations.copy()
    mask = np.zeros(truth.shape[:-1], dtype=bool)
    indices = rng.choice(mask.size, round(mask.size * cfg["outlier_fraction"]),
                         replace=False)
    mask.flat[indices] = True
    corrupt[mask] += rng.normal(0, cfg["outlier_sigma_px"], (mask.sum(), 2))
    initial_poses = poses.copy()
    initial_poses[1:, :3] += rng.normal(
        0, cfg["initial_rotation_sigma_rad"], (n - 1, 3))
    initial_poses[1:, 3:] += rng.normal(
        0, cfg["initial_translation_sigma_m"], (n - 1, 3))
    initial_points = points + rng.normal(0, cfg["initial_point_sigma_m"], points.shape)
    return dict(K=K, poses_gt=poses, points_gt=points, truth=truth,
                observations=observations, corrupt=corrupt, outlier_mask=mask,
                initial_poses=initial_poses, initial_points=initial_points)


class JointBA:
    """World-to-left-camera Rodrigues + translation, then world XYZ points."""

    def __init__(self, observations, K, baseline, first_pose, anchored=True):
        self.observations = observations
        self.K, self.baseline = K, baseline
        self.first_pose = np.array(first_pose, copy=True)
        self.n, _, self.m, _ = observations.shape
        self.start = int(anchored)
        self.pose_size = (self.n - self.start) * 6

    def pack(self, poses, points):
        return np.r_[poses[self.start:].ravel(), points.ravel()]

    def unpack(self, x):
        variable = x[:self.pose_size].reshape(-1, 6)
        poses = np.vstack([self.first_pose, variable]) if self.start else variable
        return poses, x[self.pose_size:].reshape(self.m, 3)

    def residual(self, x):
        poses, points = self.unpack(x)
        return (project(poses, points, self.K, self.baseline)
                - self.observations).ravel()

    def jacobian(self, x):
        poses, points = self.unpack(x)
        J = np.zeros((self.observations.size, len(x)))
        for i, pose in enumerate(poses):
            R = rotation(pose[:3])
            for side in range(2):
                t = pose[3:] - [side * self.baseline, 0, 0]
                _, cv_jac = cv2.projectPoints(points, pose[:3], t, self.K, None)
                row = (i * 2 + side) * self.m * 2
                if i >= self.start:
                    col = (i - self.start) * 6
                    J[row:row + self.m * 2, col:col + 6] = cv_jac[:, :6]
                # Chain pinhole derivative with world-to-camera rotation.
                camera_points = points @ R.T + t
                for j, (X, Y, Z) in enumerate(camera_points):
                    D = np.array([[self.K[0, 0] / Z, 0, -self.K[0, 0] * X / Z**2],
                                  [0, self.K[1, 1] / Z, -self.K[1, 1] * Y / Z**2]])
                    col = self.pose_size + 3 * j
                    J[row + 2*j:row + 2*j + 2, col:col + 3] = D @ R
        return J

    def solve(self, x0, cfg, loss="linear", numerical=False):
        return least_squares(self.residual, x0,
                             jac="3-point" if numerical else self.jacobian,
                             method="trf", tr_solver="exact", x_scale="jac",
                             loss=loss, f_scale=cfg["robust_f_scale_px"],
                             max_nfev=cfg["max_nfev"],
                             ftol=1e-10, xtol=1e-10, gtol=1e-9)


def gauge_transform(poses, points, Q, d):
    transformed = poses.copy()
    for i, p in enumerate(poses):
        Rnew = rotation(p[:3]) @ Q.T
        transformed[i, :3] = Rotation.from_matrix(Rnew).as_rotvec()
        transformed[i, 3:] = p[3:] - Rnew @ d
    return transformed, points @ Q.T + d


def ba_errors(poses, points, data):
    position = np.linalg.norm(centers(poses) - centers(data["poses_gt"]), axis=1)
    angular = np.array([Rotation.from_matrix(rotation(p[:3]) @ rotation(g[:3]).T)
                        .magnitude() for p, g in zip(poses, data["poses_gt"])])
    point = np.linalg.norm(points - data["points_gt"], axis=1)
    # Exclude the exactly anchored camera from the camera RMSE denominator.
    return dict(camera_center_rmse_m=float(np.sqrt(np.mean(position[1:]**2))),
                camera_rotation_rmse_deg=float(np.rad2deg(np.sqrt(np.mean(angular[1:]**2)))),
                point_rmse_m=float(np.sqrt(np.mean(point**2))))


def wrap(angle):
    return np.arctan2(np.sin(angle), np.cos(angle))


def rot2(theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])


def relative(a, b):
    return np.r_[rot2(a[2]).T @ (b[:2] - a[:2]), wrap(b[2] - a[2])]


def compose(a, z):
    return np.r_[a[:2] + rot2(a[2]) @ z[:2], wrap(a[2] + z[2])]


def make_graph(cfg, seed):
    rng = np.random.default_rng(seed)
    angle = np.linspace(0, 2*np.pi, cfg["nodes"])
    r = cfg["radius_m"]
    truth = np.c_[r*np.sin(angle), r*(1-np.cos(angle)), wrap(angle)]
    truth[-1] = truth[0]
    edges = np.c_[np.arange(len(truth)-1), np.arange(1, len(truth))]
    measurements = np.array([relative(truth[i], truth[j]) for i, j in edges])
    sigma = np.array([cfg["odometry_translation_sigma_m"]]*2
                     + [cfg["odometry_rotation_sigma_rad"]])
    measurements += rng.normal(0, sigma, measurements.shape)
    measurements[:, 2] = wrap(measurements[:, 2] + cfg["odometry_rotation_bias_rad"])
    initial = np.zeros_like(truth)
    for k, z in enumerate(measurements):
        initial[k+1] = compose(initial[k], z)
    return dict(poses_gt=truth, initial=initial, odometry_edges=edges,
                odometry_measurements=measurements, odometry_sigma=sigma)


class PoseGraph:
    """SE(2) relative-coordinate residual (not the full Lie logarithm)."""

    def __init__(self, edges, measurements, sigmas, first_pose):
        self.edges = np.asarray(edges, dtype=int)
        self.measurements = np.asarray(measurements)
        self.sigmas = np.broadcast_to(sigmas, self.measurements.shape).copy()
        self.first_pose = np.array(first_pose, copy=True)

    def unpack(self, x):
        return np.vstack([self.first_pose, x.reshape(-1, 3)])

    def raw_residual(self, poses):
        predicted = np.array([relative(poses[i], poses[j]) for i, j in self.edges])
        residual = predicted - self.measurements
        residual[:, 2] = wrap(residual[:, 2])
        return residual

    def residual(self, x):
        return (self.raw_residual(self.unpack(x)) / self.sigmas).ravel()

    def solve(self, initial, cfg):
        return least_squares(self.residual, initial[1:].ravel(), jac="3-point",
                             method="trf", x_scale="jac", loss="linear",
                             max_nfev=cfg["max_nfev"],
                             ftol=1e-10, xtol=1e-10, gtol=1e-9)


def graph_cases(data, cfg):
    edges = data["odometry_edges"]
    z = data["odometry_measurements"]
    sigma = np.tile(data["odometry_sigma"], (len(edges), 1))
    result = {"odometry": PoseGraph(edges, z, sigma, data["poses_gt"][0])}
    # End-to-start direction is explicit; correct closure is exact synthetic GT.
    loop_edge = [len(data["poses_gt"])-1, 0]
    correct = relative(data["poses_gt"][-1], data["poses_gt"][0])
    false = np.r_[cfg["false_loop_translation_m"], cfg["false_loop_rotation_rad"]]
    for name, loop in [("correct_loop", correct), ("false_loop", false)]:
        result[name] = PoseGraph(np.vstack([edges, loop_edge]), np.vstack([z, loop]),
                                np.vstack([sigma, [cfg["loop_translation_sigma_m"]]*2
                                           + [cfg["loop_rotation_sigma_rad"]]]),
                                data["poses_gt"][0])
    return result


def solver_info(result):
    return dict(success=bool(result.success), status=int(result.status),
                message=str(result.message), cost=float(result.cost),
                optimality=float(result.optimality), nfev=int(result.nfev),
                njev=int(result.njev), finite=bool(np.isfinite(result.x).all()))
