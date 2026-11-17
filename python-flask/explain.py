"""Explain one pixel: the exact calculation each tool does, with the real numbers.

behind.py calls explain(tool, img, out, form, ref, x, y). It returns
  steps  : a list of {"title", "lines", "grids"} shown on the back of the After card
  result : what our hand calculation got (checked against what OpenCV really produced)

Everything here only READS the picture. The real result always comes from processing.py.
Colour pictures in OpenCV are stored B, G, R, but we write them as R, G, B like people do.
"""
import math

import cv2
import numpy as np

import processing as dip

CH = [("R", 2), ("G", 1), ("B", 0)]          # name, index in OpenCV's B,G,R order


# ------------------------------------------------------------------ small helpers

def f(v, d=4):
    """A number, written short: 3, 0.25, 158.26 ..."""
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    v = float(v)
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.{d}f}".rstrip("0").rstrip(".")


def sq(v):
    """v², with brackets for negative numbers: (−4)²"""
    return f"({f(v)})²" if v < 0 else f"{f(v)}²"


def px(img, x, y):
    """[('R', 196), ('G', 156), ('B', 130)] or [('gray', 158)]"""
    if img.ndim == 2:
        return [("gray", int(img[y, x]))]
    return [(n, int(img[y, x, i])) for n, i in CH]


def px_text(img, x, y):
    return ", ".join(f"{n} {v}" for n, v in px(img, x, y))


def step(title, lines=(), grids=()):
    return {"title": title, "lines": list(lines), "grids": list(grids)}


def grid(label, rows, mark=None, fmt=f):
    """A small table of numbers. mark = (row, col) of the cell to highlight."""
    return {"label": label, "rows": [[fmt(v) for v in r] for r in rows], "mark": list(mark) if mark else None}


def window(a, x, y, k, border=cv2.BORDER_REFLECT_101):
    """The k x k neighbours around (x, y) of a 2-D array, with OpenCV's border rule."""
    r = k // 2
    p = cv2.copyMakeBorder(a, r, r, r, r, border)
    return p[y:y + k, x:x + k]


def gray_of(img, x, y):
    """Lines that show the gray formula for this pixel, and the gray value OpenCV uses."""
    g = int(dip.to_gray(img)[y, x])
    if img.ndim == 2:
        return g, [f"The picture is already gray: value = {g}"]
    b, gg, r = (int(v) for v in img[y, x])
    exact = 0.299 * r + 0.587 * gg + 0.114 * b
    return g, [f"gray = 0.299 × R + 0.587 × G + 0.114 × B",
               f"     = 0.299 × {r} + 0.587 × {gg} + 0.114 × {b}",
               f"     = {exact:.3f}  →  {g}"]


def products(win, ker):
    """'(-1 × 120) + (1 × 130) + ...' and the total."""
    terms, total = [], 0.0
    for wv, kv in zip(np.ravel(win), np.ravel(ker)):
        if kv != 0:
            terms.append(f"({f(kv)} × {f(wv)})")
            total += float(kv) * float(wv)
    lines, line = [], ""
    for t in terms:                                   # wrap long sums
        piece = t if not line else " + " + t
        if len(line) + len(piece) > 44:
            lines.append(line)
            line = "  + " + t
        else:
            line += piece
    lines.append(line)
    return lines, total


def per_channel(img, x, y, fn):
    """Run fn(name, value) -> (lines, result) for each channel, collect lines and results."""
    lines, res = [], []
    for name, v in px(img, x, y):
        l, r = fn(name, v)
        lines += l
        res.append(r)
    return lines, res


def normalize_lines(mag, value, what="magnitude"):
    """The last step of sobel/prewitt/roberts/laplacian/fft: stretch to 0-255 (to_uint8)."""
    lo, hi = float(mag.min()), float(mag.max())
    out = (value - lo) / (hi - lo) * 255 if hi > lo else 0
    return [f"to_uint8 stretches every {what} in the picture to 0 ... 255:",
            f"smallest {what} in the whole picture = {f(lo)}",
            f"largest  {what} in the whole picture = {f(hi)}",
            f"new = ({f(value)} − {f(lo)}) / ({f(hi)} − {f(lo)}) × 255 = {out:.3f}",
            f"→ cut to a whole number: {int(out)}"], int(out)


# ------------------------------------------------------------------ ENHANCE

def ex_brightness_contrast(img, out, F, x, y):
    a, b = F("alpha", 1), F("beta", 0)

    def one(n, v):
        raw = a * v + b
        r = int(min(255, max(0, round(abs(raw)))))
        return [f"{n}: |{f(a)} × {v} + {f(b)}| = {f(abs(raw))}  →  {r}"], r
    lines, res = per_channel(img, x, y, one)
    return [step("Formula:  g(x, y) = |α × f(x, y) + β|,  then kept in 0 ... 255",
                 [f"α (contrast) = {f(a)},   β (brightness) = {f(b)}"]),
            step("The same formula for each colour channel", lines)], res


def ex_gamma(img, out, F, x, y):
    g = F("gamma", 1)

    def one(n, v):
        r01 = v / 255
        s = 255 * r01 ** g
        res = int(np.clip(np.round(s), 0, 255))
        return [f"{n}: r / 255 = {v} / 255 = {r01:.4f}",
                f"   {r01:.4f} ^ {f(g)} = {r01 ** g:.4f}",
                f"   255 × {r01 ** g:.4f} = {s:.3f}  →  rounded {res}", ""], res
    lines, res = per_channel(img, x, y, one)
    return [step("Formula:  s = 255 × (r / 255) ^ γ", [f"γ (gamma) = {f(g)}",
                 "r = the old value, s = the new value. The code makes a lookup table of all",
                 "256 answers first, then cv2.LUT looks each pixel up in it."]),
            step("For each colour channel", lines[:-1])], res


def ex_negative(img, out, F, x, y):
    lines, res = per_channel(img, x, y, lambda n, v: ([f"{n}: 255 − {v} = {255 - v}"], 255 - v))
    return [step("Formula:  s = 255 − r", ["Dark becomes bright and bright becomes dark."]),
            step("For each colour channel", lines)], res


def ex_stretch(img, out, F, x, y):
    lo, hi = int(img.min()), int(img.max())
    if hi == lo:
        return [step("Every pixel has the same value, so nothing changes")], [v for _, v in px(img, x, y)]

    def one(n, v):
        s = (v - lo) / (hi - lo) * 255
        return [f"{n}: ({v} − {lo}) / ({hi} − {lo}) × 255 = {s:.3f}  →  {int(s)}"], int(s)
    lines, res = per_channel(img, x, y, one)
    return [step("Formula:  s = (r − r_min) / (r_max − r_min) × 255",
                 ["First Python looks at ALL the numbers in the picture:",
                  f"r_min = {lo}   (darkest value)", f"r_max = {hi}   (brightest value)"]),
            step("For each colour channel (the decimals are cut off by astype(np.uint8))", lines)], res


def ex_equalize(img, out, F, x, y):
    g, glines = gray_of(img, x, y)
    gray = dip.to_gray(img)
    hist = np.bincount(gray.ravel(), minlength=256)
    N = gray.size
    first = int(np.nonzero(hist)[0][0])
    cmin = int(hist[first])
    cdf = int(hist[:g + 1].sum())
    v = (cdf - cmin) * 255 / (N - cmin) if N > cmin else first
    res = int(min(255, max(0, round(v))))
    return [step("1. Turn the pixel gray", glines),
            step("2. Count the pixels (the histogram)",
                 [f"total pixels N = {N}",
                  f"pixels with exactly gray {g}: {int(hist[g])}",
                  f"cdf({g}) = pixels with gray ≤ {g} = {cdf}",
                  f"darkest gray used = {first}, it has cdf_min = {cmin} pixels"]),
            step("3. Spread the cdf over 0 ... 255",
                 ["new = (cdf(r) − cdf_min) / (N − cdf_min) × 255",
                  f"    = ({cdf} − {cmin}) / ({N} − {cmin}) × 255",
                  f"    = {v:.3f}  →  rounded {res}",
                  f"So {100 * cdf / N:.1f}% of the picture is this dark or darker, which puts it at {res}."])], [res]


def ex_clahe(img, out, F, x, y):
    clip, tiles = F("clip", 2), int(F("tile", 8))
    g, glines = gray_of(img, x, y)
    gray = dip.to_gray(img)
    H, W = gray.shape
    # OpenCV pads the picture so it splits evenly into tiles
    # (quirk copied from OpenCV: if either side doesn't divide evenly, BOTH sides get padded)
    if W % tiles or H % tiles:
        pw, ph = tiles - W % tiles, tiles - H % tiles
        pad = cv2.copyMakeBorder(gray, 0, ph, 0, pw, cv2.BORDER_REFLECT_101)
    else:
        pw = ph = 0
        pad = gray
    tw, th = pad.shape[1] // tiles, pad.shape[0] // tiles
    area = tw * th
    limit = max(int(clip * area / 256), 1)

    def lut(tx, ty):
        t = pad[ty * th:(ty + 1) * th, tx * tw:(tx + 1) * tw]
        hist = np.bincount(t.ravel(), minlength=256).astype(np.int64)
        clipped = int(np.maximum(hist - limit, 0).sum())
        hist = np.minimum(hist, limit)
        batch, residual = clipped // 256, clipped % 256
        hist += batch
        if residual:
            stepr = max(256 // residual, 1)
            for i in range(0, 256, stepr):
                if residual <= 0:
                    break
                hist[i] += 1
                residual -= 1
        cdf = np.cumsum(hist)
        return np.clip(np.round(cdf * 255.0 / area), 0, 255).astype(int), clipped

    txf, tyf = x / tw - 0.5, y / th - 0.5
    tx1, ty1 = math.floor(txf), math.floor(tyf)
    xa, ya = txf - tx1, tyf - ty1
    tx2, ty2 = min(tx1 + 1, tiles - 1), min(ty1 + 1, tiles - 1)
    tx1, ty1 = max(tx1, 0), max(ty1, 0)
    l11, c11 = lut(tx1, ty1)
    l12, _ = lut(tx2, ty1)
    l21, _ = lut(tx1, ty2)
    l22, _ = lut(tx2, ty2)
    v = (l11[g] * (1 - xa) + l12[g] * xa) * (1 - ya) + (l21[g] * (1 - xa) + l22[g] * xa) * ya
    res = int(min(255, max(0, round(v))))
    return [step("1. Turn the pixel gray", glines),
            step("2. Cut the picture into tiles",
                 ([f"the picture is padded by {pw} × {ph} mirrored pixels so it splits evenly"] if pw or ph else [])
                 + [f"{tiles} × {tiles} tiles, each {tw} × {th} pixels = {area} pixels",
                  f"clip limit = clip × area / 256 = {f(clip)} × {area} / 256 → {limit} pixels per gray level",
                  "Each tile gets its own equalization, but no gray level may have more than",
                  f"{limit} pixels: the extra ones are shared out evenly (this stops noise from exploding).",
                  f"In tile ({tx1}, {ty1}), {c11} pixels were above the limit and were shared out."]),
            step("3. Each tile's own equalization of gray " + str(g),
                 [f"tile ({tx1}, {ty1}) says {l11[g]}     tile ({tx2}, {ty1}) says {l12[g]}",
                  f"tile ({tx1}, {ty2}) says {l21[g]}     tile ({tx2}, {ty2}) says {l22[g]}"]),
            step("4. Blend the 4 nearest tiles (bilinear), so tile edges don't show",
                 [f"x weight = {xa:.3f},  y weight = {ya:.3f}",
                  f"top    = {l11[g]} × {1 - xa:.3f} + {l12[g]} × {xa:.3f} = {l11[g] * (1 - xa) + l12[g] * xa:.3f}",
                  f"bottom = {l21[g]} × {1 - xa:.3f} + {l22[g]} × {xa:.3f} = {l21[g] * (1 - xa) + l22[g] * xa:.3f}",
                  f"result = top × {1 - ya:.3f} + bottom × {ya:.3f} = {v:.3f}  →  {res}"])], [res]


def ex_log(img, out, F, x, y):
    c = F("c", 1)
    k = c * 255 / np.log(256)

    def one(n, v):
        s = k * np.log1p(np.float32(v))
        r = int(np.clip(s, 0, 255))
        return [f"{n}: {k:.3f} × ln(1 + {v}) = {k:.3f} × {math.log1p(v):.4f} = {s:.3f}  →  {r}"], r
    lines, res = per_channel(img, x, y, one)
    return [step("Formula:  s = c × 255 / ln(256) × ln(1 + r)",
                 [f"c = {f(c)}", f"c × 255 / ln(256) = {f(c)} × 255 / {math.log(256):.4f} = {k:.4f}",
                  "(this scale makes 255 stay 255 when c = 1)"]),
            step("For each colour channel (decimals cut off)", lines)], res


def ex_bitplane(img, out, F, x, y):
    bit = int(F("bit", 7))
    g, glines = gray_of(img, x, y)
    b = format(g, "08b")
    marked = "".join(f"[{d}]" if 7 - i == bit else d for i, d in enumerate(b))
    on = (g >> bit) & 1
    return [step("1. Turn the pixel gray", glines),
            step("2. Write it in binary (8 bits: bit 7 on the left, bit 0 on the right)",
                 [f"{g} = {b}", f"bit {bit} is in [ ]:  {marked}",
                  "bit values: 128 64 32 16 8 4 2 1"]),
            step("3. Keep only that bit",
                 [f"({g} >> {bit}) & 1 = {on}", f"{on} × 255 = {on * 255}",
                  "So the pixel becomes " + ("white" if on else "black") + "."])], [on * 255]


# ------------------------------------------------------------------ TRANSFORM

def ex_crop(img, out, F, x, y):
    H, W = img.shape[:2]
    cx, cy = F("x", 0), F("y", 0)
    x0, y0 = min(int(W * cx / 100), W - 1), min(int(H * cy / 100), H - 1)
    sx, sy = x + x0, y + y0
    return [step("1. Turn the % settings into pixels",
                 [f"picture is {W} × {H}",
                  f"left   x0 = {W} × {f(cx)}% = {x0}", f"top    y0 = {H} × {f(cy)}% = {y0}",
                  f"the new picture is {out.shape[1]} × {out.shape[0]}  (img[{y0}:{y0 + out.shape[0]}, {x0}:{x0 + out.shape[1]}])"]),
            step("2. Find where this pixel came from",
                 [f"new pixel (x {x}, y {y})  =  old pixel ({x} + {x0}, {y} + {y0})  =  old (x {sx}, y {sy})",
                  f"old pixel = {px_text(img, sx, sy)}", "Crop does not change colours, only which pixels are kept."])], \
        [v for _, v in px(img, sx, sy)]


def cubic_w(t, a=-0.75):
    t = abs(t)
    if t <= 1:
        return (a + 2) * t ** 3 - (a + 3) * t ** 2 + 1
    if t < 2:
        return a * t ** 3 - 5 * a * t ** 2 + 8 * a * t - 4 * a
    return 0.0


def ex_resize(img, out, F, x, y):
    H, W = img.shape[:2]
    oh, ow = out.shape[:2]
    pct, interp = F("percent", 50), F.s("interp", "linear")
    sx_, sy_ = W / ow, H / oh
    head = step("1. New size", [f"{W} × {H}  ×  {f(pct)}%  =  {ow} × {oh}",
                                f"one new pixel covers {sx_:.4f} × {sy_:.4f} old pixels"])
    if interp == "nearest":
        ox, oy = min(int(math.floor(x * sx_)), W - 1), min(int(math.floor(y * sy_)), H - 1)
        return [head, step("2. Nearest neighbour: copy the closest old pixel",
                           [f"old x = floor({x} × {sx_:.4f}) = {ox}", f"old y = floor({y} × {sy_:.4f}) = {oy}",
                            f"old pixel = {px_text(img, ox, oy)}  →  copied as it is"])], [v for _, v in px(img, ox, oy)]
    fx, fy = (x + 0.5) * sx_ - 0.5, (y + 0.5) * sy_ - 0.5
    lines = [f"old x = ({x} + 0.5) × {sx_:.4f} − 0.5 = {fx:.4f}",
             f"old y = ({y} + 0.5) × {sy_:.4f} − 0.5 = {fy:.4f}",
             "That is between pixels, so it mixes the old pixels around it."]
    x0, y0 = math.floor(fx), math.floor(fy)
    u, v = fx - x0, fy - y0
    if interp == "linear":
        xs = [min(max(x0, 0), W - 1), min(max(x0 + 1, 0), W - 1)]
        ys = [min(max(y0, 0), H - 1), min(max(y0 + 1, 0), H - 1)]
        wts = [(1 - u) * (1 - v), u * (1 - v), (1 - u) * v, u * v]
        pts = [(xs[0], ys[0]), (xs[1], ys[0]), (xs[0], ys[1]), (xs[1], ys[1])]
        res, chl = [], []
        for n, i in (CH if img.ndim == 3 else [("gray", None)]):
            vals = [int(img[py, pxx] if i is None else img[py, pxx, i]) for pxx, py in pts]
            tot = sum(a * b for a, b in zip(vals, wts))
            r = int(min(255, max(0, round(tot))))
            res.append(r)
            chl.append(f"{n}: " + " + ".join(f"{a}×{w:.3f}" for a, w in zip(vals, wts)) + f" = {tot:.2f} → {r}")
        return [head, step("2. Where the new pixel sits on the old picture", lines),
                step("3. Bilinear: mix the 4 nearest old pixels",
                     [f"the 4 pixels: ({xs[0]},{ys[0]}) ({xs[1]},{ys[0]}) ({xs[0]},{ys[1]}) ({xs[1]},{ys[1]})",
                      f"u = {u:.3f}, v = {v:.3f}",
                      "weights = (1−u)(1−v), u(1−v), (1−u)v, uv = " + ", ".join(f"{w:.3f}" for w in wts)] + chl)], res
    # cubic: 4 x 4 neighbours
    wx = [cubic_w(u + 1), cubic_w(u), cubic_w(1 - u), cubic_w(2 - u)]
    wy = [cubic_w(v + 1), cubic_w(v), cubic_w(1 - v), cubic_w(2 - v)]
    cols = [min(max(x0 - 1 + i, 0), W - 1) for i in range(4)]
    rows = [min(max(y0 - 1 + i, 0), H - 1) for i in range(4)]
    res, chl, grids = [], [], []
    for n, i in (CH if img.ndim == 3 else [("gray", None)]):
        blk = np.array([[int(img[r, c] if i is None else img[r, c, i]) for c in cols] for r in rows])
        tot = float(np.array(wy) @ blk @ np.array(wx))
        r = int(min(255, max(0, round(tot))))
        res.append(r)
        grids.append(grid(f"{n} (4 × 4 old pixels)", blk))
        chl.append(f"{n}: Σ weight_row × weight_col × pixel = {tot:.2f} → {r}")
    return [head, step("2. Where the new pixel sits on the old picture", lines),
            step("3. Bicubic: mix the 16 nearest old pixels with cubic weights (a = −0.75)",
                 [f"u = {u:.3f}, v = {v:.3f}",
                  "column weights = " + ", ".join(f"{w:.3f}" for w in wx),
                  "row weights    = " + ", ".join(f"{w:.3f}" for w in wy)] + chl, grids)], res


def ex_rotate(img, out, F, x, y):
    H, W = img.shape[:2]
    mode = F.s("mode", "cw")
    if mode == "cw":
        sx, sy, rule = y, H - 1 - x, f"old x = new y = {y},   old y = (H − 1) − new x = {H - 1} − {x} = {H - 1 - x}"
    elif mode == "ccw":
        sx, sy, rule = W - 1 - y, x, f"old x = (W − 1) − new y = {W - 1} − {y} = {W - 1 - y},   old y = new x = {x}"
    else:
        sx, sy, rule = W - 1 - x, H - 1 - y, f"old x = {W - 1} − {x} = {W - 1 - x},   old y = {H - 1} − {y} = {H - 1 - y}"
    name = {"cw": "90° clockwise", "ccw": "90° anticlockwise", "180": "180°"}[mode]
    return [step(f"Rotate {name}: every pixel moves, no colour changes",
                 [f"old picture {W} × {H}  →  new picture {out.shape[1]} × {out.shape[0]}",
                  f"new pixel (x {x}, y {y}) comes from:", rule,
                  f"old pixel (x {sx}, y {sy}) = {px_text(img, sx, sy)}"])], [v for _, v in px(img, sx, sy)]


def ex_flip(img, out, F, x, y):
    H, W = img.shape[:2]
    mode = F.s("mode", "h")
    sx = W - 1 - x if mode in ("h", "both") else x
    sy = H - 1 - y if mode in ("v", "both") else y
    lines = []
    if mode in ("h", "both"):
        lines.append(f"mirror left-right:  old x = (W − 1) − x = {W - 1} − {x} = {sx}")
    if mode in ("v", "both"):
        lines.append(f"mirror up-down:     old y = (H − 1) − y = {H - 1} − {y} = {sy}")
    code = {"h": 1, "v": 0, "both": -1}[mode]
    return [step(f"cv2.flip(img, {code}): pixels swap places, colours stay the same",
                 lines + [f"old pixel (x {sx}, y {sy}) = {px_text(img, sx, sy)}"])], [v for _, v in px(img, sx, sy)]


# ------------------------------------------------------------------ FILTERS

def neighbour_grids(img, x, y, k, border=cv2.BORDER_REFLECT_101):
    """The k x k window of each channel, with the centre marked."""
    chans = [("gray", img)] if img.ndim == 2 else [(n, img[:, :, i]) for n, i in CH]
    return [(n, window(np.ascontiguousarray(a), x, y, k, border)) for n, a in chans]


def ex_mean(img, out, F, x, y):
    k = dip.make_odd(F("size", 5))
    wins = neighbour_grids(img, x, y, k)
    lines, res, grids = [], [], []
    for n, w in wins:
        s = int(w.sum())
        r = int(round(s / (k * k)))
        res.append(r)
        lines.append(f"{n}: sum of the {k * k} numbers = {s},   {s} / {k * k} = {s / (k * k):.3f}  →  {r}")
        if k <= 7:
            grids.append(grid(f"{n} neighbours", w, (k // 2, k // 2)))
    return [step(f"Window size {k} × {k} (made odd: {F('size', 5):g} → {k})",
                 ["Each new value = the average of the pixel and its neighbours.",
                  "Edges of the picture are mirrored (BORDER_REFLECT_101)." if k > 1 else ""]),
            step("The neighbours of this pixel" + ("" if k <= 7 else " (too big to draw, sums only)"), [], grids),
            step("Average them, channel by channel", lines)], res


def ex_gaussian(img, out, F, x, y):
    k = dip.make_odd(F("size", 5))
    g1 = cv2.getGaussianKernel(k, 0).ravel()
    sigma = 0.3 * ((k - 1) * 0.5 - 1) + 0.8
    ker = np.outer(g1, g1)
    wins = neighbour_grids(img, x, y, k)
    lines, res, grids = [], [], []
    if k <= 7:
        grids.append(grid("Gaussian weights", ker, (k // 2, k // 2), fmt=lambda v: f"{v:.3f}"))
    for n, w in wins:
        tot = float((w * ker).sum())
        r = int(round(tot))
        res.append(r)
        if k <= 7:
            grids.append(grid(f"{n} neighbours", w, (k // 2, k // 2)))
        lines.append(f"{n}: Σ (weight × neighbour) = {tot:.3f}  →  {r}")
    return [step(f"Window {k} × {k}, σ worked out from the size",
                 [f"σ = 0.3 × ((k − 1) × 0.5 − 1) + 0.8 = {sigma:.3f}",
                  "weight = e^(−(dx² + dy²) / (2σ²)), then scaled so all weights add up to 1",
                  "1-D weights: " + ", ".join(f"{v:.4f}" for v in g1),
                  "Close neighbours count more than far ones."]),
            step("Weights and neighbours", [] if k <= 7 else ["(window too big to draw)"], grids),
            step("Weighted sum, channel by channel", lines)], res


def ex_median(img, out, F, x, y):
    k = dip.make_odd(F("size", 5))
    wins = neighbour_grids(img, x, y, k, cv2.BORDER_REPLICATE)
    lines, res, grids = [], [], []
    for n, w in wins:
        s = sorted(int(v) for v in w.ravel())
        m = s[len(s) // 2]
        res.append(m)
        if k <= 7:
            grids.append(grid(f"{n} neighbours", w, (k // 2, k // 2)))
        shown = s if len(s) <= 25 else s[:10] + ["…"] + s[-10:]
        lines += [f"{n} sorted: " + " ".join(map(str, shown)), f"   middle one (number {len(s) // 2 + 1} of {len(s)}) = {m}"]
    return [step(f"Window {k} × {k}: sort the neighbours and take the middle one",
                 ["The median ignores extreme values, so salt-and-pepper noise disappears."]),
            step("The neighbours", [] if k <= 7 else ["(window too big to draw)"], grids),
            step("Sort and pick the middle", lines)], res


def ex_bilateral(img, out, F, x, y):
    sigma = F("sigma", 75)
    d, r = 9, 4
    H, W = img.shape[:2]
    pad = cv2.copyMakeBorder(img, r, r, r, r, cv2.BORDER_REFLECT_101).astype(np.float64)
    c = pad[y + r, x + r]
    rows, num, den = [], np.zeros(img.shape[2] if img.ndim == 3 else 1), 0.0
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r:
                continue
            p = pad[y + r + dy, x + r + dx]
            cd = float(np.abs(p - c).sum())
            ws = math.exp(-(dx * dx + dy * dy) / (2 * sigma * sigma))
            wc = math.exp(-(cd * cd) / (2 * sigma * sigma))
            w = ws * wc
            num = num + w * np.atleast_1d(p)
            den += w
            rows.append((dx, dy, p, cd, ws, wc, w))
    vals = num / den
    res = [int(round(vals[i])) for _, i in CH] if img.ndim == 3 else [int(round(vals[0]))]
    near = sorted(rows, key=lambda t: (t[0] ** 2 + t[1] ** 2, t[1], t[0]))[:9]
    tl = ["(dx, dy)  colour             colour diff   w_space × w_colour = w"]
    for dx, dy, p, cd, ws, wc, w in near:
        col = f"R{int(p[2])} G{int(p[1])} B{int(p[0])}" if img.ndim == 3 else f"{int(p)}"
        tl.append(f"({dx:+d}, {dy:+d})  {col:<17}  {cd:>6.0f}      {ws:.3f} × {wc:.3f} = {w:.4f}")
    return [step("Bilateral filter: average only the neighbours that LOOK similar",
                 [f"window: circle of radius {r} (d = {d}) → {len(rows)} neighbours",
                  f"σ_space = σ_colour = {f(sigma)}",
                  "w_space  = e^(−(dx² + dy²) / (2σ²))      → near pixels count more",
                  "w_colour = e^(−(colour diff)² / (2σ²))   → similar colours count more",
                  "colour diff = |ΔR| + |ΔG| + |ΔB|  (so edges are kept sharp)"]),
            step("The 9 closest neighbours (all " + str(len(rows)) + " are used)", tl),
            step("New value = Σ (w × neighbour) / Σ w",
                 [f"Σ w = {den:.4f}"] + [f"{n}: {num[i]:.2f} / {den:.4f} = {vals[i]:.3f} → {res[j]}"
                                        for j, (n, i) in enumerate(CH if img.ndim == 3 else [("gray", 0)])])], res


def ex_noise(img, out, F, x, y):
    mean, std = F("mean", 0), F("std", 20)
    noise = np.random.default_rng(0).normal(mean, std, img.shape)

    def one(n, v):
        i = dict(CH).get(n)
        z = noise[y, x] if i is None else noise[y, x, i]
        s = float(np.float32(v) + np.float32(z))
        r = int(np.clip(s, 0, 255))
        return [f"{n}: {v} + ({z:+.3f}) = {s:.3f}  →  {r}"], r
    lines, res = per_channel(img, x, y, one)
    return [step("Formula:  new = old + random noise,  then kept in 0 ... 255",
                 [f"noise ~ Normal(mean = {f(mean)}, std = {f(std)})",
                  "About 68% of the noise is within ±std, 95% within ±2 × std.",
                  "The seed is fixed (default_rng(0)), so the same settings give the same grain."]),
            step("The random number drawn for this pixel, per channel", lines)], res


# ------------------------------------------------------------------ EDGES

def edge_explain(img, x, y, kx, ky, label, magfn, anchor_k=3):
    g, glines = gray_of(img, x, y)
    gray = dip.to_gray(img)
    k = kx.shape[0]
    if k == 2:                       # Roberts: 2 x 2 window, anchor at its bottom-right
        pad = cv2.copyMakeBorder(gray, 1, 0, 1, 0, cv2.BORDER_REFLECT_101)
        win = pad[y:y + 2, x:x + 2].astype(float)
        mark = (1, 1)
    else:
        win = window(gray, x, y, 3).astype(float)
        mark = (1, 1)
    lx, gx = products(win, kx)
    ly, gy = products(win, ky)
    mag = math.sqrt(gx * gx + gy * gy)
    allmag = magfn()
    nl, res = normalize_lines(allmag, mag)
    return g, [step("1. Turn the pixel gray", glines),
               step(f"2. Take its {k} × {k} gray neighbours", [], [grid("gray neighbours", win, mark),
                                                                    grid(f"{label} Gx kernel", kx), grid(f"{label} Gy kernel", ky)]),
               step("3. Multiply each neighbour by the kernel and add up",
                    ["Gx (change left → right):"] + ["  " + l for l in lx] + [f"  = {f(gx)}", "Gy (change top → bottom):"]
                    + ["  " + l for l in ly] + [f"  = {f(gy)}"]),
               step("4. Edge strength (gradient magnitude)",
                    [f"√(Gx² + Gy²) = √({sq(gx)} + {sq(gy)}) = √{f(gx * gx + gy * gy)} = {mag:.3f}",
                     "Big number = strong edge here. 0 = flat area."]),
               step("5. Make it fit in 0 ... 255", nl)], [res]


def ex_sobel(img, out, F, x, y):
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], float)
    ky = kx.T.copy()

    def mags():
        g = dip.to_gray(img)
        return np.sqrt(cv2.Sobel(g, cv2.CV_64F, 1, 0, ksize=3) ** 2 + cv2.Sobel(g, cv2.CV_64F, 0, 1, ksize=3) ** 2)
    _, steps, res = edge_explain(img, x, y, kx, ky, "Sobel", mags)
    return steps, res


def ex_prewitt(img, out, F, x, y):
    kx = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], float)
    ky = np.array([[-1, -1, -1], [0, 0, 0], [1, 1, 1]], float)

    def mags():
        g = dip.to_gray(img)
        return np.sqrt(cv2.filter2D(g, cv2.CV_32F, kx.astype(np.float32)) ** 2 + cv2.filter2D(g, cv2.CV_32F, ky.astype(np.float32)) ** 2)
    _, steps, res = edge_explain(img, x, y, kx, ky, "Prewitt", mags)
    return steps, res


def ex_roberts(img, out, F, x, y):
    kx = np.array([[1, 0], [0, -1]], float)
    ky = np.array([[0, 1], [-1, 0]], float)

    def mags():
        g = dip.to_gray(img)
        return np.sqrt(cv2.filter2D(g, cv2.CV_32F, kx.astype(np.float32)) ** 2 + cv2.filter2D(g, cv2.CV_32F, ky.astype(np.float32)) ** 2)
    _, steps, res = edge_explain(img, x, y, kx, ky, "Roberts", mags)
    return steps, res


def ex_laplacian(img, out, F, x, y):
    g, glines = gray_of(img, x, y)
    gray = dip.to_gray(img)
    ker = np.array([[2, 0, 2], [0, -8, 0], [2, 0, 2]], float)
    win = window(gray, x, y, 3).astype(float)
    l, tot = products(win, ker)
    allm = np.abs(cv2.Laplacian(gray, cv2.CV_64F, ksize=3))
    nl, res = normalize_lines(allm, abs(tot), "|Laplacian|")
    return [step("1. Turn the pixel gray", glines),
            step("2. Its 3 × 3 gray neighbours and the Laplacian kernel (OpenCV, ksize = 3)", [],
                 [grid("gray neighbours", win, (1, 1)), grid("kernel", ker, (1, 1))]),
            step("3. Multiply and add up (second derivative)",
                 l + [f"= {f(tot)}", f"take the size only: |{f(tot)}| = {f(abs(tot))}",
                      "Positive or negative both mean the brightness bends here (an edge)."]),
            step("4. Make it fit in 0 ... 255", nl)], [res]


def ex_canny(img, out, F, x, y):
    low, high = F("low", 100), F("high", 200)
    g, glines = gray_of(img, x, y)
    gray = dip.to_gray(img)
    dx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    dy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.abs(dx) + np.abs(dy)
    gx, gy, m = float(dx[y, x]), float(dy[y, x]), float(mag[y, x])
    ang = (math.degrees(math.atan2(gy, gx)) + 180) % 180
    H, W = gray.shape
    if ang < 22.5 or ang >= 157.5:
        d, nb = "left-right (0°)", [(x - 1, y), (x + 1, y)]
    elif ang < 67.5:
        d, nb = "diagonal (45°)", [(x - 1, y - 1), (x + 1, y + 1)]
    elif ang < 112.5:
        d, nb = "up-down (90°)", [(x, y - 1), (x, y + 1)]
    else:
        d, nb = "diagonal (135°)", [(x + 1, y - 1), (x - 1, y + 1)]
    nbv = [float(mag[min(max(b, 0), H - 1), min(max(a, 0), W - 1)]) for a, b in nb]
    is_max = m > nbv[0] and m >= nbv[1]
    real = int(out[y, x])
    win = window(gray, x, y, 3)
    if not is_max or m <= low:
        verdict = (f"{f(m)} is not the biggest along the edge direction → thinned away (0)" if not is_max
                   else f"{f(m)} ≤ low = {f(low)} → too weak, not an edge (0)")
    elif m > high:
        verdict = f"{f(m)} > high = {f(high)} → STRONG edge, kept (255)"
    else:
        verdict = (f"{f(low)} < {f(m)} ≤ {f(high)} → weak edge: kept only if it touches a strong edge → "
                   + ("it does (255)" if real else "it does not (0)"))
    return [step("1. Turn the pixel gray", glines),
            step("2. Sobel gradients (3 × 3)", [f"Gx = {f(gx)},   Gy = {f(gy)}"], [grid("gray neighbours", win, (1, 1))]),
            step("3. Edge strength and direction",
                 [f"strength = |Gx| + |Gy| = {f(abs(gx))} + {f(abs(gy))} = {f(m)}   (Canny's default L1 form)",
                  f"direction = atan2(Gy, Gx) = {ang:.1f}° → {d}"]),
            step("4. Non-maximum suppression (make edges 1 pixel thin)",
                 [f"neighbours across the edge: {nb[0]} = {f(nbv[0])},  {nb[1]} = {f(nbv[1])}",
                  f"is {f(m)} the biggest of the three? " + ("yes" if is_max else "no")]),
            step("5. Double threshold + hysteresis", [f"low = {f(low)},  high = {f(high)}", verdict])], [real]


# ------------------------------------------------------------------ COLOUR

def hsi_lines(r, g, b):
    R, G, B = np.float32(r), np.float32(g), np.float32(b)
    I = (R + G + B) / 3
    tot = R + G + B
    S = 1 - 3 * min(R, G, B) / tot if tot > 0 else 0.0
    num = 0.5 * ((R - G) + (R - B))
    den = math.sqrt(float((R - G) ** 2 + (R - B) * (G - B)))
    if den > 1e-10:
        th = math.degrees(math.acos(max(-1, min(1, num / den))))
        Hh = th if B <= G else 360 - th
    else:
        th, Hh = 0.0, 0.0
    lines = [f"I = (R + G + B) / 3 = ({r} + {g} + {b}) / 3 = {I:.3f}",
             f"S = 1 − 3 × min(R, G, B) / (R + G + B) = 1 − 3 × {min(r, g, b)} / {r + g + b} = {S:.4f}",
             f"θ = arccos( ½((R−G) + (R−B)) / √((R−G)² + (R−B)(G−B)) )",
             f"  = arccos( {num:.2f} / {den:.3f} ) = {th:.2f}°" if den > 1e-10 else "  (R = G = B: gray, so hue is set to 0)",
             f"B ≤ G, so H = θ = {Hh:.2f}°" if B <= G else f"B > G, so H = 360° − θ = {Hh:.2f}°"]
    return float(Hh), float(S), float(I), lines


def ex_hsi_component(img, out, F, x, y):
    which = F.s("which", "h")
    b, g, r = (int(v) for v in img[y, x])
    Hh, S, I, lines = hsi_lines(r, g, b)
    if which == "h":
        h8 = int(np.clip(Hh / 2, 0, 179))
        res = [v for _, v in px(out, x, y)]
        last = step("Show H as a colour",
                    [f"OpenCV stores hue as H / 2 = {Hh:.2f} / 2 → {h8}",
                     f"paint it at full saturation and brightness: HSV({h8}, 255, 255) → RGB",
                     f"= R {res[0]}, G {res[1]}, B {res[2]}"])
    elif which == "s":
        res = [int(np.clip(S * 255, 0, 255))]
        last = step("Show S as gray", [f"S × 255 = {S:.4f} × 255 = {S * 255:.3f} → {res[0]}"])
    else:
        res = [int(np.clip(I, 0, 255))]
        last = step("Show I as gray", [f"I = {I:.3f} → {res[0]}"])
    return [step("RGB → HSI (the textbook formulas in rgb_to_hsi)", [f"R = {r}, G = {g}, B = {b}"] + lines), last], res


def ex_hsi_roundtrip(img, out, F, x, y):
    b, g, r = (int(v) for v in img[y, x])
    Hh, S, I, lines = hsi_lines(r, g, b)
    c60 = math.radians(60)
    if Hh < 120:
        h = math.radians(Hh)
        B = I * (1 - S); R = I * (1 + S * math.cos(h) / math.cos(c60 - h)); G = 3 * I - R - B
        sec = [f"sector 1 (0° ≤ H < 120°), h = {Hh:.2f}°",
               f"B = I(1 − S) = {B:.3f}", f"R = I(1 + S cos h / cos(60° − h)) = {R:.3f}", f"G = 3I − R − B = {G:.3f}"]
    elif Hh < 240:
        h = math.radians(Hh - 120)
        R = I * (1 - S); G = I * (1 + S * math.cos(h) / math.cos(c60 - h)); B = 3 * I - R - G
        sec = [f"sector 2 (120° ≤ H < 240°), h = H − 120° = {Hh - 120:.2f}°",
               f"R = I(1 − S) = {R:.3f}", f"G = I(1 + S cos h / cos(60° − h)) = {G:.3f}", f"B = 3I − R − G = {B:.3f}"]
    else:
        h = math.radians(Hh - 240)
        G = I * (1 - S); B = I * (1 + S * math.cos(h) / math.cos(c60 - h)); R = 3 * I - G - B
        sec = [f"sector 3 (240° ≤ H ≤ 360°), h = H − 240° = {Hh - 240:.2f}°",
               f"G = I(1 − S) = {G:.3f}", f"B = I(1 + S cos h / cos(60° − h)) = {B:.3f}", f"R = 3I − G − B = {R:.3f}"]
    res = [int(np.clip(round(v), 0, 255)) for v in (R, G, B)]
    return [step("1. RGB → HSI", [f"R = {r}, G = {g}, B = {b}"] + lines),
            step("2. HSI → RGB again (hsi_to_rgb)", sec + [f"rounded: R {res[0]}, G {res[1]}, B {res[2]}",
                                                          f"error: |{r}−{res[0]}| + |{g}−{res[1]}| + |{b}−{res[2]}| = {abs(r - res[0]) + abs(g - res[1]) + abs(b - res[2])}"])], res


def ex_colorspace(img, out, F, x, y):
    space, ch = F.s("space", "hsv"), int(F("channel", 0))
    b, g, r = (int(v) for v in img[y, x])
    if space == "gray":
        gv, gl = gray_of(img, x, y)
        return [step("RGB → Gray", gl)], [gv]
    conv = cv2.cvtColor(img[y:y + 1, x:x + 1], dip.SPACES[space][0])[0, 0]
    names = dip.SPACES[space][1]
    if space == "hsv":
        V, mn = max(r, g, b), min(r, g, b)
        diff = V - mn
        S = 255 * diff / V if V else 0
        if diff == 0:
            Hd, hl = 0.0, "max = min (gray), so H = 0"
        elif V == r:
            Hd = 60 * (g - b) / diff; hl = f"max is R: H = 60 × (G − B) / (max − min) = 60 × ({g} − {b}) / {diff} = {Hd:.2f}°"
        elif V == g:
            Hd = 120 + 60 * (b - r) / diff; hl = f"max is G: H = 120 + 60 × (B − R) / (max − min) = {Hd:.2f}°"
        else:
            Hd = 240 + 60 * (r - g) / diff; hl = f"max is B: H = 240 + 60 × (R − G) / (max − min) = {Hd:.2f}°"
        if Hd < 0:
            Hd += 360
        lines = [f"V = max(R, G, B) = max({r}, {g}, {b}) = {V}",
                 f"S = 255 × (max − min) / max = 255 × ({V} − {mn}) / {V} = {S:.2f} → {int(conv[1])}",
                 hl, f"OpenCV keeps H in 0 ... 179, so H / 2 = {Hd / 2:.2f} → {int(conv[0])}"]
    elif space == "ycrcb":
        Y = 0.299 * r + 0.587 * g + 0.114 * b
        lines = [f"Y  = 0.299 R + 0.587 G + 0.114 B = {Y:.3f} → {int(conv[0])}",
                 f"Cr = (R − Y) × 0.713 + 128 = ({r} − {Y:.3f}) × 0.713 + 128 = {(r - Y) * 0.713 + 128:.3f} → {int(conv[1])}",
                 f"Cb = (B − Y) × 0.564 + 128 = ({b} − {Y:.3f}) × 0.564 + 128 = {(b - Y) * 0.564 + 128:.3f} → {int(conv[2])}"]
    else:
        lab = cv2.cvtColor(np.float32([[[b, g, r]]]) / 255, cv2.COLOR_BGR2LAB)[0, 0]
        lin = [((c / 255) / 12.92) if c / 255 <= 0.04045 else (((c / 255) + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
        X = 0.412453 * lin[0] + 0.357580 * lin[1] + 0.180423 * lin[2]
        Yy = 0.212671 * lin[0] + 0.715160 * lin[1] + 0.072169 * lin[2]
        Z = 0.019334 * lin[0] + 0.119193 * lin[1] + 0.950227 * lin[2]
        lines = [f"1. undo screen gamma: R' {lin[0]:.4f}, G' {lin[1]:.4f}, B' {lin[2]:.4f}",
                 f"2. to XYZ (matrix): X {X:.4f}, Y {Yy:.4f}, Z {Z:.4f}",
                 f"3. L* = 116 × f(Y) − 16 = {lab[0]:.3f}   a* = {lab[1]:.3f}   b* = {lab[2]:.3f}",
                 f"4. fit in 0 ... 255:  L = L* × 255 / 100 = {lab[0] * 2.55:.2f} → {int(conv[0])},",
                 f"   a = a* + 128 = {lab[1] + 128:.2f} → {int(conv[1])},   b = b* + 128 = {lab[2] + 128:.2f} → {int(conv[2])}"]
    if ch == 0:
        res = [int(conv[2]), int(conv[1]), int(conv[0])]
        last = step("Show all 3 channels at once",
                    [f"{names[0]}, {names[1]}, {names[2]} = {int(conv[0])}, {int(conv[1])}, {int(conv[2])}",
                     f"they are put where the screen expects B, G, R, so the screen shows R {res[0]}, G {res[1]}, B {res[2]}",
                     "That is why the colours look strange."])
    else:
        res = [int(conv[ch - 1])]
        last = step(f"Show only channel {names[ch - 1]} as gray", [f"{names[ch - 1]} = {res[0]}"])
    return [step(f"RGB → {space.upper()}  for R = {r}, G = {g}, B = {b}", lines), last], res


def ex_channel(img, out, F, x, y):
    which = F.s("which", "r")
    v = int(img[y, x, {"b": 0, "g": 1, "r": 2}[which]])
    return [step(f"Keep only the {which.upper()} channel", [f"pixel = {px_text(img, x, y)}",
                 f"{which.upper()} = {v}  →  shown as gray {v}",
                 f"Bright here = a lot of {dict(r='red', g='green', b='blue')[which]} in this spot."])], [v]


# ------------------------------------------------------------------ PIXELS

def ex_sample(img, out, F, x, y):
    size = F("size", 32)
    h, w = img.shape[:2]
    scale = size / max(h, w)
    sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
    smx, smy = min(int(math.floor(x * sw / w)), sw - 1), min(int(math.floor(y * sh / h)), sh - 1)
    ox, oy = min(int(math.floor(smx * w / sw)), w - 1), min(int(math.floor(smy * h / sh)), h - 1)
    return [step("1. Sample down", [f"long side {max(h, w)} → {f(size)} pixels: scale = {f(size)} / {max(h, w)} = {scale:.4f}",
                                     f"small picture = {sw} × {sh}",
                                     f"each small pixel stands for about {w / sw:.2f} × {h / sh:.2f} old pixels"]),
            step("2. Which small pixel is this?", [f"small x = floor({x} × {sw} / {w}) = {smx}",
                                                     f"small y = floor({y} × {sh} / {h}) = {smy}"]),
            step("3. Which old pixel did that small pixel copy? (nearest neighbour)",
                 [f"old x = floor({smx} × {w} / {sw}) = {ox}", f"old y = floor({smy} × {h} / {sh}) = {oy}",
                  f"old pixel = {px_text(img, ox, oy)}",
                  "Every pixel in the same block copies this same one, so you see big squares."])], [v for _, v in px(img, ox, oy)]


def ex_quantize(img, out, F, x, y):
    bits = int(F("bits", 3))
    levels = 2 ** bits
    stp = 256 / levels

    def one(n, v):
        q = math.floor(v / stp)
        o = int(round(q * 255 / (levels - 1)))
        return [f"{n}: bucket = floor({v} / {f(stp)}) = {q}   →   {q} × 255 / {levels - 1} = {q * 255 / (levels - 1):.2f} → {o}"], o
    lines, res = per_channel(img, x, y, one)
    return [step("Fewer levels", [f"{bits} bits → 2^{bits} = {levels} levels",
                                  f"bucket width = 256 / {levels} = {f(stp)}",
                                  "Every value in the same bucket gets the same output, which makes bands."]),
            step("For each colour channel", lines)], res


def ex_components(img, out, F, x, y):
    t, conn = F("thresh", 128), int(F("connectivity", 8))
    g, glines = gray_of(img, x, y)
    gray = dip.to_gray(img)
    _, binary = cv2.threshold(gray, t, 255, cv2.THRESH_BINARY)
    n, labels = cv2.connectedComponents(binary, connectivity=conn)
    lab = int(labels[y, x])
    win = window(binary, x, y, 3, cv2.BORDER_CONSTANT) // 255
    s = [step("1. Turn the pixel gray", glines),
         step("2. Threshold to black and white",
              [f"{g} > {f(t)} ?  " + ("yes → white (1)" if g > t else "no → black (0)")]),
         step(f"3. Look at its neighbours ({conn}-connectivity)",
              ["4-connectivity: only up, down, left, right count as touching." if conn == 4
               else "8-connectivity: the 4 diagonals also count as touching."],
              [grid("black/white neighbours (1 = white)", win, (1, 1))])]
    res = [v for _, v in px(out, x, y)]
    if lab == 0:
        s.append(step("4. Result", ["The pixel is black (background, label 0) → stays black."]))
    else:
        size = int((labels == lab).sum())
        s.append(step("4. Which group is it in?",
                      [f"{n - 1} white groups found; this pixel is in group number {lab}",
                       f"that group has {size} pixels",
                       f"every group gets a random colour: group {lab} → R {res[0]}, G {res[1]}, B {res[2]}"]))
    return s, res


def ex_threshold(img, out, F, x, y):
    mode, t = F.s("mode", "otsu"), F("t", 128)
    g, glines = gray_of(img, x, y)
    gray = dip.to_gray(img)
    s = [step("1. Turn the pixel gray", glines)]
    if mode in ("global", "otsu"):
        if mode == "otsu":
            T, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            hist = np.bincount(gray.ravel(), minlength=256).astype(float)
            p = hist / hist.sum()
            ti = int(T)
            w0 = p[:ti + 1].sum(); w1 = 1 - w0
            m0 = (np.arange(ti + 1) * p[:ti + 1]).sum() / w0 if w0 else 0
            m1 = (np.arange(ti + 1, 256) * p[ti + 1:]).sum() / w1 if w1 else 0
            s.append(step("2. Otsu picks the threshold by itself",
                          ["It tries every t from 0 to 255 and keeps the one where the dark group and",
                           "the bright group are the most different: max  ω0 ω1 (μ0 − μ1)²",
                           f"best t = {ti}:  ω0 = {w0:.3f} (dark share), ω1 = {w1:.3f} (bright share)",
                           f"μ0 = {m0:.2f} (dark average), μ1 = {m1:.2f} (bright average)",
                           f"ω0 ω1 (μ0 − μ1)² = {w0 * w1 * (m0 - m1) ** 2:.2f}"]))
            t = T
        res = 255 if g > t else 0
        s.append(step("Compare", [f"{g} > {f(t)} ?  " + ("yes → white (255)" if g > t else "no → black (0)")]))
        return s, [res]
    blk = window(gray, x, y, 11, cv2.BORDER_REPLICATE).astype(float)
    if mode == "mean":
        m = blk.sum() / 121
        local = int(round(m))
        ml = [f"local mean = sum of the 11 × 11 = 121 neighbours / 121 = {f(blk.sum())} / 121 = {m:.3f} → {local}"]
    else:
        gk = cv2.getGaussianKernel(11, 0)
        m = float((blk * (gk @ gk.T)).sum())
        local = int(round(m))
        ml = [f"local mean = Gaussian-weighted average of the 11 × 11 neighbours = {m:.3f} → {local}"]
    T = local - 2
    res = 255 if g > T else 0
    s.append(step("2. Adaptive: each pixel gets its own threshold from its neighbourhood",
                  ml + [f"threshold = local mean − C = {local} − 2 = {T}",
                        f"{g} > {T} ?  " + ("yes → white (255)" if g > T else "no → black (0)")]))
    return s, [res]


def ex_kmeans(img, out, F, x, y):
    k = int(F("k", 3))
    centers = np.unique(out.reshape(-1, 3), axis=0)
    b, g, r = (int(v) for v in img[y, x])
    lines, best = [], None
    for c in centers:
        cb, cg, cr = (int(v) for v in c)
        d = math.sqrt((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2)
        lines.append(f"to R{cr} G{cg} B{cb}:  √(({r}−{cr})² + ({g}−{cg})² + ({b}−{cb})²) = {d:.2f}")
        if best is None or d < best[0]:
            best = (d, (cr, cg, cb))
    return [step(f"K-Means found {k} cluster colours (centres) for the whole picture",
                 ["It starts with k colours, gives every pixel to the nearest one, moves each",
                  "centre to the average of its pixels, and repeats (up to 50 times)."]),
            step(f"This pixel R{r} G{g} B{b}: distance to each centre", lines),
            step("Paint it with the nearest centre", [f"nearest = R{best[1][0]} G{best[1][1]} B{best[1][2]}  (distance {best[0]:.2f})"])], \
        list(best[1])


def ex_morph(img, out, F, x, y):
    op, size = F.s("op", "erode"), F("size", 3)
    k = dip.make_odd(size)
    g, glines = gray_of(img, x, y)
    gray = dip.to_gray(img)
    ker = np.ones((k, k), np.uint8)
    s = [step("1. Turn the pixel gray", glines)]
    show = k <= 7
    if op in ("erode", "dilate"):
        w = window(gray, x, y, k, cv2.BORDER_REPLICATE)
        v = int(w.min() if op == "erode" else w.max())
        s.append(step(f"2. {'Erosion' if op == 'erode' else 'Dilation'}: look at the {k} × {k} square around it",
                      [f"{'smallest' if op == 'erode' else 'biggest'} value in the square = {v}",
                       "Erosion takes the minimum, so bright areas shrink." if op == "erode"
                       else "Dilation takes the maximum, so bright areas grow."],
                      [grid("neighbours", w, (k // 2, k // 2))] if show else []))
        return s, [v]
    first = cv2.erode(gray, ker) if op == "open" else cv2.dilate(gray, ker)
    w = window(first, x, y, k, cv2.BORDER_REPLICATE)
    v = int(w.max() if op == "open" else w.min())
    a, b2 = ("erode (min)", "dilate (max)") if op == "open" else ("dilate (max)", "erode (min)")
    s.append(step(f"2. {'Opening' if op == 'open' else 'Closing'} = first {a}, then {b2}",
                  [f"after the first step, the {k} × {k} square around this pixel is shown",
                   f"second step takes the {'biggest' if op == 'open' else 'smallest'} = {v}",
                   "Opening removes small bright specks. Closing fills small dark holes."],
                  [grid(f"after {a.split()[0]}", w, (k // 2, k // 2))] if show else []))
    return s, [v]


def ex_fft(img, out, F, x, y):
    mode, radius = F.s("mode", "spectrum"), F("radius", 30)
    g = dip.to_gray(img).astype(np.float32)
    rows, cols = g.shape
    Fs = np.fft.fftshift(np.fft.fft2(g))
    u, v = x - cols // 2, y - rows // 2
    s = [step("1. Fourier transform of the gray picture",
              [f"F(u, v) = Σx Σy f(x, y) × e^(−2πi(ux/{cols} + vy/{rows}))",
               "It rewrites the picture as a sum of waves. fftshift puts the slow waves",
               "(low frequency) in the centre and the fast ones (fine detail) outside.",
               f"F(0, 0) = sum of all gray values = {np.abs(np.fft.fft2(g)[0, 0]):.0f}  (the average brightness)"])]
    if mode == "spectrum":
        val = abs(Fs[y, x])
        lg = math.log1p(val)
        allm = np.log1p(np.abs(Fs))
        nl, res = normalize_lines(allm, lg, "log value")
        s.append(step("2. This spot of the spectrum",
                      [f"this pixel is frequency (u, v) = ({u}, {v}) from the centre",
                       f"|F| = {val:.2f}", f"log(1 + |F|) = {lg:.4f}  (log so small waves are visible too)"]))
        s.append(step("3. Make it fit in 0 ... 255", nl))
        return s, [res]
    dist = np.sqrt((np.arange(rows)[:, None] - rows / 2) ** 2 + (np.arange(cols)[None, :] - cols / 2) ** 2)
    mask = dist <= radius
    if mode == "high":
        mask = ~mask
    back = np.real(np.fft.ifft2(np.fft.ifftshift(Fs * mask)))
    val = float(back[y, x])
    s.append(step(f"2. {'Low' if mode == 'low' else 'High'}-pass mask, radius {f(radius)}",
                  [f"keep frequencies {'inside' if mode == 'low' else 'outside'} a circle of radius {f(radius)} around the centre",
                   f"kept {int(mask.sum())} of {mask.size} frequencies ({100 * mask.mean():.2f}%), the rest are set to 0"]))
    s.append(step("3. Inverse Fourier transform back to a picture",
                  [f"at this pixel the waves add up to {val:.3f}", f"original gray here was {int(dip.to_gray(img)[y, x])}"]))
    if mode == "low":
        res = int(np.clip(val, 0, 255))
        s.append(step("4. Keep it in 0 ... 255", [f"{val:.3f} → {res}"]))
    else:
        nl, res = normalize_lines(np.abs(back), abs(val), "|value|")
        s.append(step("4. Take the size and stretch to 0 ... 255", [f"|{val:.3f}| = {abs(val):.3f}"] + nl))
    return s, [res]


# ------------------------------------------------------------------ COMPARE

def ex_match(img, out, F, x, y, ref=None):
    if ref is None:
        return [step("Upload a reference picture first")], None
    lines, res = [], []
    for n, i in CH:
        src, tpl = img[:, :, i].ravel(), ref[:, :, i].ravel()
        v = int(img[y, x, i])
        sv, sc = np.unique(src, return_counts=True)
        tv, tc = np.unique(tpl, return_counts=True)
        sq, tq = np.cumsum(sc) / src.size, np.cumsum(tc) / tpl.size
        q = float(sq[np.searchsorted(sv, v)])
        m = float(np.interp(q, tq, tv))
        r = int(np.clip(m, 0, 255))
        res.append(r)
        lines += [f"{n}: {v} → {100 * q:.2f}% of your picture's {n} values are ≤ {v}",
                  f"   the reference reaches {100 * q:.2f}% at value {m:.3f} → {r}"]
    return [step("Histogram matching: keep each pixel's RANK, borrow the reference's values",
                 ["For each channel, find what share of the picture is this dark or darker,",
                  "then find the value in the reference picture with the same share."]),
            step("For each colour channel", lines)], res


def ex_compare(img, out, F, x, y, ref=None):
    if ref is None:
        return [step("Upload a reference picture first")], None
    tol = F("tol", 5)
    g1, l1 = gray_of(img, x, y)
    ref2 = cv2.resize(ref, (img.shape[1], img.shape[0]))
    g2, l2 = gray_of(ref2, x, y)
    d = abs(g1 - g2)
    res = 255 if d <= tol else 0
    return [step("1. Your picture, gray", l1),
            step("2. The reference (resized to the same size), gray", l2),
            step("3. Compare", [f"difference = |{g1} − {g2}| = {d}",
                                f"{d} ≤ tolerance {f(tol)} ?  " + ("yes → similar → white (255)" if d <= tol else "no → different → black (0)")])], [res]


# ------------------------------------------------------------------ main

class Settings:
    def __init__(self, form):
        self.form = form

    def __call__(self, key, default):
        return float(self.form.get(key, default))

    def s(self, key, default):
        return self.form.get(key, default)


def explain(tool, img, out, form, ref, x, y):
    """Returns (steps, our_result, real_result) for pixel (x, y) of the RESULT picture."""
    fn = globals().get("ex_" + tool)
    real = [v for _, v in px(out, x, y)]
    if fn is None:
        return [], None, real
    F = Settings(form)
    same = out.shape[:2] == img.shape[:2]
    if not same and tool not in ("crop", "resize", "rotate"):
        return [step("The picture changed size, so pixels can't be lined up one to one.")], None, real
    try:
        if tool in ("match", "compare"):
            steps, mine = fn(img, out, F, x, y, ref=ref)
        else:
            steps, mine = fn(img, out, F, x, y)
    except Exception as e:                      # never break the page because of the explanation
        return [step("Could not work out the details for this pixel", [str(e)])], None, real
    return steps, mine, real
