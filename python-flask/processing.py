import cv2
import numpy as np


def to_gray(img):
    if img.ndim == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


# ---------------- ENHANCE ----------------

def brightness_contrast(img, alpha, beta):
    # g(x,y) = alpha * f(x,y) + beta
    return cv2.convertScaleAbs(img, alpha=alpha, beta=beta)


def gamma(img, g):
    # s = 255 * (r / 255) ^ g   (power-law transform, done with a lookup table)
    table = np.array([255 * (i / 255.0) ** g for i in range(256)])
    table = np.clip(np.round(table), 0, 255).astype(np.uint8)
    return cv2.LUT(img, table)


def negative(img):
    # s = 255 - r
    return 255 - img


def contrast_stretch(img):
    # s = (r - r_min) / (r_max - r_min) * 255
    r_min = int(img.min())
    r_max = int(img.max())
    if r_max == r_min:
        return img.copy()
    out = (img.astype(np.float32) - r_min) / (r_max - r_min) * 255
    return out.astype(np.uint8)


def hist_equalize(img):
    return cv2.equalizeHist(to_gray(img))


def clahe(img, clip, tile):
    c = cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile))
    return c.apply(to_gray(img))


# ---------------- TRANSFORM ----------------

def crop(img, x, y, w, h):
    # x, y, w, h are percentages (0-100) of the image size
    H, W = img.shape[:2]
    x0 = min(int(W * x / 100), W - 1)
    y0 = min(int(H * y / 100), H - 1)
    x1 = min(W, x0 + max(1, int(W * w / 100)))
    y1 = min(H, y0 + max(1, int(H * h / 100)))
    return img[y0:y1, x0:x1]


def resize(img, percent, interp):
    methods = {
        "nearest": cv2.INTER_NEAREST,
        "linear": cv2.INTER_LINEAR,
        "cubic": cv2.INTER_CUBIC,
    }
    H, W = img.shape[:2]
    new_w = max(1, int(W * percent / 100))
    new_h = max(1, int(H * percent / 100))
    return cv2.resize(img, (new_w, new_h), interpolation=methods[interp])


def rotate(img, mode):
    codes = {
        "cw": cv2.ROTATE_90_CLOCKWISE,
        "ccw": cv2.ROTATE_90_COUNTERCLOCKWISE,
        "180": cv2.ROTATE_180,
    }
    return cv2.rotate(img, codes[mode])


def flip(img, mode):
    codes = {"h": 1, "v": 0, "both": -1}
    return cv2.flip(img, codes[mode])


# ---------------- FILTERS ----------------

def make_odd(k):
    # filter windows must be odd numbers: 3, 5, 7, ...
    k = int(k)
    return k // 2 * 2 + 1


def mean_filter(img, k):
    k = make_odd(k)
    return cv2.blur(img, (k, k))


def gaussian_filter(img, k):
    k = make_odd(k)
    return cv2.GaussianBlur(img, (k, k), 0)


def median_filter(img, k):
    k = make_odd(k)
    return cv2.medianBlur(img, k)


def bilateral_filter(img, sigma):
    return cv2.bilateralFilter(img, 9, sigma, sigma)


def gaussian_noise(img, mean, std):
    noise = np.random.normal(mean, std, img.shape)
    noisy = img.astype(np.float32) + noise
    return np.clip(noisy, 0, 255).astype(np.uint8)


# ---------------- EDGES ----------------

def to_uint8(arr):
    # stretch any numbers to 0-255 so we can show them
    return cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def sobel(img):
    g = to_gray(img)
    gx = cv2.Sobel(g, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_64F, 0, 1, ksize=3)
    return to_uint8(np.sqrt(gx ** 2 + gy ** 2))


def prewitt(img):
    g = to_gray(img)
    kx = np.array([[-1, 0, 1],
                   [-1, 0, 1],
                   [-1, 0, 1]], dtype=np.float32)
    ky = np.array([[-1, -1, -1],
                   [0, 0, 0],
                   [1, 1, 1]], dtype=np.float32)
    gx = cv2.filter2D(g, cv2.CV_32F, kx)
    gy = cv2.filter2D(g, cv2.CV_32F, ky)
    return to_uint8(np.sqrt(gx ** 2 + gy ** 2))


def roberts(img):
    g = to_gray(img)
    kx = np.array([[1, 0],
                   [0, -1]], dtype=np.float32)
    ky = np.array([[0, 1],
                   [-1, 0]], dtype=np.float32)
    gx = cv2.filter2D(g, cv2.CV_32F, kx)
    gy = cv2.filter2D(g, cv2.CV_32F, ky)
    return to_uint8(np.sqrt(gx ** 2 + gy ** 2))


def canny(img, low, high):
    return cv2.Canny(to_gray(img), low, high)


# ---------------- COLOR ----------------

def rgb_to_hsi(rgb):
    R = rgb[:, :, 0].astype(np.float32)
    G = rgb[:, :, 1].astype(np.float32)
    B = rgb[:, :, 2].astype(np.float32)

    # Intensity
    I = (R + G + B) / 3.0

    # Saturation
    total = R + G + B
    smallest = np.minimum(np.minimum(R, G), B)
    S = np.zeros_like(I)
    nonzero = total > 0
    S[nonzero] = 1 - 3 * smallest[nonzero] / total[nonzero]

    # Hue
    num = 0.5 * ((R - G) + (R - B))
    den = np.sqrt((R - G) ** 2 + (R - B) * (G - B))
    theta = np.zeros_like(I)
    valid = den > 1e-10
    theta[valid] = np.arccos(np.clip(num[valid] / den[valid], -1, 1))
    H = np.where(B <= G, theta, 2 * np.pi - theta)
    H = np.rad2deg(H)
    H[~valid] = 0

    return np.dstack((H, S, I))


def hsi_to_rgb(hsi):
    H = hsi[:, :, 0]
    S = hsi[:, :, 1]
    I = hsi[:, :, 2]
    R = np.zeros_like(I)
    G = np.zeros_like(I)
    B = np.zeros_like(I)
    c60 = np.deg2rad(60)

    # sector 1: 0 <= H < 120
    m = (H >= 0) & (H < 120)
    h = np.deg2rad(H[m])
    B[m] = I[m] * (1 - S[m])
    R[m] = I[m] * (1 + S[m] * np.cos(h) / np.cos(c60 - h))
    G[m] = 3 * I[m] - R[m] - B[m]

    # sector 2: 120 <= H < 240
    m = (H >= 120) & (H < 240)
    h = np.deg2rad(H[m] - 120)
    R[m] = I[m] * (1 - S[m])
    G[m] = I[m] * (1 + S[m] * np.cos(h) / np.cos(c60 - h))
    B[m] = 3 * I[m] - R[m] - G[m]

    # sector 3: 240 <= H <= 360
    m = H >= 240
    h = np.deg2rad(H[m] - 240)
    G[m] = I[m] * (1 - S[m])
    B[m] = I[m] * (1 + S[m] * np.cos(h) / np.cos(c60 - h))
    R[m] = 3 * I[m] - G[m] - B[m]

    rgb = np.clip(np.round(np.dstack((R, G, B))), 0, 255)
    return rgb.astype(np.uint8)


def hsi_component(img, which):
    # img is BGR (OpenCV), the HSI formulas need RGB
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    hsi = rgb_to_hsi(rgb)
    if which == "h":
        # show hue as real colors (full saturation and brightness)
        h = np.clip(hsi[:, :, 0] / 2, 0, 179).astype(np.uint8)
        full = np.full_like(h, 255)
        return cv2.cvtColor(np.dstack((h, full, full)), cv2.COLOR_HSV2BGR)
    if which == "s":
        return np.clip(hsi[:, :, 1] * 255, 0, 255).astype(np.uint8)
    return np.clip(hsi[:, :, 2], 0, 255).astype(np.uint8)


def hsi_roundtrip(img):
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    back = hsi_to_rgb(rgb_to_hsi(rgb))
    return cv2.cvtColor(back, cv2.COLOR_RGB2BGR)


SPACES = {
    "gray": (None, ["Gray"]),
    "hsv": (cv2.COLOR_BGR2HSV, ["H", "S", "V"]),
    "lab": (cv2.COLOR_BGR2LAB, ["L", "a", "b"]),
    "ycrcb": (cv2.COLOR_BGR2YCrCb, ["Y", "Cr", "Cb"]),
}


def color_space(img, space, channel):
    # returns (image, names of the channels)
    code, names = SPACES[space]
    if code is None:
        return to_gray(img), names
    conv = cv2.cvtColor(img, code)
    channel = int(channel)
    if channel == 0:
        # all 3 channels at once, shown as if they were B, G, R
        return conv, names
    return np.ascontiguousarray(conv[:, :, channel - 1]), names


def rgb_channel(img, which):
    index = {"b": 0, "g": 1, "r": 2}[which]
    return np.ascontiguousarray(img[:, :, index])


# ---------------- PIXELS ----------------

def sample(img, size):
    # keep only `size` pixels on the long side, then enlarge back
    # with nearest neighbor so you can SEE the big blocky pixels
    h, w = img.shape[:2]
    scale = size / max(h, w)
    sw = max(1, int(w * scale))
    sh = max(1, int(h * scale))
    small = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_NEAREST)
    big = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    return big, sw, sh


def quantize(img, bits):
    levels = 2 ** int(bits)
    step = 256 / levels
    # which "bucket" each pixel falls in
    q = np.floor(img / step)
    out = np.round(q * 255 / (levels - 1))    # spread buckets over 0-255
    return out.astype(np.uint8)


def components(img, thresh, connectivity):
    gray = to_gray(img)
    _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
    n, labels = cv2.connectedComponents(binary, connectivity=int(connectivity))
    rng = np.random.RandomState(1)
    colors = rng.randint(60, 255, size=(n, 3)).astype(np.uint8)
    colors[0] = (0, 0, 0)                     # background stays black
    return colors[labels], n - 1


# ---------------- COMPARE ----------------

def match_hist(img, ref):
    from skimage.exposure import match_histograms
    out = match_histograms(img, ref, channel_axis=-1)
    return np.clip(out, 0, 255).astype(np.uint8)


def compare(img, ref, tol):
    g1 = to_gray(img).astype(np.int16)
    ref = cv2.resize(ref, (img.shape[1], img.shape[0]))
    g2 = to_gray(ref).astype(np.int16)
    similar = np.abs(g1 - g2) <= tol
    out = np.where(similar, 255, 0).astype(np.uint8)
    return out, float(similar.mean() * 100)


# ---------------- ANALYSIS ----------------

def histogram(img):
    gray = to_gray(img)
    return np.bincount(gray.ravel(), minlength=256).tolist()


def stats(img):
    g = to_gray(img).astype(np.float32)
    lo = float(g.min())
    hi = float(g.max())
    mean = float(g.mean())
    michelson = (hi - lo) / (hi + lo) if (hi + lo) > 0 else 0.0
    rms = float(np.sqrt(np.mean((g - mean) ** 2)))
    return {
        "min": lo,
        "max": hi,
        "mean": round(mean, 2),
        "range": hi - lo,
        "michelson": round(michelson, 4),
        "rms": round(rms, 2),
    }

# ---------------- MORE ENHANCE / EDGES ----------------


def log_transform(img, c):
    # s = c * log(1 + r), scaled so 255 stays 255 when c = 1
    out = c * 255 / np.log(256) * np.log1p(img.astype(np.float32))
    return np.clip(out, 0, 255).astype(np.uint8)


def bit_plane(img, bit):
    # keep only one bit of every pixel (7 = MSB, 0 = LSB)
    g = to_gray(img)
    return (((g >> int(bit)) & 1) * 255).astype(np.uint8)


def laplacian(img):
    lap = cv2.Laplacian(to_gray(img), cv2.CV_64F, ksize=3)
    return to_uint8(np.abs(lap))


# ---------------- SEGMENTATION ----------------

def threshold(img, mode, t):
    g = to_gray(img)
    if mode == "global":
        _, out = cv2.threshold(g, int(t), 255, cv2.THRESH_BINARY)
        return out, int(t)
    if mode == "mean":
        return cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                     cv2.THRESH_BINARY, 11, 2), None
    if mode == "gaussian":
        return cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 11, 2), None
    found, out = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return out, found


def kmeans(img, k):
    data = np.float32(img.reshape((-1, 3)))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
    _, labels, centers = cv2.kmeans(data, int(k), None, criteria, 3,
                                    cv2.KMEANS_PP_CENTERS)
    return np.uint8(centers)[labels.flatten()].reshape(img.shape)


# ---------------- MORPHOLOGY ----------------

def morph(img, op, size):
    g = to_gray(img)
    k = np.ones((make_odd(size), make_odd(size)), np.uint8)
    if op == "erode":
        return cv2.erode(g, k)
    if op == "dilate":
        return cv2.dilate(g, k)
    if op == "open":
        return cv2.morphologyEx(g, cv2.MORPH_OPEN, k)
    return cv2.morphologyEx(g, cv2.MORPH_CLOSE, k)


# ---------------- FREQUENCY DOMAIN ----------------

def fft_tool(img, mode, radius):
    g = to_gray(img).astype(np.float32)
    F = np.fft.fftshift(np.fft.fft2(g))
    if mode == "spectrum":
        return to_uint8(np.log1p(np.abs(F)))
    rows, cols = g.shape
    y, x = np.ogrid[:rows, :cols]
    dist = np.sqrt((y - rows / 2) ** 2 + (x - cols / 2) ** 2)
    mask = dist <= radius                 # low-pass keeps the center
    if mode == "high":
        mask = ~mask                      # high-pass keeps the outside
    back = np.real(np.fft.ifft2(np.fft.ifftshift(F * mask)))
    if mode == "high":
        return to_uint8(np.abs(back))
    return np.clip(back, 0, 255).astype(np.uint8)
