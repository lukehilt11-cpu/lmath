"""
linalg.py — matrices and vectors, computed exactly (fractions and radicals).

Type a matrix as  [[1,2],[3,4]]  or  1 2; 3 4.   Two inputs are separated by |.
"""
import re

import sympy as sp

from .. import parse as P
from ..errors import MathError, UsageError
from ..fmt import approx, box, mstr, show
from ..registry import command
from .algebra import mstr_matrix


def parse_matrix(ctx, text, label="matrix"):
    t = (text or "").strip()
    if not t:
        if not ctx.interactive:
            raise UsageError(f"I need a {label}. Type it like  [[1,2],[3,4]]  or  1 2; 3 4")
        rows = []
        print(f"  Enter the {label} one row at a time (numbers separated by spaces). Blank line to finish.")
        while True:
            r = ctx.ask(f"row {len(rows) + 1}")
            if not r:
                break
            rows.append(r)
        t = "; ".join(rows)
    if t.startswith("["):
        inner = re.findall(r"\[([^\[\]]*)\]", t)
        if len(inner) > 1 or t.startswith("[["):
            rows = [[x for x in re.split(r"[,\s]+", r.strip()) if x] for r in inner]
        else:
            rows = [[x for x in re.split(r"[,\s]+", inner[0].strip()) if x]]
    else:
        rows = [[x for x in re.split(r"[,\s]+", r.strip()) if x] for r in t.split(";") if r.strip()]
    if not rows or not rows[0]:
        raise MathError("I couldn't read that matrix.")
    if len({len(r) for r in rows}) != 1:
        raise MathError("Every row of a matrix needs the same number of entries.")
    return sp.Matrix([[ctx.number(x, "entry") for x in r] for r in rows])


def parse_vec(ctx, text, label="vector"):
    t = (text or "").strip().strip("[]()<>")
    if not t:
        t = ctx.ask(label)
    return sp.Matrix([ctx.number(x, "entry") for x in re.split(r"[,\s]+", t.strip("[]()<> ")) if x])


def _vec_str(v):
    return "[" + ", ".join(mstr(x) for x in v) + "]"


def _two(a, what):
    parts = a.parts("|;") if a.rest else []
    if len(parts) != 2:
        raise UsageError(f"Give two {what} separated by |   e.g.  dot 1 2 3 | 4 5 6")
    return parts


@command("minfo", "Linear Algebra", "minfo <matrix>", "Shape, rank, trace, determinant, and more.", aliases=("info", "matrix"),
         examples=("minfo [[1,2],[3,4]]", "minfo 2 0; 0 3"))
def minfo(ctx, a):
    M = parse_matrix(ctx, a.rest)
    lines = [mstr_matrix(M), "", f"Shape: {M.rows} × {M.cols}", f"Rank:  {M.rank()}"]
    if M.is_square:
        d = M.det()
        lines += [f"Trace: {mstr(M.trace())}", f"Det:   {show(d)}", f"Invertible: {'yes' if d != 0 else 'no (singular)'}",
                  f"Symmetric: {'yes' if M == M.T else 'no'}"]
    box("Matrix info", lines)


@command("det", "Linear Algebra", "det <matrix>", "Determinant (exact).", examples=("det [[1,2],[3,4]]", "det 2 0 1; 1 3 2; 0 1 1"))
def det(ctx, a):
    M = parse_matrix(ctx, a.rest)
    if not M.is_square:
        raise MathError("The determinant needs a square matrix.")
    lines = [mstr_matrix(M), ""]
    if M.rows == 2:
        p, q, r, s_ = M[0, 0], M[0, 1], M[1, 0], M[1, 1]
        lines.append(f"det = ad − bc = ({mstr(p)})({mstr(s_)}) − ({mstr(q)})({mstr(r)})")
    lines.append(f"det = {show(M.det())}")
    box("Determinant", lines)


@command("inv", "Linear Algebra", "inv <matrix>", "Inverse of a square matrix (exact fractions).", aliases=("inverse",),
         examples=("inv [[4,7],[2,6]]", "inv 1 2 3; 0 1 4; 5 6 0"))
def inv(ctx, a):
    M = parse_matrix(ctx, a.rest)
    if not M.is_square:
        raise MathError("Only square matrices have inverses.")
    d = M.det()
    if d == 0:
        box("Inverse", ["The determinant is 0, so this matrix is singular — no inverse exists."])
        return
    lines = [f"det = {show(d)}"]
    if M.rows == 2:
        lines += ["For [[a,b],[c,d]]:  A⁻¹ = 1/(ad − bc) · [[d, −b], [−c, a]]"]
    lines += ["", "A⁻¹ =", mstr_matrix(M.inv())]
    box("Inverse", lines)


@command("rref", "Linear Algebra", "rref <matrix>", "Reduced row echelon form.", examples=("rref 1 2 3; 4 5 6; 7 8 10",))
def rref(ctx, a):
    M = parse_matrix(ctx, a.rest)
    R, piv = M.rref()
    box("Reduced row echelon form", [mstr_matrix(R), "", f"Pivot columns: {', '.join(str(p + 1) for p in piv)}", f"Rank = {len(piv)}"])


@command("eig", "Linear Algebra", "eig <matrix>", "Eigenvalues and eigenvectors (exact).", aliases=("eigenvalues",),
         examples=("eig [[2,1],[1,2]]", "eig 4 1; 2 3"))
def eig(ctx, a):
    M = parse_matrix(ctx, a.rest)
    if not M.is_square:
        raise MathError("Eigenvalues need a square matrix.")
    lines = []
    try:
        for val, mult, vecs in M.eigenvects():
            lines.append(f"λ = {show(sp.simplify(val))}   (multiplicity {mult})")
            for v in vecs:
                lines.append("    eigenvector " + _vec_str(sp.simplify(v)))
    except (NotImplementedError, sp.PolynomialError):
        for val, mult in M.eigenvals().items():
            lines.append(f"λ ≈ {approx(val)}   (multiplicity {mult})")
    lines += ["", f"Characteristic polynomial: {mstr(sp.factor(M.charpoly(sp.Symbol('λ')).as_expr()))}"]
    box("Eigenvalues & eigenvectors", lines)


@command("charpoly", "Linear Algebra", "charpoly <matrix>", "Characteristic polynomial.", aliases=("char_poly",), examples=("charpoly [[2,1],[1,2]]",))
def charpoly(ctx, a):
    M = parse_matrix(ctx, a.rest)
    if not M.is_square:
        raise MathError("The characteristic polynomial needs a square matrix.")
    cp = M.charpoly(sp.Symbol("λ")).as_expr()
    box("Characteristic polynomial", [f"det(A − λI) = {mstr(cp)}", f"factored: {mstr(sp.factor(cp))}"])


@command("svd", "Linear Algebra", "svd <matrix>", "Singular values (and the decomposition when numpy is available).", examples=("svd [[3,0],[0,4]]",))
def svd(ctx, a):
    M = parse_matrix(ctx, a.rest)
    try:
        import numpy as np
        U, S, Vt = np.linalg.svd(np.array(M.tolist(), dtype=float))
        fm = lambda A: "\n".join("  [ " + "  ".join(f"{v: .5f}" for v in row) + " ]" for row in A)
        box("SVD", ["Singular values: " + ", ".join(f"{v:.6g}" for v in S), "", "U =", fm(U), "", "Vᵀ =", fm(Vt)])
    except ImportError:
        vals = M.singular_values()
        box("SVD", ["Singular values: " + ", ".join(show(sp.simplify(v)) for v in vals)])


@command("lu", "Linear Algebra", "lu <matrix>", "LU decomposition (exact), with row swaps P if needed.", examples=("lu [[2,1],[4,3]]",))
def lu(ctx, a):
    M = parse_matrix(ctx, a.rest)
    if not M.is_square:
        raise MathError("LU decomposition needs a square matrix.")
    L, U, perm = M.LUdecomposition()
    Pm = sp.eye(M.rows)
    for i, j in perm:
        Pm.row_swap(i, j)
    box("LU decomposition (P·A = L·U)", ["P =", mstr_matrix(Pm), "", "L =", mstr_matrix(L), "", "U =", mstr_matrix(U)])


@command("qr", "Linear Algebra", "qr <matrix>", "QR decomposition (exact, via Gram–Schmidt).", examples=("qr [[1,1],[1,0],[0,1]]",))
def qr(ctx, a):
    M = parse_matrix(ctx, a.rest)
    Q, R = M.QRdecomposition()
    box("QR decomposition", ["Q =", mstr_matrix(Q.applyfunc(sp.simplify)), "", "R =", mstr_matrix(R.applyfunc(sp.simplify))])


@command("lstsq", "Linear Algebra", "lstsq <A> | <b>", "Least-squares solution of Ax ≈ b (exact).", aliases=("least_squares",),
         examples=("lstsq [[1,1],[1,2],[1,3]] | 1 2 2",))
def lstsq(ctx, a):
    pa, pb = _two(a, "inputs (matrix | vector)")
    A, b = parse_matrix(ctx, pa), parse_vec(ctx, pb)
    if A.rows != b.rows:
        raise MathError("A and b need the same number of rows.")
    x = (A.T * A).inv() * A.T * b if (A.T * A).det() != 0 else None
    if x is None:
        raise MathError("AᵀA is singular — the columns of A aren't independent.")
    res = (A * x - b)
    box("Least squares", ["x = (AᵀA)⁻¹Aᵀb", "x = " + _vec_str(x.applyfunc(sp.simplify)), f"‖Ax − b‖ = {show(sp.simplify(res.norm()))}"])


@command("dot", "Linear Algebra", "dot <u> | <v>", "Dot product, plus the angle between the vectors.", examples=("dot 1 2 3 | 4 5 6",))
def dot(ctx, a):
    pu, pv = _two(a, "vectors")
    u, v = parse_vec(ctx, pu, "u"), parse_vec(ctx, pv, "v")
    if len(u) != len(v):
        raise MathError("The vectors need the same number of entries.")
    d = u.dot(v)
    lines = [f"u · v = " + " + ".join(f"({mstr(x)})({mstr(y)})" for x, y in zip(u, v)) + f" = {mstr(d)}"]
    if u.norm() != 0 and v.norm() != 0:
        c = sp.simplify(d / (u.norm() * v.norm()))
        th = sp.simplify(sp.acos(c) * 180 / sp.pi)
        lines.append(f"cos θ = {show(c)}  →  θ = {mstr(th) if th.is_Rational else '≈ ' + approx(th)}°")
        lines.append("The vectors are " + ("perpendicular (orthogonal)." if d == 0 else "not perpendicular."))
    box("Dot product", lines)


@command("cross", "Linear Algebra", "cross <u> | <v>", "Cross product of two 3-D vectors.", examples=("cross 1 2 3 | 4 5 6",))
def cross(ctx, a):
    pu, pv = _two(a, "vectors")
    u, v = parse_vec(ctx, pu, "u"), parse_vec(ctx, pv, "v")
    if len(u) != 3 or len(v) != 3:
        raise MathError("The cross product needs two 3-D vectors.")
    c = u.cross(v)
    box("Cross product", [f"u × v = {_vec_str(c)}", f"|u × v| = {show(sp.simplify(c.norm()))}  (area of the parallelogram)"])


@command("norm", "Linear Algebra", "norm <vector> [order]", "Length of a vector (order 2 by default; 1 or inf also work).", examples=("norm 3 4", "norm 1 -2 2 order=1"))
def norm(ctx, a):
    kw = a.kw("order")
    v = parse_vec(ctx, a.rest)
    o = kw.get("order", "2")
    n = sp.oo if o in ("inf", "oo") else ctx.number(o, "order")
    box(f"‖v‖_{o}", [show(sp.simplify(v.norm(n)))])


@command("proj", "Linear Algebra", "proj <u> | <v>", "Projection of u onto v.", aliases=("project",), examples=("proj 3 4 | 1 0",))
def proj(ctx, a):
    pu, pv = _two(a, "vectors")
    u, v = parse_vec(ctx, pu, "u"), parse_vec(ctx, pv, "v")
    if v.norm() == 0:
        raise MathError("Can't project onto the zero vector.")
    sc = u.dot(v) / v.dot(v)
    box("Projection of u onto v", ["proj = (u·v / v·v) v", f"scalar = {mstr(sc)}", f"proj = {_vec_str(sc * v)}"])


@command("gs", "Linear Algebra", "gs <v1> | <v2> | …", "Gram–Schmidt orthogonalization (exact).", aliases=("gram_schmidt",),
         examples=("gs 1 1 0 | 1 0 1 | 0 1 1",))
def gs(ctx, a):
    parts = a.parts("|;")
    if len(parts) < 2:
        raise UsageError("Give two or more vectors separated by |")
    vecs = [parse_vec(ctx, p) for p in parts]
    ortho = sp.GramSchmidt(vecs, False)
    box("Gram–Schmidt", ["Orthogonal vectors:"] + [f"  {_vec_str(v.applyfunc(sp.simplify))}" for v in ortho] +
        ["", "Orthonormal:"] + [f"  {_vec_str(v.applyfunc(lambda t: sp.radsimp(sp.simplify(t / sp.sqrt(sum(q ** 2 for q in v))))))}" for v in ortho])


@command("mul", "Linear Algebra", "mul <A> | <B>", "Multiply two matrices.", aliases=("matmul",), examples=("mul [[1,2],[3,4]] | [[0,1],[1,0]]",))
def mul(ctx, a):
    pa, pb = _two(a, "matrices")
    A, B = parse_matrix(ctx, pa), parse_matrix(ctx, pb)
    if A.cols != B.rows:
        raise MathError(f"Can't multiply: A has {A.cols} columns but B has {B.rows} rows.")
    box("Matrix product A·B", [mstr_matrix(A * B)])


@command("transpose", "Linear Algebra", "transpose <matrix>", "Transpose of a matrix.", examples=("transpose 1 2 3; 4 5 6",))
def transpose(ctx, a):
    box("Transpose", [mstr_matrix(parse_matrix(ctx, a.rest).T)])
