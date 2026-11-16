"""Step 1 of the parity test: run every tool with the ORIGINAL Python code and save the results.

    pip install -r python-flask/requirements.txt
    python tests/make_reference.py
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "python-flask"))
import app as flask_app  # noqa: E402  (run_tool lives in app.py)

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

# a test picture with gradients, shapes and noise (BGR, like cv2.imread gives)
rng = np.random.RandomState(0)
h, w = 301, 402
y, x = np.mgrid[:h, :w]
img = np.dstack([(x * 255 / w), (y * 255 / h), ((x + y) % 255)]).astype(np.float32)
cv2.circle(img, (150, 120), 60, (30, 200, 90), -1)
cv2.rectangle(img, (250, 40), (370, 200), (220, 40, 40), -1)
img = np.clip(img * 0.7 + 30 + rng.normal(0, 8, img.shape), 0, 255).astype(np.uint8)
ref = cv2.convertScaleAbs(cv2.GaussianBlur(cv2.flip(img, 1), (9, 9), 0), alpha=0.8, beta=10)

open(os.path.join(OUT, "in.rgb"), "wb").write(cv2.cvtColor(img, cv2.COLOR_BGR2RGB).tobytes())
open(os.path.join(OUT, "ref.rgb"), "wb").write(cv2.cvtColor(ref, cv2.COLOR_BGR2RGB).tobytes())

cases = json.load(open(os.path.join(HERE, "cases.json")))
meta = []
for i, (tool, form) in enumerate(cases):
    out, note = flask_app.run_tool(img, tool, form, ref)
    if out.ndim == 3:
        out = cv2.cvtColor(out, cv2.COLOR_BGR2RGB)
    open(os.path.join(OUT, f"py{i}.raw"), "wb").write(np.ascontiguousarray(out).tobytes())
    meta.append(dict(shape=list(out.shape), note=note))
json.dump(dict(h=h, w=w, cases=meta), open(os.path.join(OUT, "py.json"), "w"))
print(f"saved {len(cases)} Python results to tests/out/")
