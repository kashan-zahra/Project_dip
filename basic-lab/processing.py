"""DIP Lab Basics - the image-processing functions.

Every function takes an image (a NumPy array from cv2.imread, colours in BGR order)
and returns the processed image. One function per lab topic.
"""
import cv2
import numpy as np
from skimage.exposure import match_histograms


def to_gray(img):
    # colour (3 channels) -> gray (1 channel); a gray image is returned unchanged
    if img.ndim == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


# ---------------------------------------------------------------- 1. intensity (point) operations

def negative(img):
    # s = 255 - r      (dark becomes bright, bright becomes dark)
    return 255 - img


def brightness_contrast(img, alpha, beta):
    # s = alpha * r + beta      alpha = contrast, beta = brightness (result clipped to 0..255)
    return cv2.convertScaleAbs(img, alpha=alpha, beta=beta)


def contrast_stretch(img):
    # s = (r - r_min) / (r_max - r_min) * 255      stretch the used range to the full 0..255
    r_min, r_max = int(img.min()), int(img.max())
    if r_max == r_min:
        return img.copy()
    out = (img.astype(np.float32) - r_min) / (r_max - r_min) * 255
    return out.astype(np.uint8)


# ---------------------------------------------------------------- 2. histogram

def histogram(img):
    # how many pixels have each gray level 0..255
    hist = cv2.calcHist([to_gray(img)], [0], None, [256], [0, 256])
    return hist.flatten().astype(int).tolist()


def hist_equalize(img):
    # spread the gray levels evenly using the cumulative histogram (CDF)
    return cv2.equalizeHist(to_gray(img))


def clahe(img, clip, tile):
    # equalization done in small tiles; clip limit stops noise from being boosted too much
    c = cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile))
    return c.apply(to_gray(img))


def hist_match(img, ref):
    # make img's histogram look like ref's histogram
    out = match_histograms(img, ref, channel_axis=-1)
    return np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- 3. crop and resize

def crop(img, x, y, w, h):
    # x, y, w, h are percentages of the image size; cropping is just array slicing
    H, W = img.shape[:2]
    x0, y0 = int(W * x / 100), int(H * y / 100)
    x1, y1 = min(W, x0 + max(1, int(W * w / 100))), min(H, y0 + max(1, int(H * h / 100)))
    return img[y0:y1, x0:x1]


def resize(img, percent, method):
    # nearest = copy the closest pixel (KNN), bilinear = mix 4 pixels, bicubic = mix 16 pixels
    methods = {"nearest": cv2.INTER_NEAREST, "bilinear": cv2.INTER_LINEAR, "bicubic": cv2.INTER_CUBIC}
    H, W = img.shape[:2]
    size = (max(1, int(W * percent / 100)), max(1, int(H * percent / 100)))
    return cv2.resize(img, size, interpolation=methods[method])


def sampling(img, samples):
    # keep only `samples` pixels along the long side, then blow it back up -> blocky picture
    H, W = img.shape[:2]
    s = samples / max(H, W)
    small = cv2.resize(img, (max(1, int(W * s)), max(1, int(H * s))), interpolation=cv2.INTER_NEAREST)
    return cv2.resize(small, (W, H), interpolation=cv2.INTER_NEAREST)


# ---------------------------------------------------------------- 4. noise

def gaussian_noise(img, std):
    # add random noise from a normal distribution with mean 0 and the given standard deviation
    noise = np.random.normal(0, std, img.shape)
    return np.clip(img + noise, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- 5. edge detection

def edges(img, method):
    gray = to_gray(img).astype(np.float32)
    if method == "canny":
        return cv2.Canny(to_gray(img), 100, 200)
    if method == "sobel":
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    elif method == "prewitt":
        kx = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], np.float32)
        gx = cv2.filter2D(gray, cv2.CV_32F, kx)
        gy = cv2.filter2D(gray, cv2.CV_32F, kx.T)
    else:  # roberts
        kx = np.array([[1, 0], [0, -1]], np.float32)
        ky = np.array([[0, 1], [-1, 0]], np.float32)
        gx = cv2.filter2D(gray, cv2.CV_32F, kx)
        gy = cv2.filter2D(gray, cv2.CV_32F, ky)
    magnitude = np.sqrt(gx ** 2 + gy ** 2)          # edge strength
    return cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


# ---------------------------------------------------------------- 6. colour: RGB -> HSI

def hsi(img, part):
    # I = (R+G+B)/3,  S = 1 - 3*min(R,G,B)/(R+G+B),  H = angle on the colour wheel
    b, g, r = [c.astype(np.float64) for c in cv2.split(img)]
    if part == "intensity":
        return ((r + g + b) / 3).astype(np.uint8)
    total = r + g + b + 1e-10
    if part == "saturation":
        s = 1 - 3 * np.minimum(np.minimum(r, g), b) / total
        return (s * 255).astype(np.uint8)
    num = 0.5 * ((r - g) + (r - b))
    den = np.sqrt((r - g) ** 2 + (r - b) * (g - b)) + 1e-10
    theta = np.degrees(np.arccos(np.clip(num / den, -1, 1)))
    h = np.where(b <= g, theta, 360 - theta)           # 0..360 degrees
    return (h / 360 * 255).astype(np.uint8)            # shown as gray 0..255


# ---------------------------------------------------------------- 7. pixel connectivity

def connectivity(img, conn):
    # black & white first, then label every group of touching white pixels
    _, binary = cv2.threshold(to_gray(img), 128, 255, cv2.THRESH_BINARY)
    count, labels = cv2.connectedComponents(binary, connectivity=conn)
    rng = np.random.default_rng(1)
    colours = rng.integers(60, 255, (count, 3), dtype=np.uint8)
    colours[0] = 0                                      # background stays black
    return colours[labels], count - 1
