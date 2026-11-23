"""Reproduce arithmetic in advanced-literature.md; not SLAM validation.

Run from the repository root:
    python3 research/camera-slam-textbook/notes/advanced-verification.py

Only the adjacent advanced-verification.json is written. Python standard library
only. Expected values are transcribed from the notes, not extracted as answers
from the equations under test. Conceptual exercises are explicitly excluded.
"""

import hashlib
import json
import math
from pathlib import Path
import platform


ABS_TOL = 1e-12
REL_TOL = 1e-12


def flatten(value):
    if isinstance(value, (list, tuple)):
        return [item for child in value for item in flatten(child)]
    return [float(value)]


def shape(value):
    if isinstance(value, (list, tuple)):
        return [shape(child) for child in value]
    return None


def comparison(actual, expected):
    a, e = flatten(actual), flatten(expected)
    same_shape = shape(actual) == shape(expected)
    finite = all(math.isfinite(v) for v in a + e)
    passed = same_shape and finite and all(
        math.isclose(x, y, abs_tol=ABS_TOL, rel_tol=REL_TOL)
        for x, y in zip(a, e)
    )
    error = max((abs(x - y) for x, y in zip(a, e)), default=0.0)
    return passed, error if finite and same_shape else None


def matmul(a, b):
    return [[sum(x * y for x, y in zip(row, col)) for col in zip(*b)]
            for row in a]


def verify():
    cases = []

    def check(name, reference, inputs, equation, actual, expected, units):
        passed, error = comparison(actual, expected)
        cases.append({
            "id": name, "notes_reference": reference, "inputs": inputs,
            "equation": equation, "actual": actual, "expected": expected,
            "output_units": units, "max_absolute_error": error,
            "passed": passed,
        })

    check("parallax_small_angle", "1.2", {"baseline_m": 0.1, "depth_m": [5, 50]},
          "angle ~= baseline/depth (small-angle model)",
          [0.1 / 5, 0.1 / 50], [0.02, 0.002], "rad")

    x, y, z, f = 1.0, 2.0, 5.0, 500.0
    j_pi = [[f / z, 0, -f * x / z**2], [0, f / z, -f * y / z**2]]
    # Left perturbation, translation first: dp/dxi = [I | -[p]_x].
    dp = [[1, 0, 0, 0, z, -y], [0, 1, 0, -z, 0, x],
          [0, 0, 1, y, -x, 0]]
    j_pose = matmul(j_pi, dp)
    check("projection_jacobian", "1.6", {"point_m": [x, y, z], "f_px": f},
          "J_pi = [[f/Z,0,-f*X/Z^2],[0,f/Z,-f*Y/Z^2]]", j_pi,
          [[100, 0, -20], [0, 100, -40]], "px/m")
    check("pose_jacobian_product", "1.6", {"J_pi": j_pi, "dp_dxi": dp},
          "J_pose = J_pi [I | -[p]_x]", j_pose,
          [[100, 0, -20, -40, 520, -200], [0, 100, -40, -580, 40, 100]],
          "columns 0..2: px/m; columns 3..5: px/rad")
    for label, reference, column, step, expected in [
        ("translation_1cm", "1.6", 0, 0.01, [1, 0]),
        ("rotation_1mrad", "1.6", 5, 0.001, [-0.2, 0.1]),
        ("translation_2cm", "exercise 1", 0, 0.02, [2, 0]),
        ("rotation_2mrad", "exercise 2", 5, 0.002, [-0.4, 0.2]),
    ]:
        check(label, reference, {"column": column, "step": step},
              "first-order pixel change = J_pose[:,column]*step",
              [row[column] * step for row in j_pose], expected, "px")

    q = math.hypot(6 / 2, 8 / 2)
    check("whitening", "exercise 3", {"residual_px": [6, 8], "sigma_px": 2},
          "r_bar=r/sigma; q=norm(r_bar)", [6 / 2, 8 / 2, q], [3, 4, 5],
          "dimensionless")
    for q, reference, expected in [(10, "1.7", [0.2, 18, 50]),
                                    (5, "exercise 3", [0.4, 8, 12.5])]:
        delta = 2
        check("huber_q_" + str(q), reference, {"q": q, "delta": delta},
              "[weight=delta/q, Huber=delta*(q-delta/2), quadratic=q^2/2]",
              [delta / q, delta * (q - delta / 2), q**2 / 2], expected,
              "dimensionless")

    u, w, v, gc, gp = 6, 2, 4, -8, -4
    schur = u - w * w / v
    rhs = -gc + w * gp / v
    dc = rhs / schur
    dp_value = -(gp + w * dc) / v
    check("schur_solution", "1.8; exercise 4", {"U": u, "W_cp": w,
          "V": v, "g_c": gc, "g_p": gp},
          "S=U-W_cp^2/V; rhs=-g_c+W_cp*g_p/V; solve then back-substitute",
          [schur, rhs, dc, dp_value], [5, 6, 1.2, 0.4], "dimensionless")
    check("schur_original_equations", "1.8; exercise 4", {"delta": [dc, dp_value]},
          "H*delta+g", [u * dc + w * dp_value + gc, w * dc + v * dp_value + gp],
          [0, 0], "dimensionless")
    hp, gprior = 1 - (-1)**2 / 2, -1 - (-1) / 2 * 1
    check("marginal_prior", "1.10; exercise 7", {"H": [[2, -1], [-1, 1]],
          "g": [1, -1]}, "Schur prior; optimum=-g_prior/H_prior; variance=1/H_prior",
          [hp, gprior, -gprior / hp, 1 / hp], [0.5, -0.5, 1, 2], "dimensionless")

    a, b = [0.6, 0.3, 0.1], [0.5, 0.2, 0.3]
    l1 = sum(abs(x - y) for x, y in zip(a, b))
    check("bow_score", "1.13; exercise 6", {"a": a, "b": b},
          "[L1(a-b), 1-L1(a-b)/2]", [l1, 1 - l1 / 2], [0.4, 0.8],
          "dimensionless; score is not loop probability")
    p, t, scale = [1, 1, 1], [1, 0, 0], 2
    transformed = [scale * x + y for x, y in zip(p, t)]
    restored = [(x - y) / scale for x, y in zip(transformed, t)]
    check("sim3_identity_rotation", "1.15", {"p": p, "t": t, "s": scale},
          "p'=s*p+t; p=(p'-t)/s for R=I", [transformed, restored],
          [[3, 2, 2], [1, 1, 1]], "arbitrary consistent length units")
    check("photometric_affine", "2.2", {"I_i": 100, "I_j": 120, "b_j": 20,
          "alpha": 1, "b_i": 0}, "[(I_j-b_j)-(I_i-b_i), I_j-I_i]",
          [(120 - 20) - (100 - 0), 120 - 100], [0, 20], "intensity")
    check("photometric_gradient", "2.3; exercise 8", {"gradient": [4, 0],
          "warp_px": [0.5, 2]}, "dot(gradient,warp)", 4 * 0.5 + 0 * 2, 2, "intensity")
    check("nullspace_dimension", "2.6; exercise 9", {"views": 5, "feature_rank": 3},
          "2*views-feature_rank (rank assumed, not measured)", 2 * 5 - 3, 7,
          "residual dimensions, not pose observability rank")
    dt, acceleration, bias = 0.2, 2, 0.1
    check("constant_acceleration_1d", "2.8; exercise 10", {"dt_s": dt,
          "a_m_s2": acceleration, "bias_m_s2": bias, "initial_velocity": 0},
          "[a*dt, 0.5*a*dt^2, 0.5*bias*dt^2]",
          [acceleration * dt, 0.5 * acceleration * dt**2, 0.5 * bias * dt**2],
          [0.4, 0.04, 0.002], "[m/s,m,m]; gravity already removed")
    check("initialization_scale_1d", "2.9", {"visual_displacement": 0.5,
          "dt_s": 1, "preintegrated_displacement_m": 1},
          "[scale for known v=0, residual for (s,v)=(2,0), residual for (4,1)]",
          [1 / 0.5, 0.5 * 2 - 0 - 1, 0.5 * 4 - 1 - 1], [2, 0, 0],
          "[m/visual_unit,m,m]; no initialization algorithm tested")
    check("time_offset", "2.10", {"pixel_velocity_px_s": [80, -20], "offset_s": 0.01},
          "pixel_velocity*offset", [80 * 0.01, -20 * 0.01], [0.8, -0.2], "px")
    check("time_offset_bound", "2.10", {"pixel_velocity_px_s": [80, -20],
          "error_budget_px": 0.5}, "budget/norm(pixel_velocity)",
          0.5 / math.hypot(80, -20), 0.006063390625908324, "s")

    fused = (2 * 0.5 + 1 * -0.25) / (2 + 1)
    check("tsdf_weighted_mean", "2.14; exercise 11", {"F_old": 0.5, "W_old": 2,
          "f_obs": -0.25, "w_obs": 1, "mu_m": 0.1},
          "[weighted_mean, total_weight, mean*mu]", [fused, 2 + 1, fused * 0.1],
          [0.25, 3, 0.025], "[normalized_TSDF,weight,m]; not ESDF")
    check("zero_crossing", "2.15", {"x_m": [0, 0.1], "F": [0.2, -0.3]},
          "x0+(x1-x0)*F0/(F0-F1)", 0 + 0.1 * 0.2 / (0.2 - -0.3), 0.04, "m")
    log_hit = math.log(0.7 / 0.3)
    check("occupancy_two_hits", "2.16; exercise 12", {"prior": 0.5, "hit": 0.7,
          "independent_hits": 2}, "sigmoid(2*logit(0.7))",
          1 / (1 + math.exp(-2 * log_hit)), 49 / 58, "probability under independence assumption")
    check("clearance", "2.17; exercise 13", {"distance_m": 0.35,
          "radius_m": 0.3, "margin_m": 0.1}, "distance-radius-margin",
          0.35 - 0.3 - 0.1, -0.05, "m; not a safety certification")
    check("depth_backprojection_x", "2.12; exercise 14", {"u_px": 420,
          "cx_px": 320, "fx_px": 500, "Z_m": 2}, "X=(u-cx)*Z/fx",
          (420 - 320) * 2 / 500, 0.4, "m; optical-axis depth assumed")
    check("assignment_sums", "3.3", {"scores": [[0.9, 0.8], [0.89, 0.1]]},
          "[diagonal_sum, off_diagonal_sum]", [0.9 + 0.1, 0.8 + 0.89], [1, 1.69],
          "scores; not a SuperGlue implementation")
    probs = [0.5 * 0.8**2, 0.5 * 0.2**2]
    check("semantic_independent_fusion", "3.12", {"prior": [0.5, 0.5],
          "observation": [0.8, 0.2], "count": 2}, "normalize(prior*observation^2)",
          [x / sum(probs) for x in probs], [16 / 17, 1 / 17], "probability")
    check("resize_coordinates", "exercise 15", {"fx": 800, "cx": 640, "u": 1000,
          "scale": 0.5}, "[fx,cx,u]*scale (simple coordinate scaling convention)",
          [800 * 0.5, 640 * 0.5, 1000 * 0.5], [400, 320, 500], "px")
    elements = 2048**2
    check("score_matrix_storage", "3.9; exercise 16", {"rows": 2048, "columns": 2048,
          "bytes_per_element": 4}, "[rows*columns, elements*4, bytes/2^20]",
          [elements, elements * 4, elements * 4 / 2**20], [4194304, 16777216, 16],
          "[elements,bytes,MiB]; not measured total VRAM")
    check("gaussian_alpha_compositing", "exercise 17", {"alpha": [0.5, 0.4],
          "colors": [[1, 0, 0], [0, 0, 1]], "background": [0, 0, 0]},
          "[red contribution, green, blue contribution, remaining transmittance]",
          [0.5, 0, (1 - 0.5) * 0.4, (1 - 0.5) * (1 - 0.4)], [0.5, 0, 0.2, 0.3],
          "normalized color and transmittance; not geometry validation")
    return cases


def main():
    # A failing or malformed comparison must never be recorded as a pass.
    comparator_ok = (
        comparison([1, 2], [1, 2])[0]
        and not comparison([1, 2], [1, 3])[0]
        and not comparison([1], [1, 2])[0]
        and not comparison([[1]], [1])[0]
        and not comparison(float("nan"), 0)[0]
        and not comparison(float("inf"), float("inf"))[0]
    )
    here = Path(__file__).resolve().parent
    notes = here / "advanced-literature.md"
    cases = verify()
    passed = sum(case["passed"] for case in cases)
    result = {
        "schema_version": 1,
        "scope": "Educational equation and numeric checks only; no algorithm validation.",
        "limitations": [
            "No dataset, sensor, finite-difference Jacobian, SLAM, VIO, neural model or benchmark run.",
            "Numerical agreement does not establish physical assumptions or observability.",
            "Examples are transcribed from notes; this is not an automatic audit of all prose.",
            "Conceptual exercises 5, 18, 19, 20 are not tested; exercise 6 checks its score only.",
        ],
        "reproduce_from_repository_root": "python3 research/camera-slam-textbook/notes/advanced-verification.py",
        "dependencies": "Python 3 standard library only",
        "python_version": platform.python_version(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "notes_sha256_at_run": hashlib.sha256(notes.read_bytes()).hexdigest(),
        "absolute_tolerance": ABS_TOL,
        "relative_tolerance": REL_TOL,
        "comparator_negative_controls_passed": comparator_ok,
        "summary": {"total": len(cases), "passed": passed, "failed": len(cases) - passed},
        "all_numeric_checks_passed": comparator_ok and passed == len(cases),
        "checks": cases,
    }
    output = here / "advanced-verification.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False) + "\n",
                      encoding="utf-8")
    print(f"{passed}/{len(cases)} numeric checks passed; comparator controls: {comparator_ok}")
    print(output)
    return 0 if result["all_numeric_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
