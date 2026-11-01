import base64
from common import *


def main():
    out=directory('playback'); poses=np.load(ART/'evaluation/aligned_poses.npz'); K,tr=calibration()
    times=np.loadtxt(SEQ/'times.txt')[:CFG['frames']]; frames=[]
    for i in range(CFG['frames']):
        img=image(i); ok,jpg=cv2.imencode('.jpg',img,[cv2.IMWRITE_JPEG_QUALITY,75]);assert ok
        scan=np.fromfile(SEQ/'velodyne'/f'{i:06d}.bin',dtype='<f4').reshape(-1,4)
        sample=scan[::max(1,len(scan)//2000)]
        pc=transform(sample[:,:3],tr); pc=pc[pc[:,2]>0]; projected=pc@K.T;uv=projected[:,:2]/projected[:,2,None]
        keep=(uv[:,0]>=0)&(uv[:,0]<img.shape[1])&(uv[:,1]>=0)&(uv[:,1]<img.shape[0])
        right=cv2.imread(str(SEQ/'image_1'/f'{i:06d}.png'),0)
        assert right is not None and right.shape==img.shape, f'Missing or mismatched right camera: {i}'
        ok,right_jpg=cv2.imencode('.jpg',right,[cv2.IMWRITE_JPEG_QUALITY,75]);assert ok
        features=[]; matches=[]
        if i:
            with np.load(ART/'vo/baseline'/f'{i:06d}.npz') as pair:
                features=pair['points_current'].tolist()
                matches=[[*a,*b,int(m!=0)] for a,b,m in zip(pair['points_previous'].tolist(),features,pair['pose_mask'].ravel())]
        frames.append(dict(image=base64.b64encode(jpg).decode(),right=base64.b64encode(right_jpg).decode(),matches=matches,time=float(times[i]),lidar=sample[:,:3].tolist(),projection=uv[keep].tolist(),features=features))
    payload=dict(frames=frames,width=img.shape[1],height=img.shape[0],poses={name:poses[name][:,:3,3].tolist() for name in ['gt','baseline_sim3','lo_metric','lo_sim3']})
    html=Path(__file__).with_name('playback.html').read_text().replace('__DATA__',json.dumps(payload))
    (out/'index.html').write_text(html)
    print(out/'index.html')


if __name__=='__main__':main()
