"""Small teaching operators; OpenCV/SciPy supply production numerical kernels."""
import cv2
import numpy as np
from scipy import ndimage


def srgb_encode(x):
    x = np.asarray(x, dtype=float)
    return np.where(x <= 0.0031308, 12.92*x, 1.055*np.maximum(x, 0)**(1/2.4)-0.055)


def srgb_decode(x):
    x = np.asarray(x, dtype=float)
    return np.where(x <= 0.04045, x/12.92, ((x+0.055)/1.055)**2.4)


def psnr(reference, estimate, peak=255.0):
    mse = np.mean((np.asarray(reference, float)-np.asarray(estimate, float))**2)
    return float('inf') if mse == 0 else float(10*np.log10(peak**2/mse))


def ssim(reference, estimate, peak=255.0):
    """Explicit population moments, 11x11 sigma1.5, valid centers only."""
    a, b = np.asarray(reference, float), np.asarray(estimate, float)
    blur = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5, borderType=cv2.BORDER_REFLECT_101)
    ma, mb = blur(a), blur(b)
    va, vb = np.maximum(blur(a*a)-ma*ma, 0), np.maximum(blur(b*b)-mb*mb, 0)
    cov = blur(a*b)-ma*mb
    c1, c2 = (0.01*peak)**2, (0.03*peak)**2
    score = ((2*ma*mb+c1)*(2*cov+c2))/((ma*ma+mb*mb+c1)*(va+vb+c2))
    return float(score[5:-5, 5:-5].mean())


def gradients(image):
    x = np.asarray(image, np.float64)
    gx = cv2.Sobel(x, cv2.CV_64F, 1, 0, ksize=3, scale=1/8, borderType=cv2.BORDER_REFLECT_101)
    gy = cv2.Sobel(x, cv2.CV_64F, 0, 1, ksize=3, scale=1/8, borderType=cv2.BORDER_REFLECT_101)
    return gx, gy


def nms_four_bins(magnitude, angle):
    """Teaching four-direction NMS, not OpenCV internal Canny output."""
    angle = np.rad2deg(angle) % 180
    bins = (np.floor((angle+22.5)/45).astype(int)) % 4
    out = np.zeros_like(magnitude)
    # In image coordinates y points down, so +45 degrees compares SE and NW.
    for direction, (dy, dx) in enumerate([(0, 1), (1, 1), (1, 0), (1, -1)]):
        p = np.roll(magnitude, (dy, dx), (0, 1))
        q = np.roll(magnitude, (-dy, -dx), (0, 1))
        keep = (bins == direction) & (magnitude >= p) & (magnitude >= q)
        out[keep] = magnitude[keep]
    out[[0, -1], :] = 0
    out[:, [0, -1]] = 0
    return out


def hysteresis(nms, low, high):
    if not 0 < low <= high:
        raise ValueError('Require 0 < low <= high')
    strong, eligible = nms >= high, nms >= low
    return ndimage.binary_propagation(strong, structure=np.ones((3, 3)), mask=eligible)


def teaching_canny(image, sigma=1.2, low=8, high=20):
    smooth = cv2.GaussianBlur(np.asarray(image, float), (0, 0), sigma,
                              borderType=cv2.BORDER_REFLECT_101)
    gx, gy = gradients(smooth)
    magnitude = np.hypot(gx, gy)
    angle = np.arctan2(gy, gx)
    nms = nms_four_bins(magnitude, angle)
    return dict(smooth=smooth, gx=gx, gy=gy, magnitude=magnitude, angle=angle,
                nms=nms, strong=nms >= high, eligible=nms >= low,
                edges=hysteresis(nms, low, high))


def otsu_scores(hist):
    p = np.asarray(hist, float)/np.sum(hist)
    w = np.cumsum(p)
    m = np.cumsum(p*np.arange(len(p)))
    score = np.zeros_like(p)
    valid = (w > 0) & (w < 1)
    score[valid] = (m[-1]*w[valid]-m[valid])**2/(w[valid]*(1-w[valid]))
    return score


def confusion(truth, prediction):
    t, p = np.asarray(truth, bool), np.asarray(prediction, bool)
    tp, fp, fn, tn = (int(x.sum()) for x in (t&p, ~t&p, t&~p, ~t&~p))
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, precision=tp/max(tp+fp, 1),
                recall=tp/max(tp+fn, 1), iou=tp/max(tp+fp+fn, 1))
