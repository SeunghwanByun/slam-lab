import unittest
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from run import fusion, composite, projection_jacobian, plane_jacobian, preintegrate, align_points, queue_latency


class NumericalContracts(unittest.TestCase):
    def test_01_fusion(self):
        self.assertAlmostEqual(fusion([2,2.03,1.98],[1,1,4]),1.9916666666666667)

    def test_02_tsdf(self):
        self.assertAlmostEqual(fusion([.5,-.25],[2,1]),.25)

    def test_03_weight_scale(self):
        self.assertEqual(fusion([1,3],[2,2]),fusion([1,3],[8,8]))

    def test_04_occupancy(self):
        self.assertAlmostEqual(1/(1+np.exp(-2*np.log(4))),16/17)

    def test_05_plane_rank(self):
        p=np.array([[0,0,1],[1,0,1],[0,1,1],[1,1,1.]])
        self.assertEqual(np.linalg.matrix_rank(plane_jacobian(p,np.tile([0,0,1.],(4,1)))),3)

    def test_06_plane_null(self):
        j=plane_jacobian(np.array([[1,2,3.]]),np.array([[0,0,1.]]))
        np.testing.assert_allclose(j @ [0,0,1,1,1,0],0)

    def test_07_compositing(self):
        c,w=composite([.5,.25,.8],np.eye(3),np.ones(3))
        np.testing.assert_allclose(c,[.575,.2,.375])

    def test_08_mass(self):
        _,w=composite([.5,.25,.8],np.eye(3),np.ones(3))
        self.assertAlmostEqual(w.sum()+.5*.75*.2,1)

    def test_09_transparent(self):
        c,_=composite([0,0,0],np.eye(3),np.ones(3))
        np.testing.assert_allclose(c,1)

    def test_10_opaque(self):
        c,_=composite([1,.5,.5],np.eye(3),np.ones(3))
        np.testing.assert_allclose(c,[1,0,0])

    def test_11_projection_derivative(self):
        p=np.array([.3,.1,2.]); eps=1e-6
        project=lambda v:500*v[:2]/v[2]
        numeric=np.column_stack([(project(p+np.eye(3)[k]*eps)-project(p-np.eye(3)[k]*eps))/(2*eps) for k in range(3)])
        np.testing.assert_allclose(projection_jacobian(p,500),numeric,atol=1e-7)

    def test_12_covariance(self):
        j=projection_jacobian([.3,.1,2],500)
        cov=j @ np.diag([.04**2,.08**2,.12**2]) @ j.T
        np.testing.assert_allclose(cov,[[120.25,6.75],[6.75,402.25]])

    def test_13_positive_covariance(self):
        j=projection_jacobian([.3,.1,2],500)
        self.assertTrue((np.linalg.eigvalsh(j @ j.T)>0).all())

    def test_14_constant_acceleration(self):
        r,v,p,_=preintegrate(np.tile([1,0,0.],(2,1)),np.zeros((2,3)),.1)
        np.testing.assert_allclose(v,[.2,0,0]);np.testing.assert_allclose(p,[.02,0,0])

    def test_15_rotation(self):
        r,_,_,_=preintegrate(np.zeros((2,3)),np.tile([0,0,1.],(2,1)),.1)
        np.testing.assert_allclose(r,Rotation.from_rotvec([0,0,.2]).as_matrix(),atol=1e-15)

    def test_16_gravity(self):
        _,v,p,_=preintegrate(np.tile([0,0,9.81],(2,1)),np.zeros((2,3)),.1)
        np.testing.assert_allclose(p+np.array([0,0,-9.81])*.2**2/2,0,atol=1e-15)

    def test_17_similarity(self):
        x=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1.]])
        aligned,s=align_points(2*x+3,x,True)
        np.testing.assert_allclose(aligned,x,atol=1e-14);self.assertAlmostEqual(s,.5)

    def test_18_rigid_no_scale(self):
        x=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1.]])
        aligned,s=align_points(2*x,x)
        self.assertEqual(s,1);self.assertGreater(np.linalg.norm(aligned-x),.1)

    def test_19_queue(self):
        np.testing.assert_allclose(queue_latency([20,60,20],30),[20,60,50])

    def test_20_perspective(self):
        self.assertAlmostEqual(1/(.25/1+.25/2+.5/4),2)

    def test_21_photometric(self):
        l=np.array([[0,0,1],[.6,0,.8],[0,.6,.8]])
        g=np.linalg.solve(l,[.4,.44,.32])
        np.testing.assert_allclose(g,[.2,0,.4],atol=1e-15)

    def test_22_timing_shift(self):
        self.assertAlmostEqual(500*.5*.02,5)

    def test_23_depth_uncertainty(self):
        self.assertAlmostEqual(500*.5/(10**2)*.2,.5)

    def test_24_fusion_variance(self):
        self.assertAlmostEqual(1/(1/.01**2+1/.02**2),.00008)

    def test_25_backprojection(self):
        np.testing.assert_allclose([(420-320)*2/500,(290-240)*2/500,2],[.4,.2,2])

    def test_26_weighted_depth_exercise(self):
        self.assertAlmostEqual(fusion([2,2.04],[10000,2500]),2.008)

    def test_27_zero_crossing(self):
        self.assertAlmostEqual(1.9+.3/(.3+.2)*.1,1.96)

    def test_28_null_motion_exercise(self):
        j=plane_jacobian(np.array([[1,2,1.]]),np.array([[0,0,1.]]))
        np.testing.assert_allclose(j,[[2,-1,0,0,0,1]])
        self.assertAlmostEqual(float((j @ [0,0,.1,.2,-.3,0])[0]),0)

    def test_29_clipping(self):
        self.assertAlmostEqual((.1-.05)/(.25-.05),.25)

    def test_30_perspective_attribute(self):
        q=np.array([.25,.25,.5])/np.array([1,2,4])
        self.assertAlmostEqual(float(q @ [0,0,1]/q.sum()),.25)

    def test_31_reverse_composite(self):
        c,_=composite([.8,.25,.5],np.eye(3)[::-1],np.ones(3))
        np.testing.assert_allclose(c,[.15,.125,.875])

    def test_32_density_interval(self):
        self.assertAlmostEqual(1-np.exp(-2*.1),1-np.exp(-1*.2))

    def test_33_positional_encoding(self):
        phases=np.pi*.25*np.array([1,2])
        actual=np.column_stack((np.sin(phases),np.cos(phases))).ravel()
        np.testing.assert_allclose(actual,[np.sqrt(.5),np.sqrt(.5),1,0],atol=1e-15)

    def test_34_gaussian_cross_term(self):
        cov=np.array([[120.25,6.75],[6.75,402.25]])
        d=np.array([10.,10.])
        exact=d @ np.linalg.solve(cov,d)
        algebra=100*(402.25+120.25-13.5)/np.linalg.det(cov)
        self.assertAlmostEqual(exact,algebra)
        self.assertLess(exact,np.sum(d*d/np.diag(cov)))

    def test_35_dynamic_bias(self):
        self.assertAlmostEqual(.75*.4,.3)
        self.assertAlmostEqual(.02/np.sqrt(25),.004)

    def test_36_loop_posterior(self):
        self.assertAlmostEqual(.9*.01/(.9*.01+.01*.99),10/21)

    def test_37_imu_bias(self):
        self.assertAlmostEqual(.5*.02*3**2,.09)
        self.assertAlmostEqual(-.5*.2**2*.01,-.0002)

    def test_38_correlated_variance(self):
        self.assertAlmostEqual(1/10+.01/500,.10002)
        self.assertAlmostEqual(1.01/500,.00202)

    def test_39_integration_convergence(self):
        exact=np.array([(1-np.cos(2))/.2**2,10/.2-np.sin(2)/.2**2,0])
        errors=[]
        for dt in [.1,.05]:
            n=round(10/dt)
            _,_,p,_=preintegrate(np.tile([1.,0,0],(n,1)),np.tile([0,0,.2],(n,1)),dt)
            errors.append(np.linalg.norm(p-exact))
        self.assertLess(errors[1],.6*errors[0])

    def test_40_reprojection(self):
        p=np.array([.4,.2,2.])
        uv=500*p[:2]/p[2]+[320,240]
        np.testing.assert_allclose(uv,[420,290])

    def test_41_rigid_inverse(self):
        r=Rotation.from_rotvec([.2,-.3,.1]).as_matrix()
        t=np.array([1.,2,3]);p=np.array([.4,.2,2.])
        np.testing.assert_allclose(r.T @ (r @ p+t-t),p,atol=1e-15)

    def test_42_rotation_matrix_contract(self):
        r,_,_,_=preintegrate(np.zeros((100,3)),np.tile([.2,.1,.3],(100,1)),.1)
        np.testing.assert_allclose(r.T @ r,np.eye(3),atol=1e-13)
        self.assertAlmostEqual(np.linalg.det(r),1)


if __name__ == "__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(NumericalContracts)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    output=Path(__file__).resolve().parents[1]/"artifacts/tests"
    output.mkdir(parents=True,exist_ok=True)
    (output/"results.json").write_text(json.dumps({"run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"successful":result.wasSuccessful()},indent=2))
    raise SystemExit(not result.wasSuccessful())
