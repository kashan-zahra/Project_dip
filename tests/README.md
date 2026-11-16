# Parity test: does the JavaScript port give the same results as Python?

The website and the Android app run `web/js/processing.js` (OpenCV.js). The original lab
code is `python-flask/processing.py` (OpenCV for Python). This test runs 47 tool settings
through both on the same picture and compares every pixel.

```bash
pip install -r python-flask/requirements.txt
python tests/make_reference.py          # 1. results from the Python version
npm install @techstark/opencv-js
node tests/compare.js                   # 2. compare with the JavaScript version
```

Current result: **44 of 47 cases match within 1 gray level** (most are pixel-identical).
The 3 expected differences:

| Case | Why |
|---|---|
| Pixel Connectivity | Same regions and same count; the random colour given to each region differs. |
| K-Means | The JS version learns the colours from a sample of pixels so it stays fast on phones (about 0.1% of pixels differ). |
| HSI Hue | A few near-gray pixels where the hue is unstable (float precision). |
