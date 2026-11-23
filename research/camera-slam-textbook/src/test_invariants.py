"""Executable contracts, including dynamic GT-denial while estimation runs."""
import ast
import builtins
import io
from pathlib import Path
import unittest
from unittest.mock import patch
import cv2
import numpy as np
from common import CFG, calibration, initialize
from geometry import pose, inverse, transform, project, accumulate, similarity, align_poses
from odometry import estimate_pnp, estimate_essential
from observations import track
from evaluation import metrics


class Invariants(unittest.TestCase):
    def setUp(self):
        initialize()
        self.K, self.b, self.p0, self.p1=calibration()
        self.R=cv2.Rodrigues(np.array([.1,-.05,.02]))[0]
        self.T=pose(self.R,[1,2,3])
        rng=np.random.default_rng(10)
        self.X=np.c_[rng.uniform(-2,2,80),rng.uniform(-1,1,80),rng.uniform(8,20,80)]

    def test_inverse(self):
        np.testing.assert_allclose(self.T@inverse(self.T),np.eye(4),atol=1e-12)

    def test_composition(self):
        np.testing.assert_allclose(transform(self.T@self.T,self.X),transform(self.T,transform(self.T,self.X)),atol=1e-12)

    def test_projection(self):
        np.testing.assert_allclose(project(self.K,np.array([[0.,0.,10.]])),self.K[:2,2][None])

    def test_projection_scale_invariant(self):
        np.testing.assert_allclose(project(self.K,self.X),project(self.K,7*self.X))

    def test_triangulation_metric(self):
        a=project(self.K,self.X)
        b=project(self.K,self.X-[self.b,0,0])
        h=cv2.triangulatePoints(self.p0,self.p1,a.T,b.T)
        np.testing.assert_allclose((h[:3]/h[3]).T,self.X,atol=1e-9)

    def test_baseline_depth(self):
        a=project(self.K,self.X); b=project(self.K,self.X-[self.b,0,0])
        np.testing.assert_allclose(self.K[0,0]*self.b/(a[:,0]-b[:,0]),self.X[:,2])

    def test_accumulation_direction(self):
        np.testing.assert_allclose(accumulate(np.eye(4),self.T),inverse(self.T))

    def test_pnp_direction(self):
        result=estimate_pnp(self.X,project(self.K,transform(self.T,self.X)),self.K,37)
        self.assertTrue(result['accepted'])
        np.testing.assert_allclose(result['T'],self.T,atol=1e-5)

    def test_hold(self):
        result=estimate_pnp(np.empty((0,3)),np.empty((0,2)),self.K,37)
        self.assertFalse(result['accepted'])
        np.testing.assert_equal(accumulate(self.T,result['T']),self.T)

    def test_sim3_known(self):
        b=2.5*(self.X@self.R.T)+[2,3,-1]
        s,R,t=similarity(self.X,b)
        np.testing.assert_allclose(s,2.5)
        np.testing.assert_allclose(s*(self.X@R.T)+t,b,atol=1e-12)
        self.assertAlmostEqual(np.linalg.det(R),1.)

    def test_alignment_stationary_rejected(self):
        with self.assertRaises(ValueError): similarity(np.zeros((10,3)),np.zeros((10,3)))

    def test_metric_identity(self):
        poses=np.repeat(np.eye(4)[None],10,axis=0)
        poses[:,0,3]=np.arange(10)
        result,*_=metrics(poses,poses)
        self.assertTrue(all(x==0 for x in result.values()))

    def test_mono_unit_not_metric(self):
        T=pose(np.eye(3),[.3,0,.6])
        result=estimate_essential(project(self.K,self.X),project(self.K,transform(T,self.X)),self.K,37)
        self.assertTrue(result['accepted'])
        self.assertAlmostEqual(np.linalg.norm(result['T'][:3,3]),1.)

    def test_gt_separation_static(self):
        for name in ('common','geometry','observations','odometry'):
            source=Path(__file__).with_name(name+'.py').read_text()
            tree=ast.parse(source)
            imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
            self.assertNotIn('evaluation',imports)
            self.assertNotIn("DATA/'poses'",source)
            self.assertNotIn('loadtxt',source)

    def test_gt_denied_dynamically(self):
        original=builtins.open
        io_original=io.open
        def guarded(file,*args,**kwargs):
            if '/poses/' in str(file): raise AssertionError('GT read attempted')
            return original(file,*args,**kwargs)
        def guarded_io(file,*args,**kwargs):
            if '/poses/' in str(file): raise AssertionError('GT read attempted')
            return io_original(file,*args,**kwargs)
        pixels=project(self.K,transform(self.T,self.X))
        with patch('builtins.open',guarded),patch('io.open',guarded_io):
            self.assertTrue(estimate_pnp(self.X,pixels,self.K,37)['accepted'])
            from odometry import run_segment
            run_segment(0,2)

    def test_disjoint_segments(self):
        a,b=CFG['segments']
        self.assertFalse(set(range(*a)) & set(range(*b)))
        self.assertLessEqual(max(stop-start for start,stop in CFG['segments']),200)

    def test_empty_tracks(self):
        im=np.zeros((30,30),np.uint8)
        self.assertEqual(len(track(im,im,np.empty((0,2)))['valid']),0)

    def test_failed_lk_buffers_normalized(self):
        im=np.zeros((80,80),np.uint8)
        result=track(im,im,np.array([[40,40]],np.float32))
        self.assertFalse(result['status_forward'][0])
        self.assertTrue(np.isnan(result['lk_error'][0]))
        self.assertTrue(np.isnan(result['current'][0]).all())
        self.assertFalse(result['valid'][0])

    def test_synthetic_summary_separates_holds(self):
        from synthetic import rotation_summary
        rows=[dict(E_accepted=True,E_rotation_error_deg=.2),
              dict(E_accepted=False,E_rotation_error_deg=2.),dict(E_accepted=False,E_rotation_error_deg=2.)]
        result=rotation_summary(rows)
        self.assertEqual(result['essential_accepted'],1)
        self.assertEqual(result['essential_failed_hold'],2)
        self.assertEqual(result['system_output_rotation_median_including_hold_deg'],2.)
        self.assertEqual(result['successful_estimate_rotation_median_deg'],.2)
        self.assertIsNone(rotation_summary(rows[1:])['successful_estimate_rotation_median_deg'])


if __name__=='__main__':
    unittest.main(verbosity=2)
