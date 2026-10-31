"""Sequential research runner; never changes the main VO pipeline."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',choices=['all','playback'],default='all')
    args=parser.parse_args()
    study=Path(__file__).resolve().parents[1]; root=study.parents[1]
    env=os.environ.copy()
    env.setdefault('MPLCONFIGDIR',str(root/'.cache/matplotlib'))
    env.setdefault('XDG_CACHE_HOME',str(root/'.cache'))
    if args.stage=='playback' and not (study/'artifacts/evaluation/aligned_poses.npz').exists():
        raise SystemExit('Missing estimated poses: first run this command with --stage all.')
    scripts=['orb_stages','vo','lo','evaluate','geometry_stages','playback'] if args.stage=='all' else ['playback']
    for name in scripts:
        subprocess.run([sys.executable,str(study/'src'/f'{name}.py')],cwd=root,env=env,check=True)
    subprocess.run([sys.executable,str(root/'research/20261031_loop-readiness/src/audit.py')],cwd=root,env=env,check=True)
    print('Open:',study/'artifacts/playback/index.html')


if __name__=='__main__':main()
