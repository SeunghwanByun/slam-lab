import time
from common import *


def run(variant):
    out=directory('vo/'+variant); K,_=calibration()
    orb=cv2.ORB_create(nfeatures=CFG['orb_features']); poses=[np.eye(4)]; rows=[]
    previous=image(0); pk,pd=orb.detectAndCompute(previous,None)
    for i in range(1,CFG['frames']):
        current=image(i); start=time.perf_counter(); kp,desc=orb.detectAndCompute(current,None)
        if pd is None or desc is None: matches=[]
        elif variant=='baseline': matches=sorted(cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck=True).match(pd,desc),key=lambda m:m.distance)[:CFG['match_limit']]
        else:
            pairs=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(pd,desc,k=2)
            matches=sorted([p[0] for p in pairs if len(p)==2 and p[0].distance<CFG['ratio_threshold']*p[1].distance],key=lambda m:m.distance)[:CFG['match_limit']]
        a=np.float32([pk[m.queryIdx].pt for m in matches]).reshape(-1,2)
        b=np.float32([kp[m.trainIdx].pt for m in matches]).reshape(-1,2)
        pose=poses[-1].copy(); status='held'; mask=np.zeros((len(matches),1),np.uint8); E=np.empty((0,3)); R=np.eye(3); t=np.zeros((3,1)); essential_mask=mask.copy()
        if len(matches)>=8:
            try:
                cv2.setRNGSeed(CFG['seed']+i)
                E,mask=cv2.findEssentialMat(a,b,K,method=cv2.RANSAC,prob=CFG['ransac_probability'],threshold=CFG['ransac_threshold_px'])
                if E is None: raise ValueError('No E')
                essential_mask=mask.copy()
                n,R,t,mask=cv2.recoverPose(E,a,b,K,mask=mask)
                if n>=5:
                    relative=np.eye(4); relative[:3,:3]=R; relative[:3,3]=t.ravel()
                    pose=pose@np.linalg.inv(relative); status='tracked'
            except (cv2.error,ValueError): status='failed-held'
        duration=time.perf_counter()-start
        poses.append(pose)
        rows.append(dict(frame=i,features=len(kp),matches=len(matches),inliers=int(np.count_nonzero(mask)),status=status,seconds=duration))
        np.savez_compressed(out/f'{i:06d}.npz',points_previous=a,points_current=b,distances=[m.distance for m in matches],E=E if E is not None else np.empty((0,3)),R=R,t=t,essential_mask=essential_mask,pose_mask=mask)
        if i in CFG['diagnostic_frames'] and variant=='baseline':
            drawn=cv2.drawMatches(previous,pk,current,kp,matches[:100],None,matchColor=(0,190,80),singlePointColor=(180,180,180),matchesMask=[int(v) for v in mask.ravel()[:100]!=0],flags=2)
            fig,ax=plt.subplots(figsize=(13,4)); ax.imshow(cv2.cvtColor(drawn,cv2.COLOR_BGR2RGB)); ax.axis('off'); ax.set_title(f'Frames {i-1}->{i}: {np.count_nonzero(mask)}/{len(matches)} pose inliers (best 100 shown)'); finish(fig,f'vo_matches_{i:03d}.png')
        previous,pk,pd=current,kp,desc
    poses=np.array(poses); check_poses(poses); np.save(out/'poses.npy',poses); save_csv(out/'frames.csv',rows)
    print(f'VO {variant}: {len(poses)} poses saved',flush=True)


if __name__=='__main__':
    for variant in CFG['vo_variants']: run(variant)
