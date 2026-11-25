"""Reproduce all D1-D4 figures, arrays, metrics and provenance locally."""
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy import ndimage, signal
from PIL import Image
from imaging import srgb_encode, srgb_decode, psnr, ssim, gradients, teaching_canny, confusion

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
CFG = json.loads((BASE/'configs/default.json').read_text())
FIG = BASE/'figures'
ART = BASE/'artifacts'
plt.rcParams.update({'font.size': 10, 'axes.titlesize': 10, 'axes.labelsize': 9,
                     'legend.fontsize': 8, 'figure.constrained_layout.use': True})


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, fig):
    fig.savefig(FIG/name, dpi=CFG['dpi'], facecolor='white')
    plt.close(fig)


def panel(ax, image, title, vmin=0, vmax=255, cmap='gray'):
    ax.imshow(image, cmap=cmap, vmin=vmin, vmax=vmax, interpolation='nearest')
    ax.set_title(title)
    ax.set_xlabel('x [pixel]')
    ax.set_ylabel('y [pixel]')


def record(module, arrays, metrics):
    out = ART/module
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out/'arrays.npz', **arrays)
    (out/'metrics.json').write_text(json.dumps(metrics, indent=2, allow_nan=False)+'\n')
    print(module, json.dumps(metrics), flush=True)


def main():
    start = time.perf_counter()
    FIG.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    cv2.setNumThreads(1)
    rng = np.random.default_rng(CFG['seed'])
    left = cv2.imread(str(ROOT/CFG['image_left']), cv2.IMREAD_UNCHANGED)
    right = cv2.imread(str(ROOT/CFG['image_right']), cv2.IMREAD_UNCHANGED)
    assert left.dtype == np.uint8 and left.ndim == 2 and right.shape == left.shape
    x, y, w, h = CFG['roi_xywh']
    roi = left[y:y+h, x:x+w].astype(float)
    means = np.array(CFG['sensor_means_e'], float)
    draws = rng.poisson(means[:, None], (len(means), CFG['sensor_trials']))
    draws = draws + rng.normal(0, CFG['sensor_read_sigma_e'], draws.shape)
    theoretical = means+CFG['sensor_read_sigma_e']**2
    fig, ax = plt.subplots(1, 2, figsize=(7, 3.4))
    ax[0].loglog(means, theoretical, label='Poisson + read theory')
    ax[0].scatter(means, draws.var(axis=1), label='100000 draws', color='crimson', s=20)
    ax[0].set(xlabel='Mean photoelectrons [e-]', ylabel='Variance [e- squared]')
    ax[0].legend()
    ax[1].loglog(means, means/np.sqrt(theoretical), 'o-', label='Total SNR')
    ax[1].loglog(means, np.sqrt(means), '--', label='Shot-only limit')
    ax[1].set(xlabel='Mean photoelectrons [e-]', ylabel='Signal / noise SD [1]')
    ax[1].legend()
    save('01_photon_noise.png', fig)
    line = np.linspace(0, 1, 256)
    rgb = np.zeros((96, 256, 3))
    rgb[:, :85] = (0.7, 0.15, 0.1)
    rgb[:, 85:170] = (0.1, 0.6, 0.2)
    rgb[:, 170:] = (0.1, 0.15, 0.8)
    rgb *= np.linspace(0.1, 1, 96)[:, None, None]
    cast = rgb*np.array([0.5, 1, 0.7])
    mosaic = np.zeros(rgb.shape[:2])
    mosaic[0::2, 0::2] = cast[0::2, 0::2, 0]
    mosaic[0::2, 1::2] = cast[0::2, 1::2, 1]
    mosaic[1::2, 0::2] = cast[1::2, 0::2, 1]
    mosaic[1::2, 1::2] = cast[1::2, 1::2, 2]
    fig, ax = plt.subplots(2, 2, figsize=(7, 5.5))
    ax[0, 0].plot(line, line, label='Linear'); ax[0, 0].plot(line, srgb_encode(line), label='sRGB')
    ax[0, 0].set(xlabel='Linear component [1]', ylabel='Encoded component [1]'); ax[0, 0].legend()
    panel(ax[0, 1], mosaic, 'Synthetic RGGB measured sites', 0, 1)
    panel(ax[1, 0], srgb_encode(cast), 'Synthetic color cast (display sRGB)', 0, 1)
    panel(ax[1, 1], srgb_encode(rgb), 'Known-gain white balance', 0, 1)
    save('02_color_encoding.png', fig)
    motion = np.ones((1, 15), float)/15
    blurred = cv2.filter2D(roi, -1, motion, borderType=cv2.BORDER_REFLECT_101)
    doubled = np.clip(2*roi, 0, 255)
    fig, ax = plt.subplots(3, 1, figsize=(7, 7.8))
    panel(ax[0], roi, 'KITTI 00 / left 000000: measured PNG ROI')
    panel(ax[1], blurred, 'Synthetic 15-pixel horizontal box PSF')
    panel(ax[2], doubled, 'Synthetic DN x2 + clipping (not exposure calibration)')
    save('03_kitti_measurement.png', fig)
    record('d1', dict(means=means, sampled_mean=draws.mean(axis=1), sampled_variance=draws.var(axis=1),
                      roi=roi, blur=blurred, doubled=doubled, synthetic_rgb=rgb, mosaic=mosaic),
           dict(shape=list(left.shape), dtype=str(left.dtype), roi_xywh=CFG['roi_xywh'],
                original_saturation_fraction=float((roi == 255).mean()),
                doubled_saturation_fraction=float((doubled == 255).mean()),
                photon_variances=draws.var(axis=1).tolist(), theoretical_variances=theoretical.tolist(),
                mean_linear_of_encoded_midpoint=float(srgb_decode(0.5)),
                encoded_linear_midpoint=float(srgb_encode(0.5))))
    n = np.arange(64)
    high = np.cos(2*np.pi*0.7*n)
    low = np.cos(2*np.pi*0.3*n)
    t = np.linspace(0, 15, 1000)
    fig, ax = plt.subplots(2, 1, figsize=(7, 5.4))
    ax[0].plot(t, np.cos(2*np.pi*0.7*t), label='0.7 cycles/pixel continuous')
    ax[0].plot(t, np.cos(2*np.pi*0.3*t), '--', label='0.3 cycles/pixel continuous')
    ax[0].scatter(n[:16], high[:16], s=20, color='black', label='identical integer samples')
    ax[0].set(xlabel='x [pixel]', ylabel='Amplitude [1]'); ax[0].legend(loc='lower left')
    f = np.fft.rfftfreq(64)
    ax[1].stem(f, np.abs(np.fft.rfft(high))/64, basefmt=' ')
    ax[1].set(xlabel='Discrete frequency [cycles/pixel]', ylabel='DFT magnitude / N [1]',
              title='Finite 64-point window: leakage near 0.3 cycles/pixel')
    save('04_alias_frequency.png', fig)
    direct = roi[::4, ::4]
    prefiltered = cv2.GaussianBlur(roi, (0, 0), 1.6, borderType=cv2.BORDER_REFLECT_101)[::4, ::4]
    area = cv2.resize(roi, (w//4, h//4), interpolation=cv2.INTER_AREA)
    fig, ax = plt.subplots(2, 2, figsize=(7, 5.4))
    for axis, a, title in zip(ax.flat, [roi, direct, prefiltered, area],
                             ['Original ROI 400x240', 'Stride 4: phase = 0', 'Gaussian sigma1.6 + stride4', 'Area 4x4: different center phase']):
        panel(axis, a, title)
    save('05_kitti_downsample.png', fig)
    patch = np.arange(1, 10, dtype=float).reshape(3, 3)
    kernel = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]], float)/16
    fig, ax = plt.subplots(1, 3, figsize=(7, 2.9))
    for axis, a, title in zip(ax, [patch, kernel, patch*kernel], ['3x3 patch [DN]', 'Weights [1]', 'Products [DN], sum=5']):
        axis.imshow(a, cmap='Blues'); axis.set_title(title); axis.set_xticks([]); axis.set_yticks([])
        for (r, c), val in np.ndenumerate(a):
            axis.text(c, r, f'{val:.4g}', ha='center', va='center', color='white' if val > a.max()*0.65 else 'black')
    save('06_convolution_numeric.png', fig)
    record('d2', dict(high=high, low=low, direct=direct, prefiltered=prefiltered, area=area, patch=patch, kernel=kernel),
           dict(alias_max_difference=float(np.max(np.abs(high-low))), weighted_sum=float((patch*kernel).sum()),
                dft4_real=np.fft.fft([1, 2, 3, 4]).real.tolist(), dft4_imag=np.fft.fft([1, 2, 3, 4]).imag.tolist(),
                direct_variance=float(direct.var()), prefiltered_variance=float(prefiltered.var()),
                note='No low-resolution ground truth; variances are descriptive, not accuracy.'))
    noisy = roi+rng.normal(0, CFG['noise_sigma_dn'], roi.shape)
    u = rng.random(roi.shape)
    impulse = np.where(u < CFG['impulse_probability']/2, 0,
                       np.where(u > 1-CFG['impulse_probability']/2, 255, roi))
    def filters(a):
        return {'input': a,
                'gaussian': cv2.GaussianBlur(a, (0, 0), CFG['gaussian_sigma_px'], borderType=cv2.BORDER_REFLECT_101),
                'median3': cv2.medianBlur(a.astype(np.float32), 3).astype(float),
                'bilateral': cv2.bilateralFilter(a.astype(np.float32), 9, CFG['bilateral_sigma_color_dn'],
                                                CFG['bilateral_sigma_space_px'], borderType=cv2.BORDER_REFLECT_101).astype(float)}
    outputs = {kind: filters(a) for kind, a in [('gaussian_noise', noisy), ('impulse', impulse)]}
    scores = {kind: {name: {'psnr_db': psnr(roi, a), 'ssim': ssim(roi, a)} for name, a in values.items()}
              for kind, values in outputs.items()}
    fig, ax = plt.subplots(2, 2, figsize=(7, 5.4))
    for axis, (name, a) in zip(ax.flat, outputs['gaussian_noise'].items()):
        panel(axis, a, f'{name}: {scores["gaussian_noise"][name]["psnr_db"]:.2f} dB')
    save('07_gaussian_denoising.png', fig)
    fig, ax = plt.subplots(2, 2, figsize=(7, 5.4))
    for axis, (name, a) in zip(ax.flat, outputs['impulse'].items()):
        panel(axis, a, f'{name}: {scores["impulse"][name]["psnr_db"]:.2f} dB')
    save('08_impulse_failure.png', fig)
    clean = np.full((128, 256), 60.0); clean[:, 128:] = 190
    clean[40:88, 60:62] = 190
    corrupt = clean+rng.normal(0, 15, clean.shape)
    smooths = [cv2.GaussianBlur(corrupt, (0, 0), s, borderType=cv2.BORDER_REFLECT_101) for s in [0.5, 1, 2, 4]]
    # Exact periodic Gaussian transfer function: explicitly synthetic forward model.
    fy = np.fft.fftfreq(clean.shape[0])[:, None]; fx = np.fft.fftfreq(clean.shape[1])[None, :]
    transfer = np.exp(-2*np.pi**2*1.8**2*(fx*fx+fy*fy))
    observation = np.fft.ifft2(np.fft.fft2(clean)*transfer).real+rng.normal(0, 2, clean.shape)
    inverse = np.fft.ifft2(np.fft.fft2(observation)/np.maximum(transfer, 1e-6)).real
    regularized = np.fft.ifft2(np.fft.fft2(observation)*transfer/(transfer**2+0.01)).real
    fig, ax = plt.subplots(2, 1, figsize=(7, 5.8))
    ax[0].plot(clean[64], color='black', label='Synthetic truth')
    for s, a in zip([0.5, 1, 2, 4], smooths): ax[0].plot(a[64], label=f'sigma={s} px', alpha=.8)
    ax[0].set(xlabel='x [pixel]', ylabel='Intensity [DN]', title='Thin line loss and edge bias'); ax[0].legend(ncol=3, loc='lower right')
    ax[1].plot(clean[64], label='Truth', color='black'); ax[1].plot(observation[64], label='Blur + noise')
    ax[1].plot(regularized[64], label='Regularized inverse K=0.01')
    ax[1].set(xlabel='x [pixel]', ylabel='Intensity [DN]', title=f'Naive inverse PSNR {psnr(clean, inverse):.1f} dB (outside plot)')
    ax[1].legend()
    save('09_bias_inverse.png', fig)
    scores['synthetic_inverse'] = {'observation_psnr': psnr(clean, observation), 'inverse_psnr': psnr(clean, inverse),
                                   'regularized_psnr': psnr(clean, regularized), 'inverse_max_abs_dn': float(np.abs(inverse).max())}
    scores['synthetic_sigma_sweep'] = {str(s): psnr(clean, a) for s, a in zip([0.5, 1, 2, 4], smooths)}
    record('d3', dict(reference=roi, noisy=noisy, impulse=impulse, clean=clean, observation=observation,
                      inverse=inverse, regularized=regularized,
                      **{kind+'_'+name: a for kind, val in outputs.items() for name, a in val.items()}), scores)
    stages = teaching_canny(roi, CFG['gaussian_sigma_px'], CFG['canny_low_dn_per_px'], CFG['canny_high_dn_per_px'])
    scharrx = cv2.Scharr(stages['smooth'], cv2.CV_64F, 1, 0, scale=1/32)
    lap = cv2.Laplacian(stages['smooth'], cv2.CV_64F, ksize=1)
    dog = cv2.GaussianBlur(roi, (0, 0), 1.6)-cv2.GaussianBlur(roi, (0, 0), 1.0)
    fig, ax = plt.subplots(2, 2, figsize=(7, 5.4))
    for axis, a, title in zip(ax.flat, [stages['gx'], stages['gy'], lap, dog],
                             ['Sobel gx [DN/pixel]', 'Sobel gy [DN/pixel]', 'Laplacian [DN/pixel^2]', 'DoG (1.6 px - 1.0 px)\noutput [DN]']):
        lim = max(np.abs(a).max(), 1)
        im = axis.imshow(a, cmap='coolwarm', vmin=-lim, vmax=lim); axis.set_title(title)
        axis.set_xlabel('x [pixel]'); axis.set_ylabel('y [pixel]'); fig.colorbar(im, ax=axis, shrink=.75)
    save('10_signed_derivatives.png', fig)
    fig, ax = plt.subplots(3, 2, figsize=(7, 7.5))
    fields = [('smooth', 'Gaussian sigma=1.2 px;\noutput [DN]', 255), ('magnitude', 'Gradient magnitude [DN/pixel]', 80),
              ('nms', 'Teaching 4-bin NMS [DN/pixel]', 80), ('strong', 'Strong >=20 [binary]', 1),
              ('eligible', 'Eligible >=8 [binary]', 1), ('edges', '8-connected hysteresis [binary]', 1)]
    for axis, (name, title, vmax) in zip(ax.flat, fields): panel(axis, stages[name], title, 0, vmax)
    save('11_canny_stages.png', fig)
    cv_edges = cv2.Canny(np.clip(np.rint(stages['smooth']), 0, 255).astype(np.uint8), 64, 160, L2gradient=True)
    counts = {}
    fig, ax = plt.subplots(2, 2, figsize=(7, 5.4))
    for axis, (lo, hi) in zip(ax.flat, [(3, 8), (8, 20), (16, 40)]):
        e = teaching_canny(roi, 1.2, lo, hi)['edges']; counts[f'{lo}_{hi}'] = int(e.sum())
        panel(axis, e, f'Teaching thresholds {lo}/{hi}: {e.sum()}', 0, 1)
    panel(ax[1, 1], cv_edges, f'OpenCV 64/160 L2: {(cv_edges>0).sum()}', 0, 255)
    save('12_canny_thresholds.png', fig)
    yy, xx = np.mgrid[:128, :192]
    truth = ((xx-96)**2+(yy-64)**2 < 30**2)
    illumination = 25+xx*0.9+truth*55
    illum8 = np.clip(np.rint(illumination), 0, 255).astype(np.uint8)
    threshold, mask = cv2.threshold(illum8, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    objects = np.zeros((64, 96), np.uint8)
    objects[10:40, 12:40] = 1; objects[10:40, 42:70] = 1
    objects[20:24, 20:24] = 0; objects[50, 50] = 1
    opened = cv2.morphologyEx(objects, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    closed = cv2.morphologyEx(objects, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    fig, ax = plt.subplots(2, 2, figsize=(7, 5.4))
    for axis, a, title, vmax in zip(ax.flat, [illum8, mask, objects, closed],
                                  ['Synthetic object + lighting ramp', f'Otsu T={threshold:.0f}: not object truth',
                                   'Two objects, one hole, one speck', 'Closing5: merged objects, filled hole'], [255, 255, 1, 1]):
        panel(axis, a, title, 0, vmax)
    save('13_otsu_topology.png', fig)
    metrics = {'teaching_counts': counts, 'opencv_edge_count': int((cv_edges>0).sum()),
               'otsu_threshold_dn': threshold, 'otsu_confusion': confusion(truth, mask > 0),
               'components8_original': cv2.connectedComponents(objects, connectivity=8)[0]-1,
               'components8_opened': cv2.connectedComponents(opened, connectivity=8)[0]-1,
               'components8_closed': cv2.connectedComponents(closed, connectivity=8)[0]-1,
               'notes': 'KITTI counts are not accuracy; Canny stages are teaching approximation.'}
    record('d4', dict(**stages, scharrx=scharrx, laplacian=lap, dog=dog, opencv_edges=cv_edges,
                      synthetic_truth=truth, illumination=illum8, otsu=mask, objects=objects, opened=opened, closed=closed), metrics)
    manifest = {'seed': CFG['seed'], 'config': CFG, 'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'runtime_seconds': time.perf_counter()-start, 'platform': platform.platform(),
                'versions': {'python': sys.version, 'numpy': np.__version__, 'scipy': scipy.__version__,
                             'opencv': cv2.__version__, 'matplotlib': matplotlib.__version__},
                'input_sha256': {p: digest(ROOT/p) for p in [CFG['image_left'], CFG['image_right']]},
                'source_sha256': {str(p.relative_to(BASE)): digest(p) for p in sorted((BASE/'src').glob('*.py'))},
                'config_sha256': digest(BASE/'configs/default.json'),
                'figure_sha256': {p.name: digest(p) for p in sorted(FIG.glob('*.png'))},
                'figure_dimensions': {p.name: list(Image.open(p).size) for p in sorted(FIG.glob('*.png'))},
                'artifact_sha256': {str(p.relative_to(ART)): digest(p) for p in sorted(ART.glob('d*/*'))},
                'real_vs_synthetic': 'KITTI gray ROI is measured PNG, not raw radiance. All added noise/color/PSF are synthetic.'}
    (ART/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('runtime_seconds', manifest['runtime_seconds'], flush=True)


if __name__ == '__main__':
    main()
