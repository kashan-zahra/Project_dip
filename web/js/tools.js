// Image Lab - the list of tools: names, settings, simple names and plain-language help.
// To add a tool: add it here, add the maths to processing.js (runTool), and optionally to learn-data.js.

// ============ TOOL LIST: add new tools here later ============
const TOOLS = {
    // ---------- Enhance ----------
    brightness_contrast: {
        group: "Enhance", label: "Brightness / Contrast",
        info: "g(x,y) = alpha * f(x,y) + beta.  alpha controls contrast, beta controls brightness.",
        controls: [
            { name: "alpha", label: "Contrast (alpha)", type: "range", min: 0.1, max: 3, step: 0.1, value: 1 },
            { name: "beta", label: "Brightness (beta)", type: "range", min: -100, max: 100, step: 1, value: 0 }
        ]
    },
    gamma: {
        group: "Enhance", label: "Gamma Correction",
        info: "s = 255 x (r / 255) ^ gamma. gamma below 1 brightens dark areas, above 1 darkens the image.",
        controls: [
            { name: "gamma", label: "Gamma", type: "range", min: 0.1, max: 3, step: 0.1, value: 1 }
        ]
    },
    negative: {
        group: "Enhance", label: "Negative",
        info: "s = 255 - r. Every pixel is flipped: dark becomes bright.",
        controls: []
    },
    stretch: {
        group: "Enhance", label: "Contrast Stretching",
        info: "s = (r - r_min) / (r_max - r_min) x 255. Spreads the pixel values to fill 0 to 255.",
        controls: []
    },
    equalize: {
        group: "Enhance", label: "Histogram Equalization",
        info: "Uses the CDF of the histogram to spread the gray levels evenly. Output is gray.",
        controls: []
    },
    clahe: {
        group: "Enhance", label: "CLAHE",
        info: "Equalization done on small tiles, with a clip limit so noise is not boosted too much.",
        controls: [
            { name: "clip", label: "Clip limit", type: "range", min: 1, max: 20, step: 1, value: 2 },
            { name: "tile", label: "Tile grid size", type: "range", min: 2, max: 16, step: 1, value: 8 }
        ]
    },

    // ---------- Transform ----------
    crop: {
        group: "Transform", label: "Crop",
        info: "Cut out a part of the image. Values are percentages of the image size.",
        controls: [
            { name: "x", label: "Start X (%)", type: "range", min: 0, max: 99, step: 1, value: 25 },
            { name: "y", label: "Start Y (%)", type: "range", min: 0, max: 99, step: 1, value: 25 },
            { name: "w", label: "Width (%)", type: "range", min: 1, max: 100, step: 1, value: 50 },
            { name: "h", label: "Height (%)", type: "range", min: 1, max: 100, step: 1, value: 50 }
        ]
    },
    resize: {
        group: "Transform", label: "Resize (Interpolation)",
        info: "Changes the image size. Interpolation decides how the new pixel values are guessed.",
        controls: [
            { name: "percent", label: "Scale (%)", type: "range", min: 10, max: 300, step: 10, value: 50 },
            {
                name: "interp", label: "Interpolation", type: "select",
                options: [["nearest", "Nearest neighbor"], ["linear", "Bilinear"], ["cubic", "Bicubic"]]
            }
        ]
    },
    rotate: {
        group: "Transform", label: "Rotate",
        info: "Rotates the pixel matrix by 90 or 180 degrees.",
        controls: [
            {
                name: "mode", label: "Direction", type: "select",
                options: [["cw", "90 clockwise"], ["ccw", "90 counter-clockwise"], ["180", "180"]]
            }
        ]
    },
    flip: {
        group: "Transform", label: "Flip",
        info: "Mirrors the image.",
        controls: [
            {
                name: "mode", label: "Flip type", type: "select",
                options: [["h", "Horizontal"], ["v", "Vertical"], ["both", "Both"]]
            }
        ]
    },

    // ---------- Filters ----------
    mean: {
        group: "Filters", label: "Mean (Average) Filter",
        info: "Each pixel becomes the average of its neighbors. Smooths the image, but also blurs edges.",
        controls: [
            { name: "size", label: "Window size", type: "range", min: 3, max: 15, step: 2, value: 5 }
        ]
    },
    gaussian: {
        group: "Filters", label: "Gaussian Filter",
        info: "Like the mean filter, but nearby pixels count more than far pixels. Gives a smoother blur.",
        controls: [
            { name: "size", label: "Window size", type: "range", min: 3, max: 15, step: 2, value: 5 }
        ]
    },
    median: {
        group: "Filters", label: "Median Filter",
        info: "Each pixel becomes the middle value of its neighbors. Best for removing salt-and-pepper dots.",
        controls: [
            { name: "size", label: "Window size", type: "range", min: 3, max: 15, step: 2, value: 5 }
        ]
    },
    bilateral: {
        group: "Filters", label: "Bilateral Filter",
        info: "Smooths flat areas but keeps edges sharp, because it also checks how different the pixel values are.",
        controls: [
            { name: "sigma", label: "Strength", type: "range", min: 10, max: 200, step: 5, value: 75 }
        ]
    },
    noise: {
        group: "Filters", label: "Add Gaussian Noise",
        info: "Adds random values (bell curve shaped) to every pixel. Try this first, then clean it with the filters above.",
        controls: [
            { name: "mean", label: "Noise mean", type: "range", min: -50, max: 50, step: 1, value: 0 },
            { name: "std", label: "Noise strength (std)", type: "range", min: 1, max: 100, step: 1, value: 20 }
        ]
    },

    // ---------- Edges ----------
    sobel: {
        group: "Edges", label: "Sobel",
        info: "Finds edges by measuring how fast brightness changes, left-right and up-down. Output is gray.",
        controls: []
    },
    prewitt: {
        group: "Edges", label: "Prewitt",
        info: "Similar to Sobel, but all neighbor rows have equal weight.",
        controls: []
    },
    roberts: {
        group: "Edges", label: "Roberts",
        info: "Uses a tiny 2x2 window across the diagonals. Fast, but sensitive to noise.",
        controls: []
    },
    canny: {
        group: "Edges", label: "Canny",
        info: "Thin, clean edges. Edges stronger than the high threshold are kept. Weak ones are kept only if they touch a strong one.",
        controls: [
            { name: "low", label: "Low threshold", type: "range", min: 0, max: 255, step: 5, value: 100 },
            { name: "high", label: "High threshold", type: "range", min: 0, max: 255, step: 5, value: 200 }
        ]
    },

    // ---------- Color ----------
    hsi_component: {
        group: "Color", label: "HSI Components",
        info: "Splits color into Hue (the color itself, 0 to 360 degrees), Saturation (how pure the color is) and Intensity (brightness = average of R, G, B).",
        controls: [
            {
                name: "which", label: "Show", type: "select",
                options: [["h", "Hue"], ["s", "Saturation"], ["i", "Intensity"]]
            }
        ]
    },
    hsi_roundtrip: {
        group: "Color", label: "RGB to HSI to RGB",
        info: "Converts to HSI and back again. If the formulas are right, the result looks the same as the original.",
        controls: []
    },
    colorspace: {
        group: "Color", label: "Color Spaces",
        info: "The same image written in different color systems. HSV = hue, saturation, value. LAB = lightness plus two color axes. YCrCb = brightness plus two color differences (used in JPEG and video).",
        controls: [
            {
                name: "space", label: "Color space", type: "select",
                options: [["hsv", "HSV"], ["lab", "LAB"], ["ycrcb", "YCrCb"], ["gray", "Gray"]]
            },
            {
                name: "channel", label: "Channel", type: "select",
                options: [["0", "All channels"], ["1", "Channel 1 (H / L / Y)"], ["2", "Channel 2 (S / a / Cr)"], ["3", "Channel 3 (V / b / Cb)"]]
            }
        ]
    },
    channel: {
        group: "Color", label: "RGB Channels",
        info: "Shows one color channel as a gray image. Bright means a lot of that color is in the pixel.",
        controls: [
            {
                name: "which", label: "Channel", type: "select",
                options: [["r", "Red"], ["g", "Green"], ["b", "Blue"]]
            }
        ]
    },

    // ---------- Pixels ----------
    sample: {
        group: "Pixels", label: "Sampling",
        info: "Sampling = how many pixels you keep. Fewer samples gives big blocks and less detail.",
        controls: [
            { name: "size", label: "Pixels on the long side", type: "range", min: 4, max: 256, step: 4, value: 32 }
        ]
    },
    quantize: {
        group: "Pixels", label: "Quantization",
        info: "Quantization = how many intensity levels you keep. Levels = 2 to the power of bits.",
        controls: [
            { name: "bits", label: "Bits per channel", type: "range", min: 1, max: 8, step: 1, value: 3 }
        ]
    },
    components: {
        group: "Pixels", label: "Pixel Connectivity",
        info: "Turns the image into black and white with a threshold, then groups touching white pixels. 4-connectivity: only up, down, left, right. 8-connectivity: also the diagonals.",
        controls: [
            { name: "thresh", label: "Threshold", type: "range", min: 0, max: 255, step: 1, value: 128 },
            {
                name: "connectivity", label: "Connectivity", type: "select",
                options: [["4", "4-connectivity"], ["8", "8-connectivity"]]
            }
        ]
    },

    log: {
        group: "Enhance", label: "Log Transform",
        info: "s = c x log(1 + r). Expands dark values and compresses bright ones.",
        controls: [{ name: "c", label: "c", type: "range", min: 0.5, max: 2, step: 0.1, value: 1 }]
    },
    bitplane: {
        group: "Enhance", label: "Bit-plane Slicing",
        info: "A pixel is 8 bits. This shows one bit at a time. Bit 7 matters most.",
        controls: [{ name: "bit", label: "Bit (7 = MSB, 0 = LSB)", type: "range", min: 0, max: 7, step: 1, value: 7 }]
    },
    laplacian: {
        group: "Edges", label: "Laplacian",
        info: "Second-derivative edge detector. Finds edges in every direction at once.", controls: []
    },
    threshold: {
        group: "Segment", label: "Thresholding",
        info: "Turns the image into black and white. Global uses your value, Otsu picks it automatically, adaptive decides per neighborhood.",
        controls: [
            {
                name: "mode", label: "Method", type: "select",
                options: [["otsu", "Otsu"], ["global", "Global"], ["mean", "Adaptive (mean)"], ["gaussian", "Adaptive (Gaussian)"]]
            },
            { name: "t", label: "Threshold (Global only)", type: "range", min: 0, max: 255, step: 1, value: 128 }]
    },
    kmeans: {
        group: "Segment", label: "K-Means",
        info: "Clusters pixels by color into K groups. A simple way to segment an image.",
        controls: [{ name: "k", label: "Clusters (K)", type: "range", min: 2, max: 8, step: 1, value: 3 }]
    },
    morph: {
        group: "Morphology", label: "Erode / Dilate / Open / Close",
        info: "Shape operations using a square window.",
        controls: [
            {
                name: "op", label: "Operation", type: "select",
                options: [["erode", "Erosion"], ["dilate", "Dilation"], ["open", "Opening"], ["close", "Closing"]]
            },
            { name: "size", label: "Window size", type: "range", min: 3, max: 15, step: 2, value: 3 }]
    },
    fft: {
        group: "Frequency", label: "FFT Filters",
        info: "Moves the image to the frequency domain. Low frequencies = smooth areas, high frequencies = edges and details.",
        controls: [
            {
                name: "mode", label: "Show", type: "select",
                options: [["spectrum", "Spectrum"], ["low", "Low-pass"], ["high", "High-pass"]]
            },
            { name: "radius", label: "Cutoff radius", type: "range", min: 5, max: 200, step: 5, value: 30 }]
    },

    // ---------- Compare (need a reference image) ----------
    match: {
        group: "Compare", label: "Histogram Matching", needsRef: true,
        info: "Changes your image so its histogram looks like the reference image's histogram.",
        controls: []
    },
    compare: {
        group: "Compare", label: "Pixel Similarity", needsRef: true,
        info: "Compares both images pixel by pixel. A pixel is 'similar' if the difference is within the tolerance. White = similar, black = different.",
        controls: [
            { name: "tol", label: "Tolerance", type: "range", min: 0, max: 50, step: 1, value: 5 }
        ]
    }
};


// ============ FRIENDLY NAMES AND PLAIN HELP (shown next to the technical names) ============
const CAT_NAMES = {
    Enhance: "Enhance", Transform: "Resize & Rotate", Filters: "Blur & Noise", Edges: "Edges",
    Color: "Colour", Pixels: "Pixels", Segment: "Black & White / Regions", Morphology: "Shapes",
    Frequency: "Frequency (FFT)", Compare: "Compare 2 photos"
};
const FRIENDLY = {
    brightness_contrast: ["lighter, darker, punchier", "Make the whole picture lighter or darker (brightness), and make the difference between dark and light parts bigger or smaller (contrast)."],
    gamma: ["brighten or darken shadows", "Changes mostly the middle tones. Below 1 opens up dark areas, above 1 makes the picture darker and richer."],
    negative: ["invert, like a film negative", "Every colour is flipped: black becomes white, blue becomes yellow, and so on."],
    stretch: ["use the full light range", "If the photo looks dull or grey, this spreads its brightness out so the darkest part becomes black and the brightest becomes white."],
    equalize: ["automatic contrast (gray)", "Spreads the brightness levels evenly so hidden details in dark or bright areas show up. The result is black and white."],
    clahe: ["smart local contrast", "Like automatic contrast, but done in small squares so every area gets its own boost. Great for foggy or dark photos. Output is gray."],
    log: ["lift dark areas", "Brightens dark parts a lot and bright parts only a little. Useful for very dark images."],
    bitplane: ["see each bit layer", "Every pixel is stored as 8 bits (on/off switches). This shows one switch at a time: bit 7 holds the main picture, bit 0 looks like noise."],
    crop: ["cut out a part", "Keep only a rectangle of the picture. The sliders set where it starts and how big it is."],
    resize: ["make bigger or smaller", "Changes the picture size. The method decides how new pixels are filled in: Nearest looks blocky, Bilinear smooth, Bicubic smoothest."],
    rotate: ["turn 90 or 180 degrees", "Turns the picture."],
    flip: ["mirror image", "Mirrors the picture left-right, upside down, or both."],
    mean: ["simple blur", "Each pixel becomes the average of the pixels around it. A bigger window means more blur."],
    gaussian: ["soft, natural blur", "A smoother blur where close pixels count more than far ones. Looks like an out-of-focus camera."],
    median: ["remove dots and specks", "Replaces each pixel with the middle value of its neighbours. Removes salt-and-pepper dots while keeping edges fairly sharp."],
    bilateral: ["smooth skin, keep edges", "Smooths flat areas but keeps outlines sharp. Often used for beauty filters."],
    noise: ["add grain", "Adds random grain to the picture. Try it, then remove it with the blur filters to compare them."],
    sobel: ["find edges", "Shows where brightness changes quickly, which is where edges are. Bright lines = strong edges."],
    prewitt: ["find edges (simple)", "Another edge finder, very similar to Sobel but a bit simpler."],
    roberts: ["find edges (fast, small)", "The oldest and fastest edge finder. Uses a tiny 2 x 2 window, so it picks up noise easily."],
    canny: ["clean, thin outlines", "The most popular edge finder: thin white lines on black. Lower thresholds = more edges, higher = only strong edges."],
    laplacian: ["edges in all directions", "Finds edges in every direction at once, but also reacts strongly to noise."],
    hsi_component: ["colour, purity, brightness", "Splits colour into Hue (which colour), Saturation (how strong the colour is) and Intensity (how bright)."],
    hsi_roundtrip: ["check the HSI formulas", "Converts the photo to HSI and back. If it looks the same as the original, the formulas are correct."],
    colorspace: ["other ways to store colour", "Shows the picture in HSV, LAB or YCrCb, which are other ways computers describe colour. Pick one channel to see it on its own."],
    channel: ["red, green or blue only", "Shows how much red, green or blue is in each pixel: bright = a lot, dark = little."],
    sample: ["fewer pixels, blocky look", "Keeps fewer pixels, then blows the picture back up, so you see big blocks. Shows why resolution matters."],
    quantize: ["fewer shades, banding", "Keeps fewer brightness levels per colour. With few levels, smooth areas turn into visible bands."],
    components: ["count separate blobs", "Makes the picture black and white, then gives every separate white blob its own colour and counts them."],
    threshold: ["black & white only", "Every pixel becomes pure black or pure white. Otsu picks the cut-off automatically; Global uses your slider."],
    kmeans: ["group similar colours", "Reduces the picture to K colours by grouping similar ones. A simple way to split a picture into regions."],
    morph: ["shrink or grow shapes", "Works on bright shapes: Erosion shrinks them, Dilation grows them, Opening removes small specks, Closing fills small holes."],
    fft: ["smooth or sharpen via frequencies", "Every picture is made of smooth parts (low frequencies) and fine details (high frequencies). Low-pass keeps the smooth parts (blur); high-pass keeps details (edges)."],
    match: ["copy another photo's look", "Changes your photo's brightness and colour spread so it looks like the reference photo."],
    compare: ["spot the differences", "Compares two photos pixel by pixel. White = the same (within the tolerance), black = different."]
};
Object.keys(FRIENDLY).forEach(k => {
    if (TOOLS[k]) { TOOLS[k].simple = FRIENDLY[k][0]; TOOLS[k].help = FRIENDLY[k][1]; }
});

const STAT_LABELS = [
    ["min", "Minimum intensity", "Darkest pixel (0 = black)"],
    ["max", "Maximum intensity", "Brightest pixel (255 = white)"],
    ["mean", "Mean intensity", "Average brightness"],
    ["range", "Simple contrast (max - min)", "Brightest minus darkest. Bigger = more contrast"],
    ["michelson", "Michelson contrast", "From 0 (flat) to 1 (full contrast)"],
    ["rms", "RMS contrast", "How spread out the brightness is. Bigger = more contrast"]
];

// ============ FLASK VERSION: ONLY THE TOPICS FROM OUR DIP LAB ============
// The Python/Flask version shows just the tools we did in the lab scripts.
// (The website and the Android app keep all 35 tools.)
// To show a hidden tool here again, add its name to this list.
const LAB_TOOLS = [
    "negative",                          // negate.txt
    "brightness_contrast",               // Image Contrast.py, Image Contrast-alpha-beta.py
    "stretch",                           // HistogramStretching.py
    "equalize",                          // BasicHistEqualization.py, NormalizedHistEqualization.py
    "clahe",                             // Gray-CLAHE.py
    "crop", "resize",                    // Image Croping-2.py, ImageResize.py, InterpolationKNN.py, Image-KNN.py
    "noise",                             // GussianNoise.py
    "sobel", "prewitt", "roberts", "canny",   // EdgeDetection.py
    "hsi_component", "hsi_roundtrip",    // RGB2HSI.py, HSI2RGB-2.py
    "sample",                            // Sampling.py
    "components",                        // Pixel Connectivity-Graph.py
    "match",                             // ImageMatching1.py, ImageMatching2.py
];
if (window.IMAGE_LAB_SERVER) {
    Object.keys(TOOLS).forEach(key => { if (!LAB_TOOLS.includes(key)) delete TOOLS[key]; });
    const getApp = document.getElementById("getApp");      // no APK download from the Python version
    if (getApp) getApp.style.display = "none";
}
