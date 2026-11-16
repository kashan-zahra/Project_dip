# Theory text for the "Learn more" pages (used by build_learn_data.py).

# Theory text for the "Learn more" pages. Plain words first, then the idea behind it.
T = {
"brightness_contrast": dict(
    what="A point operation: every pixel is changed on its own, without looking at its neighbours.",
    how="Each pixel value is multiplied by alpha and then beta is added. Alpha above 1 stretches the values apart (more contrast), below 1 squeezes them together (less contrast). Beta shifts everything up or down (brighter or darker). Results above 255 or below 0 are clipped.",
    formula="g(x, y) = alpha * f(x, y) + beta",
    uses="Quick exposure fixes, the brightness and contrast sliders in every photo app."),
"gamma": dict(
    what="A power-law transform that changes the middle tones more than the darkest and brightest ones.",
    how="Pixel values are first scaled to 0..1, raised to the power gamma, then scaled back to 0..255. Because 0 and 1 stay 0 and 1, pure black and pure white never move. The code builds a lookup table of all 256 answers once, so the whole image is converted very fast.",
    formula="s = 255 * (r / 255) ^ gamma",
    uses="Display and camera gamma correction, revealing details in shadows, medical images."),
"negative": dict(
    what="The simplest point operation: it flips every intensity.",
    how="Each value is subtracted from the maximum, 255. Dark pixels become bright and bright ones dark. For colour images each channel is flipped, so every colour turns into its opposite.",
    formula="s = 255 - r",
    uses="Reading X-rays and film negatives, making small dark details easier to see."),
"stretch": dict(
    what="Contrast stretching (normalization) spreads the used range of values over the full 0..255.",
    how="It finds the darkest value r_min and the brightest r_max in the picture, then maps r_min to 0 and r_max to 255 with a straight line. A dull photo using only 60..180 is stretched to use the whole range.",
    formula="s = (r - r_min) / (r_max - r_min) * 255",
    uses="Fixing faded scans and foggy photos, preparing images for analysis."),
"equalize": dict(
    what="Histogram equalization automatically redistributes the gray levels so they are used more evenly.",
    how="It counts how often each gray level appears (the histogram), then builds the cumulative distribution function (CDF). Each pixel value is replaced by its CDF value scaled to 0..255. Crowded ranges get spread out, so hidden details appear. Open Lab Data to see the histogram flatten.",
    formula="s_k = 255 * sum(p(r_j), j = 0..k)   where p(r_j) = count(r_j) / total pixels",
    uses="Medical images, satellite images, low-contrast photos."),
"clahe": dict(
    what="Contrast Limited Adaptive Histogram Equalization: equalization done separately on small tiles.",
    how="The image is split into a grid of tiles and each tile is equalized on its own, so dark and bright regions both get improved. To stop noise from being boosted too much, each tile's histogram is clipped at the clip limit before equalizing. Neighbouring tiles are blended with bilinear interpolation so no tile borders show.",
    formula="Per tile: clip histogram at (clip limit), then equalize; blend tiles bilinearly",
    uses="X-rays and CT scans, underwater and night photos, a common step before face or text recognition."),
"log": dict(
    what="A log transform expands dark values and compresses bright ones.",
    how="The logarithm grows quickly at first and then slowly. So small (dark) values are spread far apart, and large (bright) values are packed together. The constant is chosen so that 255 still maps to 255 when c = 1.",
    formula="s = c * log(1 + r),  scaled so that r = 255 gives s = 255",
    uses="Showing Fourier spectra (see the FFT tool), images with a huge brightness range."),
"bitplane": dict(
    what="Bit-plane slicing shows one of the 8 bits that make up each pixel value.",
    how="A gray value from 0 to 255 is stored as 8 bits. Bit 7 (the most significant bit) is worth 128, bit 0 only 1. Shifting the value right by n and keeping the last bit gives bit n; it is shown as white (1) or black (0). The top bits hold the shape of the picture; the bottom bits look like random noise.",
    formula="bit_n = (r >> n) AND 1,  shown as bit_n * 255",
    uses="Image compression, hiding messages in images (steganography uses the low bits)."),
"crop": dict(
    what="Cropping keeps a rectangular part of the image and removes the rest.",
    how="An image is a 2-D array of pixels, so cropping is just array slicing: keep rows y0..y1 and columns x0..x1. Here the start and size are given as percentages of the image, converted to pixel positions.",
    formula="out = img[y0 : y1, x0 : x1]",
    uses="Framing photos, cutting out a region of interest before analysis."),
"resize": dict(
    what="Resizing changes the number of pixels, so new pixel values have to be guessed (interpolated).",
    how="Every pixel of the new image is mapped back to a position in the old one, which usually falls between pixels. Nearest neighbour copies the closest pixel (fast, blocky). Bilinear mixes the 4 nearest pixels by distance (smooth). Bicubic uses 16 pixels and a cubic curve (smoothest, sharper than bilinear).",
    formula="Bilinear: f(x, y) = weighted average of the 4 neighbours by distance",
    uses="Thumbnails, zooming, preparing images for a neural network's fixed input size."),
"rotate": dict(
    what="Rotation by 90 or 180 degrees just rearranges the pixel grid.",
    how="For multiples of 90 degrees no new values are needed: rows become columns (transpose) and the order is reversed. That is why it is exact and loses no quality, unlike rotating by other angles.",
    formula="90 degrees clockwise: out[x, H - 1 - y] = img[y, x]",
    uses="Fixing sideways phone photos, data augmentation for machine learning."),
"flip": dict(
    what="Flipping mirrors the image horizontally, vertically or both.",
    how="Horizontal flip reverses the order of the columns, vertical flip reverses the rows. Doing both is the same as rotating by 180 degrees.",
    formula="Horizontal: out[y, x] = img[y, W - 1 - x]",
    uses="Selfie cameras, data augmentation for machine learning."),
"mean": dict(
    what="The mean (box) filter is the simplest smoothing filter.",
    how="A small window (kernel) slides over the image. Each pixel becomes the average of all pixels in the window. This is called convolution. A bigger window averages more pixels, so the result is blurrier. It removes noise but also blurs edges.",
    formula="g(x, y) = (1 / k^2) * sum of f over the k x k window",
    uses="Simple noise reduction, the first step in many algorithms."),
"gaussian": dict(
    what="A weighted blur: close neighbours count more than far ones, following a bell-shaped (Gaussian) curve.",
    how="The kernel weights come from the 2-D Gaussian function, so the centre pixel has the largest weight and the weights fade smoothly. This blurs more naturally than the mean filter and does not create blocky artefacts. OpenCV picks sigma from the window size when sigma is 0.",
    formula="G(x, y) = (1 / (2 pi sigma^2)) * e^(-(x^2 + y^2) / (2 sigma^2))",
    uses="Noise reduction before edge detection (Canny uses it), background blur."),
"median": dict(
    what="A non-linear filter: each pixel becomes the middle value (median) of its neighbours.",
    how="The values in the window are sorted and the middle one is taken. A single very bright or dark pixel (salt-and-pepper noise) is an extreme value, so it never ends up in the middle and simply disappears. Edges stay much sharper than with averaging.",
    formula="g(x, y) = median of f over the k x k window",
    uses="Removing salt-and-pepper noise from scans and old photos."),
"bilateral": dict(
    what="An edge-preserving smoothing filter.",
    how="Like a Gaussian blur, but each neighbour's weight also depends on how similar its value is. Neighbours across an edge have very different values, so they get almost no weight and the edge is not blurred. Flat areas are smoothed normally. The 'Strength' slider sets both sigma values.",
    formula="weight = G_space(distance) * G_range(|I(p) - I(q)|)",
    uses="Beauty and skin smoothing filters, cartoon effects, noise removal while keeping detail."),
"noise": dict(
    what="Adds Gaussian (normal) noise, the kind of grain a camera sensor makes in low light.",
    how="For every pixel a random number is drawn from a normal distribution with the chosen mean and standard deviation, and added to the pixel. A bigger standard deviation means stronger grain. The result is clipped to 0..255.",
    formula="g(x, y) = f(x, y) + n,   n ~ N(mean, std^2)",
    uses="Testing denoising filters, data augmentation for machine learning."),
"sobel": dict(
    what="An edge detector that measures how fast brightness changes (the gradient).",
    how="Two 3 x 3 kernels estimate the derivative in x (left-right) and in y (up-down); they also smooth slightly by weighting the centre row twice. The two results are combined into the gradient magnitude. Large magnitude means a strong edge.",
    formula="Gx = [-1 0 1; -2 0 2; -1 0 1] * f,   Gy = Gx transposed,   |G| = sqrt(Gx^2 + Gy^2)",
    uses="Feature detection, lane detection in self-driving cars, a building block of many detectors."),
"prewitt": dict(
    what="An edge detector very similar to Sobel.",
    how="It uses the same idea of two derivative kernels, but every row of the kernel has equal weight (no extra weight on the centre). It is slightly simpler and a little more sensitive to noise than Sobel.",
    formula="Gx = [-1 0 1; -1 0 1; -1 0 1] * f,   |G| = sqrt(Gx^2 + Gy^2)",
    uses="Teaching edge detection, simple feature extraction."),
"roberts": dict(
    what="The Roberts cross: one of the first edge detectors, using tiny 2 x 2 kernels.",
    how="It measures differences along the two diagonals. Because the kernels are so small it is very fast and gives thin edges, but it reacts strongly to noise.",
    formula="Gx = [1 0; 0 -1] * f,   Gy = [0 1; -1 0] * f,   |G| = sqrt(Gx^2 + Gy^2)",
    uses="Fast, simple edge detection on clean images."),
"canny": dict(
    what="The most widely used edge detector: thin, clean, connected edges.",
    how="It runs in 4 steps: 1) smooth with a Gaussian to reduce noise, 2) find the gradient with Sobel, 3) non-maximum suppression thins edges to 1 pixel by keeping only local maxima, 4) hysteresis: edges above the high threshold are kept, edges between low and high are kept only if they touch a strong edge.",
    formula="strong: |G| > high,   weak: low < |G| <= high (kept only if connected to strong)",
    uses="Object detection, document scanning apps, robotics, measuring shapes."),
"laplacian": dict(
    what="A second-derivative edge detector that works in all directions at once.",
    how="Instead of the slope of the brightness, it measures how the slope changes (curvature). Edges are where the second derivative crosses zero. Because one kernel covers both x and y, it is direction-independent, but it amplifies noise strongly.",
    formula="Laplacian(f) = d2f/dx2 + d2f/dy2   (kernel [0 1 0; 1 -4 1; 0 1 0])",
    uses="Sharpening, blob detection, finding fine detail."),
"hsi_component": dict(
    what="HSI describes colour the way people talk about it: Hue, Saturation, Intensity.",
    how="Hue is the angle of the colour on the colour wheel (0 = red, 120 = green, 240 = blue). Saturation says how pure the colour is (0 = gray). Intensity is the average of R, G and B. The code computes these with the formulas below, pixel by pixel, using NumPy arrays.",
    formula="I = (R + G + B) / 3,   S = 1 - 3 * min(R, G, B) / (R + G + B),   H = theta (or 360 - theta if B > G)",
    uses="Colour-based segmentation (finding skin, fruit or traffic signs), adjusting colour without changing brightness."),
"hsi_roundtrip": dict(
    what="Converts the image RGB -> HSI -> RGB to check that the conversion formulas are correct.",
    how="The inverse formulas depend on which third of the colour wheel the hue is in (0-120, 120-240, 240-360). If both directions are right, the result equals the original up to tiny rounding errors. The note shows the error (MAE, MSE, max).",
    formula="Sector 0-120:  B = I(1 - S),  R = I(1 + S cos H / cos(60 - H)),  G = 3I - (R + B)",
    uses="Verifying colour-space code, a classic lab exercise."),
"colorspace": dict(
    what="The same colours written in different coordinate systems.",
    how="HSV separates colour (hue), purity (saturation) and brightness (value). LAB has lightness L plus two colour axes a (green-red) and b (blue-yellow) and is designed so equal distances look equally different to people. YCrCb separates brightness Y from two colour differences; JPEG and video store colour detail at lower resolution in Cr and Cb.",
    formula="Y = 0.299 R + 0.587 G + 0.114 B,   Cr = (R - Y) * 0.713 + 128,   Cb = (B - Y) * 0.564 + 128",
    uses="JPEG and video compression, colour tracking, skin detection."),
"channel": dict(
    what="A colour image is three gray images stacked: red, green and blue.",
    how="Each pixel stores three numbers. Taking only one of them gives a gray image where bright means 'a lot of this colour'. OpenCV stores channels in B, G, R order, so red is index 2.",
    formula="red channel = img[:, :, 2]   (OpenCV uses BGR order)",
    uses="Understanding colour, vegetation analysis in satellite images, colour correction."),
"sample": dict(
    what="Sampling decides how many pixels (samples) represent the scene, which sets the spatial resolution.",
    how="The image is shrunk so the long side has only N pixels, throwing detail away, then enlarged back with nearest-neighbour so each kept sample becomes a visible block. Fewer samples means bigger blocks. If samples are too few, fine patterns turn into false patterns (aliasing).",
    formula="scale = N / max(width, height)",
    uses="Understanding resolution, pixel-art effects, censoring with mosaic."),
"quantize": dict(
    what="Quantization decides how many intensity levels each pixel can have.",
    how="With b bits there are 2^b levels. Each value is put into one of 2^b equal buckets, and the bucket number is spread back over 0..255. With few levels, smooth gradients turn into visible steps called false contours or banding.",
    formula="levels L = 2^b,   q = floor(r / (256 / L)),   s = round(q * 255 / (L - 1))",
    uses="Image compression, GIF colour reduction, posterize effects."),
"components": dict(
    what="Connected-component labelling finds and counts separate objects in a black-and-white image.",
    how="First the image is thresholded to black and white. Then white pixels that touch each other are given the same label. With 4-connectivity only up, down, left and right neighbours count; with 8-connectivity diagonals count too, so diagonal touching joins objects. Each label gets its own colour.",
    formula="4-neighbours of (x, y): (x+-1, y), (x, y+-1);   8-neighbours add the 4 diagonals",
    uses="Counting cells, coins or particles, reading characters (OCR), quality inspection."),
"threshold": dict(
    what="Thresholding turns a gray image into pure black and white (binary).",
    how="Global: one cut-off T for the whole image. Otsu: tries every T and picks the one that best separates the histogram into two groups (largest variance between the groups). Adaptive: every pixel gets its own T from the mean (or Gaussian-weighted mean) of an 11 x 11 neighbourhood minus 2, which handles uneven lighting.",
    formula="s = 255 if r > T else 0;   Otsu: T = argmax( w0 * w1 * (mu0 - mu1)^2 )",
    uses="Scanning documents, separating objects from background, preparing images for OCR."),
"kmeans": dict(
    what="K-Means clustering groups all pixel colours into K clusters.",
    how="Every pixel is a point in 3-D colour space (B, G, R). K-Means starts with K centre colours (chosen with k-means++), assigns each pixel to the nearest centre, moves each centre to the average of its pixels, and repeats until the centres stop moving. Each pixel is then painted with its centre colour.",
    formula="minimize sum over pixels of || pixel - nearest centre ||^2",
    uses="Colour quantization, simple image segmentation, finding dominant colours. Note: the app learns the colours from a sample of pixels to stay fast on phones."),
"morph": dict(
    what="Morphological operations change the shape of bright regions using a square window (structuring element).",
    how="Erosion keeps a pixel bright only if the whole window is bright (minimum), so shapes shrink and specks vanish. Dilation makes it bright if any pixel in the window is bright (maximum), so shapes grow and holes fill. Opening = erosion then dilation (removes small specks). Closing = dilation then erosion (fills small holes and gaps).",
    formula="erode: min over window,   dilate: max over window,   open = dilate(erode(f)),   close = erode(dilate(f))",
    uses="Cleaning binary images, separating touching objects, fingerprint and text processing."),
"fft": dict(
    what="The Fourier transform describes an image as a sum of waves (frequencies) instead of pixels.",
    how="The 2-D FFT turns the image into a spectrum; fftshift moves the low frequencies (smooth areas) to the centre, high frequencies (edges, detail) are farther out. A low-pass filter keeps only a circle around the centre, then the inverse FFT gives a smoothed image. A high-pass filter keeps only the outside, leaving edges. The spectrum is shown with log scaling because the centre is much brighter than the rest.",
    formula="F(u, v) = sum over x, y of f(x, y) * e^(-j 2 pi (ux / M + vy / N));   keep where distance from centre <= radius",
    uses="Removing periodic noise, compression, image analysis, understanding blur and sharpening."),
"match": dict(
    what="Histogram matching (specification) gives your image the same brightness and colour distribution as a reference image.",
    how="For each channel it computes the cumulative distribution (CDF) of both images. Each value of your image is mapped to the reference value with the same CDF position, so the result's histogram follows the reference's histogram. The code uses scikit-image's match_histograms.",
    formula="s = CDF_ref^-1( CDF_src(r) )",
    uses="Making photos from different cameras look consistent, colour grading, medical image normalization."),
"compare": dict(
    what="Pixel-by-pixel comparison of two images.",
    how="The reference is resized to the same size, both are turned gray, and the absolute difference of each pixel pair is computed. If the difference is at most the tolerance, the pixel counts as similar (white); otherwise different (black). The note reports the percentage of similar pixels.",
    formula="similar(x, y) = | f1(x, y) - f2(x, y) | <= tolerance",
    uses="Spotting changes between two photos, quality control, simple motion detection."),
}
