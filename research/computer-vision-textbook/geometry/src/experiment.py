"""Independent teaching experiments; not a production geometry backend."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import time
import cv2
import numpy as np
import scipy
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
CFG = json.loads((BASE / 'configs/experiment.json').read_text())
plt.rcParams.update({'font.size': 10, 'axes.grid': True, 'figure.figsize': (7, 4.7)})

def homogeneous(x):
    return np.column_stack([x, np.ones(len(x))])

def project(P, X):
    h = homogeneous(X) @ P.T
    return h[:, :2] / h[:, 2:3]

def normalize(x):
    c = x.mean(axis=0)
    s = np.sqrt(2) / np.linalg.norm(x-c, axis=1).mean()
    T = np.array([[s, 0, -s*c[0]], [0, s, -s*c[1]], [0, 0, 1.]])
    return (homogeneous(x) @ T.T)[:, :2], T

def eight_point(a, b, normalized=True):
    if normalized:
        a, T = normalize(a)
        b, U = normalize(b)
    else:
        T = U = np.eye(3)
    A = np.einsum('ni,nj->nij', homogeneous(b), homogeneous(a)).reshape(-1, 9)
    # An 8x9 matrix needs the ninth right singular vector, absent in reduced SVD.
    _, s, vt = np.linalg.svd(A, full_matrices=True)
    F = vt[-1].reshape(3, 3)
    u, d, v = np.linalg.svd(F)
    d[-1] = 0
    F = U.T @ (u @ np.diag(d) @ v) @ T
    return F / np.linalg.norm(F), s, A

def sampson(F, a, b):
    x, y = homogeneous(a), homogeneous(b)
    fx, fty = x @ F.T, y @ F
    r = np.sum(y * fx, axis=1)
    return r*r / (np.sum(fx[:, :2]**2, axis=1) + np.sum(fty[:, :2]**2, axis=1))

def vconstraint(H, i, j):
    a, b = H[:, i], H[:, j]
    return np.array([a[0]*b[0], a[0]*b[1]+a[1]*b[0], a[1]*b[1],
                     a[2]*b[0]+a[0]*b[2], a[2]*b[1]+a[1]*b[2], a[2]*b[2]])

def path_cost(C, p1, p2):
    L = np.empty_like(C)
    L[0] = C[0]
    for i in range(1, len(C)):
        prev = L[i-1]
        low = prev.min()
        left = np.r_[np.inf, prev[:-1]] + p1
        right = np.r_[prev[1:], np.inf] + p1
        L[i] = C[i] + np.minimum.reduce([prev, left, right, np.full(len(prev), low+p2)]) - low
    return L

def savefig(name):
    plt.tight_layout()
    plt.savefig(BASE / 'figures' / f'{name}.png', dpi=CFG['dpi'])
    plt.close()

def output(module, arrays, metrics):
    p = BASE / 'artifacts' / module
    p.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(p / 'arrays.npz', **arrays)
    (p / 'metrics.json').write_text(json.dumps(metrics, indent=2))

def projective(rng):
    H = np.array([[1.2, .35, .2], [.15, 1., .1], [.18, .12, 1.]])
    fig, axs = plt.subplots(1, 2, figsize=(7, 3.8))
    for a in np.linspace(0, 4, 9):
        for pts in [np.array([[a, 0], [a, 4]]), np.array([[0, a], [4, a]])]:
            q = homogeneous(pts) @ H.T
            q = q[:, :2] / q[:, 2:]
            axs[0].plot(*pts.T, color='#246b86')
            axs[1].plot(*q.T, color='#b94c45')
    for ax, title in zip(axs, ['Metric plane', 'Projective image']):
        ax.set(title=title, xlabel='x (arbitrary units)', ylabel='y (arbitrary units)', aspect='equal')
    savefig('d13_01_projective_grid')
    K = np.array([[700., 0, 320], [0, 720, 240], [0, 0, 1]])
    obj = np.zeros((54, 3), np.float32)
    obj[:, :2] = np.mgrid[0:9, 0:6].T.reshape(-1, 2) * .04
    allsv, errors, estimates = [], [], []
    for mode in ['tilted', 'frontoparallel']:
        V, images = [], []
        for i in range(8):
            rv = np.array([.10+.05*i, -.3+.08*i, .03*i]) if mode == 'tilted' else np.array([0., 0., .03*i])
            R = cv2.Rodrigues(rv)[0]
            t = np.array([-.13+.02*i, -.1, 1.+.05*i])
            hh = K @ np.column_stack([R[:, :2], t])
            V.extend([vconstraint(hh, 0, 1), vconstraint(hh, 0, 0)-vconstraint(hh, 1, 1)])
            im = cv2.projectPoints(obj, rv, t, K, None)[0].reshape(-1, 2)
            images.append((im + rng.normal(0, .15, im.shape)).astype(np.float32))
        V = np.array(V)
        V /= np.linalg.norm(V, axis=1)[:, None]
        sv = np.linalg.svd(V, compute_uv=False)
        allsv.append(sv)
        flags = cv2.CALIB_FIX_K1 | cv2.CALIB_FIX_K2 | cv2.CALIB_FIX_K3 | cv2.CALIB_ZERO_TANGENT_DIST
        rms, kk, *_ = cv2.calibrateCamera([obj]*8, images, (640,480), None, None, flags=flags)
        errors.append(float(rms)); estimates.append(kk.tolist())
    plt.semilogy(np.arange(1,7), np.maximum(np.array(allsv).T,1e-18), 'o-')
    plt.xlabel('Singular-value index'); plt.ylabel('Row-normalized constraint singular value')
    plt.legend(['Tilted boards', 'Frontoparallel boards']); plt.title('Calibration: more images do not ensure observability')
    savefig('d13_02_calibration_degeneracy')
    x = np.linspace(-.8,.8,200)
    plt.plot(x, x, label='Ideal x'); plt.plot(x, x*(1-.25*x*x), label='k1=-0.25')
    plt.xlabel('Normalized x (unitless)'); plt.ylabel('Distorted x (unitless)'); plt.legend()
    plt.title('Radial distortion on y=0; synthetic camera')
    savefig('d13_03_distortion')
    output('projective', {'H':H, 'K':K, 'constraint_singular_values':allsv},
           {'calibration_rms_px':errors, 'estimated_K':estimates, 'modes':['tilted','frontoparallel']})

def multiview(rng):
    n, f, b = CFG['points'], CFG['focal_px'], CFG['baseline_m']
    K = np.array([[f,0,620],[0,f,180],[0,0,1.]])
    X = rng.uniform([-3,-1,4],[3,1,30],(n,3))
    R = cv2.Rodrigues(np.array([.01,.04,-.02]))[0]
    P = K @ np.column_stack([np.eye(3), np.zeros(3)])
    Q = K @ np.column_stack([R,np.array([-b,.01,.02])])
    a0, b0 = project(P,X), project(Q,X)
    a, bb = a0+rng.normal(0,.5,a0.shape), b0+rng.normal(0,.5,b0.shape)
    vals, cond = [], []
    for normal in [False, True]:
        F,s,_ = eight_point(a,bb,normal)
        vals.append(np.sqrt(sampson(F,a0,b0))); cond.append(float(s[0]/s[-1]))
    plt.boxplot(vals, tick_labels=['Raw pixel coordinates','Normalized coordinates'])
    plt.ylabel('Sampson distance on noiseless observations (px)'); plt.title('Eight-point fit: identical noisy correspondences')
    savefig('d14_01_normalization')
    baselines = np.array([.02,.05,.1,.2,.54,1.])
    depth_errors=[]; reproj=[]
    for base in baselines:
        qq=K @ np.column_stack([np.eye(3),[-base,0,0]])
        yy=project(qq,X)+rng.normal(0,.5,(n,2))
        xx=project(P,X)+rng.normal(0,.5,(n,2))
        h=cv2.triangulatePoints(P,qq,xx.T,yy.T); rec=(h[:3]/h[3]).T
        depth_errors.append(float(np.median(np.abs(rec[:,2]-X[:,2]))))
        reproj.append(float(np.median(np.linalg.norm(project(P,rec)-xx,axis=1))))
    fig,axs=plt.subplots(1,2,figsize=(7,3.8))
    axs[0].loglog(baselines,depth_errors,'o-'); axs[1].semilogx(baselines,reproj,'o-',color='#b94c45')
    for ax in axs: ax.set_xlabel('Baseline (m)')
    axs[0].set_ylabel('Median depth error (m)'); axs[1].set_ylabel('Median reprojection residual (px)')
    savefig('d14_02_parallax_failure')
    zz=np.array([5.,20.,80.]); samples=rng.normal(0,.5,(3,30000))+f*b/zz[:,None]
    depths=f*b/samples; inv=samples/(f*b)
    fig,axs=plt.subplots(1,2,figsize=(7,3.8))
    for i,z in enumerate(zz):
        axs[0].hist(depths[i],bins=100,range=(0,120),density=True,histtype='step',label=f'Z={z:g} m')
        axs[1].hist(inv[i]-1/z,bins=80,density=True,histtype='step',label=f'Z={z:g} m')
    axs[0].set(xlabel='Estimated Z (m)',ylabel='Density (1/m)'); axs[1].set(xlabel='Inverse-depth error (1/m)',ylabel='Density (m)'); axs[0].legend()
    axs[1].xaxis.set_major_locator(MaxNLocator(3))
    savefig('d14_03_inverse_depth')
    output('multiview', {'X':X,'a':a,'b':bb,'P':P,'Q':Q,'baselines':baselines,'depth_errors':depth_errors,'reprojection':reproj},
           {'condition_raw_normalized':cond,'sampson_median_px':[float(np.median(v)) for v in vals],
            'baseline_m':baselines.tolist(),'depth_error_m':depth_errors,'reprojection_px':reproj})

def stereo(rng):
    width,D=160,24
    gt=np.full(width,5); gt[60:100]=14
    C=(np.arange(D)[None,:]-gt[:,None])**2*.25+rng.uniform(0,3,(width,D))
    C[28:48]=rng.uniform(0,3,(20,D)); C[66:72,5]=0
    estimates=[]
    for p2 in [0,4,40]:
        S=path_cost(C,min(1,p2),p2)+path_cost(C[::-1],min(1,p2),p2)[::-1]-C
        estimates.append(np.argmin(S,axis=1))
    plt.imshow(C.T,origin='lower',aspect='auto',cmap='magma',vmax=25)
    plt.plot(gt,color='cyan',label='True disparity'); plt.xlabel('Scanline x (px)'); plt.ylabel('Disparity (px)')
    plt.colorbar(label='Synthetic unary cost (arbitrary units)'); plt.legend(); savefig('d15_01_cost_volume')
    for est,p2 in zip(estimates,[0,4,40]): plt.plot(est,label=f'P2={p2}',alpha=.8)
    plt.plot(gt,'k--',label='Truth'); plt.xlabel('Scanline x (px)'); plt.ylabel('Disparity (px)'); plt.legend(ncol=2)
    plt.title('Toy two-path aggregation: textureless gap and edge'); savefig('d15_02_penalty_ablation')
    pair=[ROOT/f'data/kitti/dataset/sequences/00/image_{i}/000000.png' for i in [0,1]]
    left,right=[cv2.imread(str(p),cv2.IMREAD_GRAYSCALE) for p in pair]
    if left is None or right is None: raise FileNotFoundError(pair)
    block=CFG['stereo_block']
    matcher=cv2.StereoSGBM_create(minDisparity=0,numDisparities=CFG['stereo_disparities'],blockSize=block,
        P1=8*block*block,P2=32*block*block,uniquenessRatio=10,speckleWindowSize=100,speckleRange=2,disp12MaxDiff=1)
    disparity=matcher.compute(left,right).astype(float)/16
    fig,axs=plt.subplots(2,1,figsize=(7,5.2))
    axs[0].imshow(left,cmap='gray'); axs[0].set_title('KITTI 00 frame 000000, left grayscale')
    im=axs[1].imshow(np.ma.masked_less_equal(disparity,0),cmap='turbo',vmin=0,vmax=96)
    axs[1].set_title('OpenCV StereoSGBM; masked invalid values')
    for ax in axs: ax.set(xlabel='u (px)',ylabel='v (px)')
    fig.colorbar(im,ax=axs[1],label='Disparity (px)',shrink=.8); savefig('d15_03_kitti_disparity')
    output('stereo',{'cost':C,'gt':gt,'estimates':estimates,'kitti_disparity':disparity},
           {'toy_mae_px':[float(np.mean(np.abs(e-gt))) for e in estimates], 'P2':[0,4,40],
            'kitti_positive_fraction':float(np.mean(disparity>0)), 'kitti_accuracy':'not evaluated; no disparity GT',
            'data_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pair}})

def sfm(rng):
    J=np.array([[1.,0.,1.],[0.,1.,1.],[1.,0.,-1.],[0.,1.,-1.],[1.,-1.,1.]])
    r=np.array([-1.,-2.,0.,1.,.5]); H=J.T@J; g=J.T@r
    A,B,D=H[:2,:2],H[:2,2:],H[2:,2:]
    S=A-B@np.linalg.solve(D,B.T); rhs=-g[:2]+B@np.linalg.solve(D,g[2:])
    dc=np.linalg.solve(S,rhs); dp=np.linalg.solve(D,-g[2:]-B.T@dc)
    full=np.linalg.solve(H,-g); reduced=np.r_[dc,dp]
    fig,axs=plt.subplots(1,3,figsize=(7,3.2))
    for ax,m,title in zip(axs,[J,H,S],['Jacobian J','Normal H=J.T J','Schur S']):
        im=ax.imshow(m,cmap='coolwarm',vmin=-4,vmax=4); ax.set_title(title); ax.grid(False)
        ax.set_xticks(np.arange(m.shape[1])); ax.set_yticks(np.arange(m.shape[0]))
        for (i,j),v in np.ndenumerate(m): ax.text(j,i,f'{v:g}',ha='center',va='center',fontsize=9)
    savefig('d16_01_schur')
    n=12; incidence=np.zeros((n-1,n))
    for i in range(n-1): incidence[i,i]=-1; incidence[i,i+1]=1
    hg=incidence.T@incidence
    eig=np.linalg.eigvalsh(hg); fixed=np.linalg.eigvalsh(hg[1:,1:])
    plt.plot(np.arange(len(eig)),eig,'o-',label='Free translation gauge')
    plt.plot(np.arange(len(fixed)),fixed,'s-',label='First state fixed')
    plt.xlabel('Eigenvalue index'); plt.ylabel('Information eigenvalue (1/m^2)'); plt.legend(); savefig('d16_02_gauge')
    meas=np.ones(n-1)+rng.normal(0,.03,n-1)
    def res(v, loop=False):
        e=np.diff(np.r_[0,v])-meas
        return np.r_[e,(v[-1]-4.)] if loop else e
    initial=np.cumsum(meas)
    ls=least_squares(lambda v:res(v,True),initial).x
    robust=least_squares(lambda v:res(v,True),initial,loss='huber',f_scale=.1).x
    for y,label in [(np.arange(n),'Truth'),(np.r_[0,initial],'Odometry only'),(np.r_[0,ls],'False loop + L2'),(np.r_[0,robust],'False loop + Huber')]: plt.plot(y,'o-',label=label)
    plt.xlabel('State index'); plt.ylabel('Position (m)'); plt.legend(); plt.title('Equal-weight chain: robust loss is not a loop verifier')
    savefig('d16_03_false_loop')
    output('sfm',{'J':J,'H':H,'S':S,'g':g,'full':full,'schur':reduced,'gauge_eigenvalues':eig,'fixed_eigenvalues':fixed,'ls':ls,'huber':robust},
           {'full_step':full.tolist(),'schur_step':reduced.tolist(),'step_difference':float(np.linalg.norm(full-reduced)),
            'chain_rmse_m':{'odometry':float(np.sqrt(np.mean((initial-np.arange(1,n))**2))),
                            'false_loop_l2':float(np.sqrt(np.mean((ls-np.arange(1,n))**2))),
                            'false_loop_huber':float(np.sqrt(np.mean((robust-np.arange(1,n))**2)))}})

def main():
    start=time.perf_counter(); (BASE/'figures').mkdir(exist_ok=True)
    rng=np.random.default_rng(CFG['seed']); cv2.setRNGSeed(CFG['seed']); cv2.setNumThreads(1)
    for fn in [projective,multiview,stereo,sfm]: fn(rng)
    files=list((BASE/'src').glob('*.py'))+list((BASE/'configs').glob('*.json'))
    manifest={'seed':CFG['seed'],'runtime_s':time.perf_counter()-start,'python':platform.python_version(),
              'numpy':np.__version__,'scipy':scipy.__version__,'opencv':cv2.__version__,'matplotlib':matplotlib.__version__,
              'platform':platform.platform(),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'source_sha256':{str(p.relative_to(BASE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
              'figure_count':len(list((BASE/'figures').glob('*.png'))),'scope':'educational synthetic experiments and one KITTI pair; no production SLAM'}
    (BASE/'artifacts/manifest.json').write_text(json.dumps(manifest,indent=2)); print(json.dumps(manifest,indent=2))

if __name__=='__main__': main()
