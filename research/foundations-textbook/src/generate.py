"""Reproducible teaching models and one actual KITTI projection, not a SLAM engine."""
import hashlib
import json
import subprocess
from pathlib import Path
import cv2
import numpy as np
import scipy
from scipy.optimize import least_squares
from scipy.stats import norm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Ellipse

STUDY=Path(__file__).resolve().parents[1]; ROOT=STUDY.parents[1]
CFG=json.loads((STUDY/'configs/lessons.json').read_text())
ART=STUDY/'artifacts'; FIG=STUDY/'figures'
ART.mkdir(parents=True,exist_ok=True); FIG.mkdir(exist_ok=True)
font=Path('/System/Library/Fonts/AppleSDGothicNeo.ttc')
if font.exists():
    font_manager.fontManager.addfont(str(font))
    plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams.update({'axes.unicode_minus':False,'font.size':11,'axes.titlesize':13})
RESULT={}; CHECKS=[]

def check(name,condition):
    assert bool(condition),name
    CHECKS.append(name)

def save(module,**arrays):
    folder=ART/module; folder.mkdir(exist_ok=True)
    np.savez_compressed(folder/'values.npz',**arrays)

def figsave(fig,name):
    fig.tight_layout(pad=1.6,h_pad=2,w_pad=2)
    fig.savefig(FIG/f'{name}.png',dpi=160); plt.close(fig)

def frames():
    p=np.array([1.,0.]);R=np.array([[0.,-1.],[1.,0.]]);t=np.array([2.,0.]);q=R@p+t;wrong=R@(p+t)
    check('inverse transform',np.allclose(R.T@(q-t),p));check('order matters',not np.allclose(q,wrong))
    fig,axes=plt.subplots(1,2,figsize=(12,4.7))
    for ax in axes:
        ax.set(xlim=(-1,4),ylim=(-1,4),xlabel='세계 x (m)',ylabel='세계 y (m)');ax.set_aspect('equal');ax.grid(alpha=.2)
        ax.quiver([0,0],[0,0],[1,0],[0,1],angles='xy',scale_units='xy',scale=1,color=['#b6344b','#168d75'])
    axes[0].quiver([2,2],[0,0],R[0],R[1],angles='xy',scale_units='xy',scale=1,color=['#d69e00','#2477ba'])
    axes[0].scatter(*q,c='black',s=60);axes[0].annotate('B에서 (1,0)\nA에서 (2,1)',q,xytext=(2.2,1.5),arrowprops={'arrowstyle':'->'})
    axes[0].text(0,-.5,'A 원점');axes[0].text(2,-.5,'B 원점');axes[0].set_title('같은 점, 다른 좌표 [교육 모델]')
    axes[1].plot([1,0,2],[0,1,1],'o-',label='회전 후 이동: (2,1)');axes[1].plot([1,3,0],[0,0,3],'s--',label='이동 후 회전: (0,3)');axes[1].legend(fontsize=9);axes[1].set_title('순서를 바꾸면 다른 점');figsave(fig,'01_frames_order')
    a=np.array([3.,4.]);check('norm',np.isclose(np.linalg.norm(a),5))
    fig,ax=plt.subplots(figsize=(7,4.6));ax.quiver([0,0],[0,0],[3,3],[4,0],angles='xy',scale_units='xy',scale=1,color=['#2477ba','#cc4655']);ax.plot([3,3],[0,4],'k:');ax.text(1.2,2.2,'길이 5');ax.text(1,-.5,'x축 투영 길이 3');ax.set(xlim=(-.5,5),ylim=(-1,5),xlabel='x',ylabel='y',title='벡터 (3,4): 크기와 방향');ax.grid(alpha=.2);ax.set_aspect('equal');figsave(fig,'02_vectors')
    save('frames',p=p,R=R,t=t,q=q,wrong=wrong,a=a);RESULT['frames']={'point':q.tolist(),'wrong_order':wrong.tolist(),'norm':5.}

def camera():
    f=CFG['fx_px'];z=np.linspace(2,40,200)
    fig,axes=plt.subplots(1,2,figsize=(12,4.7))
    for depth,col in [(5,'#2477ba'),(10,'#d36632')]:axes[0].plot([0,depth],[0,1],'o-',c=col,label=f'X=1m, Z={depth}m: u-cx={f/depth:.0f}px')
    axes[0].axvline(1,color='gray');axes[0].set(xlabel='Z 전방 (m)',ylabel='X 오른쪽 (m)',title='가상 영상면과 광선');axes[0].legend(fontsize=8)
    axes[1].plot(z,f/z);axes[1].set(xlabel='깊이 Z (m)',ylabel='u-cx (px)',title='u-cx = fX/Z, 여기서 X=1m');axes[1].grid(alpha=.2);figsave(fig,'03_projection')
    disparity=f*CFG['baseline_m']/z;sigma=z*z/(f*CFG['baseline_m'])*CFG['disparity_sigma_px']
    fig,axes=plt.subplots(1,2,figsize=(12,4.6));axes[0].plot(z,disparity);axes[0].set(xlabel='깊이 (m)',ylabel='시차 (px)',title='멀수록 좌우 시차는 작다');axes[1].plot(z,sigma,c='#bb4055');axes[1].set(xlabel='깊이 (m)',ylabel='깊이 표준편차 근사 (m)',title='같은 0.5px 오차가 큰 거리 오차로');figsave(fig,'04_stereo_uncertainty')
    check('projection scale ambiguity',np.isclose(f*1/5,f*2/10));check('stereo example',np.isclose(f*CFG['baseline_m']/27,10));save('camera',depth=z,u=f/z,disparity=disparity,depth_sigma=sigma)
    seq=ROOT/'data/kitti/dataset/sequences'/CFG['kitti_sequence'];stem=f'{CFG["frame"]:06d}';im=cv2.imread(str(seq/'image_0'/f'{stem}.png'),0);assert im is not None
    cal={k:np.fromstring(v,sep=' ').reshape(3,4) for k,v in (line.split(':',1) for line in (seq/'calib.txt').read_text().splitlines())}
    raw=np.fromfile(seq/'velodyne'/f'{stem}.bin',dtype='<f4').reshape(-1,4);pc=np.c_[raw[:,:3],np.ones(len(raw))]@cal['Tr'].T
    uvh=np.c_[pc,np.ones(len(pc))]@cal['P0'].T;positive=(pc[:,2]>0)&(uvh[:,2]>0);uv=np.full((len(pc),2),np.nan);uv[positive]=uvh[positive,:2]/uvh[positive,2,None]
    visible=positive&(uv[:,0]>=0)&(uv[:,0]<im.shape[1])&(uv[:,1]>=0)&(uv[:,1]<im.shape[0]);indices=np.flatnonzero(visible);check('KITTI visible points',len(indices)>1000)
    center=np.array([im.shape[1]*.5,im.shape[0]*.7]);chosen=indices[np.argmin(np.linalg.norm(uv[indices]-center,axis=1))]
    fig,ax=plt.subplots(figsize=(12,4.2));ax.imshow(im,cmap='gray');s=indices[::12];dots=ax.scatter(uv[s,0],uv[s,1],c=pc[s,2],s=2,cmap='turbo',vmin=0,vmax=60)
    ax.scatter(*uv[chosen],s=100,facecolors='none',edgecolors='white',linewidths=2);ax.annotate('단일 점 계산 예',uv[chosen],xytext=(30,30),textcoords='offset points',color='white',arrowprops={'arrowstyle':'->','color':'white'});ax.axis('off');ax.set_title('실제 KITTI 00 / frame120: LiDAR → 왼쪽 카메라');fig.colorbar(dots,ax=ax,label='카메라 Z (m)',shrink=.8);figsave(fig,'05_kitti_projection')
    save('kitti',Tr=cal['Tr'],P0=cal['P0'],index=chosen,lidar=raw[chosen],camera=pc[chosen],pixel=uv[chosen],indices=indices,pixels=uv[indices])
    RESULT['kitti']={'visible':len(indices),'raw_points':len(raw),'index':int(chosen),'lidar':raw[chosen,:3].tolist(),'camera':pc[chosen].tolist(),'pixel':uv[chosen].tolist(),'P0':cal['P0'].tolist(),'Tr':cal['Tr'].tolist(),'image_sha256':hashlib.sha256((seq/'image_0'/f'{stem}.png').read_bytes()).hexdigest()}

def estimation():
    z=np.array(CFG['measurements_m']);grid=np.linspace(.5,4.2,600);r=grid[:,None]-z;d=CFG['huber_delta_m'];squared=np.sum(r*r,axis=1);huber=np.sum(np.where(np.abs(r)<=d,.5*r*r,d*(np.abs(r)-.5*d)),axis=1)
    fit=least_squares(lambda x:x[0]-z,[1.],loss='huber',f_scale=d).x[0];check('mean optimum',np.isclose(z.mean(),1.6));check('robust optimum',np.isclose(fit,1.05,atol=1e-6))
    fig,axes=plt.subplots(1,2,figsize=(12,4.7));axes[0].plot(grid,squared);axes[0].axvline(1.6,c='#cc4655',label='평균 1.6m');axes[0].legend();axes[0].set(xlabel='추정 x (m)',ylabel='제곱합 (m²)',title='이상치 4.0m에 끌리는 최소제곱')
    axes[1].plot(grid,huber,c='#168d75');axes[1].axvline(fit,c='#cc4655',label='Huber 1.05m');axes[1].legend();axes[1].set(xlabel='추정 x (m)',ylabel='Huber 합',title='큰 잔차의 영향 완화; 정답 보장 아님');figsave(fig,'06_least_squares_robust')
    A=np.diag([2.,.2]);angle=np.linspace(0,2*np.pi,200);circle=np.stack([np.cos(angle),np.sin(angle)]);fig,axes=plt.subplots(1,2,figsize=(11,4.7));axes[0].plot(*circle,label='입력');axes[0].plot(*(A@circle),label='A로 변환');axes[0].set_aspect('equal');axes[0].legend();axes[0].set(title='특잇값 2, 0.2: 방향별 늘림',xlabel='x',ylabel='y')
    xx,yy=np.meshgrid(np.linspace(-1,1,120),np.linspace(-3,3,120));axes[1].contour(xx,yy,4*xx*xx+.04*yy*yy,levels=[.04,.1,.2,.4,1]);axes[1].set(title='약한 방향: 작은 비용 변화',xlabel='강한 방향',ylabel='약한 방향');figsave(fig,'07_svd_observability')
    cov=np.array([[4.,1.5],[1.5,1.]]);samples=np.random.default_rng(CFG['seed']).multivariate_normal([0,0],cov,1000);values,vectors=np.linalg.eigh(cov);theta=np.degrees(np.arctan2(vectors[1,-1],vectors[0,-1]));fig,ax=plt.subplots(figsize=(7,5));ax.scatter(samples[:,0],samples[:,1],s=3,alpha=.2);ax.add_patch(Ellipse((0,0),2*np.sqrt(values[-1]),2*np.sqrt(values[0]),angle=theta,fill=False,color='#cc4655',lw=2,label='Mahalanobis 반경1: 2D 약39.3%'));ax.set_aspect('equal');ax.set(xlabel='x 오차 (m)',ylabel='y 오차 (m)',title='공분산: 크기와 방향');ax.legend(fontsize=8);figsave(fig,'08_covariance')
    zs=np.array(CFG['fusion_measurements_m']);sig=np.array(CFG['fusion_sigma_m']);w=1/sig**2;mle=float(np.sum(w*zs)/sum(w));var=1/sum(w);prior=CFG['prior_mean_m'];pv=CFG['prior_sigma_m']**2;postvar=1/(1/var+1/pv);post=postvar*(mle/var+prior/pv)
    x=np.linspace(7,15,600);fig,ax=plt.subplots(figsize=(10,4.8))
    for mean,std,label in [(zs[0],sig[0],'측정 A'),(zs[1],sig[1],'측정 B'),(mle,np.sqrt(var),'MLE 10.4'),(post,np.sqrt(postvar),f'MAP {post:.3f}')]:ax.plot(x,norm.pdf(x,mean,std),label=label)
    ax.set(xlabel='상태 x (m)',ylabel='상태축에서 정규화한 곡선 (1/m)',title='독립 Gaussian + 고정 분산이라는 가정');ax.legend();figsave(fig,'09_mle_map')
    check('fusion mean',np.isclose(mle,10.4));check('MAP',np.isclose(post,9.333333333333334));check('covariance positive',np.all(values>0));save('estimation',measurements=z,grid=grid,squared=squared,huber=huber,robust=fit,A=A,covariance=cov,samples=samples,mle=mle,mle_var=var,map=post,map_var=postvar)
    RESULT['estimation']={'mean':float(z.mean()),'huber':float(fit),'condition_number':float(np.linalg.cond(A)),'mle':mle,'mle_variance':float(var),'map':float(post),'map_variance':float(postvar)}

def linearization():
    target=CFG['gn_target'];x=CFG['gn_start'];trace=[]
    for i in range(CFG['gn_steps']):
        r=x*x-target;j=2*x;e=1e-6;finite=((x+e)**2-(x-e)**2)/(2*e);check(f'Jacobian {i}',abs(finite-j)<1e-5);trace.append([x,r,j,r*r]);x=x-r/j
    trace.append([x,x*x-target,2*x,(x*x-target)**2]);trace=np.array(trace);check('GN solution',abs(x-2)<1e-8);check('GN chosen start cost decreases',np.all(np.diff(trace[:,3])<0))
    grid=np.linspace(.3,3,200);fig,axes=plt.subplots(1,2,figsize=(12,4.8));axes[0].plot(grid,grid**2-target,label='r(x)=x²-4');axes[0].plot(grid,-3+2*(grid-1),'--',label='x=1의 접선');axes[0].axhline(0,c='gray');axes[0].legend();axes[0].set(xlabel='x',ylabel='r',title='현재 위치 근처에서 직선으로');axes[1].plot(np.arange(len(trace)),np.log10(np.maximum(trace[:,3],1e-18)),'o-');axes[1].set(xlabel='반복',ylabel='log10(잔차 제곱), 하한 -18',title='선택한 시작점의 비용 감소');figsave(fig,'10_jacobian_iteration')
    angle=.5;K=np.array([[0.,-angle,0],[angle,0,0],[0,0,0]]);naive=np.eye(3)+K;proper,_=cv2.Rodrigues(np.array([0.,0.,angle]));unit=np.array([1.,0.,0.]);check('SO3 constraint',np.allclose(proper.T@proper,np.eye(3)));check('additive invalid',not np.allclose(naive.T@naive,np.eye(3)))
    th=np.linspace(0,2*np.pi,200);fig,ax=plt.subplots(figsize=(7,5));ax.plot(np.cos(th),np.sin(th),c='gray',label='단위원')
    for v,col,label in [(unit,'black','원래 점'),(proper@unit,'#168d75','Rodrigues: 길이1'),(naive@unit,'#cc4655','I+[w]x: 길이>1')]:ax.scatter(v[0],v[1],c=col,s=50,label=label)
    ax.set_aspect('equal');ax.legend(fontsize=9);ax.set(xlabel='x',ylabel='y',title='회전은 길이를 보존한다');figsave(fig,'11_rotation_constraint');save('linearization',trace=trace,naive=naive,proper=proper)
    RESULT['linearization']={'trace':trace.tolist(),'naive_norm':float(np.linalg.norm(naive@unit)),'proper_norm':float(np.linalg.norm(proper@unit))}

def graph_imu():
    inc=np.array([1.1,1.1,-.9,-.9]);before=np.r_[0,np.cumsum(inc)]
    def residual(x):
        p=np.r_[0,x];return np.r_[(np.diff(p)-inc)/.1,p[-1]/.05]
    solved=least_squares(residual,before[1:]);after=np.r_[0,solved.x];jac=np.zeros((4,5))
    for i in range(4):jac[i,i:i+2]=[-1,1]
    check('gauge rank',np.linalg.matrix_rank(jac)==4);check('global shift invisible',np.allclose(jac@np.ones(5),0));check('loop residual reduced',abs(after[-1])<abs(before[-1]))
    fig,axes=plt.subplots(1,2,figsize=(12,4.7))
    for data,label in [(np.array([0,1,2,1,0]),'설명용 참값'),(before,'누적 odometry'),(after,'loop 제약 후')]:axes[0].plot(range(5),data,'o-',label=label)
    axes[0].set(xlabel='시점',ylabel='1D 위치 (m)',title='1D 교육 모델: 재방문 제약');axes[0].legend(fontsize=8);axes[1].bar(['보정 전','보정 후'],[before[-1],after[-1]],color=['#cc4655','#168d75']);axes[1].set(ylabel='끝점-시작점 (m)',title='loop를 무한정 고정하지 않음');figsave(fig,'12_pose_graph')
    fig,ax=plt.subplots(figsize=(11,3.5));xx=np.arange(5);ax.scatter(xx,np.zeros(5),s=450,facecolors='white',edgecolors='#2477ba',linewidths=2,zorder=3)
    for i in range(5):ax.text(i,0,f'x{i}',ha='center',va='center')
    for i in range(4):ax.plot([i,i+1],[0,0],c='gray');ax.scatter(i+.5,0,marker='s',s=70,c='#168d75',zorder=4)
    ax.plot([0,0,4,4],[0,1,1,0],c='#cc4655');ax.scatter(2,1,marker='s',s=70,c='#cc4655');ax.text(2,1.25,'loop factor: x4 - x0 ≈ 0',ha='center');ax.plot([0,0],[0,-.6],c='black');ax.scatter(0,-.6,marker='s',s=70,c='black');ax.text(.2,-.6,'anchor: x0 = 0');ax.set(xlim=(-.5,4.5),ylim=(-1,1.6),title='원: 미지 상태 / 사각형: 관측 제약');ax.axis('off');figsave(fig,'13_factor_graph')
    time=np.linspace(0,CFG['duration_s'],601);error=.5*CFG['imu_accel_bias_mps2']*time**2;yaw=CFG['imu_gyro_bias_degps']*time;fig,axes=plt.subplots(1,2,figsize=(12,4.6));axes[0].plot(time,error);axes[0].set(xlabel='시간 (s)',ylabel='위치 오차 (m)',title='1D 가속도 bias 0.02m/s² 적분');axes[1].plot(time,yaw,c='#cc4655');axes[1].set(xlabel='시간 (s)',ylabel='방향 오차 (deg)',title='각속도 bias 0.1deg/s 적분');figsave(fig,'14_imu_bias')
    offsets=np.linspace(0,.1,100);shift=CFG['fx_px']*CFG['timing_speed_mps']*offsets/CFG['timing_depth_m'];one=CFG['fx_px']*CFG['timing_speed_mps']*CFG['timing_offset_s']/CFG['timing_depth_m'];fig,ax=plt.subplots(figsize=(8,4.5));ax.plot(offsets*1000,shift);ax.scatter([20],[one],c='#cc4655');ax.annotate('20ms → 10px',(20,10),xytext=(30,5),arrowprops={'arrowstyle':'->'});ax.set(xlabel='시간 어긋남 (ms)',ylabel='가로 영상 오차 근사 (px)',title='가로 운동 10m/s, 깊이10m, f=500px [교육 모델]');figsave(fig,'15_time_offset')
    check('IMU endpoint',np.isclose(error[-1],36));check('timing example',np.isclose(one,10));save('graph',increments=inc,before=before,after=after,J=jac,residual=solved.fun);save('imu',time=time,position_error=error,yaw_error=yaw,offsets=offsets,pixel_shift=shift)
    RESULT['graph']={'before':before.tolist(),'after':after.tolist(),'loop_before_m':float(before[-1]),'loop_after_m':float(after[-1])};RESULT['imu']={'position_error_60s_m':float(error[-1]),'yaw_error_60s_deg':float(yaw[-1]),'timing_error_px':float(one)}

if __name__=='__main__':
    frames();camera();estimation();linearization();graph_imu();RESULT['checks']=CHECKS
    RESULT['environment']={'opencv':cv2.__version__,'numpy':np.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'config_sha256':hashlib.sha256((STUDY/'configs/lessons.json').read_bytes()).hexdigest()}
    (ART/'summary.json').write_text(json.dumps(RESULT,indent=2,ensure_ascii=False,allow_nan=False));print(json.dumps(RESULT,indent=2,ensure_ascii=False))
