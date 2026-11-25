import unittest
import cv2
import numpy as np
from scipy import signal, ndimage
from imaging import srgb_encode, srgb_decode, psnr, ssim, gradients, nms_four_bins, hysteresis, otsu_scores, confusion


class ImagingTests(unittest.TestCase):
    def test_srgb_roundtrip(self):
        x = np.linspace(0, 1, 1001)
        np.testing.assert_allclose(srgb_decode(srgb_encode(x)), x, atol=1e-7)

    def test_srgb_midpoint(self):
        self.assertAlmostEqual(float(srgb_decode(.5)), .21404114048223255)
        self.assertAlmostEqual(float(srgb_encode(.5)), .7353569830524495)

    def test_sensor_variance_formula(self):
        self.assertEqual(64+3**2, 73)
        self.assertAlmostEqual(64/np.sqrt(73), 7.49063342055, places=9)

    def test_poisson_sample_variance(self):
        rng = np.random.default_rng(20261125)
        x = rng.poisson(64, 200000)+rng.normal(0, 3, 200000)
        self.assertLess(abs(x.var()-73), 1)

    def test_quantization_uniform_variance(self):
        e = np.linspace(-.5, .5, 100001)
        self.assertAlmostEqual(e.var(), 1/12, places=5)

    def test_3x3_convolution(self):
        p = np.arange(1, 10).reshape(3, 3)
        k = np.outer([1, 2, 1], [1, 2, 1])/16
        self.assertEqual(float(signal.convolve2d(p, k, mode='valid')[0, 0]), 5)

    def test_correlation_sign(self):
        p = np.tile(np.arange(5, dtype=float), (5, 1))
        k = np.array([[-1, 0, 1]])
        self.assertEqual(cv2.filter2D(p, -1, k)[2, 2], 2)
        self.assertEqual(signal.convolve2d(p, k, mode='same')[2, 2], -2)

    def test_separable(self):
        a = np.arange(100, dtype=float).reshape(10, 10)
        g = np.array([1, 2, 1], float)/4
        np.testing.assert_allclose(cv2.filter2D(a, -1, np.outer(g, g)), cv2.sepFilter2D(a, -1, g, g))

    def test_dft_four(self):
        np.testing.assert_allclose(np.fft.fft([1, 2, 3, 4]), [10, -2+2j, -2, -2-2j])

    def test_parseval(self):
        x = np.array([1, 2, 3, 4])
        self.assertAlmostEqual(float(np.sum(abs(np.fft.fft(x))**2)/4), 30)

    def test_alias_identity(self):
        n = np.arange(64)
        np.testing.assert_allclose(np.cos(2*np.pi*.7*n), np.cos(2*np.pi*.3*n), atol=1e-13)

    def test_dtype_wrap(self):
        a = np.array([10], np.uint8); b = np.array([20], np.uint8)
        self.assertEqual(int((a-b)[0]), 246)
        self.assertEqual(float((a.astype(float)-b)[0]), -10)

    def test_psnr_worked(self):
        self.assertAlmostEqual(psnr(np.zeros(2), np.array([3, 4]), 255), 37.1617034786, places=8)

    def test_ssim_identity(self):
        a = np.arange(400).reshape(20, 20).astype(float)
        self.assertAlmostEqual(ssim(a, a), 1)

    def test_noise_filter_variance(self):
        k = np.outer([1, 2, 1], [1, 2, 1])/16
        self.assertAlmostEqual(16*np.sum(k*k), 2.25)

    def test_ramp_derivative(self):
        a = np.tile(np.arange(20)*3.0, (20, 1))
        gx, gy = gradients(a)
        np.testing.assert_allclose(gx[2:-2, 2:-2], 3)
        np.testing.assert_allclose(gy, 0)

    def test_nms_direction(self):
        a = np.zeros((5, 5)); a[2, 1:4] = [1, 4, 2]
        result = nms_four_bins(a, np.zeros_like(a))
        self.assertEqual(result[2, 2], 4); self.assertEqual(result[2, 1], 0)

    def test_hysteresis_path(self):
        a = np.zeros((7, 7)); a[3, 1:5] = [10, 5, 5, 5]; a[0, 6] = 5
        b = hysteresis(a, 4, 9)
        self.assertEqual(int(b.sum()), 4); self.assertFalse(b[0, 6])

    def test_threshold_validation(self):
        with self.assertRaises(ValueError): hysteresis(np.zeros((3, 3)), 5, 4)

    def test_otsu_worked(self):
        scores = otsu_scores([2, 2, 0, 2, 2])
        self.assertEqual(int(np.argmax(scores)), 1)
        self.assertAlmostEqual(scores[1], 2.25)

    def test_connectivity(self):
        a = np.eye(3, dtype=np.uint8)
        self.assertEqual(ndimage.label(a, ndimage.generate_binary_structure(2, 1))[1], 3)
        self.assertEqual(ndimage.label(a, np.ones((3, 3)))[1], 1)

    def test_morphology_idempotence(self):
        a = np.zeros((20, 20), np.uint8); a[5:15, 5:15] = 1; a[2, 2] = 1
        k = np.ones((3, 3), np.uint8)
        b = cv2.morphologyEx(a, cv2.MORPH_OPEN, k)
        np.testing.assert_array_equal(b, cv2.morphologyEx(b, cv2.MORPH_OPEN, k))

    def test_confusion_worked(self):
        r = confusion([1, 1, 0, 0], [1, 0, 1, 0])
        self.assertEqual((r['tp'], r['fp'], r['fn'], r['tn']), (1, 1, 1, 1))
        self.assertAlmostEqual(r['iou'], 1/3)

    def test_gain_vs_exposure(self):
        self.assertAlmostEqual(16/np.sqrt(16+9), 3.2)
        self.assertAlmostEqual(4*16/(4*np.sqrt(16+9)), 3.2)
        self.assertGreater(64/np.sqrt(64+9), 3.2)

    def test_clipping_not_invertible(self):
        x = np.array([.2, .8])
        self.assertAlmostEqual(float(x.mean()), .5)
        self.assertAlmostEqual(float((np.clip(2*x, 0, 1)/2).mean()), .35)

    def test_quantization_units(self):
        self.assertAlmostEqual((2**2/12)/(2**2), 1/12)

    def test_white_balance(self):
        gains = np.array([2, 1, 10/7])
        np.testing.assert_allclose(np.array([20, 40, 35])*gains, [40, 40, 50])

    def test_changed_patch(self):
        p = np.arange(1, 10, dtype=float).reshape(3, 3); p[1, 1] = 21
        k = np.outer([1, 2, 1], [1, 2, 1])/16
        self.assertEqual(float(np.sum(p*k)), 9)

    def test_bilinear_worked(self):
        p = np.array([[20, 60], [100, 140]], float)
        weights = np.outer([.5, .5], [.75, .25])
        self.assertEqual(float(np.sum(p*weights)), 70)
        self.assertEqual(float(np.sum((p+7)*weights)), 77)

    def test_border_worked(self):
        a = np.tile([10., 20., 30.], (3, 1))
        k = np.ones((1, 3))/3
        self.assertAlmostEqual(cv2.filter2D(a, -1, k, borderType=cv2.BORDER_REFLECT_101)[1, 0], 50/3)
        self.assertAlmostEqual(cv2.filter2D(a, -1, k, borderType=cv2.BORDER_REPLICATE)[1, 0], 40/3)

    def test_dft_phase(self):
        value = np.fft.fft([1, 2, 3, 4])[1]
        self.assertAlmostEqual(abs(value), np.sqrt(8))
        self.assertAlmostEqual(np.angle(value), 3*np.pi/4)

    def test_bilateral_two_values(self):
        weight = .5*np.exp(-.5)
        self.assertAlmostEqual((50+70*weight)/(1+weight), 54.6539307524, places=9)

    def test_bias_squared(self):
        self.assertAlmostEqual(np.mean([0, 0, 100])**2, 10000/9)

    def test_regularized_inverse(self):
        self.assertAlmostEqual(.1*2/(.1**2+.01), 10)
        self.assertEqual(2/.1, 20)

    def test_psnr_unit_invariance(self):
        a = np.array([3., 4.])
        self.assertAlmostEqual(psnr(np.zeros(2), a), psnr(np.zeros(2), a/255, 1))

    def test_sobel_example(self):
        a = np.tile([10., 20., 30.], (3, 1))
        gx, gy = gradients(a)
        self.assertEqual(gx[1, 1], 10); self.assertEqual(gy[1, 1], 0)
        self.assertEqual(cv2.Sobel(a, cv2.CV_64F, 1, 0)[1, 1], 80)

    def test_norm_threshold(self):
        self.assertGreater(3+4, 6)
        self.assertLess(np.hypot(3, 4), 6)

    def test_otsu_second_threshold(self):
        scores = otsu_scores([2, 2, 0, 2, 2])
        self.assertAlmostEqual(scores[0], 4/3)
        self.assertAlmostEqual(scores[1], scores[2])

    def test_laplacian_constant_and_impulse(self):
        a = np.ones((9, 9))*100
        np.testing.assert_allclose(cv2.Laplacian(a, cv2.CV_64F, ksize=1), 0)
        a[:] = 0; a[4, 4] = 100
        self.assertEqual(cv2.Laplacian(a, cv2.CV_64F, ksize=1)[4, 4], -400)

    def test_nms_diagonal(self):
        a = np.zeros((5, 5)); a[1, 1] = 3; a[2, 2] = 8; a[3, 3] = 9
        result = nms_four_bins(a, np.full_like(a, np.pi/4))
        self.assertEqual(result[2, 2], 0)

    def test_hysteresis_subset(self):
        rng = np.random.default_rng(18)
        a = rng.uniform(0, 30, (20, 20))
        edges = hysteresis(a, 8, 20)
        self.assertTrue(np.all(~edges | (a >= 8)))
        self.assertTrue(np.all(~(a >= 20) | edges))


if __name__ == '__main__': unittest.main(verbosity=2)
