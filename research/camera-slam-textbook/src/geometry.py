"""T_ab maps b to a. Column vectors; points are stored as N x 3 rows."""
import numpy as np


def pose(R=None, t=None):
    T = np.eye(4)
    if R is not None:
        T[:3, :3] = R
    if t is not None:
        T[:3, 3] = np.asarray(t).reshape(3)
    return T


def inverse(T):
    return pose(T[:3, :3].T, -T[:3, :3].T @ T[:3, 3])


def transform(T, X):
    return X @ T[:3, :3].T + T[:3, 3]


def project(K, X):
    q = X @ K.T
    return q[:, :2] / q[:, 2, None]


def accumulate(previous, current_from_previous):
    return previous @ inverse(current_from_previous)


def similarity(a, b):
    ac, bc = a - a.mean(0), b - b.mean(0)
    variance = np.mean(np.sum(ac * ac, axis=1))
    if variance < 1e-12:
        raise ValueError('Cannot align a stationary trajectory')
    U, s, Vt = np.linalg.svd(bc.T @ ac / len(a))
    signs = np.ones(3)
    signs[-1] = np.linalg.det(U @ Vt)
    R = U @ np.diag(signs) @ Vt
    scale = float(s @ signs / variance)
    return scale, R, b.mean(0) - scale * R @ a.mean(0)


def align_poses(poses, target_positions):
    s, R, t = similarity(poses[:, :3, 3], target_positions)
    aligned = poses.copy()
    aligned[:, :3, :3] = R @ poses[:, :3, :3]
    aligned[:, :3, 3] = s * (poses[:, :3, 3] @ R.T) + t
    return aligned, s, R, t
