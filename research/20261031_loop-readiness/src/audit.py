import base64
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import cKDTree


def main():
    study = Path(__file__).resolve().parents[1]
    root = study.parents[1]
    cfg = json.loads((study/'configs/audit.json').read_text())
    seq = root/'data/kitti/dataset/sequences'/cfg['sequence']
    gt_path = root/'data/kitti/dataset/poses'/f'{cfg["sequence"]}.txt'
    poses = np.loadtxt(gt_path).reshape(-1,3,4)
    xyz = poses[:,:,3]; rotations = poses[:,:,:3]
    times = np.loadtxt(seq/'times.txt')
    assert len(times)==len(poses) and np.isfinite(poses).all() and (np.diff(times)>0).all()
    travel = np.r_[0,np.cumsum(np.linalg.norm(np.diff(xyz,axis=0),axis=1))]
    pairs = cKDTree(xyz).query_pairs(cfg['max_distance_m'],output_type='ndarray')
    pairs = pairs[(pairs[:,1]-pairs[:,0])>=cfg['min_frame_gap']]
    rows = []
    for a,b in pairs:
        distance = float(np.linalg.norm(xyz[a]-xyz[b]))
        angle = float(np.rad2deg(np.arccos(np.clip((np.trace(rotations[a].T@rotations[b])-1)/2,-1,1))))
        if travel[b]-travel[a]<cfg['min_travel_m'] or angle>cfg['max_view_angle_deg']:continue
        rows.append(dict(first=int(a),second=int(b),distance_m=distance,frame_gap=int(b-a),
                         elapsed_s=float(times[b]-times[a]),travel_m=float(travel[b]-travel[a]),view_angle_deg=angle))
    rows.sort(key=lambda r:(r['distance_m'],r['first'],r['second']))
    chosen=[]
    for row in rows:
        if all(np.linalg.norm(xyz[row['first']]-xyz[r['first']])>=cfg['representative_spacing_m'] for r in chosen):
            chosen.append(row)
        if len(chosen)==cfg['representative_pairs']:break
    assert chosen, 'No qualifying revisit candidates'
    art=study/'artifacts'; figures=study/'figures'; viewer=art/'loops'
    viewer.mkdir(parents=True,exist_ok=True); figures.mkdir(exist_ok=True)
    with (art/'candidates.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    summary=dict(sequence=cfg['sequence'],frames=len(poses),gt_path_m=float(travel[-1]),
                 start_end_distance_m=float(np.linalg.norm(xyz[0]-xyz[-1])),candidates=len(rows),
                 representatives=chosen,gt_sha256=hashlib.sha256(gt_path.read_bytes()).hexdigest(),
                 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
                 method='GT-oracle candidate audit; no loop detection or pose graph optimization')
    (art/'summary.json').write_text(json.dumps(summary,indent=2))
    fig,ax=plt.subplots(figsize=(9,7));ax.plot(xyz[:,0],xyz[:,2],c='gray',lw=1,label='Full GT trajectory')
    ax.scatter(xyz[0,0],xyz[0,2],marker='s',c='black',label='Start')
    ax.scatter(xyz[-1,0],xyz[-1,2],marker='x',c='black',label='End')
    for k,row in enumerate(chosen):
        p=xyz[row['first']];ax.scatter(p[0],p[2],s=60);ax.annotate(f'{k+1}: {row["first"]} / {row["second"]}',(p[0],p[2]),xytext=(8,8),textcoords='offset points')
    ax.axis('equal');ax.set(xlabel='Camera0 X (m)',ylabel='Camera0 Z (m)',title='KITTI 00: GT-based revisit candidates, NOT loop closure output');ax.legend();fig.tight_layout()
    fig.savefig(figures/'full_trajectory.png',dpi=150);plt.close(fig)
    cards=[]
    for k,row in enumerate(chosen):
        images=[cv2.imread(str(seq/'image_0'/f'{i:06d}.png'),0) for i in (row['first'],row['second'])]
        assert all(im is not None for im in images)
        fig,axes=plt.subplots(2,1,figsize=(12,7))
        for ax,im,idx in zip(axes,images,[row['first'],row['second']]):
            ax.imshow(im,cmap='gray');ax.set_title(f'Frame {idx}');ax.axis('off')
        fig.suptitle(f'Candidate {k+1}: GT distance {row["distance_m"]:.3f}m, gap {row["elapsed_s"]:.1f}s, view angle {row["view_angle_deg"]:.2f} deg')
        fig.tight_layout();fig.savefig(figures/f'pair_{k+1}.png',dpi=120);plt.close(fig)
        encoded=[]
        for im in images:
            ok,jpg=cv2.imencode('.jpg',im);assert ok;encoded.append(base64.b64encode(jpg).decode())
        cards.append(dict(**row,images=encoded))
    payload=dict(summary=summary,pairs=cards,path_image=base64.b64encode((figures/'full_trajectory.png').read_bytes()).decode())
    template=(study/'src/viewer.html').read_text()
    (viewer/'index.html').write_text(template.replace('__DATA__',json.dumps(payload)))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
