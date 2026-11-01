"""Measured ORB outputs and explicitly educational, independently inspectable stages."""
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[1]
CFG = json.loads((STUDY/'configs/experiment.json').read_text())
ART = STUDY/'artifacts'
FIG = STUDY/'figures'
ART.mkdir(parents=True, exist_ok=True)
FIG.mkdir(exist_ok=True)
cv2.setNumThreads(1)
cv2.setRNGSeed(CFG['seed'])


def savefig(fig, name):
    fig.tight_layout(pad=1.6, h_pad=2.8, w_pad=1.8)
    fig.savefig(FIG/name, dpi=160)
    plt.close(fig)


def savejson(name, value):
    (ART/name).write_text(json.dumps(value, indent=2, allow_nan=False))


def main():
    source = ROOT/'data/kitti/dataset/sequences'/CFG['sequence']/'image_0'/f'{CFG["frame"]:06d}.png'
    img = cv2.imread(str(source), 0)
    assert img is not None
    h, w = img.shape
    # Same direct-from-original resizing as the old educational figure, not internal ORB buffers.
    pyramid = [cv2.resize(img, None, fx=CFG['scale_factor']**-i, fy=CFG['scale_factor']**-i,
                         interpolation=cv2.INTER_LINEAR) for i in range(CFG['levels'])]
    np.savez_compressed(ART/'pyramid.npz', **{f'level_{i}':p for i,p in enumerate(pyramid)})
    old = np.load(ROOT/'research/20261031_vo-lo-study/artifacts/orb/pyramid.npz')
    assert all(np.array_equal(pyramid[i], old[f'level_{i}']) for i in range(4))
    orb = cv2.ORB_create(nfeatures=CFG['features'], scaleFactor=CFG['scale_factor'], nlevels=CFG['levels'],
                         patchSize=CFG['patch_size'], fastThreshold=CFG['fast_threshold'])
    keypoints, descriptors = orb.detectAndCompute(img, None)
    np.savez_compressed(ART/'actual_orb.npz', xy=[k.pt for k in keypoints],
                        octave=[k.octave for k in keypoints], size=[k.size for k in keypoints],
                        angle=[k.angle for k in keypoints], response=[k.response for k in keypoints], descriptors=descriptors)
    counts = np.bincount([k.octave for k in keypoints], minlength=CFG['levels'])
    assert descriptors.dtype==np.uint8 and descriptors.shape==(len(keypoints),32)
    assert counts.sum()==len(keypoints) and len(counts)==CFG['levels']
    rows = []
    for i,p in enumerate(pyramid):
        restored = cv2.resize(p, (w,h), interpolation=cv2.INTER_LINEAR)
        rows.append(dict(level=i, width=p.shape[1], height=p.shape[0], downscale=CFG['scale_factor']**i,
                         length_fraction=CFG['scale_factor']**-i, patch_original_px=31*CFG['scale_factor']**i,
                         orb_count=int(counts[i]), restored_mae=float(np.abs(img.astype(float)-restored).mean()),
                         sha256=hashlib.sha256(p.tobytes()).hexdigest()))
        assert i==0 or rows[-1]['restored_mae']>0
    assert len({r['sha256'] for r in rows})==CFG['levels']
    with (ART/'levels.csv').open('w') as f:
        writer=csv.DictWriter(f, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    fig,axes=plt.subplots(4,2,figsize=(14,12))
    for i,(ax,p) in enumerate(zip(axes.flat,pyramid)):
        ax.set_facecolor('#dce2e4'); ax.imshow(p,cmap='gray',vmin=0,vmax=255,interpolation='nearest')
        ax.set(xlim=(-.5,w-.5),ylim=(h-.5,-.5),xlabel='Level pixels (common axis)',ylabel='Level pixels',
               title=f'L{i}: {p.shape[1]} x {p.shape[0]} | 1/{CFG["scale_factor"]**i:.3f} | ORB n={counts[i]}')
    savefig(fig,'01_pyramid_common_axes.png')
    x,y,rw,rh=CFG['roi']
    fig,axes=plt.subplots(2,4,figsize=(14,7))
    for i,(ax,p) in enumerate(zip(axes.flat,pyramid)):
        sx=p.shape[1]/w;sy=p.shape[0]/h
        x0,x1=round(x*sx),round((x+rw)*sx);y0,y1=round(y*sy),round((y+rh)*sy)
        crop=p[y0:y1,x0:x1]
        np.save(ART/f'roi_level_{i}.npy',crop)
        ax.imshow(crop,cmap='gray',vmin=0,vmax=255,interpolation='nearest'); ax.axis('off')
        ax.set_title(f'L{i}: same scene, {crop.shape[1]} x {crop.shape[0]} samples')
    savefig(fig,'02_roi_equal_display.png')
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    axes[0].imshow(img,cmap='gray');axes[0].add_patch(Rectangle((x,y),rw,rh,fill=False,color='red',lw=2))
    axes[0].set_title('Red: same-scene ROI used above');axes[0].axis('off')
    patch_center=(820,230)
    axes[1].imshow(img,cmap='gray',interpolation='nearest')
    for i in [0,3,7]:
        size=31*CFG['scale_factor']**i
        axes[1].add_patch(Rectangle((patch_center[0]-size/2,patch_center[1]-size/2),size,size,fill=False,
                                    edgecolor=['#f2b900','#00a0b0','#ef4060'][[0,3,7].index(i)],lw=2,label=f'L{i}: {size:.1f} original px'))
    axes[1].set(xlim=(740,900),ylim=(310,150),title='Fixed 31-level-pixel patch: growing original footprint')
    axes[1].legend(fontsize=8);savefig(fig,'03_patch_footprint.png')
    fast=cv2.FastFeatureDetector_create(threshold=CFG['fast_threshold'],nonmaxSuppression=True,
                                       type=cv2.FAST_FEATURE_DETECTOR_TYPE_9_16)
    candidates=fast.detect(img)
    fast.setNonmaxSuppression(False);unsuppressed=fast.detect(img)
    response=cv2.cornerHarris(img,7,3,.04)
    valid=[k for k in candidates if 20<k.pt[0]<w-20 and 20<k.pt[1]<h-20]
    ranked=sorted(valid,key=lambda k:response[round(k.pt[1]),round(k.pt[0])],reverse=True)[:500]
    cx,cy=map(round,ranked[0].pt)
    offsets=np.array([(0,-3),(1,-3),(2,-2),(3,-1),(3,0),(3,1),(2,2),(1,3),(0,3),(-1,3),(-2,2),(-3,1),(-3,0),(-3,-1),(-2,-2),(-1,-3)])
    ring=img[cy+offsets[:,1],cx+offsets[:,0]].astype(int); center=int(img[cy,cx]); t=CFG['fast_threshold']
    states=np.where(ring>center+t,1,np.where(ring<center-t,-1,0))
    passes=any(np.all(np.roll(states,-start)[:9]==sign) for start in range(16) for sign in [-1,1]);assert passes
    np.savez_compressed(ART/'fast_harris.npz', xy=[k.pt for k in candidates], selected=[k.pt for k in ranked],response=response,ring=ring,states=states,center=[cx,cy,center])
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    patch=img[cy-4:cy+5,cx-4:cx+5]
    axes[0].imshow(patch,cmap='gray',vmin=0,vmax=255,interpolation='nearest')
    for j,(dx,dy) in enumerate(offsets):
        axes[0].text(dx+4,dy+4,str(j),ha='center',va='center',fontsize=10,color='#ff3456',bbox=dict(facecolor='white',alpha=.75,edgecolor='none',pad=.1))
    axes[0].scatter([4],[4],c='cyan');axes[0].set_title(f'Actual FAST-9 corner ({cx},{cy}), I(p)={center}')
    axes[1].plot(range(16),ring,'o-',label='Ring intensity');axes[1].axhline(center+t,c='red',label='I(p)+20');axes[1].axhline(center-t,c='blue',label='I(p)-20')
    axes[1].set(xlabel='Ring index (cyclic)',ylabel='Intensity 0..255',title='9 contiguous bright OR dark values required');axes[1].legend();savefig(fig,'04_fast_ring.png')
    fig,axes=plt.subplots(3,1,figsize=(13,10))
    for ax,points,title in zip(axes,[unsuppressed,candidates,ranked],['FAST without NMS','FAST with NMS','Educational Harris top 500']):
        ax.imshow(img,cmap='gray');xy=np.array([k.pt for k in points]);ax.scatter(xy[:,0],xy[:,1],s=1,c='#f0c400');ax.set_title(f'{title}: {len(points)}');ax.axis('off')
    savefig(fig,'05_nms_harris.png')
    yy,xx=np.mgrid[:41,:41];toys=[np.full((41,41),.5,np.float32),(xx>=20).astype(np.float32),((xx>=20)&(yy>=20)).astype(np.float32)]
    fig,axes=plt.subplots(2,3,figsize=(12,7));toy_stats=[]
    for i,(toy,name) in enumerate(zip(toys,['Flat','Edge','Corner'])):
        eigen=cv2.cornerEigenValsAndVecs(toy,7,3)[20,20,:2];r=float(cv2.cornerHarris(toy,7,3,.04)[20,20])
        toy_stats.append(dict(name=name,eigen=eigen.tolist(),response=r))
        axes[0,i].imshow(toy,cmap='gray',vmin=0,vmax=1);axes[0,i].set_title(f'{name}: R={r:.5f}');axes[0,i].axis('off')
        axes[1,i].bar(['lambda1','lambda2'],eigen,color=['#148f99','#d35966']);axes[1,i].set_ylim(0,.45)
    savefig(fig,'06_harris_eigenvalues.png');savejson('harris_toys.json',toy_stats)
    assert toy_stats[0]['response']==0 and toy_stats[1]['response']<0<toy_stats[2]['response']
    yy,xx=np.mgrid[-15:16,-15:16];disk=xx*xx+yy*yy<=225
    patch=img[cy-15:cy+16,cx-15:cx+16].astype(float)
    m00=float((patch*disk).sum());m10=float((xx*patch*disk).sum());m01=float((yy*patch*disk).sum())
    theta=float(np.arctan2(m01,m10));centroid=[m10/m00,m01/m00]
    rng=np.random.default_rng(CFG['seed']);pairs=rng.integers(-10,11,(256,2,2))
    rot=np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])
    steered=np.rint(pairs@rot.T).astype(int);smooth=cv2.GaussianBlur(img,(7,7),2)
    values=smooth[cy+steered[:,:,1],cx+steered[:,:,0]];bits=values[:,0]<values[:,1]
    np.savez_compressed(ART/'orientation_brief.npz',patch=patch,moments=[m00,m10,m01],theta=theta,centroid=centroid,pairs=pairs,steered=steered,values=values,bits=bits)
    fig,axes=plt.subplots(1,3,figsize=(14,5))
    axes[0].imshow(patch,cmap='gray');axes[0].scatter([15],[15],c='cyan',label='center')
    axes[0].scatter([15+centroid[0]],[15+centroid[1]],c='red',label='centroid')
    axes[0].arrow(15,15,10*np.cos(theta),10*np.sin(theta),color='yellow',head_width=1)
    axes[0].set_title(f'Intensity moment angle: {np.degrees(theta):.1f} deg');axes[0].legend(fontsize=8)
    axes[1].imshow(patch,cmap='gray')
    for pair in steered[:8]:axes[1].plot(pair[:,0]+15,pair[:,1]+15,'o-',markersize=3)
    axes[1].set_title('8 rotated comparisons (DEMO random tests)')
    axes[2].imshow(bits.reshape(16,16),cmap='gray',vmin=0,vmax=1,interpolation='nearest');axes[2].set_title('256 DEMO bits; not learned rBRIEF')
    savefig(fig,'07_orientation_brief.png')
    fig,axes=plt.subplots(2,4,figsize=(14,7))
    for level,ax in enumerate(axes.flat):
        ax.imshow(img,cmap='gray');points=np.array([k.pt for k in keypoints if k.octave==level]);
        if len(points):ax.scatter(points[:,0],points[:,1],c='#f2c100',s=2)
        ax.set_title(f'Actual ORB octave {level}: {counts[level]}');ax.axis('off')
    savefig(fig,'08_actual_octaves.png')
    other=cv2.imread(str(source.with_name(f'{CFG["frame"]+1:06d}.png')),0);kp2,d2=orb.detectAndCompute(other,None)
    matches=sorted(cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck=True).match(descriptors,d2),key=lambda m:m.distance)
    m=matches[0];a=descriptors[m.queryIdx];b=d2[m.trainIdx];xor=np.bitwise_xor(a,b)
    assert int(np.unpackbits(xor).sum())==int(m.distance)
    fig,axes=plt.subplots(2,1,figsize=(13,6))
    draw=cv2.drawMatches(img,keypoints,other,kp2,matches[:35],None,flags=2)
    axes[0].imshow(cv2.cvtColor(draw,cv2.COLOR_BGR2RGB));axes[0].axis('off');axes[0].set_title('Actual ORB / BF cross-check: best 35; NOT geometry-verified')
    axes[1].imshow(np.stack([np.unpackbits(a),np.unpackbits(b),np.unpackbits(xor)]),aspect='auto',cmap='gray',interpolation='nearest');axes[1].set_yticks([0,1,2],['frame120','frame121','XOR']);axes[1].set_title(f'Best match Hamming = {int(m.distance)} / 256 differing bits')
    savefig(fig,'09_hamming.png');np.savez_compressed(ART/'matching.npz',a=a,b=b,xor=xor,matches=[[m.queryIdx,m.trainIdx,m.distance] for m in matches])
    savejson('summary.json',dict(config=CFG,opencv=cv2.__version__,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),old_four_arrays_equal=True,levels=rows,
              fast_without_nms=len(unsuppressed),fast_nms=len(candidates),harris_selected=len(ranked),ring=ring.tolist(),center=[cx,cy,center],
              ring_states=states.tolist(),fast9_pass=bool(passes),moments=[m00,m10,m01],angle_deg=float(np.degrees(theta)),centroid=centroid,
              brief_first8_values=values[:8].tolist(),brief_first8_bits=bits[:8].astype(int).tolist(),actual_descriptor_shape=list(descriptors.shape),hamming=int(matches[0].distance),matches=len(matches),tests='old arrays equal; nonzero resize errors; FAST9; XOR popcount'))
    print((ART/'summary.json').read_text())


if __name__=='__main__':
    main()
