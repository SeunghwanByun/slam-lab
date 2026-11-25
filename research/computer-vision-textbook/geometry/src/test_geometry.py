import unittest
import numpy as np
import cv2
from experiment import homogeneous, project, normalize, eight_point, sampson, path_cost, vconstraint

class GeometryTests(unittest.TestCase):
    def test_homogeneous_scale(self):
        p=np.array([2.,3.,1.]); q=7*p
        np.testing.assert_allclose(p[:2]/p[2],q[:2]/q[2])
    def test_line_incidence(self):
        p,q=np.array([1,2,1]),np.array([3,4,1]); l=np.cross(p,q)
        self.assertEqual(l@p,0); self.assertEqual(l@q,0)
    def test_line_transform(self):
        H=np.array([[1,.2,0],[0,1,0],[.1,0,1.]])
        p=np.array([1.,2,1]); l=np.array([2.,-1,0])
        self.assertAlmostEqual((np.linalg.inv(H).T@l)@(H@p),0)
    def test_cross_ratio(self):
        def cr(a,b,c,d): return ((c-a)/(c-b))/((d-a)/(d-b))
        z=np.array([0.,1,3,5]); q=(2*z+1)/(.2*z+1)
        self.assertAlmostEqual(cr(*z),cr(*q)); self.assertAlmostEqual(cr(*z),1.2)
    def test_normalization(self):
        p,T=normalize(np.array([[100.,200],[200,300],[300,200]]))
        np.testing.assert_allclose(p.mean(0),0,atol=1e-12)
        self.assertAlmostEqual(np.linalg.norm(p,axis=1).mean(),np.sqrt(2))
    def test_exact_eight_full_svd(self):
        rng=np.random.default_rng(3); X=rng.uniform([-2,-1,3],[2,1,10],(8,3))
        P=np.column_stack([np.eye(3),[0,0,0]]); Q=np.column_stack([np.eye(3),[-.5,.02,.01]])
        a,b=project(P,X),project(Q,X); F,s,A=eight_point(a,b)
        self.assertEqual(A.shape,(8,9)); self.assertLess(np.max(sampson(F,a,b)),1e-20)
        self.assertLess(np.linalg.svd(F,compute_uv=False)[-1],1e-12)
    def test_zhang_constraint(self):
        K=np.array([[700.,0,320],[0,720,240],[0,0,1]])
        R=cv2.Rodrigues(np.array([.2,.1,0]))[0]; H=K@np.column_stack([R[:,:2],[0,0,2]])
        B=np.linalg.inv(K).T@np.linalg.inv(K); b=B[[0,0,1,0,1,2],[0,1,1,2,2,2]]
        self.assertAlmostEqual(vconstraint(H,0,1)@b,0,places=10)
        self.assertAlmostEqual((vconstraint(H,0,0)-vconstraint(H,1,1))@b,0,places=10)
    def test_depth_example(self): self.assertAlmostEqual(700*.54/18.9,20)
    def test_uncertainty_example(self): self.assertAlmostEqual(20**2/(700*.54)*.5,.5291005291)
    def test_subpixel(self):
        a,b,c=5.,2.,3.; self.assertAlmostEqual((a-c)/(2*(a-2*b+c)),.25)
    def test_path_offset_invariance(self):
        C=np.array([[1.,4,9],[2,0,4],[3,1,0]])
        np.testing.assert_allclose(path_cost(C+10,1,3),path_cost(C,1,3)+10)
    def test_path_no_penalty(self):
        C=np.array([[1.,4,9],[2,0,4],[3,1,0]])
        np.testing.assert_allclose(path_cost(C,0,0),C)
    def test_schur(self):
        H=np.array([[3.,-1,1],[-1,3,-1],[1,-1,5]])
        g=np.array([-.5,-1.5,-3.5]); x=np.linalg.solve(H,-g)
        A,B,D=H[:2,:2],H[:2,2:],H[2:,2:]
        S=A-B@np.linalg.solve(D,B.T)
        dc=np.linalg.solve(S,-g[:2]+B@np.linalg.solve(D,g[2:]))
        dp=np.linalg.solve(D,-g[2:]-B.T@dc)
        np.testing.assert_allclose(x,[1/6,5/6,5/6])
        np.testing.assert_allclose(x,np.r_[dc,dp])
    def test_sad_ssd(self):
        d=np.array([10,20,30])-np.array([12,19,29])
        self.assertEqual(np.abs(d).sum(),4); self.assertEqual((d*d).sum(),6)
    def test_zncc(self):
        a=np.array([10.,20,30]); b=2*a+10
        a-=a.mean(); b-=b.mean()
        self.assertAlmostEqual(a@b/(np.linalg.norm(a)*np.linalg.norm(b)),1)
    def test_sgm_worked_step(self):
        np.testing.assert_allclose(path_cost(np.array([[4.,1,3],[2,0,4]]),1,3)[1],[3,0,5])
    def test_rotation_average(self):
        A=np.array([[1.,0],[-1,1],[0,1]]); y=np.array([10.,12,25])
        np.testing.assert_allclose(np.linalg.lstsq(A,y,rcond=None)[0],[11,24])
    def test_distortion_example(self):
        self.assertAlmostEqual(800*.5*(1-.2*.25)-800*.5,-20)
    def test_plane_homography(self):
        R=cv2.Rodrigues(np.array([.1,.02,0]))[0]; t=np.array([-.5,.1,.02])
        n=np.array([0.,0,1]); h=4.; q=np.array([.2,.1,1])
        y=R@(h*q/(n@q))+t; z=(R+np.outer(t,n)/h)@q
        np.testing.assert_allclose(y[:2]/y[2],z[:2]/z[2])
    def test_gauge(self):
        J=np.array([[-1.,1,0],[0,-1,1]])
        np.testing.assert_allclose(J@np.ones(3),0)
    def test_triangulation(self):
        P=np.column_stack([np.eye(3),np.zeros(3)]); Q=np.column_stack([np.eye(3),[-.5,0,0]])
        X=np.array([[.2,.1,5.]])
        a,b=project(P,X),project(Q,X); h=cv2.triangulatePoints(P,Q,a.T,b.T)
        np.testing.assert_allclose((h[:3]/h[3]).T,X)
    def test_census_monotone(self):
        x=np.array([1.,8.,4.,6.]); y=3*x+9
        np.testing.assert_array_equal(x<x[2],y<y[2])

if __name__=='__main__': unittest.main(verbosity=2)
