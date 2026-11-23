"""Reproduce the original 61 arithmetic and 8 matrix checks, not experiments.

Run with Python 3 and its standard library. Results are written beside this
script; no report, shared source, dataset, or experiment output is modified.
"""

import hashlib
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path


def matvec(matrix, vector):
    return [sum(a * b for a, b in zip(row, vector)) for row in matrix]


def dot(left, right):
    return sum(a * b for a, b in zip(left, right))


def main():
    checks = []

    def check(name, expression, actual, expected, category="arithmetic"):
        tolerance = 1e-6 if category == "arithmetic" else 1e-10
        actual_values = actual if isinstance(actual, list) else [actual]
        expected_values = expected if isinstance(expected, list) else [expected]
        errors = [abs(a - b) for a, b in zip(actual_values, expected_values)]
        passed = len(actual_values) == len(expected_values) and all(
            math.isfinite(a) and math.isfinite(b) and error <= tolerance
            for a, b, error in zip(actual_values, expected_values, errors)
        )
        checks.append({
            "id": len(checks) + 1,
            "name": name,
            "category": category,
            "expression": expression,
            "actual": actual,
            "expected": expected,
            "absolute_tolerance": tolerance,
            "max_absolute_error": max(errors, default=0),
            "passed": passed,
        })

    check("N1 normalized x", "(400-320)/800", (400-320)/800, .1)
    check("N1 normalized y", "(300-240)/600", (300-240)/600, .1)
    check("N1 ray norm", "sqrt(1.02)", math.sqrt(1.02), 1.009950494)
    check("N1 unit ray x/y", ".1/sqrt(1.02)", .1/math.sqrt(1.02), .099014754)
    check("N1 unit ray z", "1/sqrt(1.02)", 1/math.sqrt(1.02), .990147543)
    check("N2 distorted u", ".2*(1-.2*.05)*500+320", .2*(1-.2*.05)*500+320, 419)
    check("N2 distorted v", ".1*.99*500+240", .1*.99*500+240, 289.5)
    check("N3 normalized x", "(190-150)/400", (190-150)/400, .1)
    check("N3 normalized y", "(130-100)/300", (130-100)/300, .1)
    check("N4 row interval s", ".02/1000", .02/1000, 20e-6)
    check("N4 displacement px", "500*20e-6*200", 500*20e-6*200, 2)
    check("N5 blur 10ms px", "500*2/10*.01", 500*2/10*.01, 1)
    check("N5 blur 2ms px", "500*2/10*.002", 500*2/10*.002, .2)
    check("N6 irradiance first", "80/(.01*.8)", 80/(.01*.8), 10000)
    check("N6 irradiance second", "160/(.02*.8)", 160/(.02*.8), 10000)
    check("N6 clipped estimate", "255/(.04*.8)", 255/(.04*.8), 7968.75)
    check("N7 RGB gray", ".299*100+.587*150+.114*200", .299*100+.587*150+.114*200, 140.75)
    check("N7 swapped gray", ".299*200+.587*150+.114*100", .299*200+.587*150+.114*100, 159.25)
    check("N8 first u", "500*2/5+320", 500*2/5+320, 520)
    check("N8 second u", "500/5+320", 500/5+320, 420)
    check("N8 scalar epipolar residual", ".2-.2", .2-.2, 0)
    check("N9 plane shift px", "500*(-.2)", 500*(-.2), -100)
    check("N9 other depth shift px", "500*(-1/10)", 500*(-1/10), -50)
    check("N10 centroid distance", "hypot(1,1)", math.hypot(1,1), math.sqrt(2))
    check("N11 five-point trials", "ceil(log(.01)/log(1-.5**5))", math.ceil(math.log(.01)/math.log(1-.5**5)), 146)
    check("N11 eight-point trials", "ceil(log(.01)/log(1-.5**8))", math.ceil(math.log(.01)/math.log(1-.5**8)), 1177)
    check("N12 Sampson squared px", "2**2/2", 2**2/2, 2)
    check("N13 depth m", "1/(.4-.2)", 1/(.4-.2), 5)
    check("N14 angle rad", "atan(.2/10)", math.atan(.2/10), .019997334)
    check("N14 near angle deg", "degrees(atan(.2/10))", math.degrees(math.atan(.2/10)), 1.145763)
    check("N14 far angle deg", "degrees(atan(.2/100))", math.degrees(math.atan(.2/100)), .114591)
    check("N16 corrected depth m", "500*.2/(25-5)", 500*.2/(25-5), 5)
    check("N16 wrong depth m", "500*.2/25", 500*.2/25, 4)
    check("N16 right reprojection px", "500*(.5-.2)/5+315", 500*(.5-.2)/5+315, 345)
    check("N17 near sigma m", "100*.5/20**2", 100*.5/20**2, .125)
    check("N17 far sigma m", "100*.5/10**2", 100*.5/10**2, .5)
    check("N18 exact du px", "500/5.01-100", 500/5.01-100, -.199600798)
    check("N18 exact dv px", "250/5.01-50", 250/5.01-50, -.099800399)
    check("N20 solution du px", "(2*3-0)/3", (2*3-0)/3, 2)
    check("N20 solution dv px", "(-3+0)/3", (-3+0)/3, -1)
    check("N20 normal equation row1", "2*2-1", 2*2-1, 3)
    check("N20 normal equation row2", "2-2", 2-2, 0)
    check("N22 coarse displacement px", "24/2**3", 24/2**3, 3)
    check("N22 original patch width px", "7*2**3", 7*2**3, 56)
    check("Exercise1 reprojection u", "400*.8/8+300", 400*.8/8+300, 340)
    check("Exercise1 reprojection v", "500*(-.8)/8+200", 500*(-.8)/8+200, 150)
    check("Exercise2 distorted u", ".3*.975*600", .3*.975*600, 175.5)
    check("Exercise2 distorted v", ".4*.975*600", .4*.975*600, 234)
    check("Exercise3 line distance px", "(3*20+4*12-100)/5", (3*20+4*12-100)/5, 1.6)
    check("Exercise4 RANSAC trials", "ceil(log(.01)/log(1-.6**5))", math.ceil(math.log(.01)/math.log(1-.6**5)), 57)
    check("Exercise6 corrected depth m", "600*.3/(40-10)", 600*.3/(40-10), 6)
    check("Exercise6 wrong depth m", "600*.3/40", 600*.3/40, 4.5)
    check("Exercise6 relative error", "(4.5-6)/6", (4.5-6)/6, -.25)
    check("Exercise7 reprojection u", "500*1/5+320", 500*1/5+320, 420)
    check("Exercise8 G11", "2**2+1**2+3**2", 2**2+1**2+3**2, 14)
    check("Exercise9 blur px", "150*.008", 150*.008, 1.2)
    check("Exercise11 range m", "sqrt(34)", math.sqrt(34), 5.830951895)
    check("Exercise11 range-based X m", "5*.6/sqrt(1.36)", 5*.6/math.sqrt(1.36), 2.572478777)
    check("Exercise11 range-based Z m", "5/sqrt(1.36)", 5/math.sqrt(1.36), 4.287464629)
    check("Exercise12 first irradiance", "60/.005", 60/.005, 12000)
    check("Exercise12 second irradiance", "120/.010", 120/.010, 12000)

    essential = [[0,0,0], [0,0,1], [0,-1,0]]
    q1, q2 = [.4,.2,1], [.2,.2,1]
    check("N8 matrix epipolar residual", "q2^T E q1", dot(q2, matvec(essential, q1)), 0, "matrix")
    check("N8 K projection", "K q1; K=[[500,0,320],[0,500,240],[0,0,1]]", matvec([[500,0,320],[0,500,240],[0,0,1]], q1), [520,340,1], "matrix")
    check("N9 normalized homography", "Hn q1; Hn=[[1,0,-.2],[0,1,0],[0,0,1]]", matvec([[1,0,-.2],[0,1,0],[0,0,1]], q1), q2, "matrix")
    check("N9 pixel homography", "Hp*[520,340,1]; Hp=[[1,0,-100],[0,1,0],[0,0,1]]", matvec([[1,0,-100],[0,1,0],[0,0,1]], [520,340,1]), [420,340,1], "matrix")
    check("N20 LK residual", "A*[2,-1]; A=[[1,0],[0,1],[1,1]]", matvec([[1,0],[0,1],[1,1]], [2,-1]), [2,-1,1], "matrix")
    check("N21 eigenvalue3", "G*[1,1]; G=[[2,1],[1,2]]", matvec([[2,1],[1,2]], [1,1]), [3,3], "matrix")
    check("N21 eigenvalue1", "G*[1,-1]; G=[[2,1],[1,2]]", matvec([[2,1],[1,2]], [1,-1]), [1,-1], "matrix")
    check("Exercise8 unobserved vertical motion", "A*[2,99]; A=[[2,0],[1,0],[3,0]]", matvec([[2,0],[1,0],[3,0]], [2,99]), [4,2,6], "matrix")

    counts = {kind: sum(c["category"] == kind for c in checks)
              for kind in ("arithmetic", "matrix")}
    passed = counts == {"arithmetic": 61, "matrix": 8} and all(
        c["passed"] for c in checks
    )
    script = Path(__file__).resolve()
    output = script.with_suffix(".json")
    result = {
        "schema_version": 1,
        "provenance": "Python rerun of the original Node.js checks; not an original-session log",
        "scope": "Synthetic arithmetic and matrix checks only; no dataset or solver experiments",
        "source_note": "geometry-literature.md",
        "script": script.name,
        "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "command_from_repo_root": "python3 research/camera-slam-textbook/notes/geometry-verification.py",
        "relative_tolerance": 0,
        "counts": counts,
        "total": len(checks),
        "passed": sum(c["passed"] for c in checks),
        "status": "passed" if passed else "failed",
        "checks": checks,
    }
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"{result['status']}: {result['passed']}/{len(checks)} checks; {output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
