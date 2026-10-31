from scipy.spatial import cKDTree
from common import *


def main():
    out=directory('geometry'); i=136; z=np.load(ART/'vo/baseline'/f'{i:06d}.npz')
    K,_=calibration(); F=np.linalg.inv(K).T@z['E']@np.linalg.inv(K)
    a=z['points_previous']; b=z['points_current']; ah=np.c_[a,np.ones(len(a))]; bh=np.c_[b,np.ones(len(b))]
    lines=(F@ah.T).T; dist=np.abs(np.sum(lines*bh,axis=1))/np.maximum(np.linalg.norm(lines[:,:2],axis=1),1e-9)
    accepted=z['pose_mask'].ravel()!=0
    np.savez_compressed(out/'epipolar.npz',F=F,lines=lines,distance_px=dist,accepted=accepted)
    fig,axes=plt.subplots(1,2,figsize=(13,4)); img=image(i);axes[0].imshow(img,cmap='gray')
    ids=np.flatnonzero(accepted)[::max(1,int(accepted.sum())//12)][:12]
    for j in ids:
        l=lines[j]; x=np.array([0,img.shape[1]-1]); y=-(l[0]*x+l[2])/l[1]
        axes[0].plot(x,y,linewidth=.5);axes[0].scatter(*b[j],s=8)
    axes[0].set(xlim=(0,img.shape[1]),ylim=(img.shape[0],0),title='Epipolar lines and accepted observations (frame 136)')
    for ok,label in [(True,'Pose inlier'),(False,'Rejected')]:axes[1].hist(np.minimum(dist[accepted==ok],10),bins=30,alpha=.5,label=label)
    axes[1].set(xlabel='Point-to-epipolar-line distance (px), capped 10',ylabel='Matches');axes[1].legend();finish(fig,'vo_epipolar.png')
    # Educational point-to-point ICP on an actual saved scan/map pair, not KISS internal iterates.
    z=np.load(ART/'lo/000120.npz'); source=z['source']; target=z['target']; tree=cKDTree(target)
    pose=z['prediction'].copy(); rows=[]; states=[]
    for iteration in range(20):
        world=transform(source,pose); d,idx=tree.query(world); valid=d<1.0
        a=world[valid]; b=target[idx[valid]]
        if len(a)<6:raise RuntimeError('Insufficient educational ICP pairs')
        ac=a-a.mean(0);bc=b-b.mean(0);u,s,vt=np.linalg.svd(ac.T@bc)
        r=vt.T@u.T
        if np.linalg.det(r)<0:vt[-1]*=-1;r=vt.T@u.T
        t=b.mean(0)-r@a.mean(0);delta=np.eye(4);delta[:3,:3]=r;delta[:3,3]=t
        rows.append(dict(iteration=iteration,pairs=len(a),rmse_m=float(np.sqrt(np.mean(d[valid]**2))),rotation_update_deg=float(np.rad2deg(np.arccos(np.clip((np.trace(r)-1)/2,-1,1)))),translation_update_m=float(np.linalg.norm(t))))
        states.append(pose.copy());pose=delta@pose
    save_csv(out/'educational_icp.csv',rows);np.save(out/'educational_icp_poses.npy',states)
    fig,axes=plt.subplots(1,2,figsize=(12,4)); axes[0].plot([r['rmse_m'] for r in rows],marker='o');axes[0].set(xlabel='ICP iteration',ylabel='Gated nearest-neighbor RMSE (m)',title='Educational fixed-gate ICP, not KISS internal history')
    before=transform(source,z['prediction']);d,idx=tree.query(before);ids=np.flatnonzero(d<1)[::70]
    axes[1].scatter(target[::10,0],target[::10,1],s=.2,c='gray')
    for j in ids: axes[1].plot([before[j,0],target[idx[j],0]],[before[j,1],target[idx[j],1]],c='tomato',linewidth=.5)
    c=z['pose'][:2,3];axes[1].set(xlim=(c[0]-15,c[0]+15),ylim=(c[1]-15,c[1]+15),xlabel='World LiDAR x (m)',ylabel='World LiDAR y (m)',title='Initial nearest-neighbor pair examples');axes[1].set_aspect('equal');finish(fig,'lo_icp_steps.png')
    save_json(out/'summary.json',dict(epipolar_inlier_median_px=float(np.median(dist[accepted])),epipolar_rejected_median_px=float(np.median(dist[~accepted])),icp_initial_rmse_m=rows[0]['rmse_m'],icp_last_rmse_m=rows[-1]['rmse_m']))
    print('Epipolar and educational ICP steps saved')


if __name__=='__main__': main()
