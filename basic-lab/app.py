"""DIP Lab Basics - a small Flask website for our Digital Image Processing lab topics.

    python app.py      then open http://127.0.0.1:5000

How it works:
  1. the page (templates/index.html) sends the picture + the chosen tool + the settings to /process
  2. /process reads the picture with OpenCV, runs one function from processing.py
  3. it sends back the result picture (as base64 PNG), a short note and both histograms
"""
import base64

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request

import processing as dip

app = Flask(__name__)

# ---------------------------------------------------------------- the tools shown on the page
# each control: [name, label, min, max, step, default]   or   [name, label, [choices]]
TOOLS = {
    "negative": dict(label="Negative", topic="Intensity",
                     info="Every pixel is flipped: dark becomes bright.", formula="s = 255 - r", controls=[]),
    "brightness_contrast": dict(label="Brightness / Contrast", topic="Intensity",
                     info="Alpha changes the contrast, beta the brightness.", formula="s = alpha * r + beta",
                     controls=[["alpha", "Contrast (alpha)", 0, 3, 0.1, 1.5], ["beta", "Brightness (beta)", -100, 100, 1, 0]]),
    "stretch": dict(label="Contrast Stretching", topic="Intensity",
                     info="Stretches the darkest..brightest range to the full 0..255.",
                     formula="s = (r - r_min) / (r_max - r_min) * 255", controls=[]),
    "equalize": dict(label="Histogram Equalization", topic="Histogram",
                     info="Spreads the gray levels evenly. Compare the two histograms below.",
                     formula="s = 255 * CDF(r)", controls=[]),
    "clahe": dict(label="CLAHE", topic="Histogram",
                     info="Equalization in small tiles, with a limit so noise is not boosted too much.",
                     formula="per tile: clip the histogram, then equalize",
                     controls=[["clip", "Clip limit", 1, 20, 0.5, 2], ["tile", "Tile grid size", 2, 16, 1, 8]]),
    "match": dict(label="Histogram Matching", topic="Histogram",
                     info="Makes your picture's histogram look like a second (reference) picture's.",
                     formula="s = CDF_ref^-1( CDF_src(r) )", controls=[], needs_ref=True),
    "crop": dict(label="Crop", topic="Crop & Resize",
                     info="Keeps a rectangle of the picture (array slicing). Values are % of the size.",
                     formula="out = img[y0:y1, x0:x1]",
                     controls=[["x", "Left (%)", 0, 90, 1, 20], ["y", "Top (%)", 0, 90, 1, 20],
                               ["w", "Width (%)", 10, 100, 1, 50], ["h", "Height (%)", 10, 100, 1, 50]]),
    "resize": dict(label="Resize (interpolation)", topic="Crop & Resize",
                     info="Nearest (KNN) copies the closest pixel, bilinear mixes 4, bicubic mixes 16.",
                     formula="new size = old size * percent / 100",
                     controls=[["percent", "Size (%)", 10, 300, 10, 50], ["method", "Method", ["nearest", "bilinear", "bicubic"]]]),
    "sampling": dict(label="Sampling", topic="Crop & Resize",
                     info="Fewer samples (pixels) = less detail and bigger blocks.",
                     formula="keep N pixels on the long side, then enlarge",
                     controls=[["samples", "Samples (long side)", 8, 256, 8, 48]]),
    "noise": dict(label="Gaussian Noise", topic="Noise",
                     info="Adds random grain from a normal distribution.",
                     formula="g = f + n,   n ~ N(0, std^2)", controls=[["std", "Noise strength (std)", 0, 80, 1, 25]]),
    "edges": dict(label="Edge Detection", topic="Edges",
                     info="Finds where the brightness changes quickly. Try all 4 methods.",
                     formula="|G| = sqrt(Gx^2 + Gy^2)   (Canny: smooth, gradient, thin, 2 thresholds)",
                     controls=[["method", "Method", ["sobel", "prewitt", "roberts", "canny"]]]),
    "hsi": dict(label="RGB to HSI", topic="Colour",
                     info="Hue = which colour, Saturation = how pure, Intensity = how bright.",
                     formula="I = (R+G+B)/3,   S = 1 - 3*min(R,G,B)/(R+G+B)",
                     controls=[["part", "Show", ["h", "s", "i"]]]),
    "connectivity": dict(label="Pixel Connectivity", topic="Pixels",
                     info="Each colour is one group of touching white pixels. Compare 4 and 8.",
                     formula="4: up, down, left, right   8: also the diagonals",
                     controls=[["conn", "Connectivity", ["4", "8"]]]),
}


def run_tool(img, tool, form, ref):
    """Run one tool. Returns (result image, note)."""
    num = lambda name: float(form.get(name))
    if tool == "negative":
        return dip.negative(img), ""
    if tool == "brightness_contrast":
        return dip.brightness_contrast(img, num("alpha"), num("beta")), ""
    if tool == "stretch":
        return dip.contrast_stretch(img), f"Range {int(img.min())}..{int(img.max())} was stretched to 0..255."
    if tool == "equalize":
        return dip.hist_equalize(img), ""
    if tool == "clahe":
        return dip.clahe(img, num("clip"), int(num("tile"))), ""
    if tool == "match":
        if ref is None:
            return img, "Choose a reference picture to match."
        return dip.hist_match(img, ref), ""
    if tool == "crop":
        return dip.crop(img, num("x"), num("y"), num("w"), num("h")), ""
    if tool == "resize":
        out = dip.resize(img, num("percent"), form.get("method"))
        return out, f"New size: {out.shape[1]} x {out.shape[0]} pixels."
    if tool == "sampling":
        return dip.sampling(img, int(num("samples"))), ""
    if tool == "noise":
        return dip.gaussian_noise(img, num("std")), ""
    if tool == "edges":
        return dip.edges(img, form.get("method")), ""
    if tool == "hsi":
        return dip.hsi(img, form.get("part")), ""
    if tool == "connectivity":
        out, count = dip.connectivity(img, int(form.get("conn")))
        return out, f"Found {count} separate regions with {form.get('conn')}-connectivity."
    return img, ""


def read_image(file):
    # uploaded file -> OpenCV image (BGR), at most 800 px so it stays fast
    img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]
    if max(h, w) > 800:
        s = 800 / max(h, w)
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return img


def to_png(img):
    # OpenCV image -> text the browser can show in an <img>
    ok, buf = cv2.imencode(".png", img)
    return "data:image/png;base64," + base64.b64encode(buf).decode()


@app.route("/")
def index():
    # a list of (name, tool) pairs keeps the order written above
    return render_template("index.html", tools=list(TOOLS.items()))


@app.route("/process", methods=["POST"])
def process():
    img = read_image(request.files["image"]) if "image" in request.files else None
    if img is None:
        return jsonify(error="Please choose a picture first."), 400
    ref = read_image(request.files["reference"]) if "reference" in request.files else None

    out, note = run_tool(img, request.form.get("tool"), request.form, ref)
    return jsonify(
        original=to_png(img),
        result=to_png(out),
        note=note,
        hist_original=dip.histogram(img),
        hist_result=dip.histogram(out),
    )


if __name__ == "__main__":
    app.run(debug=True)
