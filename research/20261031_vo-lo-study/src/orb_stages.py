"""Educational ORB stages and actual OpenCV outputs; not an exact ORB reimplementation."""
from common import *


def main():
    out = directory('orb'); img = image(120)
    pyramid = [cv2.resize(img, None, fx=1/1.2**i, fy=1/1.2**i) for i in range(4)]
    np.savez_compressed(out / 'pyramid.npz', **{f'level_{i}':v for i,v in enumerate(pyramid)})
    fig, axes = plt.subplots(2, 2, figsize=(12,5))
    for i,(ax,p) in enumerate(zip(axes.flat,pyramid)):
        ax.imshow(p,cmap='gray'); ax.set_title(f'Level {i}, shape={p.shape}'); ax.axis('off')
    finish(fig,'orb_01_pyramid.png')
    fast = cv2.FastFeatureDetector_create(threshold=20, nonmaxSuppression=True)
    candidates = fast.detect(img)
    response = cv2.cornerHarris(img, 7, 3, .04)
    valid = [p for p in candidates if 20 < p.pt[0] < img.shape[1]-20 and 20 < p.pt[1] < img.shape[0]-20]
    ranked = sorted(valid, key=lambda p:response[round(p.pt[1]), round(p.pt[0])], reverse=True)[:500]
    np.savez_compressed(out/'fast_harris.npz', fast=np.array([p.pt for p in candidates]),
                        selected=np.array([p.pt for p in ranked]), response=response)
    fig, axes=plt.subplots(2,1,figsize=(12,7))
    for ax,ps,title in zip(axes,[candidates,ranked],[f'FAST candidates: {len(candidates)}','Harris-ranked top 500 (education, level 0)']):
        ax.imshow(cv2.drawKeypoints(img,ps,None,color=(255,200,0))); ax.set_title(title); ax.axis('off')
    finish(fig,'orb_02_fast_harris.png')
    angles=[]; yy,xx=np.mgrid[-15:16,-15:16]; disk=xx*xx+yy*yy<=225
    for p in ranked:
        x,y=map(round,p.pt); patch=img[y-15:y+16,x-15:x+16].astype(float)
        angles.append(float(np.arctan2((yy*patch*disk).sum(),(xx*patch*disk).sum())))
    np.save(out/'centroid_angles.npy',angles)
    fig,ax=plt.subplots(figsize=(12,4)); ax.imshow(img,cmap='gray')
    xy=np.array([p.pt for p in ranked[:100]]); angle=np.array(angles[:100])
    ax.quiver(xy[:,0],xy[:,1],15*np.cos(angle),15*np.sin(angle),angles='xy',scale_units='xy',scale=1,color='yellow')
    ax.set_title('Intensity-centroid orientations: educational implementation'); ax.axis('off'); finish(fig,'orb_03_orientation.png')
    # Random tests illustrate steering only; ORB's learned rBRIEF pattern is NOT reproduced.
    rng=np.random.default_rng(CFG['seed']); pairs=rng.integers(-10,11,(256,2,2))
    angle=angles[0]; rot=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    steered=np.rint(pairs @ rot.T).astype(int); x,y=map(round,ranked[0].pt)
    smooth=cv2.GaussianBlur(img,(7,7),2)
    bits=smooth[y+steered[:,0,1],x+steered[:,0,0]] < smooth[y+steered[:,1,1],x+steered[:,1,0]]
    orb=cv2.ORB_create(nfeatures=CFG['orb_features']); kp,desc=orb.detectAndCompute(img,None)
    np.savez_compressed(out/'descriptors.npz',demo_pairs=pairs,demo_steered=steered,demo_bits=bits,
                        actual_keypoints=np.array([p.pt for p in kp]),actual_angles=[p.angle for p in kp],actual_descriptors=desc)
    fig,axes=plt.subplots(1,3,figsize=(13,4)); axes[0].imshow(img[y-20:y+21,x-20:x+21],cmap='gray')
    for pair in steered[:16]: axes[0].plot(pair[:,0]+20,pair[:,1]+20,alpha=.6)
    axes[0].set_title('16 steered tests (educational)'); axes[1].imshow(bits.reshape(16,16),cmap='gray'); axes[1].set_title('256 demo bits')
    axes[2].imshow(np.unpackbits(desc[:32],axis=1),aspect='auto',cmap='gray'); axes[2].set_title('Actual ORB: 32 x 256 bits')
    finish(fig,'orb_04_descriptor.png')
    # Known synthetic rotation measures geometric match correctness, not real-scene truth.
    matrix=cv2.getRotationMatrix2D((img.shape[1]/2,img.shape[0]/2),CFG['synthetic_rotation_deg'],1)
    warped=cv2.warpAffine(img,matrix,(img.shape[1],img.shape[0]))
    kp2,desc2=orb.detectAndCompute(warped,None)
    bf=cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck=True)
    matches=sorted(bf.match(desc,desc2),key=lambda m:m.distance)
    a=np.array([kp[m.queryIdx].pt for m in matches]); b=np.array([kp2[m.trainIdx].pt for m in matches])
    error=np.linalg.norm(a@matrix[:,:2].T+matrix[:,2]-b,axis=1)
    rows=[dict(distance=m.distance,error_px=float(e),correct=bool(e<CFG['geometry_tolerance_px'])) for m,e in zip(matches,error)]
    save_csv(out/'synthetic_rotation.csv',rows)
    selected=matches[:80]
    overlay=cv2.drawMatches(img,kp,warped,kp2,selected,None,flags=2)
    fig,axes=plt.subplots(2,1,figsize=(12,7)); axes[0].imshow(cv2.cvtColor(overlay,cv2.COLOR_BGR2RGB)); axes[0].axis('off'); axes[0].set_title('Actual ORB matches under known 30 degree warp')
    for good,color in [(True,'teal'),(False,'tomato')]:
        distances=[r['distance'] for r in rows if r['correct']==good]
        axes[1].hist(distances,bins=np.arange(0,257,8),alpha=.6,label='correct <3px' if good else 'incorrect >=3px',color=color)
    axes[1].legend(); axes[1].set(xlabel='Hamming distance',ylabel='Count'); finish(fig,'orb_05_synthetic.png')
    # Compare orientation-aware and forced-zero descriptors at SAME detected keypoint positions.
    def zero_angle(points):
        return [cv2.KeyPoint(p.pt[0],p.pt[1],p.size,0,p.response,p.octave,p.class_id) for p in points]
    ka,da=orb.compute(img,zero_angle(kp)); kb,db=orb.compute(warped,zero_angle(kp2))
    unsteered=bf.match(da,db)
    a0=np.array([ka[m.queryIdx].pt for m in unsteered]); b0=np.array([kb[m.trainIdx].pt for m in unsteered])
    e0=np.linalg.norm(a0@matrix[:,:2].T+matrix[:,2]-b0,axis=1)
    save_json(out/'summary.json',dict(fast_count=len(candidates),harris_selected=len(ranked),
        actual_orb_count=len(kp),synthetic_matches=len(matches),correct_fraction=float((error<3).mean()),
        zero_angle_matches=len(unsteered),zero_angle_correct_fraction=float((e0<3).mean()),
        note='Single synthetic rotation, positions fixed for angle ablation; demo random BRIEF is not learned ORB rBRIEF'))
    print('ORB stages verified and saved',flush=True)


if __name__=='__main__': main()
