"""Numeric contracts and solved examples; no learned-model quality assertions."""
import json
import unittest
import numpy as np
from scipy.optimize import linear_sum_assignment
from experiment import (BASE, dlt, project, normalize_points, rootsift,
                        sinkhorn, softmax, ransac_trials, huber_weights)


class NumericContracts(unittest.TestCase):
    def test_harris_and_shi(self):
        G=np.array([[1,0],[0,2],[1,1]],float); M=G.T@G
        np.testing.assert_allclose(M,[[2,1],[1,5]])
        self.assertAlmostEqual(np.linalg.det(M)-.04*np.trace(M)**2,7.04)
        self.assertAlmostEqual(np.linalg.eigvalsh(M)[0],(7-np.sqrt(13))/2)

    def test_contrast_scaling(self):
        M=np.array([[2.,1.],[1.,5.]])
        response=lambda a: np.linalg.det(a)-.04*np.trace(a)**2
        self.assertAlmostEqual(response(4*M),16*response(M))

    def test_dog_localization(self):
        g=np.array([.2,-.4,.1]); H=np.diag([-2.,-4.,-1.])
        delta=-np.linalg.solve(H,g)
        np.testing.assert_allclose(delta,[.1,-.1,.1])
        self.assertAlmostEqual(.8+.5*g@delta,.835)

    def test_incremental_sigma(self):
        self.assertAlmostEqual(np.sqrt((1.6*2**(1/3))**2-1.6**2),1.2262734984654078)

    def test_rootsift_kernel(self):
        d=np.array([[1.,3.],[3.,1.]])
        r=rootsift(d)
        np.testing.assert_allclose(np.linalg.norm(r,axis=1),1,atol=1e-7)
        self.assertAlmostEqual(float(np.sum((r[0]-r[1])**2)),2-np.sqrt(3),places=6)

    def test_rootsift_zero(self):
        np.testing.assert_array_equal(rootsift(np.zeros((1,4))),0)

    def test_ratio_squared_threshold(self):
        self.assertTrue(3/5 < .7)
        self.assertTrue(9/25 < .7**2)
        self.assertFalse(4/5 < .7)

    def test_attention_message(self):
        weights=softmax(np.array([[1.,0.,1.]])/np.sqrt(2))
        np.testing.assert_allclose(weights.sum(1),1)
        msg=weights@np.array([[2.,0.],[0.,2.],[1.,1.]])
        self.assertAlmostEqual(float(msg.sum()),2)

    def test_transport_marginals(self):
        p,h=sinkhorn([[8,2,1],[2,8,1],[1,1,4]],[1,1,2],[1,1,2])
        np.testing.assert_allclose(p.sum(0),[1,1,2],atol=1e-10)
        np.testing.assert_allclose(p.sum(1),[1,1,2],atol=1e-10)
        self.assertLess(h[-1],1e-12)

    def test_normalization_contract(self):
        q,T=normalize_points([[0,0],[2,0],[2,2],[0,2]])
        np.testing.assert_allclose(q.mean(0),0,atol=1e-12)
        self.assertAlmostEqual(np.linalg.norm(q,axis=1).mean(),np.sqrt(2))
        np.testing.assert_allclose(T,[[1,0,-1],[0,1,-1],[0,0,1]])

    def test_dlt_exact_four_points(self):
        p=np.array([[0,0],[2,0],[2,2],[0,2]],float)
        H=np.array([[1.1,.1,3],[.05,.9,2],[.01,.02,1]])
        fitted,_,_=dlt(p,project(H,p))
        np.testing.assert_allclose(fitted,H,atol=1e-10)

    def test_dlt_collinear_rejected(self):
        p=np.array([[0,0],[1,0],[2,0],[3,0]],float)
        with self.assertRaises(ValueError): dlt(p,p)

    def test_dlt_too_few_rejected(self):
        with self.assertRaises(ValueError): dlt(np.zeros((3,2)),np.zeros((3,2)))

    def test_ransac_iterations(self):
        self.assertEqual(ransac_trials(.5),72)
        self.assertEqual(ransac_trials(.8),9)
        self.assertEqual(ransac_trials(1),1)

    def test_projective_division(self):
        H=np.array([[1,0,2],[0,1,1],[.1,0,1]])
        np.testing.assert_allclose(project(H,[[2,3]]),[[10/3,10/3]])

    def test_huber_weights(self):
        np.testing.assert_allclose(huber_weights(np.array([0.,.5,2.,-4.])),[1,1,.5,.25])

    def test_lk_normal_equations(self):
        J=np.array([[1.,0.],[0.,2.],[1.,1.]])
        residual=np.array([1.,-2.,0.])
        np.testing.assert_allclose(J.T@residual,[1.,-4.])
        np.testing.assert_allclose(-np.linalg.solve(J.T@J,J.T@residual),[-1.,1.])

    def test_horn_schunck_one_update(self):
        ix,iy,it,alpha=2.,1.,-3.,1.
        d=(ix*0+iy*0+it)/(alpha**2+ix**2+iy**2)
        np.testing.assert_allclose([-ix*d,-iy*d],[1.,.5])

    def test_farneback_polynomial(self):
        A=np.array([[2.,.5],[.5,1.]])
        b1=np.array([1.,-1.]); shift=np.array([3.,-2.])
        b2=b1-2*A@shift
        np.testing.assert_allclose(b2,[-9.,0.])
        np.testing.assert_allclose(np.linalg.solve(2*A,b1-b2),shift)

    def test_forward_backward_sign(self):
        forward=np.array([4.,-2.]); backward=np.array([-3.7,2.4])
        self.assertAlmostEqual(np.linalg.norm(forward+backward),.5)

    def test_assignment_not_greedy(self):
        C=np.array([[.1,.2],[.11,.9]])
        r,c=linear_sum_assignment(C)
        np.testing.assert_array_equal(c,[1,0])
        self.assertAlmostEqual(C[r,c].sum(),.31)

    def test_kalman_example(self):
        P=np.array([[5.25,1.],[1.,1.25]])
        K=P[:,0]/6.25
        np.testing.assert_allclose(K,[.84,.16])
        np.testing.assert_allclose(np.array([12.,2.])+K,[12.84,2.16])
        post=P-np.outer(K,P[0])
        np.testing.assert_allclose(post,[[.84,.16],[.16,1.09]])

    def test_bilinear_interpolation(self):
        patch=np.array([[10.,20.],[30.,40.]])
        x,y=.25,.5
        value=(1-y)*((1-x)*patch[0,0]+x*patch[0,1])+y*((1-x)*patch[1,0]+x*patch[1,1])
        self.assertAlmostEqual(value,22.5)

    def test_raft_cost_volume_memory(self):
        self.assertEqual((48*80)**2*4,58982400)


class ArtifactContracts(unittest.TestCase):
    @unittest.skipUnless((BASE/"artifacts/summary.json").exists(),"run experiment first")
    def test_artifacts(self):
        summary=json.loads((BASE/"artifacts/summary.json").read_text())
        self.assertEqual(len(summary["features"]),12)
        self.assertFalse(summary["motion"]["temporal"]["gt_flow_available"])
        self.assertLess(summary["alignment"]["grid_median_ransac_px"],1.)
        self.assertGreater(summary["alignment"]["grid_median_dlt_px"],5.)
        self.assertEqual(len(list((BASE/"figures").glob("d*.png"))),13)


if __name__ == "__main__":
    unittest.main(verbosity=2)
