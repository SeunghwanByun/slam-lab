import unittest
import json
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.special import softmax
from experiment import BASE, attention, binary_loss, iou, mlp, nms, pr_ap, receptive


class Contracts(unittest.TestCase):
    def test_bce(self):
        self.assertAlmostEqual(binary_loss(np.array([0.]),np.array([1.])),np.log(2))
    def test_bce_stable(self):
        self.assertTrue(np.isfinite(binary_loss(np.array([1000.,-1000.]),np.array([0.,1.]))))
    def test_softmax_shift(self):
        np.testing.assert_allclose(softmax([1,2,3]),softmax([1001,1002,1003]))
    def test_mlp_gradient(self):
        x=np.array([[1.,2.],[-1.,.2]]);y=np.array([1.,0.]);p=[np.array([[.2,.1],[.3,-.1]]),np.zeros(2),np.array([.4,-.2]),np.array(.1)]
        _,gs,_=mlp(x,y,p)
        for j in range(4):
            for ix in np.ndindex(p[j].shape):
                a=[v.copy() for v in p];b=[v.copy() for v in p];a[j][ix]+=1e-5;b[j][ix]-=1e-5
                num=(mlp(x,y,a)[0]-mlp(x,y,b)[0])/2e-5
                self.assertAlmostEqual(num,gs[j][ix],places=8)
    def test_iou_example(self):
        self.assertAlmostEqual(iou([0,0,4,4],[1,0,5,4]),.6)
    def test_iou_empty(self):
        self.assertEqual(iou([0,0,0,0],[0,0,0,0]),0)
    def test_iou_disjoint(self):
        self.assertEqual(iou([0,0,1,1],[2,2,3,3]),0)
    def test_nms(self):
        self.assertEqual(nms([[0,0,4,4],[1,0,5,4],[6,0,10,4]],[.9,.8,.7],.5),[0,2])
    def test_nms_empty(self):
        self.assertEqual(nms([],[],.5),[])
    def test_ap(self):
        self.assertAlmostEqual(pr_ap([1,0,1,0,1],3)[2],34/45)
    def test_ap_failure(self):
        self.assertAlmostEqual(pr_ap([0,1,0,1,1],3)[2],.6)
    def test_assignment(self):
        c=np.array([[1,2,8],[2,8,2],[7,1,4]]);r,k=linear_sum_assignment(c)
        self.assertEqual(c[r,k].sum(),4)
    def test_attention_rows(self):
        a,o=attention(np.eye(2),np.eye(2),np.array([[2.,0],[0,4]]))
        np.testing.assert_allclose(a.sum(1),1)
        self.assertAlmostEqual(a[0,0],.6697615493266569)
        self.assertAlmostEqual(o[0,1],1.3209538026933723)
    def test_attention_permutation(self):
        q=np.array([[1.,2],[3.,4]]);v=np.array([[1.,0],[0.,2]])
        a,o=attention(q,q,v);_,p=attention(q[::-1],q[::-1],v[::-1]);np.testing.assert_allclose(p,o[::-1])
    def test_receptive(self):
        np.testing.assert_array_equal(receptive([(3,1,1),(3,2,1),(3,1,1),(3,1,2)])[-1],[17,2])
    def test_dice_iou(self):
        i=.6;self.assertAlmostEqual(2*i/(1+i),.75)
    def test_depth_alignment(self):
        y=1/np.array([2.,4,8]);x=2*y+.1;c=np.linalg.lstsq(np.c_[x,np.ones(3)],y,rcond=None)[0]
        np.testing.assert_allclose(c,[.5,-.05],atol=1e-12)
    def test_convolution_dimensions(self):
        self.assertEqual((32+2-3)//2+1,16)
    def test_logistic_worked_update(self):
        x=np.array([2.,-1.]);w=np.array([.1,.2]);g=(.5-1)*x
        nw=w-.1*g;nb=.05
        np.testing.assert_allclose(nw,[.2,.15])
        self.assertAlmostEqual(binary_loss(np.array([nw@x+nb]),np.array([1.])),.554355244468527)
    def test_dropout_variance(self):
        q=.8;h=4.;values=np.array([h/q,0]);prob=np.array([q,1-q])
        self.assertAlmostEqual(prob@values,4)
        self.assertAlmostEqual(prob@(values**2)-(prob@values)**2,4)
    def test_shared_kernel_worked(self):
        x=np.arange(1,10).reshape(3,3);k=np.array([[1,0],[0,-1]])
        patches=np.lib.stride_tricks.sliding_window_view(x,(2,2))
        np.testing.assert_array_equal((patches*k).sum((2,3)),-4*np.ones((2,2)))
        self.assertEqual(patches[:,:,1,1].sum(),28)
    def test_soft_dice_worked(self):
        p=np.array([.8,.2]);y=np.array([1.,0]);n=2*p@y;d=p.sum()+y.sum()
        self.assertAlmostEqual(1-n/d,.2)
        np.testing.assert_allclose(-(2*y*d-n)/d**2,[-.6,.4])
    def test_contrastive_worked(self):
        self.assertAlmostEqual(np.log(np.e+1)-1,.3132616875182228)
        self.assertAlmostEqual(np.log(np.e+2)-1,.5514447139320511)
    def test_box_encode_decode(self):
        a=np.array([20.,30.,10.,20.]);target=np.array([25.,25.,20.,10.])
        t=np.r_[(target[:2]-a[:2])/a[2:],np.log(target[2:]/a[2:])]
        np.testing.assert_allclose(t,[.5,-.25,np.log(2),-np.log(2)])
        np.testing.assert_allclose(np.r_[a[:2]+a[2:]*t[:2],a[2:]*np.exp(t[2:])],target)


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Contracts)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    destination=BASE/'artifacts/tests.json'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps({'checks':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful()},indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
