# DIP Lab Basics

Only the topics from our Digital Image Processing lab, processed in Python, with the same
interface and features as the full Image Lab website: Keep and add more tools, Undo, the
steps bar, compare with the original, Save, Pixel Inspector, Lab Data (histograms and
contrast) and Learn more (theory + the Python code).

| Topic | Tools (lab script) |
|---|---|
| Enhance | Negative (`negate.txt`), Brightness / Contrast (`Image Contrast.py`), Contrast Stretching (`HistogramStretching.py`), Histogram Equalization (`BasicHistEqualization.py`), CLAHE (`Gray-CLAHE.py`) |
| Resize & Rotate | Crop (`Image Croping-2.py`), Resize: nearest / bilinear / bicubic (`ImageResize.py`, `Image-KNN.py`) |
| Blur & Noise | Gaussian Noise (`GussianNoise.py`) |
| Edges | Sobel, Prewitt, Roberts, Canny (`EdgeDetection.py`) |
| Colour | HSI Components, RGB to HSI to RGB (`RGB2HSI.py`, `HSI2RGB-2.py`) |
| Pixels | Sampling (`Sampling.py`), Pixel Connectivity (`Pixel Connectivity-Graph.py`) |
| Compare 2 photos | Histogram Matching (`ImageMatching1.py`, `ImageMatching2.py`) |

## Run it

```bash
pip install -r requirements.txt     # or double-click setup.bat on Windows
python app.py                       # or double-click run.bat
```

Then open http://127.0.0.1:5000

## How it works

- `app.py` serves the shared interface from `../web` and tells it two things:
  process the pictures in Python (`IMAGE_LAB_SERVER`) and show only the lab tools (`IMAGE_LAB_BASIC`).
- When you move a slider, the page sends the picture and settings to `/process`.
  `app.py` reads the picture with OpenCV, keeps it at most 1000 px, and `run_tool()` calls the
  matching function in `processing.py`.
- The answer (result as a base64 PNG, a note, histograms and contrast numbers) is shown on the page.
- The list of lab tools is `LAB_TOOLS` at the end of `../web/js/tools.js`.
