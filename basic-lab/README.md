# DIP Lab Basics

A small Flask website with only the basic topics from our Digital Image Processing lab.
Choose a picture, pick a tool, move the sliders: Python processes the picture and the page
shows the original and the result side by side, with both histograms.

| Topic | Tools |
|---|---|
| Intensity | Negative, Brightness / Contrast, Contrast Stretching |
| Histogram | Histogram Equalization, CLAHE, Histogram Matching |
| Crop & Resize | Crop, Resize (nearest / bilinear / bicubic), Sampling |
| Noise | Gaussian Noise |
| Edges | Sobel, Prewitt, Roberts, Canny |
| Colour | RGB to HSI (H, S, I) |
| Pixels | Pixel Connectivity (4 / 8) |

## Run it

```bash
pip install -r requirements.txt     # or double-click setup.bat on Windows
python app.py                       # or double-click run.bat
```

Then open http://127.0.0.1:5000

## Files

| File | What it does |
|---|---|
| `app.py` | Flask server: the list of tools, `/` shows the page, `/process` runs a tool |
| `processing.py` | The image-processing functions, one per lab topic |
| `templates/index.html` | The page: choose picture and tool, sliders, results, histograms |
| `static/samples/` | Two free sample photos (CC0, from scikit-image) |

## How it works

1. The page sends the picture, the tool name and the slider values to `/process`.
2. `app.py` reads the picture with OpenCV (`cv2.imdecode`), keeps it at most 800 px, and calls
   the matching function in `processing.py`.
3. It sends back the result as a base64 PNG, a short note and the two histograms (`cv2.calcHist`).
4. The page shows the pictures and draws the histograms.
