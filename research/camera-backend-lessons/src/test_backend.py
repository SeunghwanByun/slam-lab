"""Executable contracts and fixed-seed observations, not universal guarantees."""

import hashlib
import io
import json
from pathlib import Path
import unittest

import numpy as np
from scipy.spatial.transform import Rotation

from backend import (JointBA, compose, depths, gauge_transform, graph_cases,
                     make_ba, make_graph, project, relative, rotation, wrap)


ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "configs/lesson.json").read_text())


class GeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = make_ba(CFG["ba"], CFG["seed"])
        cls.model = JointBA(cls.data["observations"], cls.data["K"],
                            CFG["ba"]["baseline_m"], cls.data["poses_gt"][0])

    def test_projection_worked_example(self):
        K = np.array([[520., 0, 320], [0, 520, 240], [0, 0, 1]])
        uv = project(np.zeros((1, 6)), np.array([[1., .5, 5.]]), K, .24)
        np.testing.assert_allclose(uv[0, 0, 0], [424, 292], atol=1e-12)
        np.testing.assert_allclose(uv[0, 1, 0], [399.04, 292], atol=1e-12)
        disparity = uv[0, 0, 0, 0] - uv[0, 1, 0, 0]
        self.assertAlmostEqual(520*.24/disparity, 5.)

    def test_finite_positive_visible_projection(self):
        d = self.data
        self.assertTrue(np.isfinite(d["truth"]).all())
        self.assertGreater(depths(d["poses_gt"], d["points_gt"]).min(), 0)
        for coordinate, size in [(0, 640), (1, 480)]:
            self.assertGreater(d["truth"][..., coordinate].min(), 0)
            self.assertLess(d["truth"][..., coordinate].max(), size)
        for p, gt in zip(d["poses_gt"], d["truth"]):
            camera = d["points_gt"] @ rotation(p[:3]).T + p[3:]
            pinhole = camera[:, :2] / camera[:, 2, None] * [520, 520] + [320, 240]
            np.testing.assert_allclose(gt[0], pinhole, atol=1e-10)

    def test_joint_analytic_jacobian_all_columns(self):
        m, d = self.model, self.data
        x = m.pack(d["initial_poses"], d["initial_points"])
        J = m.jacobian(x)
        numeric = np.empty_like(J)
        step = 1e-6
        for j in range(len(x)):
            delta = np.zeros_like(x)
            delta[j] = step
            numeric[:, j] = (m.residual(x+delta)-m.residual(x-delta))/(2*step)
        np.testing.assert_allclose(J, numeric, rtol=2e-5, atol=2e-6)
        self.assertGreater(np.linalg.norm(J[:, :m.pose_size]), 0)
        self.assertGreater(np.linalg.norm(J[:, m.pose_size:]), 0)

    def test_numerical_solver_matches_analytic_small_problem(self):
        cfg = dict(CFG["ba"], points=10, cameras=3)
        d = make_ba(cfg, CFG["seed"])
        m = JointBA(d["observations"], d["K"], cfg["baseline_m"], d["poses_gt"][0])
        x = m.pack(d["initial_poses"], d["initial_points"])
        analytic, numerical = m.solve(x, cfg), m.solve(x, cfg, numerical=True)
        self.assertTrue(analytic.success and numerical.success)
        self.assertAlmostEqual(analytic.cost, numerical.cost, places=7)
        np.testing.assert_allclose(analytic.x, numerical.x, rtol=2e-4, atol=2e-5)

    def test_gauge_rigid_and_scale(self):
        d = self.data
        for axis in np.eye(3):
            for Q, shift in [(np.eye(3), axis), (Rotation.from_rotvec(.2*axis).as_matrix(), np.zeros(3))]:
                p, X = gauge_transform(d["poses_gt"], d["points_gt"], Q, shift)
                np.testing.assert_allclose(project(p, X, d["K"], .24), d["truth"], atol=1e-10)
        p = d["poses_gt"].copy()
        p[:, 3:] *= 1.5
        changed = project(p, d["points_gt"]*1.5, d["K"], .24)-d["truth"]
        np.testing.assert_allclose(changed[:, 0], 0, atol=1e-10)
        self.assertGreater(np.max(np.abs(changed[:, 1])), 1.)

    def test_anchor_and_svd_nullities(self):
        d, m = self.data, self.model
        x = m.pack(d["initial_poses"], d["initial_points"])
        x += .001
        np.testing.assert_array_equal(m.unpack(x)[0][0], d["poses_gt"][0])
        for anchored, expected in [(True, 0), (False, 6)]:
            m = JointBA(d["observations"], d["K"], .24, d["poses_gt"][0], anchored)
            s = np.linalg.svd(m.jacobian(m.pack(d["poses_gt"], d["points_gt"])), compute_uv=False)
            self.assertEqual(int(np.sum(s < s[0]*1e-10)), expected)

    def test_seed_reproducibility(self):
        other = make_ba(CFG["ba"], CFG["seed"])
        for key in self.data:
            np.testing.assert_array_equal(self.data[key], other[key])

    def test_exercise_parameter_count_and_robust_influence(self):
        self.assertEqual(6*(4-1)+3*36, 126)
        self.assertEqual(4*2*36*2, 576)
        self.assertEqual(self.model.pack(self.data["poses_gt"], self.data["points_gt"]).size, 126)
        r, C = 12., 1.2
        cost = C*C*(np.sqrt(1+(r/C)**2)-1)
        influence = r/np.sqrt(1+(r/C)**2)
        self.assertAlmostEqual(cost, 13.03182089441408)
        self.assertAlmostEqual(influence, 1.194044628251987)
        self.assertLess(cost, .5*r*r)


class GraphTests(unittest.TestCase):
    def test_se2_worked_example_and_inverse(self):
        a, b = np.array([1., 2., np.pi/2]), np.array([1., 3., np.pi/2+.1])
        np.testing.assert_allclose(relative(a, b), [1, 0, .1], atol=1e-12)
        np.testing.assert_allclose(compose(a, relative(a, b)), b, atol=1e-12)
        self.assertAlmostEqual(wrap(np.deg2rad(-358)), np.deg2rad(2))

    def test_loop_direction_truth_and_anchor(self):
        data = make_graph(CFG["graph"], CFG["seed"]+1)
        cases = graph_cases(data, CFG["graph"])
        truth = data["poses_gt"]
        np.testing.assert_array_equal(cases["correct_loop"].edges[-1], [24, 0])
        np.testing.assert_allclose(cases["correct_loop"].raw_residual(truth)[-1], 0, atol=1e-12)
        np.testing.assert_allclose(cases["false_loop"].raw_residual(truth)[-1], [-2, 1.5, -.45], atol=1e-12)
        np.testing.assert_allclose(cases["odometry"].raw_residual(data["initial"]), 0, atol=1e-12)
        for model in cases.values():
            np.testing.assert_array_equal(model.unpack(data["initial"][1:].ravel()+.01)[0], truth[0])
            self.assertTrue(np.all(model.sigmas > 0))

    def test_whitening_worked_example(self):
        error = np.array([.04, -.08, .012])
        sigma = np.array([.04, .04, .012])
        np.testing.assert_allclose(error/sigma, [1, -2, 1])
        self.assertAlmostEqual(.5*np.sum((error/sigma)**2), 3.)


class ArtifactTests(unittest.TestCase):
    def test_all_arrays_finite_and_anchors_unchanged(self):
        for module in ["ba", "gauge", "pose_graph"]:
            with np.load(ROOT / f"artifacts/{module}/module.npz", allow_pickle=False) as data:
                for key in data.files:
                    self.assertTrue(np.isfinite(data[key]).all(), (module, key))
                if module == "ba":
                    for name in ["clean_ls", "outlier_ls", "outlier_robust"]:
                        p, X = data[name+"_poses"], data[name+"_points"]
                        np.testing.assert_array_equal(p[0], data["poses_gt"][0])
                        self.assertGreater(depths(p, X).min(), 0)
                        self.assertGreater(np.linalg.norm(p[1:]-data["initial_poses"][1:]), 1e-4)
                        self.assertGreater(np.linalg.norm(X-data["initial_points"]), 1e-4)
                if module == "pose_graph":
                    for name in ["odometry", "correct_loop", "false_loop"]:
                        np.testing.assert_array_equal(data[name+"_poses"][0], data["poses_gt"][0])

    def test_fixed_seed_outcomes_not_general_guarantees(self):
        ba = json.loads((ROOT / "artifacts/ba/metrics.json").read_text())
        graph = json.loads((ROOT / "artifacts/pose_graph/metrics.json").read_text())
        for name in ["clean_ls", "outlier_ls", "outlier_robust"]:
            self.assertTrue(ba[name]["solver"]["success"])
            self.assertLess(ba[name]["solver"]["cost"], ba[name]["initial_objective"])
        self.assertLess(ba["clean_ls"]["observation_coordinate_rmse_px"], 1.)
        for key in ["point_rmse_m", "camera_center_rmse_m", "camera_rotation_rmse_deg"]:
            self.assertLess(ba["clean_ls"][key], ba["initial"][key])
            self.assertLess(ba["outlier_robust"][key], ba["outlier_ls"][key])
        for name in ["odometry", "correct_loop", "false_loop"]:
            self.assertTrue(graph[name]["solver"]["success"])
        self.assertLess(graph["correct_loop"]["position_rmse_m"], graph["odometry"]["position_rmse_m"])
        self.assertGreater(graph["false_loop"]["position_rmse_m"], graph["odometry"]["position_rmse_m"])

    def test_manifest_hashes_and_nine_figures(self):
        manifest = json.loads((ROOT / "artifacts/manifest.json").read_text())
        expected = {str(p.relative_to(ROOT)) for p in list((ROOT / "src").glob("*.py"))
                    + list((ROOT / "configs").glob("*")) if p.is_file()}
        self.assertEqual(set(manifest["source_sha256"]), expected)
        for name, digest in manifest["source_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
        for name, digest in manifest["artifact_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
        figures = list((ROOT / "figures").glob("*.png"))
        self.assertEqual(len(figures), 9)
        for figure in figures:
            self.assertGreater(figure.stat().st_size, 10000)

    def test_remaining_lesson_arithmetic(self):
        K = np.array([[520., 0, 320], [0, 520, 240], [0, 0, 1]])
        uv = project(np.zeros((1, 6)), np.array([[2., 1., 10.]]), K, .24)
        np.testing.assert_allclose(uv[0, :, 0, 0], [424., 411.52], atol=1e-12)
        residual = np.array([424., 292.]) - [424.6, 291.4]
        np.testing.assert_allclose(residual, [-.6, .6], atol=1e-12)
        self.assertAlmostEqual(.5*np.sum(residual**2), .36)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    text = stream.getvalue()
    print(text)
    folder = ROOT / "artifacts/tests"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "results.txt").write_text(text)
    (folder / "metrics.json").write_text(json.dumps({"run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "successful": result.wasSuccessful()}, indent=2)+"\n")
    raise SystemExit(not result.wasSuccessful())
