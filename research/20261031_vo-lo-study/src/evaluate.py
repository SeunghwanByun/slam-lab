import hashlib
import importlib.metadata
import platform
import subprocess
from common import *


def sim3(poses, truth):
    a=poses[:,:3,3]; b=truth[:,:3,3]; ac=a-a.mean(0); bc=b-b.mean(0)
    u,s,vt=np.linalg.svd(bc.T@ac/len(a)); sign=np.ones(3); sign[-1]=np.linalg.det(u@vt)
    rotation=u@np.diag(sign)@vt; scale=float((s*sign).sum()/(ac*ac).sum()*len(a))
    translation=b.mean(0)-scale*rotation@a.mean(0)
    aligned=poses.copy(); aligned[:,:3,:3]=rotation@poses[:,:3,:3]
    aligned[:,:3,3]=scale*(a@rotation.T)+translation
    return aligned,scale


def metrics(poses,gt):
    errors=np.linalg.norm(poses[:,:3,3]-gt[:,:3,3],axis=1)
    relative=np.linalg.inv(poses[:-1])@poses[1:]
    gt_relative=np.linalg.inv(gt[:-1])@gt[1:]
    residual=np.linalg.inv(gt_relative)@relative
    rotation=np.rad2deg(np.arccos(np.clip((np.trace(residual[:,:3,:3],axis1=1,axis2=2)-1)/2,-1,1)))
    return dict(position_rmse_m=float(np.sqrt(np.mean(errors**2))),endpoint_m=float(errors[-1]),
                rpe_translation_rmse_m=float(np.sqrt(np.mean(np.sum(residual[:,:3,3]**2,axis=1)))),
                rpe_rotation_rmse_deg=float(np.sqrt(np.mean(rotation**2)))),errors,rotation


def main():
    out=directory('evaluation')
    gt=np.repeat(np.eye(4)[None],CFG['frames'],axis=0)
    gt[:,:3]=np.loadtxt(DATA/'poses'/f'{CFG["sequence"]}.txt')[:CFG['frames']].reshape(-1,3,4)
    gt=np.linalg.inv(gt[0])@gt
    raw={v:np.load(ART/'vo'/v/'poses.npy') for v in CFG['vo_variants']}
    lo=np.load(ART/'lo/poses_camera.npy'); check_poses(lo); check_poses(gt)
    summary={}; results={}; curves={}; rotations={}
    summary['lo_metric'],curves['lo_metric'],rotations['lo_metric']=metrics(lo,gt)
    results['lo_metric']=lo
    for name,pose in {**raw,'lo':lo}.items():
        aligned,scale=sim3(pose,gt); stat,err,rotation=metrics(aligned,gt)
        stat['gt_fit_scale']=scale; summary[name+'_sim3']=stat; results[name+'_sim3']=aligned; curves[name+'_sim3']=err; rotations[name+'_sim3']=rotation
    # Unit tests for evaluation conventions: a known similarity must recover truth.
    synthetic=gt.copy(); synthetic[:,:3,3]=gt[:,:3,3]*3+np.array([10,20,30])
    fitted,scale=sim3(synthetic,gt)
    assert np.allclose(fitted[:,:3,3],gt[:,:3,3],atol=1e-6) and abs(scale-1/3)<1e-6
    assert metrics(gt,gt)[0]['position_rmse_m']==0
    assert np.max(np.abs(results['lo_metric'][0]-np.eye(4)))<1e-6
    np.savez_compressed(out/'aligned_poses.npz',gt=gt,**results)
    stat_rows=[]
    for name in ['baseline','ratio','lo']:
        p=ART/'lo/frames.csv' if name=='lo' else ART/'vo'/name/'frames.csv'
        with p.open() as f: rows=list(csv.DictReader(f))
        durations=np.array([float(r['seconds']) for r in rows])
        stat=dict(method=name,frames=len(rows),median_ms=float(np.median(durations)*1000),p95_ms=float(np.percentile(durations,95)*1000))
        if name!='lo':
            fractions=np.array([int(r['inliers'])/max(1,int(r['matches'])) for r in rows])
            stat.update(held=sum(r['status']!='tracked' for r in rows),inlier_median=float(np.median(fractions)),inlier_min=float(fractions.min()),worst_inlier_frame=int(rows[int(fractions.argmin())]['frame']))
        summary[name+'_runtime']=stat
        stat_rows.append(stat)
    save_json(out/'metrics.json',summary)
    save_csv(out/'frame_errors.csv',[dict(frame=i,**{k:float(v[i]) for k,v in curves.items()}) for i in range(CFG['frames'])])
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    for ax in axes: ax.plot(gt[:,0,3],gt[:,2,3],c='black',label='GT'); ax.set_aspect('equal'); ax.set(xlabel='Camera0 X (m)',ylabel='Camera0 Z (m)')
    axes[0].plot(lo[:,0,3],lo[:,2,3],label='LO metric',c='teal'); axes[0].set_title('Metric LO: no GT scale fitting')
    for name,p in results.items():
        if name.endswith('sim3'): axes[1].plot(p[:,0,3],p[:,2,3],label=name)
    axes[1].set_title('All methods: GT-fitted Sim(3) shape diagnostic')
    for ax in axes: ax.legend(fontsize=8)
    finish(fig,'comparison_trajectory.png')
    fig,axes=plt.subplots(2,1,figsize=(11,6))
    for name,values in curves.items(): axes[0].plot(values,label=name)
    for name,values in rotations.items():
        if name!='lo_sim3': axes[1].plot(np.arange(1,len(gt)),values,label=name)
    axes[0].set(ylabel='Position error (m)',xlabel='Frame'); axes[1].set(ylabel='1-frame rotation error (deg)',xlabel='Frame')
    for ax in axes: ax.legend(fontsize=8)
    finish(fig,'comparison_errors.png')
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    for name in CFG['vo_variants']:
        with (ART/'vo'/name/'frames.csv').open() as f: rows=list(csv.DictReader(f))
        axes[0].plot([int(r['frame']) for r in rows],[int(r['inliers'])/max(1,int(r['matches'])) for r in rows],label=name)
        axes[1].hist([int(r['matches']) for r in rows],bins=20,alpha=.5,label=name)
    axes[0].set(xlabel='Frame',ylabel='Pose inlier fraction'); axes[1].set(xlabel='Matches',ylabel='Frames')
    for ax in axes:ax.legend()
    finish(fig,'comparison_matching.png')
    # Spatial color is depth, not an RGB camera: use original grayscale and projected LiDAR.
    K,tr=calibration(); scan=np.fromfile(SEQ/'velodyne/000120.bin',dtype='<f4').reshape(-1,4)
    pc=transform(scan[:,:3],tr); pc=pc[pc[:,2]>0]; uv=pc@K.T; uv=uv[:,:2]/uv[:,2,None]
    img=image(120); mask=(uv[:,0]>=0)&(uv[:,0]<img.shape[1])&(uv[:,1]>=0)&(uv[:,1]<img.shape[0])
    np.savez_compressed(out/'projection_120.npz',pixels=uv[mask],depth_m=pc[mask,2],Tr=tr,K=K)
    fig,ax=plt.subplots(figsize=(12,4)); ax.imshow(img,cmap='gray'); dots=ax.scatter(uv[mask,0],uv[mask,1],c=pc[mask,2],s=.8,cmap='turbo',vmin=0,vmax=60);fig.colorbar(dots,ax=ax,label='LiDAR depth (m)');ax.axis('off');ax.set_title('Frame 120: LiDAR projection on grayscale (depth-colored, not RGB)');finish(fig,'lidar_camera_projection.png')
    versions={dist.metadata['Name']:dist.version for dist in importlib.metadata.distributions()}
    save_json(out/'environment.json',dict(python=platform.python_version(),platform=platform.platform(),versions=versions,
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        config_sha256=hashlib.sha256((STUDY/'configs/experiment.json').read_bytes()).hexdigest(),
        calibration_sha256=hashlib.sha256((SEQ/'calib.txt').read_bytes()).hexdigest()))
    (STUDY/'configs/requirements-lock.txt').write_text('\n'.join(f'{name}=={version}' for name,version in sorted(versions.items()))+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
