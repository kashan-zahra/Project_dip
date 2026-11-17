"""Checks that explain.py (Behind the scenes) gives the same number as OpenCV for every tool.
Run from the project folder:  python tests/check_explain.py"""
import sys, itertools, cv2, numpy as np
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "python-flask"))
import app, explain
from werkzeug.datastructures import MultiDict
imgs = {"cat": app.shrink(cv2.imread(os.path.join(ROOT, "web", "samples", "cat.jpg"))),
        "coffee": app.shrink(cv2.imread(os.path.join(ROOT, "web", "samples", "coffee.jpg")))}
ref = imgs["coffee"]
CASES = {
 "brightness_contrast": [{"alpha":1.5,"beta":20},{"alpha":0.5,"beta":-40}],
 "gamma": [{"gamma":0.4},{"gamma":2.2}], "negative":[{}], "stretch":[{}], "equalize":[{}],
 "clahe": [{"clip":2,"tile":8},{"clip":4,"tile":5}],
 "crop": [{"x":10,"y":20,"w":50,"h":40}], "resize":[{"percent":50,"interp":m} for m in ("nearest","linear","cubic")]+[{"percent":170,"interp":"linear"}],
 "rotate":[{"mode":m} for m in ("cw","ccw","180")], "flip":[{"mode":m} for m in ("h","v","both")],
 "mean":[{"size":3},{"size":9}], "gaussian":[{"size":5},{"size":11}], "median":[{"size":5}], "bilateral":[{"sigma":75},{"sigma":30}],
 "noise":[{"mean":0,"std":20}], "sobel":[{}], "prewitt":[{}], "roberts":[{}], "canny":[{"low":50,"high":150},{"low":100,"high":200}],
 "hsi_component":[{"which":w} for w in "hsi"], "hsi_roundtrip":[{}],
 "colorspace":[{"space":s,"channel":c} for s in ("hsv","lab","ycrcb") for c in (0,1,2,3)]+[{"space":"gray","channel":0}],
 "channel":[{"which":w} for w in "rgb"], "sample":[{"size":32},{"size":10}], "quantize":[{"bits":3},{"bits":1}],
 "components":[{"thresh":128,"connectivity":8},{"thresh":90,"connectivity":4}], "log":[{"c":1},{"c":1.5}],
 "bitplane":[{"bit":7},{"bit":2}], "laplacian":[{}], "threshold":[{"mode":m,"t":128} for m in ("global","otsu","mean","gaussian")],
 "kmeans":[{"k":3}], "morph":[{"op":o,"size":5} for o in ("erode","dilate","open","close")],
 "fft":[{"mode":m,"radius":30} for m in ("spectrum","low","high")], "match":[{}], "compare":[{"tol":5}],
}
rng = np.random.default_rng(5)
bad = 0; total = 0; worst = {}
for tool, cases in CASES.items():
    for c in cases:
        for name, img in imgs.items():
            form = MultiDict({"tool": tool, **{k: str(v) for k, v in c.items()}})
            out, note = app.run_tool(img, tool, form, ref)
            H, W = out.shape[:2]
            pts = [(W//2, H//2), (0,0), (W-1,H-1)] + [(int(rng.integers(W)), int(rng.integers(H))) for _ in range(12)]
            for x, y in pts:
                steps, mine, real = explain.explain(tool, img, out, form, ref, x, y)
                total += 1
                if mine is None:
                    bad += 1; print("NONE", tool, c, steps[:1]); continue
                d = max(abs(a-b) for a,b in zip(mine, real))
                key=(tool, str(c)); worst[key]=max(worst.get(key,0), d)
for k, d in worst.items():
    if d > 0: print("diff", d, k)
print("checked", total, "none", bad)
