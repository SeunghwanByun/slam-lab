"""Small educational calculations; no learned KITTI predictions."""
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import scipy
import PIL
from scipy.optimize import linear_sum_assignment, minimize_scalar
from scipy.special import expit, logsumexp, softmax

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]


def binary_loss(z, y):
    return float(np.mean(np.logaddexp(0, z) - y * z))


def mlp(x, y, params):
    w, b, v, c = params
    h = np.tanh(x @ w + b)
    z = h @ v + c
    dz = (expit(z) - y) / len(y)
    dh = dz[:, None] * v * (1 - h * h)
    return binary_loss(z, y), [x.T @ dh, dh.sum(0), h.T @ dz, dz.sum()], z


def iou(a, b):
    a, b = np.asarray(a), np.asarray(b)
    inter = np.maximum(0, np.minimum(a[2:], b[2:]) - np.maximum(a[:2], b[:2])).prod()
    aa = np.maximum(0, a[2:] - a[:2]).prod()
    bb = np.maximum(0, b[2:] - b[:2]).prod()
    return float(inter / (aa + bb - inter)) if aa + bb > inter else 0.0


def nms(boxes, scores, threshold):
    order = np.argsort(-np.asarray(scores), kind='stable').tolist()
    keep = []
    while order:
        j = order.pop(0)
        keep.append(j)
        order = [k for k in order if iou(boxes[j], boxes[k]) <= threshold]
    return keep


def pr_ap(tp, n_gt):
    tp = np.asarray(tp, dtype=float)
    precision = np.cumsum(tp) / np.arange(1, len(tp) + 1)
    recall = np.cumsum(tp) / n_gt
    r = np.r_[0, recall, 1]
    p = np.r_[0, precision, 0]
    p = np.maximum.accumulate(p[::-1])[::-1]
    return precision, recall, float(np.sum(np.diff(r) * p[1:]))


def attention(q, k, v, scale=True):
    s = q @ k.T / (np.sqrt(q.shape[1]) if scale else 1)
    a = softmax(s, axis=1)
    return a, a @ v


def receptive(layers):
    r, jump = 1, 1
    values = [(r, jump)]
    for kernel, stride, dilation in layers:
        r += (kernel - 1) * dilation * jump
        jump *= stride
        values.append((r, jump))
    return np.array(values)


def reliability(z, y, bins=8):
    p = expit(z)
    conf = np.maximum(p, 1-p)
    correct = (p >= .5) == y
    out = []
    for lo, hi in zip(np.linspace(.5, 1, bins+1)[:-1], np.linspace(.5, 1, bins+1)[1:]):
        m = (conf >= lo) & (conf < hi if hi < 1 else conf <= hi)
        if m.any():
            out.append([conf[m].mean(), correct[m].mean(), int(m.sum())])
    return np.asarray(out)


def savefig(fig, name, dpi):
    fig.tight_layout()
    fig.savefig(BASE / 'figures' / f'{name}.png', dpi=dpi, facecolor='white')
    plt.close(fig)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    start = time.perf_counter()
    cfg = json.loads((BASE/'configs/default.json').read_text())
    rng = np.random.default_rng(cfg['seed'])
    for name in ['figures', 'artifacts/learning', 'artifacts/convolution', 'artifacts/evaluation', 'artifacts/attention']:
        (BASE/name).mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.grid': False})
    dpi = cfg['dpi']
    x = rng.normal(size=(cfg['samples'], 2))
    y = (x[:, 0] * x[:, 1] > 0).astype(float)
    flip = rng.random(len(y)) < .06
    y[flip] = 1-y[flip]
    params = [rng.normal(0, .4, (2, 12)), np.zeros(12), rng.normal(0, .4, 12), np.array(0.)]
    initial = [p.copy() for p in params]
    history = []
    linear = np.zeros(3)
    for _ in range(cfg['steps']):
        loss, grads, z = mlp(x[:400], y[:400], params)
        params = [p-cfg['learning_rate']*g for p,g in zip(params, grads)]
        xx = np.c_[x[:400], np.ones(400)]
        zl = xx @ linear
        linear -= cfg['learning_rate'] * xx.T @ (expit(zl)-y[:400])/400
        history.append([mlp(x[:400], y[:400], params)[0], mlp(x[400:], y[400:], params)[0], binary_loss(xx @ linear,y[:400])])
    h = np.asarray(history)
    grid = np.stack(np.meshgrid(np.linspace(-3,3,140),np.linspace(-3,3,140)),axis=-1)
    _,_,gz = mlp(grid.reshape(-1,2),np.zeros(19600),params)
    fig, ax = plt.subplots(1,2,figsize=(8,3.5))
    ax[0].plot(h[:,0],label='MLP train'); ax[0].plot(h[:,1],label='MLP held-out'); ax[0].plot(h[:,2],label='linear train')
    ax[0].set(xlabel='gradient step',ylabel='mean BCE [nat]'); ax[0].legend()
    ax[1].imshow(expit(gz).reshape(140,140),extent=(-3,3,-3,3),origin='lower',vmin=0,vmax=1,cmap='RdBu_r')
    ax[1].scatter(*x[400:].T,c=y[400:],s=8,cmap='RdBu_r',edgecolors='k',linewidths=.2)
    ax[1].set(xlabel='x1 [unitless]',ylabel='x2 [unitless]',title='Toy XOR: held-out points')
    savefig(fig,'d17_training',dpi)
    _, grads, _ = mlp(x[:15],y[:15],initial)
    eps_values = np.logspace(-2,-8,7); errors=[]
    for eps in eps_values:
        numerical=[]
        for j in range(initial[0].size):
            pp=[p.copy() for p in initial]; pm=[p.copy() for p in initial]
            pp[0].flat[j]+=eps; pm[0].flat[j]-=eps
            numerical.append((mlp(x[:15],y[:15],pp)[0]-mlp(x[:15],y[:15],pm)[0])/(2*eps))
        errors.append(np.max(np.abs(np.array(numerical)-grads[0].ravel())))
    fig, ax=plt.subplots(figsize=(7,3)); ax.loglog(eps_values,errors,'o-'); ax.set(xlabel='central-difference epsilon',ylabel='max absolute gradient error',title='Toy MLP derivative check');savefig(fig,'d17_gradient',dpi)
    latent = rng.normal(0,1.7,5000); labels = (rng.random(5000)<expit(latent)).astype(float)
    overconf=3*latent
    fit=minimize_scalar(lambda logt: binary_loss(overconf[:2500]/np.exp(logt),labels[:2500]),bounds=(-2,3),method='bounded')
    temp=float(np.exp(fit.x)); raw=reliability(overconf[2500:],labels[2500:]); cal=reliability(overconf[2500:]/temp,labels[2500:])
    fig,ax=plt.subplots(figsize=(7,3.4));ax.plot([.5,1],[.5,1],'k--',label='ideal');ax.plot(raw[:,0],raw[:,1],'o-',label='overconfident');ax.plot(cal[:,0],cal[:,1],'s-',label=f'validation T={temp:.3f}');ax.set(xlabel='mean confidence [probability]',ylabel='observed accuracy',ylim=(.4,1.02));ax.legend();savefig(fig,'d17_calibration',dpi)
    np.savez(BASE/'artifacts/learning/arrays.npz',x=x,y=y,history=h,epsilon=eps_values,gradient_error=errors,calibration_raw=raw,calibration_adjusted=cal)
    image_path=ROOT/cfg['image']; im=cv2.imread(str(image_path),cv2.IMREAD_GRAYSCALE)
    if im is None: raise FileNotFoundError(image_path)
    f=im.astype(float)/255
    blur=cv2.GaussianBlur(f,(5,5),1.0)
    sx=cv2.Sobel(f,cv2.CV_64F,1,0,ksize=3)/8
    fig,axs=plt.subplots(3,1,figsize=(8,6))
    for ax,a,title in zip(axs,[f,blur,sx],['KITTI 00 left 000000: real input','Fixed Gaussian sigma=1 px; NOT CNN','Fixed Sobel x / 8; NOT learned features']):
        ax.imshow(a,cmap='gray' if title!= 'Fixed Sobel x / 8; NOT learned features' else 'coolwarm',vmin=0 if a is not sx else -.5,vmax=1 if a is not sx else .5);ax.set(title=title,xlabel='x [px]',ylabel='y [px]')
    savefig(fig,'d18_filters',dpi)
    checker=(np.indices((32,32)).sum(0)%2).astype(float)
    direct=checker[::2,::2]; pre=cv2.GaussianBlur(checker,(5,5),.9)[::2,::2]
    fig,axs=plt.subplots(1,3,figsize=(8,3))
    for ax,a,t in zip(axs,[checker,direct,pre],['Synthetic checkerboard','Stride 2: phase alias','Blur then stride 2']): ax.imshow(a,cmap='gray',vmin=0,vmax=1,extent=(0,32,32,0));ax.set(title=t,xlabel='input x [px]')
    savefig(fig,'d18_alias',dpi)
    rf=receptive([(3,1,1),(3,2,1),(3,1,1),(3,1,2)])
    fig,axs=plt.subplots(1,2,figsize=(8,3.3));axs[0].plot(rf[:,0],'o-',label='support width');axs[0].plot(rf[:,1],'s-',label='sample spacing');axs[0].set(xlabel='layer',ylabel='input pixels');axs[0].legend()
    depth=np.arange(51);axs[1].semilogy(depth,.9**depth,label='plain scalar 0.9');axs[1].semilogy(depth,1.01**depth,label='residual 1 + 0.01');axs[1].set(xlabel='layer count',ylabel='scalar derivative magnitude');axs[1].legend();savefig(fig,'d18_receptive_residual',dpi)
    np.savez(BASE/'artifacts/convolution/arrays.npz',original=f,blur=blur,sobel=sx,checker=checker,stride=direct,prefilter=pre,receptive=rf)
    boxes=np.array([[0,0,4,4],[1,0,5,4],[6,0,10,4]],float);scores=np.array([.9,.8,.7]);keep=nms(boxes,scores,.5)
    fig,axs=plt.subplots(1,2,figsize=(8,3))
    for ax,ids,title in zip(axs,[range(3),keep],['Synthetic proposals','NMS threshold=0.5']):
        for j in ids:
            a=boxes[j];ax.add_patch(plt.Rectangle(a[:2],a[2]-a[0],a[3]-a[1],fill=False,color=['red','blue','green'][j],lw=2));ax.text(a[0]+.1,1+j*.65,f'{j}: {scores[j]}')
        ax.set(xlim=(-1,11),ylim=(5,-1),xlabel='x [px]',ylabel='y [px]',title=title)
    savefig(fig,'d19_nms',dpi)
    tp=np.array([1,0,1,0,1]);pr,rec,ap=pr_ap(tp,3);badp,badr,badap=pr_ap([0,1,0,1,1],3)
    fig,ax=plt.subplots(figsize=(7,3.5));ax.plot(rec,pr,'o-',alpha=.6,label='A: raw operating points');ax.step(np.r_[0,rec],np.r_[pr[0],np.maximum.accumulate(pr[::-1])[::-1]],where='pre',label=f'A: precision envelope AP={ap:.4f}');ax.step(np.r_[0,badr],np.r_[badp[0],np.maximum.accumulate(badp[::-1])[::-1]],where='pre',label=f'B: precision envelope AP={badap:.4f}');ax.set(xlabel='recall',ylabel='precision',xlim=(0,1.02),ylim=(0,1.05));ax.legend();savefig(fig,'d19_pr',dpi)
    yy,xx=np.indices((64,64));mask=(xx-32)**2+(yy-32)**2<16**2; pred=(xx-37)**2+(yy-32)**2<16**2
    overlap=np.logical_and(mask,pred).sum(); miou=overlap/np.logical_or(mask,pred).sum();dice=2*overlap/(mask.sum()+pred.sum())
    fig,axs=plt.subplots(1,3,figsize=(8,3));overlay=np.zeros((64,64,3));overlay[mask]=[0,.6,.2];overlay[pred]=[.8,.1,.2];overlay[mask&pred]=[.3,.3,.8]
    for ax,a,t in zip(axs,[mask,pred,overlay],['Synthetic GT','Shifted mask +5 px',f'IoU={miou:.3f}; Dice={dice:.3f}']): ax.imshow(a,cmap='gray');ax.set(title=t,xlabel='x [px]')
    savefig(fig,'d19_masks',dpi)
    cost=np.array([[1,2,8],[2,8,2],[7,1,4]],float);rows,cols=linear_sum_assignment(cost)
    np.savez(BASE/'artifacts/evaluation/arrays.npz',boxes=boxes,scores=scores,keep=keep,tp=tp,precision=pr,recall=rec,mask=mask,pred=pred,cost=cost,assignment=cols)
    q=np.eye(2); k=np.eye(2);v=np.array([[2,0],[0,4]],float);a,out=attention(q,k,v)
    fig,axs=plt.subplots(1,3,figsize=(8,3))
    for ax,arr,t in zip(axs,[q@k.T/np.sqrt(2),a,out],['Q K^T / sqrt(2)','A: row probabilities','A V: output features']):
        shown=ax.imshow(arr,cmap='Blues');ax.set(title=t,xlabel='column',ylabel='row',xticks=[0,1],yticks=[0,1])
        for ij in np.ndindex(arr.shape): ax.text(ij[1],ij[0],f'{arr[ij]:.4f}',ha='center',va='center',color='white' if shown.norm(arr[ij])>.55 else 'black')
    savefig(fig,'d20_attention',dpi)
    dims=np.array([4,16,64,256]); ent=[]
    for d in dims:
        qr=rng.normal(size=(300,d));kr=rng.normal(size=(40,d));vr=np.zeros((40,1));aa,_=attention(qr,kr,vr);ab,_=attention(qr,kr,vr,False)
        ent.append([-np.mean(np.sum(aa*np.log(aa+1e-30),axis=1)),-np.mean(np.sum(ab*np.log(ab+1e-30),axis=1))])
    ent=np.array(ent); fig,ax=plt.subplots(figsize=(7,3.3));ax.plot(dims,ent[:,0],'o-',label='scaled');ax.plot(dims,ent[:,1],'s-',label='unscaled');ax.set(xscale='log',xlabel='key dimension d',ylabel='mean row entropy [nat]');ax.legend();savefig(fig,'d20_scaling',dpi)
    crop=f[100:228,500:628];patch=16;means=crop.reshape(8,16,8,16).mean((1,3));recon=np.repeat(np.repeat(means,16,0),16,1)
    fig,axs=plt.subplots(1,2,figsize=(7,3.4));axs[0].imshow(crop,cmap='gray',vmin=0,vmax=1);axs[1].imshow(recon,cmap='gray',vmin=0,vmax=1)
    for ax,t in zip(axs,['KITTI crop: actual pixels','16 px patch mean: NOT ViT output']): ax.set(title=t,xlabel='crop x [px]',ylabel='crop y [px]')
    savefig(fig,'d20_patches',dpi)
    truth=np.linspace(2,40,100); inv=1/truth; proxy=2*inv+.1;coef=np.linalg.lstsq(np.c_[proxy,np.ones(100)],inv,rcond=None)[0]; aligned=1/(coef[0]*proxy+coef[1])
    fig,ax=plt.subplots(figsize=(7,3.4));ax.plot(truth,1/proxy,label='wrong: reciprocal treated as metres');ax.plot(truth,aligned,'--',label='oracle affine inverse-depth alignment');ax.plot(truth,truth,':',label='ideal');ax.set(xlabel='synthetic true depth [m]',ylabel='reported depth [m]');ax.legend();savefig(fig,'d20_depth',dpi)
    np.savez(BASE/'artifacts/attention/arrays.npz',q=q,k=k,v=v,weights=a,output=out,dimensions=dims,entropy=ent,truth_depth=truth,relative_inverse_depth=proxy,alignment=coef)
    results={'mlp_train_bce':float(h[-1,0]),'mlp_heldout_bce':float(h[-1,1]),'linear_train_bce':float(h[-1,2]),'gradient_max_error_at_1e_5':float(errors[3]),'temperature':temp,'test_nll_before':binary_loss(overconf[2500:],labels[2500:]),'test_nll_after':binary_loss(overconf[2500:]/temp,labels[2500:]),'iou_boxes_0_1':iou(boxes[0],boxes[1]),'nms_keep':keep,'ap_all_points':ap,'ap_bad_order':badap,'mask_iou':float(miou),'mask_dice':float(dice),'hungarian_cost':float(cost[rows,cols].sum()),'attention':a.tolist(),'attention_output':out.tolist(),'inverse_depth_affine':coef.tolist(),'alias_mse_raw':float(np.mean((direct-.5)**2)),'alias_mse_prefilter':float(np.mean((pre-.5)**2))}
    (BASE/'artifacts/results.json').write_text(json.dumps(results,indent=2)+'\n')
    files=[*sorted((BASE/'src').glob('*.py')),BASE/'configs/default.json',image_path]
    manifest={'kind':'educational; no pretrained model or benchmark','config':cfg,'versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'opencv':cv2.__version__,'matplotlib':matplotlib.__version__,'pillow':PIL.__version__},'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'runtime_seconds':time.perf_counter()-start,'input_sha256':{str(p.relative_to(ROOT)):digest(p) for p in files},'figure_sha256':{p.name:digest(p) for p in sorted((BASE/'figures').glob('*.png'))}}
    (BASE/'artifacts/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    main()
