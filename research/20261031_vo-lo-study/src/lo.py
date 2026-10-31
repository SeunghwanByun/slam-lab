import time
from scipy.spatial import cKDTree
from kiss_icp.config import KISSConfig
from kiss_icp.kiss_icp import KissICP
from common import *


def main():
    out=directory('lo'); config=KISSConfig()
    config.data.min_range=CFG['lo_min_range_m']; config.data.max_range=CFG['lo_max_range_m']
    config.data.deskew=CFG['lo_deskew']; config.mapping.voxel_size=CFG['lo_voxel_size_m']
    config.registration.max_num_threads=CFG['lo_max_threads']
    save_json(out/'effective_config.json',config.model_dump())
    odometry=KissICP(config); poses=[]; rows=[]
    for i in range(CFG['frames']):
        raw=np.fromfile(SEQ/'velodyne'/f'{i:06d}.bin',dtype='<f4').reshape(-1,4)
        assert np.isfinite(raw).all()
        xyz=raw[:,:3].astype(np.float64)
        prediction=odometry.last_pose@odometry.last_delta
        sigma=odometry.adaptive_threshold.get_threshold()
        diagnostic=i in CFG['diagnostic_frames']
        target=odometry.local_map.point_cloud().copy() if diagnostic else None
        start=time.perf_counter()
        filtered,source=odometry.register_frame(xyz,np.zeros(len(xyz)))
        duration=time.perf_counter()-start
        pose=odometry.last_pose.copy(); poses.append(pose)
        rows.append(dict(frame=i,raw_points=len(raw),filtered_points=len(filtered),source_points=len(source),sigma_m=sigma,seconds=duration))
        if diagnostic:
            tree=cKDTree(target)
            before=transform(source,prediction); after=transform(source,pose)
            db,ib=tree.query(before); da,ia=tree.query(after)
            # Distances are independent nearest-neighbor diagnostics, not internal C++ correspondences.
            np.savez_compressed(out/f'{i:06d}.npz',raw=raw,filtered=filtered,source=source,target=target,prediction=prediction,pose=pose,before_distance=db,after_distance=da,before_target_index=ib,after_target_index=ia)
            fig,axes=plt.subplots(1,3,figsize=(13,4))
            for ax,cloud,title in zip(axes,[xyz,filtered,source],['Raw','Range filtered','Voxel source']):
                ax.scatter(cloud[::max(1,len(cloud)//15000),0],cloud[::max(1,len(cloud)//15000),1],s=.2); ax.set_title(f'{title}: {len(cloud)}'); ax.set(xlim=(-50,50),ylim=(-50,50),xlabel='LiDAR x (m)',ylabel='LiDAR y (m)'); ax.set_aspect('equal')
            finish(fig,f'lo_preprocess_{i:03d}.png')
            fig,axes=plt.subplots(1,3,figsize=(13,4))
            center=pose[:2,3]
            for ax,cloud,title in zip(axes[:2],[before,after],['Motion prediction','ICP estimate']):
                ax.scatter(target[::8,0],target[::8,1],s=.2,c='gray'); ax.scatter(cloud[:,0],cloud[:,1],s=.4,c='teal'); ax.set(xlim=(center[0]-25,center[0]+25),ylim=(center[1]-25,center[1]+25),xlabel='World LiDAR x (m)',ylabel='World LiDAR y (m)'); ax.set_aspect('equal'); ax.set_title(title)
            axes[2].hist(np.minimum(db,3),bins=40,alpha=.5,label='predicted'); axes[2].hist(np.minimum(da,3),bins=40,alpha=.5,label='registered'); axes[2].legend(); axes[2].set(xlabel='Nearest-map distance (m), capped 3',ylabel='Points')
            finish(fig,f'lo_registration_{i:03d}.png')
        if i%25==0: print(f'LO {i}/{CFG["frames"]}',flush=True)
    poses=np.array(poses); check_poses(poses); np.save(out/'poses_lidar.npy',poses)
    _,tr=calibration(); camera=np.array([tr@p@np.linalg.inv(tr) for p in poses]); camera=np.linalg.inv(camera[0])@camera
    check_poses(camera); np.save(out/'poses_camera.npy',camera); save_csv(out/'frames.csv',rows)
    cloud=odometry.local_map.point_cloud(); np.save(out/'final_local_map.npy',cloud)
    fig,ax=plt.subplots(figsize=(9,7)); s=cloud[::4]; ax.scatter(s[:,0],s[:,1],c=s[:,2],s=.2,cmap='viridis',vmin=-3,vmax=3); ax.plot(poses[:,0,3],poses[:,1,3],c='tomato'); ax.set_aspect('equal'); ax.set(title='KISS-ICP final rolling local map (not loop-closed SLAM)',xlabel='World LiDAR x (m)',ylabel='World LiDAR y (m)'); finish(fig,'lo_local_map.png')
    print('LO poses and local map verified',flush=True)


if __name__=='__main__': main()
