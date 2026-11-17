"""DIP Lab Basics - only the topics from our DIP lab, processed in Python.

It uses the same interface as the full Image Lab website (the ../web folder), with all its
features (Keep, Undo, Save, Pixel Inspector, Lab Data, Learn more), but shows only the
tools we did in the lab scripts. Every picture is processed here with OpenCV (processing.py).

    pip install -r requirements.txt
    python app.py            then open http://127.0.0.1:5000
"""
import base64
import sys
import os

import cv2
import numpy as np
from flask import Flask, Response, abort, jsonify, request, send_from_directory

import behind
import processing as dip

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.normpath(os.path.join(HERE, "..", "web"))   # the shared user interface

app = Flask(__name__, static_folder=None)


def encode(img):
    ok, buf = cv2.imencode(".png", img)
    return "data:image/png;base64," + base64.b64encode(buf).decode()


def read_image(file):
    data = np.frombuffer(file.read(), np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def shrink(img, limit=1000):
    # keep big images small so the app stays fast
    h, w = img.shape[:2]
    if max(h, w) > limit:
        s = limit / max(h, w)
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return img


def optional_image(name):
    """An extra uploaded image (reference or base), or None."""
    f = request.files.get(name)
    if f is None:
        return None
    img = read_image(f)
    return shrink(img) if img is not None else None


def run_tool(img, tool, f, ref):
    """Returns (result_image, note_text)."""

    def num(key, default):
        return float(f.get(key, default))

    # ---------- Enhance ----------
    if tool == "brightness_contrast":
        return dip.brightness_contrast(img, num("alpha", 1), num("beta", 0)), ""
    if tool == "gamma":
        g = num("gamma", 1)
        if g < 1:
            note = f"gamma = {g:g} (below 1): dark areas get brighter."
        elif g > 1:
            note = f"gamma = {g:g} (above 1): the image gets darker."
        else:
            note = "gamma = 1, so the image is unchanged."
        return dip.gamma(img, g), note
    if tool == "negative":
        return dip.negative(img), ""
    if tool == "stretch":
        return dip.contrast_stretch(img), ""
    if tool == "equalize":
        return dip.hist_equalize(img), ""
    if tool == "clahe":
        return dip.clahe(img, num("clip", 2), int(num("tile", 8))), ""

    # ---------- Transform ----------
    if tool == "crop":
        return dip.crop(img, num("x", 0), num("y", 0), num("w", 50), num("h", 50)), ""
    if tool == "resize":
        return dip.resize(img, num("percent", 50), f.get("interp", "linear")), ""
    if tool == "rotate":
        return dip.rotate(img, f.get("mode", "cw")), ""
    if tool == "flip":
        return dip.flip(img, f.get("mode", "h")), ""

    # ---------- Filters ----------
    if tool == "mean":
        return dip.mean_filter(img, num("size", 5)), ""
    if tool == "gaussian":
        return dip.gaussian_filter(img, num("size", 5)), ""
    if tool == "median":
        return dip.median_filter(img, num("size", 5)), ""
    if tool == "bilateral":
        return dip.bilateral_filter(img, num("sigma", 75)), ""
    if tool == "noise":
        return dip.gaussian_noise(img, num("mean", 0), num("std", 20)), ""

    # ---------- Edges ----------
    if tool == "sobel":
        return dip.sobel(img), ""
    if tool == "prewitt":
        return dip.prewitt(img), ""
    if tool == "roberts":
        return dip.roberts(img), ""
    if tool == "canny":
        return dip.canny(img, num("low", 100), num("high", 200)), ""

    # ---------- Color ----------
    if tool == "hsi_component":
        return dip.hsi_component(img, f.get("which", "h")), ""
    if tool == "hsi_roundtrip":
        out = dip.hsi_roundtrip(img)
        diff = np.abs(img.astype(np.float32) - out.astype(np.float32))
        note = (f"RGB to HSI to RGB again. Reconstruction error: "
                f"MAE = {diff.mean():.4f}, MSE = {(diff ** 2).mean():.4f}, "
                f"max error = {diff.max():.0f}. A tiny error means the conversion is correct.")
        return out, note
    if tool == "colorspace":
        space = f.get("space", "hsv")
        ch = int(num("channel", 0))
        out, names = dip.color_space(img, space, ch)
        if space == "gray":
            note = "Gray = 0.299 R + 0.587 G + 0.114 B. One channel instead of three."
        elif ch == 0:
            note = (f"Channels are {', '.join(names)}. All three are shown together, "
                    f"so the colors look strange. Pick one channel to see it alone.")
        else:
            label = {"hsv": "HSV", "lab": "LAB", "ycrcb": "YCrCb"}[space]
            note = f"Showing channel {names[ch - 1]} of {label} as a gray image."
        return out, note
    if tool == "channel":
        return dip.rgb_channel(img, f.get("which", "r")), ""

    # ---------- Pixels ----------
    if tool == "sample":
        out, sw, sh = dip.sample(img, num("size", 32))
        note = (f"The image was sampled down to {sw} x {sh} pixels, then enlarged back. "
                f"Fewer samples means bigger blocks and less detail.")
        return out, note
    if tool == "quantize":
        bits = int(num("bits", 3))
        note = (f"{bits} bits per channel = {2 ** bits} intensity levels. "
                f"Fewer levels means visible bands (false contours).")
        return dip.quantize(img, bits), note
    if tool == "components":
        conn = int(num("connectivity", 8))
        out, n = dip.components(img, num("thresh", 128), conn)
        note = (f"Found {n} separate regions using {conn}-connectivity. "
                f"Each color is one connected group of white pixels.")
        return out, note

    # ---------- Compare (needs a reference image) ----------
    if tool in ("match", "compare"):
        if ref is None:
            return img, "Upload a reference image (the box on the left) to use this tool."
        if tool == "match":
            note = "The result's histogram now follows the reference image's histogram."
            return dip.match_hist(img, ref), note
        out, pct = dip.compare(img, ref, num("tol", 5))
        note = (f"{pct:.2f}% of the pixels are similar (white). "
                f"The rest are different (black).")
        return out, note
        # ---------- New tools ----------
    if tool == "log":
        return dip.log_transform(img, num("c", 1)), "s = c * log(1 + r): brightens dark areas, compresses bright ones."
    if tool == "bitplane":
        bit = int(num("bit", 7))
        return dip.bit_plane(img, bit), f"Showing bit {bit}. Bit 7 (MSB) carries most of the picture, bit 0 (LSB) looks like noise."
    if tool == "laplacian":
        return dip.laplacian(img), "Laplacian uses the second derivative, so it responds to edges in all directions."
    if tool == "threshold":
        mode = f.get("mode", "otsu")
        out, t = dip.threshold(img, mode, num("t", 128))
        note = "Adaptive: each pixel is compared with its local neighborhood." if t is None \
            else f"Threshold used: {t:g}. Pixels above it become white, the rest black."
        return out, note
    if tool == "kmeans":
        k = int(num("k", 3))
        return dip.kmeans(img, k), f"K-Means grouped all pixel colors into {k} clusters and painted each pixel with its cluster color."
    if tool == "morph":
        return dip.morph(img, f.get("op", "erode"), num("size", 3)), "Erosion shrinks bright areas, dilation grows them. Opening = erode then dilate. Closing = dilate then erode."
    if tool == "fft":
        mode = f.get("mode", "spectrum")
        notes = {"spectrum": "Fourier spectrum (log scaled). Center = low frequencies, outside = high frequencies.",
                 "low": "Low-pass: only low frequencies kept, so the image is smoothed.",
                 "high": "High-pass: only high frequencies kept, so only edges and details remain."}
        return dip.fft_tool(img, mode, num("radius", 30)), notes[mode]

    return img, ""


# ---------------------------------------------------------------- pages

@app.route("/")
def index():
    # the shared page from ../web, told to use Python and to show only the lab tools
    with open(os.path.join(WEB, "index.html"), encoding="utf-8") as f:
        html = f.read()
    # IMAGE_LAB_SERVER: process in Python.   IMAGE_LAB_BASIC: show only the lab tools.
    flags = "<script>window.IMAGE_LAB_SERVER = true; window.IMAGE_LAB_BASIC = true;</script>"
    html = html.replace("</head>", "    " + flags + "\n</head>", 1)
    return Response(html, mimetype="text/html")


@app.route("/<path:path>")
def web_files(path):
    # css, js, sample photos ... from ../web
    if not os.path.isfile(os.path.join(WEB, path)):
        abort(404)
    return send_from_directory(WEB, path)


# ---------------------------------------------------------------- processing

@app.route("/process", methods=["POST"])
def process():
    file = request.files.get("image")
    if file is None:
        return jsonify(error="No image uploaded"), 400

    img = read_image(file)
    if img is None:
        return jsonify(error="Could not read this image"), 400
    img = shrink(img)

    ref = optional_image("reference")
    # what the Before side shows: the photo itself, or (after Keep) the original photo
    base = optional_image("base")
    if base is None:
        base = img

    # run the tool, and record what happens behind the scenes (see behind.py)
    out, note, trace = behind.run_with_trace(sys.modules[__name__], img, request.form.get("tool", "none"), request.form, ref)

    return jsonify(
        original=encode(base),
        result=encode(out),
        note=note,
        size_original=f"{base.shape[1]} x {base.shape[0]}",
        size_result=f"{out.shape[1]} x {out.shape[0]}",
        hist_original=dip.histogram(base),
        hist_result=dip.histogram(out),
        stats_original=dip.stats(base),
        stats_result=dip.stats(out),
        trace=trace,
    )


if __name__ == "__main__":
    app.run(debug=True)
