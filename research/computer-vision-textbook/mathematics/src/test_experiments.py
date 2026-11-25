import unittest
import numpy as np
from numpy.testing import assert_allclose
from scipy import linalg, stats
from experiments import huber_location, em_fixed_variance, kf, rts, BASE


class NumericContracts(unittest.TestCase):
    def test_basis_metric(self):
        B=np.array([[1,1],[0,1]]);c=np.array([1,2])
        assert_allclose(B@c,[3,2]);self.assertEqual(c@B.T@B@c,13)

    def test_cross_product(self):
        assert_allclose(np.cross([1,2,0],[0,1,3]),[6,-3,1])

    def test_psd_eigen(self):
        C=np.array([[2,1],[1,2]])
        assert_allclose(linalg.eigvalsh(C),[1,3])

    def test_qr_least_squares(self):
        A=np.array([[1,0],[1,1],[1,2.]])
        b=np.array([1,2,2.]);x=linalg.lstsq(A,b)[0]
        assert_allclose(x,[7/6,.5]);assert_allclose(A.T@(A@x-b),[0,0],atol=1e-14)

    def test_pseudoinverse_nullspace(self):
        A=np.array([[1,1.]])
        assert_allclose(linalg.pinv(A)@np.array([2.]),[1,1])
        assert_allclose(A@np.array([1.,-1.]),[0])

    def test_svd_condition_square(self):
        A=np.diag([3.,.1]);self.assertAlmostEqual(np.linalg.cond(A.T@A),900.)

    def test_pca_exact(self):
        X=np.array([[-2,-1],[-1,0],[1,0],[2,1.]])
        assert_allclose(X.T@X/4,[[2.5,1],[1,.5]])
        assert_allclose(linalg.eigvalsh(X.T@X/4),[(3-np.sqrt(8))/2,(3+np.sqrt(8))/2])

    def test_chain_rule(self):
        x,y=2.,3.;grad=np.array([y+np.cos(x),x])*2*(x*y+np.sin(x))
        def f(p):return (p[0]*p[1]+np.sin(p[0]))**2
        numeric=np.array([(f(np.array([x,y])+1e-5*np.eye(2)[i])-f(np.array([x,y])-1e-5*np.eye(2)[i]))/2e-5 for i in range(2)])
        assert_allclose(grad,numeric,rtol=1e-9)

    def test_hessian_exact(self):
        x=1.; r=x*x-4;J=2*x
        self.assertEqual(J*J+2*r,-2.)

    def test_gn_step(self):
        J=np.array([[1,1],[1,-1.]]);r=np.array([-1,-3.])
        assert_allclose(linalg.lstsq(J,-r)[0],[2,-1])

    def test_forward_reverse_value(self):
        x,y=2.,3.;t=x*y;u=x+y;f=t*u
        self.assertEqual(f,30);assert_allclose([y*u+t,x*u+t],[21,16])

    def test_conditional_gaussian(self):
        C=np.array([[4,1.2],[1.2,1.]])
        self.assertAlmostEqual(1.2/1*2,2.4)
        self.assertAlmostEqual(C[0,0]-C[0,1]**2/C[1,1],2.56)

    def test_map(self):
        P=4.;R=1.;mu=0.;z=3.
        self.assertEqual((mu/P+z/R)/(1/P+1/R),2.4)
        self.assertEqual(1/(1/P+1/R),.8)

    def test_correlated_mean(self):
        C=np.array([[1,.9],[.9,1]]);w=np.array([.5,.5])
        self.assertAlmostEqual(w@C@w,.95)

    def test_huber_worked(self):
        self.assertAlmostEqual(huber_location(np.array([0.,0.,0.,4.]),1.),1/3,places=10)

    def test_em_monotone(self):
        y=np.array([-3,-2,-1,1,2,3.]);_,_,ll=em_fixed_variance(y)
        self.assertTrue(np.all(np.diff(ll)>=-1e-10))

    def test_em_symmetry_failure(self):
        means,_,_=em_fixed_variance(np.array([-3,-2,2,3.]),(0,0))
        assert_allclose(means,[0,0],atol=1e-14)

    def test_kf_numeric(self):
        F=np.array([[1,1],[0,1.]]);H=np.array([[1,0.]])
        m,p,pm,pp,_=kf(np.array([[2.]]),F,H,np.diag([.25,.25]),np.array([[1.]]),np.array([0.,1.]),np.eye(2))
        assert_allclose(pm[0],[1,1]);assert_allclose(pp[0],[[2.25,1],[1,1.25]])
        assert_allclose(m[0],[22/13,17/13]);assert_allclose(p[0],[[9/13,4/13],[4/13,49/52]])

    def test_information_equivalence(self):
        P=np.array([[2.25,1],[1,1.25]]);mu=np.array([1,1.]);H=np.array([[1,0.]])
        info=linalg.inv(P)+H.T@H;eta=linalg.solve(P,mu)+H.T[:,0]*2
        assert_allclose(linalg.solve(info,eta),[22/13,17/13])

    def test_schur_marginal(self):
        L=np.array([[2,-1],[-1,2.]])
        self.assertAlmostEqual(2-1/2,1.5);self.assertAlmostEqual(linalg.inv(L)[1,1],2/3)

    def test_observability(self):
        F=np.array([[1,1],[0,1]]);H=np.array([[1,0]])
        self.assertEqual(np.linalg.matrix_rank(np.vstack([H,H@F])),2)

    def test_gauge(self):
        J=np.array([[-1,1,0],[0,-1,1.]])
        assert_allclose(J@np.ones(3),0);self.assertEqual(np.linalg.matrix_rank(J),2)

    def test_three_state_gauge_solution(self):
        J=np.array([[-1,1,0],[0,-1,1.]])
        assert_allclose(linalg.eigvalsh(J.T@J),[0,1,3],atol=1e-14)
        x=linalg.pinv(J)@np.array([1.,2.])
        assert_allclose(x,[-4/3,-1/3,5/3])
        assert_allclose(J@np.array([0.,1.,3.]),J@x)

    def test_unscented_square(self):
        s=.8;points=np.array([0,s,-s]);wm=np.array([0,.5,.5]);wc=np.array([2,.5,.5]);ys=points**2
        mu=wm@ys;var=wc@(ys-mu)**2
        self.assertAlmostEqual(mu,.64);self.assertAlmostEqual(var,.8192)

    def test_gate(self):
        S=np.array([[4,1.2],[1.2,1.]])
        d=np.array([0,2.]);self.assertGreater(d@linalg.solve(S,d),stats.chi2.ppf(.95,2))

    def test_saved_monte_carlo(self):
        data=np.load(BASE/"artifacts/d8/arrays.npz")
        self.assertLess(abs(data["matched_nis"].mean()-1),.1)
        self.assertLess(abs(data["matched_nees"].mean()-2),.2)
        self.assertGreater(data["underreported_nees"].mean(),4)
        self.assertTrue(np.all(np.linalg.eigvalsh(data["matched_covs"])>0))
        self.assertTrue(np.all(np.linalg.eigvalsh(data["matched_covs"]-data["smooth_cov"])>-1e-10))


if __name__ == "__main__":unittest.main(verbosity=2)
