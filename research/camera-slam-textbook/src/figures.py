"""Print-oriented original figures rendered strictly from saved stage arrays."""
import csv
import json
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from common import ART, FIG, CFG, save_json

plt.rcParams.update({'font.size':12,'axes.titlesize':13,'axes.labelsize':12,
                     'legend.fontsize':10,'xtick.labelsize':10,'ytick.labelsize':10,
                     'figure.dpi':120,'savefig.dpi':220,'axes.grid':False})
MANIFEST=[]


def canvas(title, height=4.8):
    fig,ax=plt.subplots(figsize=(7,height),layout='constrained')
    ax.set_title('\n'.join(textwrap.wrap(title,68)))
    return fig,ax


def finish(fig,name,sources,caption,kind='actual KITTI'):
    path=FIG/(name+'.png')
    fig.savefig(path,facecolor='white')
    plt.close(fig)
    MANIFEST.append(dict(file=str(path.relative_to(FIG.parent)),kind=kind,
        sources=sources,caption_ko=caption,width_inches=7,dpi=220))


def histogram(ax,data,label,**kwargs):
    values=np.asarray(data)
    values=values[np.isfinite(values)]
    ax.hist(values,bins=40,label=label,**kwargs)


def diagnostic_figures():
    s=np.load(ART/'stereo/000000.npz')
    d=np.load(ART/'dense/000000.npz')
    t=np.load(ART/'tracking/000000.npz')
    p=np.load(ART/'reprojection/000000.npz')
    src=['artifacts/stereo/000000.npz']
    # Stacking views preserves readable pixel scale at a single-column width.
    fig,axes=plt.subplots(2,1,figsize=(7,5.2),layout='constrained',sharex=True,sharey=True)
    for ax,key,label in zip(axes,['left_image','right_image'],['Left','Right']):
        ax.imshow(s[key],cmap='gray',vmin=0,vmax=255)
        for y in (100,180,260): ax.axhline(y,color='#f54291',lw=.8)
        ax.set_title(f'Actual KITTI 00 frame 0: {label}')
        ax.set_ylabel('v (px)')
    axes[-1].set_xlabel('u (px)')
    finish(fig,'01_rectified_pair',src,'이미 정류된 좌우 입력에 같은 y선을 그렸다. raw 재정류를 수행한 그림이 아니다.')

    fig,ax=canvas('Actual: epipolar residual before geometry filtering')
    for mask,label,color in [(np.ones(len(s['dy']),bool),'Nearest','#777777'),(s['ratio_mask'],'Ratio 0.75','#168a80')]:
        v=np.abs(s['dy'][mask]); ax.ecdf(v,label=label,color=color)
    cross=np.abs(s['cross_left'][:,1]-s['cross_right'][:,1]);ax.ecdf(cross,label='Cross-check',color='#d04d50')
    ax.axvline(CFG['epipolar_px'],ls='--',c='black',label='1.5 px gate')
    ax.set(xscale='symlog',xlabel='Absolute vertical residual (px)',ylabel='Cumulative fraction')
    ax.set_xlim(left=0);ax.legend()
    finish(fig,'02_epipolar_residual',src,'게이트 전 y 오차의 누적 분포. 게이트 후 100% 일관성은 정의에 따른 결과이지 정확도 검증이 아니다.')

    fig,ax=canvas('Actual: ORB observations are 2D pixels',3.6)
    ax.imshow(s['left_image'],cmap='gray');ax.scatter(*s['all_left'].T,s=2,c='#ffe066',label='All ORB')
    ax.set(xlabel='u (px)',ylabel='v (px)')
    finish(fig,'03_orb_spatial',src,'ORB는 2D 픽셀 관측이다. 특징점만으로 3D 지도나 ORB-SLAM이 되지 않는다.')

    fig,ax=canvas('Actual: nearest / second-nearest descriptor distance')
    histogram(ax,s['ratio'],'All nearest candidates',color='#168a80')
    ax.axvline(CFG['ratio'],ls='--',c='#d04d50',label='Acceptance threshold')
    ax.set(xlabel='Hamming ratio d1 / max(d2, 1)',ylabel='Candidates');ax.legend()
    finish(fig,'04_descriptor_ratio',src,'이진 descriptor의 최근접/차근접 거리 비율. 실제 선택 조건은 d1 < 0.75*d2이며 d2=0은 거부된다.')

    fig,ax=canvas('Actual: descriptor distance versus epipolar residual')
    dots=ax.scatter(s['d1'],np.minimum(np.abs(s['dy']),60),c=s['ratio'],cmap='viridis',s=7,vmin=0,vmax=1)
    ax.axhline(1.5,c='#d04d50',ls='--');ax.axvline(64,c='#d04d50',ls='--')
    ax.set(xlabel='Nearest Hamming distance (bits)',ylabel='Absolute y error (px; clipped at 60)')
    fig.colorbar(dots,ax=ax,label='Descriptor ratio')
    finish(fig,'05_hamming_geometry',src,'작은 descriptor 거리도 기하 일관성을 보장하지 않는다. 60px 이상의 y 오차는 시각화에서만 잘랐다.')

    rows=list(csv.DictReader((ART/'stereo/000000_ablation.csv').open()))
    fig,ax=canvas('Actual: correspondence gates trade count for consistency')
    labels=['Nearest','Ratio','+ Hamming','+ y gate','+ disparity','+ depth/reproj','Cross-check']
    counts=[int(r['count']) for r in rows]
    ax.barh(labels,counts,color=['#888888']+['#168a80']*5+['#d04d50'])
    ax.invert_yaxis(); ax.set_xlabel('Retained candidates')
    for i,c in enumerate(counts):ax.text(c+20,i,str(c),va='center',fontsize=10)
    ax.set_xlim(0,max(counts)*1.15)
    finish(fig,'06_stereo_gate_ablation',src+['artifacts/stereo/000000_ablation.csv'],'동일 후보에 적용한 누적 게이트. 이 프레임에서는 Hamming 게이트의 추가 제거가 없으므로 개선을 주장하지 않는다.')

    valid=s['valid']; X=s['X'][valid]
    fig,ax=canvas('Actual: sparse stereo depth from calibrated baseline')
    ax.scatter(s['disparity'][valid],X[:,2],s=8,c='#168a80')
    ax.set(xlabel='Horizontal disparity (px)',ylabel='Triangulated depth Z (m)')
    finish(fig,'07_disparity_depth',src,'Z=fx*b/d. 깊이는 정답 오차가 아니라 알려진 baseline으로부터 얻은 추정값이다.')

    fig,ax=canvas('Actual: sparse triangulation in previous camera frame')
    dots=ax.scatter(X[:,0],X[:,2],c=X[:,1],cmap='coolwarm',s=8)
    ax.set(xlabel='Camera X (m)',ylabel='Camera Z (m)');ax.set_aspect('equal')
    fig.colorbar(dots,ax=ax,label='Camera Y (m; down)')
    finish(fig,'08_sparse_geometry',src,'카메라 좌표는 x 오른쪽, y 아래, z 전방. 먼 점의 깊이는 disparity 오차에 민감하다.')

    fig,ax=canvas('Actual: two-view triangulation reprojection residual')
    histogram(ax,s['reprojection_px'][valid],'Valid triangulations',color='#168a80')
    ax.set(xlabel='Max(left, right) reprojection error (px)',ylabel='Points')
    finish(fig,'09_triangulation_reprojection',src,'두 시점 재투영은 입력과의 자기 일관성이다. 작은 잔차만으로 올바른 대응이나 깊이를 보장하지 않는다.')

    for index,key,label,vmax in [(10,'disparity','Disparity (px)',80),(11,'depth_m','Depth Z (m)',80)]:
        fig,ax=canvas('Actual: SGBM '+label+' after validity masks',3.8)
        values=np.ma.masked_where(~d['valid'],d[key]);im=ax.imshow(values,cmap='turbo',vmin=0,vmax=vmax)
        ax.set(xlabel='u (px)',ylabel='v (px)');fig.colorbar(im,ax=ax,label=label,shrink=.8)
        finish(fig,f'{index:02d}_sgbm_{key}',['artifacts/dense/000000.npz'],'SGBM 고정소수점 출력을 16으로 나눈 뒤 양의 disparity, LR, 깊이 상한을 적용. 흰 영역은 무효, 색 상한은 표시만 제한한다.')

    fig,ax=canvas('Actual: dense validity is not depth accuracy',3.8)
    category=np.zeros(d['valid'].shape,int);category[d['positive']]=1;category[d['consistent']]=2;category[d['valid']]=3
    im=ax.imshow(category,cmap=matplotlib.colors.ListedColormap(['#333333','#d04d50','#e5ba43','#168a80']),vmin=-.5,vmax=3.5)
    bar=fig.colorbar(im,ax=ax,ticks=[0,1,2,3],shrink=.8);bar.ax.set_yticklabels(['Invalid','Positive only','LR consistent','Depth valid'])
    ax.set(xlabel='u (px)',ylabel='v (px)')
    finish(fig,'12_sgbm_validity',['artifacts/dense/000000.npz'],'모든 픽셀을 분모로 한 단계별 유효성. 좌우 검증이 텍스처 부재·반복 무늬의 오답을 모두 제거하지는 않는다.')

    fig,ax=canvas('Actual: left-right disparity consistency residual')
    histogram(ax,np.minimum(d['lr_error'][d['positive']],10),'Positive left disparity',color='#168a80')
    ax.axvline(1,c='#d04d50',ls='--');ax.set(xlabel='|d_left + d_right| (px; clipped at 10)',ylabel='Pixels')
    finish(fig,'13_sgbm_lr_residual',['artifacts/dense/000000.npz'],'우측 disparity는 음수 convention. 영상 밖 대응도 원래 배열에 보존되며 최종 mask에서 제거된다.')

    fig,ax=canvas('Actual: temporal LK, frame 0 to 1',3.8)
    ax.imshow(t['previous_image'],cmap='gray')
    for mask,color,label in [(t['valid'],'#5be0bc','FB retained'),(t['forward_valid']&~t['valid'],'#fa5b70','FB rejected')]:
        ids=np.flatnonzero(mask)[::max(1,int(mask.sum())//160)]
        a=t['previous'][ids];delta=t['current'][ids]-a
        ax.quiver(a[:,0],a[:,1],delta[:,0],delta[:,1],angles='xy',scale_units='xy',scale=1,color=color,width=.003,label=label)
    ax.legend(loc='upper right',fontsize=9);ax.set(xlabel='u (px)',ylabel='v (px)')
    finish(fig,'14_lk_tracks',['artifacts/tracking/000000.npz'],'원래 픽셀 길이의 흐름 벡터. 표시 개수만 줄였으며 전후방 mask는 전체 관측에 적용한다.')

    fig,ax=canvas('Actual: LK forward-backward round-trip error')
    histogram(ax,np.minimum(t['fb'][t['forward_valid']],5),'Forward-valid observations',color='#168a80')
    ax.axvline(1,c='#d04d50',ls='--',label='FB threshold');ax.legend()
    ax.set(xlabel='Round-trip error (px; clipped at 5)',ylabel='Tracks')
    finish(fig,'15_lk_fb_distribution',['artifacts/tracking/000000.npz'],'전후방 추적은 자기 일관성 검사이며 flow GT 정확도가 아니다. 잘못된 반복 무늬도 통과할 수 있다.')

    fig,ax=canvas('Actual: LK patch error versus round-trip error')
    mask=t['forward_valid'];ax.scatter(t['lk_error'][mask],np.minimum(t['fb'][mask],5),s=6,c='#168a80')
    ax.axhline(1,c='#d04d50',ls='--');ax.set(xlabel='OpenCV LK patch error (intensity units)',ylabel='FB error (px; clipped at 5)')
    finish(fig,'16_lk_error_scatter',['artifacts/tracking/000000.npz'],'LK patch 밝기 잔차와 기하적 왕복 잔차는 서로 다른 기준이다.')

    fig,ax=canvas('Actual: pose-only LM on the SAME RANSAC inliers')
    histogram(ax,p['before'],'EPNP / RANSAC',alpha=.55,color='#d04d50')
    histogram(ax,p['after'],'LM refined',alpha=.55,color='#168a80')
    ax.set(xlabel='Current-image reprojection residual (px)',ylabel='Inliers');ax.legend()
    finish(fig,'17_pose_only_refinement',['artifacts/reprojection/000000.npz'],'3D점을 고정하고 자세만 LM 최적화한다. 같은 inlier의 재투영 개선이며 joint BA나 일반화 평가가 아니다.')


def odometry_figures(start,stop):
    name=f'{start:06d}_{stop:06d}'
    e=np.load(ART/f'evaluation/{name}/stages.npz')
    raw=np.load(ART/f'odometry/{name}/poses.npz')
    stats=json.loads((ART/f'evaluation/{name}/metrics.json').read_text())
    rows=list(csv.DictReader((ART/f'odometry/{name}/frames.csv').open()))
    frames=np.array([int(r['frame']) for r in rows])
    source=[f'artifacts/evaluation/{name}/stages.npz',f'artifacts/odometry/{name}/frames.csv']
    def values(key):return np.array([float(r[key]) if r[key] else np.nan for r in rows])
    for method in ('stereo_fb','mono_unit'):
        title='Metric stereo: no fitted scale' if method=='stereo_fb' else 'Mono unit steps: evaluation-only Sim3 fit'
        fig,ax=canvas(f'Actual {start}:{stop} | {title}',5.8)
        ax.plot(e['gt'][:,0,3],e['gt'][:,2,3],c='black',label='GT')
        ax.plot(e[method][:,0,3],e[method][:,2,3],c='#168a80',label=method)
        ax.scatter(e[method][0,0,3],e[method][0,2,3],marker='o',c='#d04d50',label='Start')
        ax.set(xlabel='Start-camera X (m)',ylabel='Start-camera Z (m)');ax.set_aspect('equal');ax.legend()
        finish(fig,name+'_'+method+'_trajectory',source,'스테레오는 척도 적합 없음. 단안은 GT로 Sim3 적합한 형태 진단이므로 두 그림을 공정한 정확도 순위로 해석하지 않는다.')
    fig,ax=canvas(f'Actual {start}:{stop} | metric stereo error over time')
    for method,label,color in [('stereo_fb','LK + FB','#168a80'),('stereo_forward','LK forward only','#d04d50')]:
        ax.plot(e['frames'],e[method+'_error_m'],label=label,color=color)
    ax.set(xlabel='Sequence frame',ylabel='Position error (m), no scale fitting');ax.legend()
    finish(fig,name+'_metric_errors',source,'동일 구간·metric 척도의 FB on/off 비교. 개선 또는 악화를 있는 그대로 표시한다.')
    fig,ax=canvas(f'Actual {start}:{stop} | observations retained by stage')
    for key,label in [('stereo_valid','Stereo 3D'),('pnp_input','3D + temporal FB'),('pnp_inliers','PnP inliers'),('essential_inliers','E cheirality')]:
        ax.plot(frames,values(key),label=label,lw=1)
    ax.set(xlabel='Sequence frame',ylabel='Observations');ax.legend(ncol=2)
    finish(fig,name+'_inlier_counts',source,'E는 전체 ORB의 temporal track, PnP는 stereo 유효 3D 부분집합을 사용한다. 같은 관측 수의 비교가 아니다.')
    fig,ax=canvas(f'Actual {start}:{stop} | speed variation cannot fit one scale')
    gt_steps=np.linalg.norm(np.diff(e['gt'][:,:3,3],axis=0),axis=1)
    mono_steps=np.linalg.norm(np.diff(raw['mono_unit'][:,:3,3],axis=0),axis=1)*stats['mono_unit']['evaluation_scale']
    ax.plot(frames,gt_steps,c='black',label='GT displacement (evaluation)')
    ax.plot(frames,values('stereo_step_m'),label='Metric stereo',c='#168a80')
    ax.plot(frames,mono_steps,label='Mono unit x fitted scale',c='#d04d50',alpha=.8)
    ax.set(xlabel='Sequence frame',ylabel='Displacement per frame (m)');ax.legend()
    finish(fig,name+'_step_scale',source+[f'artifacts/odometry/{name}/poses.npz'],'단안의 성공 이동량은 항상 1이며 실패는 0이다. 하나의 Sim3 scale은 실제 속도 변화나 잃은 이동을 복원하지 못한다.')
    fig,ax=canvas(f'Actual {start}:{stop} | 1-frame relative pose errors')
    for method,label in [('stereo_fb','Stereo + FB'),('stereo_forward','Stereo forward')]:
        ax.plot(frames,e[method+'_rpe_m'],label=label,lw=1)
    ax.set(xlabel='Sequence frame',ylabel='Translation RPE (m)');ax.legend()
    finish(fig,name+'_relative_errors',source,'1-frame RPE이며 KITTI 공식 100..800m 구간 점수가 아니다. 회전 RPE는 별도 CSV/JSON에 보존한다.')
    fig,ax=canvas(f'Actual {start}:{stop} | FB ablation: metric ATE and holds')
    names=['Forward only','Forward + FB']; methods=['stereo_forward','stereo_fb']
    bars=ax.bar(names,[stats[m]['ate_rmse_m'] for m in methods],color=['#d04d50','#168a80'])
    ax.set_ylabel('Metric ATE RMSE (m)')
    for bar,key in zip(bars,['pnp_forward_status','pnp_status']):
        held=sum(r[key]!='tracked' for r in rows)
        ax.text(bar.get_x()+bar.get_width()/2,bar.get_height(),f'{bar.get_height():.3f} m\nheld={held}',ha='center',va='bottom',fontsize=11)
    ax.set_ylim(0,max(bar.get_height() for bar in bars)*1.3+.01)
    finish(fig,name+'_fb_ablation',source,'FB 게이트 외 동일 설정. RANSAC 입력 집합 변화로 결과가 달라진다. 인과적 일반화나 성능 개선 보장은 아니다.')
    worst=int(frames[np.argmax(e['stereo_fb_rpe_m'])]); stage=np.load(ART/f'odometry/{name}/{worst:06d}.npz')
    # Source image is the previous frame already preserved in diagnostic inputs only
    # when available; this overlay uses the immutable KITTI input directly.
    from common import image
    fig,ax=canvas(f'Actual {start}:{stop} | largest stereo RPE at frame {worst}',3.8)
    ax.imshow(image(worst),cmap='gray')
    b=stage['current_pixels'][stage['fb_mask']]; mask=np.zeros(len(b),bool);mask[stage['pnp_inlier_indices']]=True
    ax.scatter(b[~mask,0],b[~mask,1],s=9,c='#fa5b70',label='PnP rejected')
    ax.scatter(b[mask,0],b[mask,1],s=6,c='#5be0bc',label='PnP retained')
    ax.set(xlabel='u (px)',ylabel='v (px)');ax.legend(fontsize=9)
    finish(fig,name+'_worst_frame',source+[f'artifacts/odometry/{name}/{worst:06d}.npz',f'data/kitti/dataset/sequences/00/image_0/{worst:06d}.png'],'평가에서 최대 RPE 프레임을 사후 선택한 진단. 동적 객체·가림 여부는 GT mask가 없어 확정하지 않는다.')


def synthetic_figures():
    u=np.load(ART/'synthetic/uncertainty.npz')
    fig,ax=canvas('SYNTHETIC: fixed disparity noise grows with depth')
    ax.plot(u['z_m'],u['sigma_z_m'],label='First-order derivative',c='#168a80')
    ax.plot(u['z_m'],u['empirical_std_m'],label='Monte Carlo: 10,000/depth',c='#d04d50',ls='--')
    ax.set(xlabel='True depth (m)',ylabel='Depth standard deviation (m)');ax.legend()
    finish(fig,'synthetic_depth_uncertainty',['artifacts/synthetic/uncertainty.npz'],'합성 disparity Gaussian sigma=0.5px. 원거리에서 비선형 변환 때문에 1차 근사와 Monte Carlo가 달라진다. KITTI 오차 추정이 아니다.','synthetic')
    d=np.load(ART/'synthetic/distortion.npz')
    fig,ax=canvas('SYNTHETIC: invented radial / tangential lens distortion',4)
    for key,label,color in [('ideal','Ideal grid','#168a80'),('distorted','Distorted grid','#d04d50')]:
        ax.scatter(*d[key].T,s=8,label=label,c=color)
    ax.set(xlabel='u (px)',ylabel='v (px)');ax.invert_yaxis();ax.set_aspect('equal');ax.legend()
    finish(fig,'synthetic_lens_distortion',['artifacts/synthetic/distortion.npz'],'렌즈 계수는 설명용으로 만든 값이다. 이미 정류된 KITTI 영상에 이 계수를 적용하지 않는다.','synthetic')
    fig,ax=canvas('SYNTHETIC: distortion grows away from principal point')
    displacement=np.linalg.norm(d['distorted']-d['ideal'],axis=1)
    radius=np.linalg.norm(d['ideal']-d['K'][:2,2],axis=1)
    ax.scatter(radius,displacement,s=10,c='#168a80')
    ax.set(xlabel='Distance from principal point (px)',ylabel='Distortion displacement (px)')
    finish(fig,'synthetic_distortion_radius',['artifacts/synthetic/distortion.npz'],'알려진 왜곡 모델의 역변환은 실제 보정 파라미터 추정과 다르다. undistortion 수치 오차는 summary에 기록한다.','synthetic')
    rows=list(csv.DictReader((ART/'synthetic/degeneracy.csv').open()))
    cases=['normal','pure_rotation','far_depth','planar','tiny_translation']
    fig,ax=canvas('SYNTHETIC: essential-pose acceptance is not observability')
    counts=[sum(r['E_accepted']=='True' for r in rows if r['case']==c) for c in cases]
    ax.barh([c.replace('_',' ') for c in cases],counts,color='#168a80');ax.set(xlabel='Accepted estimates out of 20 trials',xlim=(0,22))
    for i,c in enumerate(counts):ax.text(c+.2,i,str(c),va='center')
    finish(fig,'synthetic_degeneracy',['artifacts/synthetic/degeneracy.csv','artifacts/synthetic/degeneracy.npz'],'순수 회전·작은 이동·먼 점·평면에서 accepted만으로 이동 방향의 신뢰성을 보장하지 않는다. PnP에는 합성 exact 3D를 주므로 공정한 stereo 비교가 아니다.','synthetic')


def main():
    MANIFEST.clear()
    diagnostic_figures()
    for start,stop in CFG['segments']:odometry_figures(start,stop)
    synthetic_figures()
    save_json(FIG/'figure_manifest.json',MANIFEST)
    print(f'Figures: {len(MANIFEST)} (actual={sum(x["kind"]=="actual KITTI" for x in MANIFEST)})',flush=True)
    return len(MANIFEST)


if __name__=='__main__':main()
