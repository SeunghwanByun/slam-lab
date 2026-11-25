"""Small synthetic teaching experiments, not a production SLAM estimator."""
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy import linalg, optimize, special, stats

BASE = Path(__file__).resolve().parents[1]
CFG = json.loads((BASE / "configs/experiment.json").read_text())
plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": .25})


def savefig(fig, name):
    (BASE / "figures").mkdir(exist_ok=True)
    fig.set_size_inches(CFG["figure_width_inches"], fig.get_figheight())
    fig.tight_layout()
    fig.savefig(BASE / "figures" / (name + ".png"), dpi=CFG["dpi"])
    plt.close(fig)


def save(chapter, arrays, metrics):
    path = BASE / "artifacts" / chapter
    path.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path / "arrays.npz", **arrays)
    (path / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False))


def huber_location(y, delta=1., steps=100):
    x = float(np.median(y))
    for _ in range(steps):
        r = np.asarray(y) - x
        w = np.minimum(1., delta / np.maximum(np.abs(r), 1e-15))
        xn = float(w @ y / w.sum())
        if abs(xn-x) < 1e-12:
            return xn
        x = xn
    return x


def em_fixed_variance(y, means=(-2., 2.), iterations=40):
    means = np.array(means, dtype=float)
    weights = np.array([.5, .5])
    history = []
    for _ in range(iterations):
        logp = np.log(weights)[None, :] + stats.norm.logpdf(y[:, None], means, .7)
        norm = special.logsumexp(logp, axis=1)
        history.append(float(norm.sum()))
        resp = np.exp(logp - norm[:, None])
        count = resp.sum(axis=0)
        weights = count / len(y)
        means = resp.T @ y / count
    return means, weights, np.array(history)


def kf(z, F, H, Q, R, m0, P0):
    m, P = m0.copy(), P0.copy()
    means, covs, predm, predp, nis = [], [], [], [], []
    for measurement in z:
        m = F @ m
        P = F @ P @ F.T + Q
        predm.append(m.copy()); predp.append(P.copy())
        nu = measurement - H @ m
        S = H @ P @ H.T + R
        K = linalg.solve(S, H @ P, assume_a="pos").T
        m = m + K @ np.atleast_1d(nu)
        A = np.eye(len(m)) - K @ H
        P = A @ P @ A.T + K @ R @ K.T
        means.append(m.copy()); covs.append(P.copy())
        nis.append(float(nu @ linalg.solve(S, nu, assume_a="pos")))
    return tuple(np.array(v) for v in (means, covs, predm, predp, nis))


def rts(means, covs, predm, predp, F):
    sm, sp = means.copy(), covs.copy()
    for t in range(len(means)-2, -1, -1):
        C = linalg.solve(predp[t+1], F @ covs[t], assume_a="pos").T
        sm[t] += C @ (sm[t+1] - predm[t+1])
        sp[t] += C @ (sp[t+1] - predp[t+1]) @ C.T
    return sm, sp


def d5(rng):
    qs, _ = linalg.qr(rng.normal(size=(30, 2)), mode="economic")
    v, _ = linalg.qr(rng.normal(size=(2, 2)))
    truth = np.array([1., -2.])
    ks = np.logspace(1, 10, 37)
    errors = {key: [] for key in ("normal", "qr", "svd")}
    failed = []
    for k in ks:
        A = qs @ np.diag([1., 1/k]) @ v.T
        b = A @ truth
        for key in errors:
            try:
                if key == "normal":
                    x = np.linalg.solve(A.T @ A, A.T @ b)
                elif key == "qr":
                    q, r = linalg.qr(A, mode="economic")
                    x = linalg.solve_triangular(r, q.T @ b)
                else:
                    x = linalg.lstsq(A, b, lapack_driver="gelsd")[0]
                err = np.linalg.norm(x-truth) / np.linalg.norm(truth)
            except np.linalg.LinAlgError:
                err = np.nan; failed.append(float(k))
            errors[key].append(err)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for key, values in errors.items(): ax.loglog(ks, values, label=key)
    ax.set(xlabel="condition number (dimensionless)", ylabel="relative solution error", title="Same noiseless problem; float64 solvers")
    ax.legend(); savefig(fig, "d5_condition")
    B = np.array([[1., 1.], [0., 1.]])
    angle = np.linspace(0, 2*np.pi, 300)
    circle = np.array([np.cos(angle), np.sin(angle)])
    fig, axs = plt.subplots(1, 2, figsize=(7, 3.5))
    for ax, data, title in zip(axs, [circle, B @ circle], ["coordinate unit circle", "physical B @ coordinate"]):
        ax.plot(*data); ax.set_aspect("equal"); ax.set(xlim=(-2,2), ylim=(-2,2), title=title, xlabel="axis 1 (m)", ylabel="axis 2 (m)")
    savefig(fig, "d5_basis")
    points = rng.multivariate_normal([0,0], [[4,1.5],[1.5,1]], size=400)
    eig, vec = linalg.eigh(np.cov(points.T))
    bad = np.vstack([points, np.repeat([[12.,-12.]], 25, axis=0)])
    _, vecbad = linalg.eigh(np.cov(bad.T))
    fig, ax = plt.subplots(figsize=(7,4.5))
    ax.scatter(*points.T, s=8, alpha=.4, label="inliers"); ax.scatter(*bad[-25:].T, marker="x", label="25 repeated outliers")
    for vv,label in [(vec[:, -1], "PCA clean"),(vecbad[:,-1], "PCA contaminated")]:
        ax.plot([-8*vv[0],8*vv[0]], [-8*vv[1],8*vv[1]], label=label)
    ax.set(xlabel="x (m)", ylabel="y (m)", title="Variance direction is not a robust geometric direction"); ax.legend()
    savefig(fig, "d5_pca")
    save("d5", {"condition":ks, **errors, "points":points, "contaminated":bad}, {"normal_singular_conditions":failed,"pca_eigenvalues":eig.tolist(),"basis_gram":(B.T@B).tolist(),"max_qr_relative_error":float(np.nanmax(errors['qr']))})


def d6():
    hs = np.logspace(-16,-1,100)
    exact = np.cos(1.)
    fwd = np.abs((np.sin(1+hs)-np.sin(1))/hs-exact)
    central = np.abs((np.sin(1+hs)-np.sin(1-hs))/(2*hs)-exact)
    complex_error = np.abs(np.imag(np.sin(1+1j*hs))/hs-exact)
    fig, ax = plt.subplots(figsize=(7,4.5))
    for y,label in [(fwd,"forward"),(central,"central"),(complex_error,"complex step")]:
        ax.loglog(hs,np.maximum(y,1e-18),label=label)
    ax.set(xlabel="step h (dimensionless)",ylabel="absolute derivative error",title="sin(x), x=1; zeros displayed at 1e-18")
    ax.legend(); savefig(fig,"d6_derivatives")
    # The paths are teaching iterations, not SciPy's internal solver trace.
    def residual(x): return np.array([10*(x[1]-x[0]**2), 1-x[0]])
    def jac(x): return np.array([[-20*x[0],10],[-1,0]])
    paths = {}
    for method in ["gradient", "GN", "damped"]:
        x=np.array([-1.2,1.]); path=[x.copy()]
        for _ in range(120 if method=="gradient" else 15):
            r=residual(x); J=jac(x)
            if method=="gradient": dx=-.001*(J.T@r)
            elif method=="GN": dx=linalg.lstsq(J,-r)[0]
            else:
                lam=1.
                for _ in range(15):
                    dx=linalg.solve(J.T@J+lam*np.eye(2),-J.T@r,assume_a="pos")
                    if np.linalg.norm(residual(x+dx)) < np.linalg.norm(r): break
                    lam*=10
            x=x+dx; path.append(x.copy())
        paths[method]=np.array(path)
    xx,yy=np.meshgrid(np.linspace(-1.6,1.6,180),np.linspace(-.8,2,180))
    cost=.5*(100*(yy-xx**2)**2+(1-xx)**2)
    fig,ax=plt.subplots(figsize=(7,4.5))
    ax.contour(xx,yy,cost,levels=[.01,.1,1,5,20,100,300],colors=".65")
    for key,path in paths.items(): ax.plot(*path.T,".-",label=key,markersize=3)
    ax.set(xlabel="x (dimensionless)",ylabel="y (dimensionless)",title="Nonlinear residual: a full GN step can increase cost"); ax.legend()
    savefig(fig,"d6_optimization")
    J=np.zeros((8,6))
    for i in range(5): J[i,i:i+2]=[-1,1]
    J[5,0]=1; J[6,[1,4]]=[-1,1]; J[7,[2,5]]=[-1,1]
    fig,axs=plt.subplots(1,2,figsize=(7,3.5))
    axs[0].spy(J,markersize=9);axs[0].set(title="Jacobian J (8 x 6)",xlabel="state column",ylabel="residual row")
    axs[1].spy(J.T@J,markersize=9);axs[1].set(title="J.T @ J (6 x 6)",xlabel="state column",ylabel="state row")
    savefig(fig,"d6_sparsity")
    save("d6",{"h":hs,"forward":fwd,"central":central,"complex":complex_error,"J":J,**paths},{"best_forward_h":float(hs[np.argmin(fwd)]),"best_central_h":float(hs[np.argmin(central)]),"GN_initial_cost":float(.5*sum(residual(paths['GN'][0])**2)),"GN_first_cost":float(.5*sum(residual(paths['GN'][1])**2)),"scipy_solution":optimize.least_squares(residual,[-1.2,1],jac=jac).x.tolist()})


def d7(rng):
    y=np.r_[rng.normal(0,.25,80),np.full(20,4.)]
    counts=np.arange(0,81,4)
    estimates=np.array([[np.mean(np.r_[y[:80],np.full(n,4.)]),huber_location(np.r_[y[:80],np.full(n,4.)],.5)] for n in counts])
    fig,axs=plt.subplots(1,2,figsize=(7,3.6))
    axs[0].hist(y,bins=25);axs[0].axvline(np.mean(y),color="C1",label="mean");axs[0].axvline(huber_location(y,.5),color="C2",label="Huber");axs[0].set(xlabel="measurement (m)",ylabel="count",title="80 inliers + 20 outliers");axs[0].legend()
    for i,label in enumerate(["mean","Huber delta=.5 m"]):axs[1].plot(counts/(80+counts),estimates[:,i],label=label)
    axs[1].set(xlabel="outlier fraction",ylabel="estimate (m)",title="Robust does not mean immune");axs[1].legend(fontsize=8)
    savefig(fig,"d7_robust")
    rho=CFG["correlation"]; cov=np.array([[1.,rho],[rho,1.]])
    pairs=rng.multivariate_normal([0,0],cov,size=CFG["correlation_trials"])
    averages=pairs.mean(axis=1)
    fig,axs=plt.subplots(1,2,figsize=(7,3.6))
    axs[0].scatter(*pairs[:1000].T,s=3,alpha=.3);axs[0].set(xlabel="sensor 1 error (m)",ylabel="sensor 2 error (m)",title="Shared noise: rho=0.9")
    grid=np.linspace(-3,3,300);axs[1].hist(averages,bins=50,density=True,alpha=.4,label="Monte Carlo")
    axs[1].plot(grid,stats.norm.pdf(grid,scale=np.sqrt(.5)),label="assumed independent")
    axs[1].plot(grid,stats.norm.pdf(grid,scale=np.sqrt((1+rho)/2)),label="correct covariance")
    axs[1].set(xlabel="average error (m)",ylabel="density (1/m)",title="Same mean; different uncertainty");axs[1].legend(fontsize=8)
    savefig(fig,"d7_correlation")
    mixture=np.r_[rng.normal(-2,.7,180),rng.normal(2,.7,120)]
    means,weights,ll=em_fixed_variance(mixture)
    same,_,same_ll=em_fixed_variance(mixture,(0,0))
    fig,axs=plt.subplots(1,2,figsize=(7,3.6))
    grid=np.linspace(-5,5,400);axs[0].hist(mixture,bins=35,density=True,alpha=.4)
    axs[0].plot(grid,sum(w*stats.norm.pdf(grid,m,.7) for m,w in zip(means,weights)),label="separated initialization")
    axs[0].plot(grid,stats.norm.pdf(grid,same[0],.7),label="symmetric failure");axs[0].set(xlabel="x (m)",ylabel="density (1/m)",title="Fixed variance Gaussian mixture");axs[0].legend(fontsize=7)
    axs[1].plot(ll,label="separated");axs[1].plot(same_ll,label="symmetric");axs[1].set(xlabel="iteration",ylabel="log likelihood",title="Monotonic is not globally optimal");axs[1].legend()
    savefig(fig,"d7_em")
    save("d7",{"observations":y,"counts":counts,"estimates":estimates,"pairs":pairs,"mixture":mixture,"log_likelihood":ll,"symmetric_ll":same_ll},{"mean_m":float(y.mean()),"huber_m":huber_location(y,.5),"empirical_average_variance_m2":float(np.var(averages)),"correct_variance_m2":.95,"naive_variance_m2":.5,"em_means":means.tolist(),"em_weights":weights.tolist(),"em_symmetric_means":same.tolist()})


def d8(rng):
    dt=CFG["dt_seconds"];F=np.array([[1.,dt],[0.,1.]])
    H=np.array([[1.,0.]]); G=np.array([[dt*dt/2],[dt]])
    Q=CFG["acceleration_sigma"]**2*(G@G.T);R=np.array([[CFG["position_sigma"]**2]])
    m0=np.array([0.,1.]);P0=np.diag([1.,.25]);n=CFG["steps"];mc=CFG["trials"]
    truths=np.empty((mc,n,2));observations=np.empty((mc,n,1))
    for j in range(mc):
        x=rng.multivariate_normal(m0,P0)
        for t in range(n):
            x=F@x+G[:,0]*rng.normal(0,CFG["acceleration_sigma"])
            truths[j,t]=x;observations[j,t]=H@x+rng.normal(0,CFG["position_sigma"])
    results={}
    for label,scale in [("matched",1.),("underreported",CFG["underreported_R_factor"])]:
        est=[]; nis=[]; nees=[]
        for j in range(mc):
            means,covs,pm,pp,ni=kf(observations[j],F,H,Q,R*scale,m0,P0)
            err=truths[j]-means
            ne=np.array([e@linalg.solve(p,e,assume_a="pos") for e,p in zip(err,covs)])
            est.append(means);nis.append(ni);nees.append(ne)
        results[label] = {"means":np.array(est),"covs":covs,"nis":np.array(nis),"nees":np.array(nees)}
    fig,axs=plt.subplots(2,1,figsize=(7,5.3),sharex=True)
    for ax,label in zip(axs,results):
        out=results[label]; err=out["means"][0,:,0]-truths[0,:,0];sigma=np.sqrt(out["covs"][:,0,0])
        ax.plot(err,label="position error");ax.fill_between(np.arange(n),-2*sigma,2*sigma,alpha=.25,label="reported +/-2 sigma");ax.set(ylabel="error (m)",title=label);ax.legend(fontsize=8)
    axs[-1].set_xlabel("step (1 s)");savefig(fig,"d8_kf_bands")
    fig,axs=plt.subplots(1,2,figsize=(7,3.6))
    for ax,key,df in [(axs[0],"nis",1),(axs[1],"nees",2)]:
        for label,out in results.items():ax.plot(out[key].mean(axis=0),label=label)
        low,high=stats.chi2.ppf([.025,.975],mc*df)/mc
        ax.axhspan(low,high,color="gray",alpha=.25,label="95% ensemble interval")
        ax.set(xlabel="step (1 s)",ylabel="ensemble mean (dimensionless)",title=key.upper());ax.legend(fontsize=7)
    savefig(fig,"d8_consistency")
    means,covs,pm,pp,_=kf(observations[0],F,H,Q,R,m0,P0)
    sm,sp=rts(means,covs,pm,pp,F)
    fig,ax=plt.subplots(figsize=(7,4.2))
    ax.plot(means[:,0]-truths[0,:,0],label="filter error");ax.plot(sm[:,0]-truths[0,:,0],label="smoother error")
    ax.plot(np.sqrt(covs[:,0,0]),"--",label="filter sigma");ax.plot(np.sqrt(sp[:,0,0]),"--",label="smoother sigma")
    ax.set(xlabel="step (1 s)",ylabel="position (m)",title="Future measurements change past estimates");ax.legend()
    savefig(fig,"d8_smoothing")
    sigma=.8;u=rng.normal(0,sigma,100000);trans=u*u
    fig,ax=plt.subplots(figsize=(7,4.2))
    ax.hist(trans,bins=100,density=True,alpha=.45,label="x^2, x~N(0,0.64)")
    ax.axvline(0,color="C1",label="EKF mean=0, var=0")
    ax.axvline(sigma*sigma,color="C2",label="UT mean=0.64, var=0.8192")
    ax.set(xlim=(0,4),xlabel="squared position (m^2)",ylabel="density (1/m^2)",title="A Gaussian moment summary loses shape");ax.legend()
    savefig(fig,"d8_unscented")
    S=np.array([[4.,1.2],[1.2,1.]])
    e,v=linalg.eigh(S);theta=np.linspace(0,2*np.pi,200)
    ellipse=v@np.diag(np.sqrt(e*stats.chi2.ppf(.95,2)))@np.array([np.cos(theta),np.sin(theta)])
    candidates=np.array([[2.,0.],[0.,2.],[4.,1.],[1.,.5]])
    ds=np.einsum("ni,ij,nj->n",candidates,linalg.inv(S),candidates)
    fig,ax=plt.subplots(figsize=(7,4.2));ax.plot(*ellipse,label="95% chi-square gate, df=2")
    ax.scatter(*candidates.T,c=np.where(ds<stats.chi2.ppf(.95,2),"C2","C3"))
    for i,p in enumerate(candidates):ax.annotate(f"{i}: d2={ds[i]:.2f}",p,xytext=(5,5),textcoords="offset points")
    ax.set(xlabel="innovation axis 1 (m)",ylabel="innovation axis 2 (m)",title="Gating tests plausibility, not identity");ax.legend()
    savefig(fig,"d8_gating")
    metrics={label:{"nis_mean":float(out["nis"].mean()),"nees_mean":float(out["nees"].mean()),"position_rmse_m":float(np.sqrt(np.mean((out["means"][:,:,0]-truths[:,:,0])**2)))} for label,out in results.items()}
    metrics.update({"sigma_point_mean_m2":sigma**2,"sigma_point_variance_m4":2*sigma**4,"monte_carlo_square_mean_m2":float(trans.mean()),"monte_carlo_square_variance_m4":float(trans.var()),"gate_d2":ds.tolist(),"nis_ensemble95":(stats.chi2.ppf([.025,.975],mc)/mc).tolist(),"nees_ensemble95":(stats.chi2.ppf([.025,.975],2*mc)/mc).tolist()})
    arrays={"truth":truths,"observations":observations,"smooth_mean":sm,"smooth_cov":sp,"F":F,"H":H,"Q":Q,"R":R}
    for label,out in results.items():arrays.update({label+"_"+key:value for key,value in out.items()})
    save("d8",arrays,metrics)


def main():
    start=time.perf_counter()
    rng=np.random.default_rng(CFG["seed"])
    d5(rng);d6();d7(rng);d8(rng)
    paths=list((BASE/"src").glob("*.py"))+list((BASE/"configs").glob("*.json"))+list((BASE/"artifacts").glob("d*/arrays.npz"))
    hashes={str(p.relative_to(BASE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    provenance={"seed":CFG["seed"],"synthetic_only":True,"versions":{"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__,"matplotlib":matplotlib.__version__},"commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"runtime_seconds":time.perf_counter()-start,"sha256":hashes}
    (BASE/"artifacts/provenance.json").write_text(json.dumps(provenance,indent=2))
    print(json.dumps(provenance,indent=2))


if __name__ == "__main__":main()
