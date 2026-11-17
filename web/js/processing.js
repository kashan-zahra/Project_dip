// =====================================================================
//  processing.js  -  the JavaScript twin of processing.py + app.py
//  Every tool runs in the browser with OpenCV.js (the same OpenCV
//  library that Python's cv2 uses), so no server is needed.
//
//  Images are cv.Mat objects:
//    colour = CV_8UC3 in RGB order (Python uses BGR, we convert where
//             it matters so the results look the same)
//    gray   = CV_8UC1
// =====================================================================
(function (root) {
    "use strict";
    let cv = null;

    // ----------------------------------------------------------- helpers
    function isGray(m) { return m.channels() === 1; }

    // a real copy (Mat.clone() in OpenCV.js 5 shares memory with the original)
    function copy(m) {
        const out = new cv.Mat();
        m.copyTo(out);
        return out;
    }

    function toGray(img) {
        if (isGray(img)) return copy(img);
        const g = new cv.Mat();
        cv.cvtColor(img, g, cv.COLOR_RGB2GRAY);
        return g;
    }

    // build a new Mat of the same size/type and fill it from a function
    function mapPixels(img, fn) {
        const out = copy(img);
        const s = img.data, d = out.data;
        for (let i = 0; i < s.length; i++) d[i] = fn(s[i]);
        return out;
    }

    function lut(img, table) {
        const out = copy(img);
        const s = img.data, d = out.data;
        for (let i = 0; i < s.length; i++) d[i] = table[s[i]];
        return out;
    }

    // stretch any float array to 0-255 (cv2.normalize NORM_MINMAX + astype uint8)
    function floatToU8(arr, rows, cols) {
        let lo = Infinity, hi = -Infinity;
        for (let i = 0; i < arr.length; i++) {
            const v = arr[i];
            if (v < lo) lo = v;
            if (v > hi) hi = v;
        }
        const out = new cv.Mat(rows, cols, cv.CV_8UC1);
        const d = out.data;
        const span = hi - lo;
        for (let i = 0; i < arr.length; i++) {
            d[i] = span > 0 ? Math.floor((arr[i] - lo) / span * 255) : 0;
        }
        return out;
    }

    function makeOdd(k) { k = Math.trunc(k); return Math.floor(k / 2) * 2 + 1; }

    function clampU8(v) { return v < 0 ? 0 : v > 255 ? 255 : v; }

    // magnitude of two float Mats -> uint8 image
    function magnitudeU8(gx, gy) {
        const a = gx.data32F, b = gy.data32F;
        const m = new Float32Array(a.length);
        for (let i = 0; i < a.length; i++) m[i] = Math.sqrt(a[i] * a[i] + b[i] * b[i]);
        return floatToU8(m, gx.rows, gx.cols);
    }

    // =============================================================== ENHANCE
    function brightnessContrast(img, alpha, beta) {
        const out = new cv.Mat();
        cv.convertScaleAbs(img, out, alpha, beta);
        return out;
    }

    function gamma(img, g) {
        const t = new Uint8Array(256);
        for (let i = 0; i < 256; i++) t[i] = clampU8(Math.round(255 * Math.pow(i / 255, g)));
        return lut(img, t);
    }

    function negative(img) { return mapPixels(img, v => 255 - v); }

    function contrastStretch(img) {
        let lo = 255, hi = 0;
        const s = img.data;
        for (let i = 0; i < s.length; i++) { if (s[i] < lo) lo = s[i]; if (s[i] > hi) hi = s[i]; }
        if (hi === lo) return copy(img);
        return mapPixels(img, v => Math.floor((v - lo) / (hi - lo) * 255));
    }

    function histEqualize(img) {
        const g = toGray(img), out = new cv.Mat();
        cv.equalizeHist(g, out);
        g.delete();
        return out;
    }

    function clahe(img, clip, tile) {
        const g = toGray(img), out = new cv.Mat();
        const c = new cv.CLAHE(clip, new cv.Size(tile, tile));
        c.apply(g, out);
        c.delete(); g.delete();
        return out;
    }

    function logTransform(img, c) {
        const k = c * 255 / Math.log(256);
        return mapPixels(img, v => clampU8(Math.floor(k * Math.log1p(v))));
    }

    function bitPlane(img, bit) {
        const g = toGray(img);
        const out = mapPixels(g, v => ((v >> bit) & 1) * 255);
        g.delete();
        return out;
    }

    // ============================================================= TRANSFORM
    function crop(img, x, y, w, h) {
        const H = img.rows, W = img.cols;
        const x0 = Math.min(Math.trunc(W * x / 100), W - 1);
        const y0 = Math.min(Math.trunc(H * y / 100), H - 1);
        const x1 = Math.min(W, x0 + Math.max(1, Math.trunc(W * w / 100)));
        const y1 = Math.min(H, y0 + Math.max(1, Math.trunc(H * h / 100)));
        const roi = img.roi(new cv.Rect(x0, y0, x1 - x0, y1 - y0));
        const out = copy(roi);
        roi.delete();
        return out;
    }

    function resize(img, percent, interp) {
        const methods = { nearest: cv.INTER_NEAREST, linear: cv.INTER_LINEAR, cubic: cv.INTER_CUBIC };
        const nw = Math.max(1, Math.trunc(img.cols * percent / 100));
        const nh = Math.max(1, Math.trunc(img.rows * percent / 100));
        const out = new cv.Mat();
        cv.resize(img, out, new cv.Size(nw, nh), 0, 0, methods[interp]);
        return out;
    }

    function rotate(img, mode) {
        const codes = { cw: cv.ROTATE_90_CLOCKWISE, ccw: cv.ROTATE_90_COUNTERCLOCKWISE, "180": cv.ROTATE_180 };
        const out = new cv.Mat();
        cv.rotate(img, out, codes[mode]);
        return out;
    }

    function flip(img, mode) {
        const codes = { h: 1, v: 0, both: -1 };
        const out = new cv.Mat();
        cv.flip(img, out, codes[mode]);
        return out;
    }

    // =============================================================== FILTERS
    function meanFilter(img, k) {
        k = makeOdd(k);
        const out = new cv.Mat();
        cv.blur(img, out, new cv.Size(k, k));
        return out;
    }

    function gaussianFilter(img, k) {
        k = makeOdd(k);
        const out = new cv.Mat();
        cv.GaussianBlur(img, out, new cv.Size(k, k), 0);
        return out;
    }

    function medianFilter(img, k) {
        k = makeOdd(k);
        const out = new cv.Mat();
        cv.medianBlur(img, out, k);
        return out;
    }

    function bilateralFilter(img, sigma) {
        const out = new cv.Mat();
        cv.bilateralFilter(img, out, 9, sigma, sigma);
        return out;
    }

    // normal random numbers (Box-Muller), like np.random.normal
    // seeded random numbers (mulberry32): the same settings always give the same grain,
    // so the picture doesn't flicker every time it is redrawn
    function seededRandom(seed) {
        return () => {
            seed = (seed + 0x6D2B79F5) | 0;
            let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
            t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        };
    }

    function gaussianNoise(img, mean, std) {
        const rand = seededRandom(1);
        const randn = () => {                    // normal random numbers (Box-Muller)
            let u = 0;
            while (u === 0) u = rand();
            return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rand());
        };
        return mapPixels(img, v => clampU8(Math.trunc(v + mean + std * randn())));
    }

    // ================================================================= EDGES
    function sobel(img) {
        const g = toGray(img), gx = new cv.Mat(), gy = new cv.Mat();
        cv.Sobel(g, gx, cv.CV_32F, 1, 0, 3);
        cv.Sobel(g, gy, cv.CV_32F, 0, 1, 3);
        const out = magnitudeU8(gx, gy);
        g.delete(); gx.delete(); gy.delete();
        return out;
    }

    function kernelEdges(img, kx, ky, size) {
        const g = toGray(img), gx = new cv.Mat(), gy = new cv.Mat();
        const KX = cv.matFromArray(size, size, cv.CV_32F, kx);
        const KY = cv.matFromArray(size, size, cv.CV_32F, ky);
        cv.filter2D(g, gx, cv.CV_32F, KX);
        cv.filter2D(g, gy, cv.CV_32F, KY);
        const out = magnitudeU8(gx, gy);
        [g, gx, gy, KX, KY].forEach(m => m.delete());
        return out;
    }

    function prewitt(img) {
        return kernelEdges(img,
            [-1, 0, 1, -1, 0, 1, -1, 0, 1],
            [-1, -1, -1, 0, 0, 0, 1, 1, 1], 3);
    }

    function roberts(img) {
        return kernelEdges(img, [1, 0, 0, -1], [0, 1, -1, 0], 2);
    }

    function canny(img, low, high) {
        const g = toGray(img), out = new cv.Mat();
        cv.Canny(g, out, low, high);
        g.delete();
        return out;
    }

    function laplacian(img) {
        const g = toGray(img), lap = new cv.Mat();
        cv.Laplacian(g, lap, cv.CV_32F, 3);
        const a = lap.data32F, m = new Float32Array(a.length);
        for (let i = 0; i < a.length; i++) m[i] = Math.abs(a[i]);
        const out = floatToU8(m, lap.rows, lap.cols);
        g.delete(); lap.delete();
        return out;
    }

    // ================================================================= COLOR
    // RGB (0-255) -> H (degrees), S (0-1), I (0-255), one pixel at a time
    function rgbToHsiPixel(R, G, B) {
        const I = (R + G + B) / 3;
        const total = R + G + B;
        const S = total > 0 ? 1 - 3 * Math.min(R, G, B) / total : 0;
        const num = 0.5 * ((R - G) + (R - B));
        const den = Math.sqrt((R - G) * (R - G) + (R - B) * (G - B));
        let H = 0;
        if (den > 1e-10) {
            const theta = Math.acos(Math.max(-1, Math.min(1, num / den)));
            H = (B <= G ? theta : 2 * Math.PI - theta) * 180 / Math.PI;
        }
        return [H, S, I];
    }

    function hsiToRgbPixel(H, S, I) {
        const c60 = Math.PI / 3;
        let R, G, B, h;
        if (H < 120) {
            h = H * Math.PI / 180;
            B = I * (1 - S);
            R = I * (1 + S * Math.cos(h) / Math.cos(c60 - h));
            G = 3 * I - R - B;
        } else if (H < 240) {
            h = (H - 120) * Math.PI / 180;
            R = I * (1 - S);
            G = I * (1 + S * Math.cos(h) / Math.cos(c60 - h));
            B = 3 * I - R - G;
        } else {
            h = (H - 240) * Math.PI / 180;
            G = I * (1 - S);
            B = I * (1 + S * Math.cos(h) / Math.cos(c60 - h));
            R = 3 * I - G - B;
        }
        return [clampU8(Math.round(R)), clampU8(Math.round(G)), clampU8(Math.round(B))];
    }

    function asColor(img) {
        if (!isGray(img)) return copy(img);
        const out = new cv.Mat();
        cv.cvtColor(img, out, cv.COLOR_GRAY2RGB);
        return out;
    }

    function hsiComponent(img, which) {
        const c = asColor(img);
        const s = c.data, n = c.rows * c.cols;
        let out;
        if (which === "h") {
            // show hue as real colours (full saturation and brightness)
            const hsv = new cv.Mat(c.rows, c.cols, cv.CV_8UC3);
            const d = hsv.data;
            for (let p = 0; p < n; p++) {
                const H = rgbToHsiPixel(s[3 * p], s[3 * p + 1], s[3 * p + 2])[0];
                d[3 * p] = Math.min(179, Math.max(0, Math.trunc(H / 2)));
                d[3 * p + 1] = 255;
                d[3 * p + 2] = 255;
            }
            out = new cv.Mat();
            cv.cvtColor(hsv, out, cv.COLOR_HSV2RGB);
            hsv.delete();
        } else {
            out = new cv.Mat(c.rows, c.cols, cv.CV_8UC1);
            const d = out.data;
            for (let p = 0; p < n; p++) {
                const hsi = rgbToHsiPixel(s[3 * p], s[3 * p + 1], s[3 * p + 2]);
                d[p] = which === "s" ? clampU8(Math.trunc(hsi[1] * 255)) : clampU8(Math.trunc(hsi[2]));
            }
        }
        c.delete();
        return out;
    }

    function hsiRoundtrip(img) {
        const c = asColor(img);
        const out = copy(c);
        const s = c.data, d = out.data, n = c.rows * c.cols;
        for (let p = 0; p < n; p++) {
            const hsi = rgbToHsiPixel(s[3 * p], s[3 * p + 1], s[3 * p + 2]);
            const rgb = hsiToRgbPixel(hsi[0], hsi[1], hsi[2]);
            d[3 * p] = rgb[0]; d[3 * p + 1] = rgb[1]; d[3 * p + 2] = rgb[2];
        }
        c.delete();
        return out;
    }

    const SPACES = {
        gray: [null, ["Gray"]],
        hsv: ["COLOR_RGB2HSV", ["H", "S", "V"]],
        lab: ["COLOR_RGB2Lab", ["L", "a", "b"]],
        ycrcb: ["COLOR_RGB2YCrCb", ["Y", "Cr", "Cb"]],
    };

    function colorSpace(img, space, channel) {
        const [codeName, names] = SPACES[space];
        if (codeName === null) return [toGray(img), names];
        const c = asColor(img), conv = new cv.Mat();
        cv.cvtColor(c, conv, cv[codeName]);
        c.delete();
        if (channel === 0) {
            // Python shows the 3 channels as if they were B, G, R.
            // Swap 1 and 3 so it looks the same on an RGB screen.
            const out = new cv.Mat();
            cv.cvtColor(conv, out, cv.COLOR_BGR2RGB);
            conv.delete();
            return [out, names];
        }
        const out = extractChannel(conv, channel - 1);
        conv.delete();
        return [out, names];
    }

    function extractChannel(m, idx) {
        const out = new cv.Mat(m.rows, m.cols, cv.CV_8UC1);
        const s = m.data, d = out.data, ch = m.channels();
        for (let p = 0; p < d.length; p++) d[p] = s[p * ch + idx];
        return out;
    }

    function rgbChannel(img, which) {
        if (isGray(img)) return copy(img);
        return extractChannel(img, { r: 0, g: 1, b: 2 }[which]);
    }

    // ================================================================ PIXELS
    function sample(img, size) {
        const h = img.rows, w = img.cols;
        const scale = size / Math.max(h, w);
        const sw = Math.max(1, Math.trunc(w * scale));
        const sh = Math.max(1, Math.trunc(h * scale));
        const small = new cv.Mat(), big = new cv.Mat();
        cv.resize(img, small, new cv.Size(sw, sh), 0, 0, cv.INTER_NEAREST);
        cv.resize(small, big, new cv.Size(w, h), 0, 0, cv.INTER_NEAREST);
        small.delete();
        return [big, sw, sh];
    }

    function quantize(img, bits) {
        const levels = Math.pow(2, bits);
        const step = 256 / levels;
        // Python's np.round is "round half to even"
        const roundEven = x => {
            const r = Math.round(x);
            return (Math.abs(x % 1) === 0.5 && r % 2 !== 0) ? r - 1 : r;
        };
        const t = new Uint8Array(256);
        for (let v = 0; v < 256; v++) {
            const q = Math.floor(v / step);
            t[v] = levels > 1 ? clampU8(roundEven(q * 255 / (levels - 1))) : 0;
        }
        return lut(img, t);
    }

    function components(img, thresh, connectivity) {
        const g = toGray(img), bin = new cv.Mat(), labels = new cv.Mat();
        cv.threshold(g, bin, thresh, 255, cv.THRESH_BINARY);
        const n = cv.connectedComponents(bin, labels, connectivity, cv.CV_32S);
        // fixed random colours (seeded), background stays black
        let seed = 1;
        const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
        const colors = new Uint8Array(n * 3);
        for (let i = 3; i < n * 3; i++) colors[i] = 60 + Math.floor(rnd() * 195);
        const out = new cv.Mat(g.rows, g.cols, cv.CV_8UC3);
        const L = labels.data32S, d = out.data;
        for (let p = 0; p < L.length; p++) {
            const c = L[p] * 3;
            d[3 * p] = colors[c]; d[3 * p + 1] = colors[c + 1]; d[3 * p + 2] = colors[c + 2];
        }
        g.delete(); bin.delete(); labels.delete();
        return [out, n - 1];
    }

    // =========================================================== SEGMENTATION
    function threshold(img, mode, t) {
        const g = toGray(img), out = new cv.Mat();
        let used = null;
        if (mode === "global") {
            cv.threshold(g, out, Math.trunc(t), 255, cv.THRESH_BINARY);
            used = Math.trunc(t);
        } else if (mode === "mean") {
            cv.adaptiveThreshold(g, out, 255, cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY, 11, 2);
        } else if (mode === "gaussian") {
            cv.adaptiveThreshold(g, out, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 11, 2);
        } else {
            used = cv.threshold(g, out, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU);
        }
        g.delete();
        return [out, used];
    }

    function kmeans(img, k) {
        const c = asColor(img);
        const n = c.rows * c.cols, s = c.data;
        // Learn the K colours from up to 60,000 pixels (keeps phones fast),
        // then paint every pixel with its nearest colour.
        const stepN = Math.max(1, Math.floor(n / 60000));
        const m = Math.ceil(n / stepN);
        const data = new cv.Mat(m, 3, cv.CV_32F);
        const f = data.data32F;
        for (let i = 0, p = 0; i < m; i++, p += stepN) {
            f[3 * i] = s[3 * p]; f[3 * i + 1] = s[3 * p + 1]; f[3 * i + 2] = s[3 * p + 2];
        }
        const labels = new cv.Mat(), centers = new cv.Mat();
        const crit = new cv.TermCriteria(cv.TermCriteria_EPS + cv.TermCriteria_MAX_ITER, 50, 0.5);
        cv.kmeans(data, k, labels, crit, 3, cv.KMEANS_PP_CENTERS, centers);
        const C = centers.data32F;
        const out = copy(c), d = out.data;
        const cu = Array.from(C, v => clampU8(Math.trunc(v)));
        for (let p = 0; p < n; p++) {
            const r = s[3 * p], g = s[3 * p + 1], b = s[3 * p + 2];
            let best = 0, bd = Infinity;
            for (let j = 0; j < k; j++) {
                const dr = r - C[3 * j], dg = g - C[3 * j + 1], db = b - C[3 * j + 2];
                const dist = dr * dr + dg * dg + db * db;
                if (dist < bd) { bd = dist; best = j; }
            }
            d[3 * p] = cu[3 * best]; d[3 * p + 1] = cu[3 * best + 1]; d[3 * p + 2] = cu[3 * best + 2];
        }
        [c, data, labels, centers].forEach(x => x.delete());
        return out;
    }

    // ============================================================ MORPHOLOGY
    function morph(img, op, size) {
        const g = toGray(img), out = new cv.Mat();
        const k = makeOdd(size);
        const kernel = cv.Mat.ones(k, k, cv.CV_8U);
        const anchor = new cv.Point(-1, -1);
        if (op === "erode") cv.erode(g, out, kernel, anchor, 1, cv.BORDER_CONSTANT, cv.morphologyDefaultBorderValue());
        else if (op === "dilate") cv.dilate(g, out, kernel, anchor, 1, cv.BORDER_CONSTANT, cv.morphologyDefaultBorderValue());
        else cv.morphologyEx(g, out, op === "open" ? cv.MORPH_OPEN : cv.MORPH_CLOSE, kernel, anchor, 1,
            cv.BORDER_CONSTANT, cv.morphologyDefaultBorderValue());
        g.delete(); kernel.delete();
        return out;
    }

    // ====================================================== FREQUENCY DOMAIN
    function fftTool(img, mode, radius) {
        const g = toGray(img), gf = new cv.Mat(), F = new cv.Mat();
        g.convertTo(gf, cv.CV_32F);
        cv.dft(gf, F, cv.DFT_COMPLEX_OUTPUT);
        const rows = g.rows, cols = g.cols, R2 = Math.floor(rows / 2), C2 = Math.floor(cols / 2);
        const z = F.data32F;

        if (mode === "spectrum") {
            // log magnitude, moved so the centre holds the low frequencies
            const mag = new Float32Array(rows * cols);
            for (let y = 0; y < rows; y++) {
                const sy = (y + R2) % rows;
                for (let x = 0; x < cols; x++) {
                    const i = 2 * (y * cols + x);
                    const sx = (x + C2) % cols;
                    mag[sy * cols + sx] = Math.log1p(Math.hypot(z[i], z[i + 1]));
                }
            }
            [g, gf, F].forEach(m => m.delete());
            return floatToU8(mag, rows, cols);
        }

        // keep frequencies inside (low-pass) or outside (high-pass) the circle
        for (let y = 0; y < rows; y++) {
            const dy = (y + R2) % rows - rows / 2;
            for (let x = 0; x < cols; x++) {
                const dx = (x + C2) % cols - cols / 2;
                const inside = Math.sqrt(dy * dy + dx * dx) <= radius;
                const keep = mode === "high" ? !inside : inside;
                if (!keep) { const i = 2 * (y * cols + x); z[i] = 0; z[i + 1] = 0; }
            }
        }
        const back = new cv.Mat();
        cv.dft(F, back, cv.DFT_INVERSE | cv.DFT_SCALE);
        const b = back.data32F, n = rows * cols;
        let out;
        if (mode === "high") {
            const m = new Float32Array(n);
            for (let p = 0; p < n; p++) m[p] = Math.abs(b[2 * p]);
            out = floatToU8(m, rows, cols);
        } else {
            out = new cv.Mat(rows, cols, cv.CV_8UC1);
            const d = out.data;
            for (let p = 0; p < n; p++) d[p] = clampU8(Math.trunc(b[2 * p]));
        }
        [g, gf, F, back].forEach(m => m.delete());
        return out;
    }

    // =============================================================== COMPARE
    // same idea as skimage.exposure.match_histograms, one channel at a time
    function matchChannel(src, tmpl) {
        const sc = new Float64Array(256), tc = new Float64Array(256);
        for (let i = 0; i < src.length; i++) sc[src[i]]++;
        for (let i = 0; i < tmpl.length; i++) tc[tmpl[i]]++;
        // template quantiles at the values that really appear
        const tv = [], tq = [];
        let acc = 0;
        for (let v = 0; v < 256; v++) if (tc[v]) { acc += tc[v]; tv.push(v); tq.push(acc / tmpl.length); }
        const map = new Uint8Array(256);
        acc = 0;
        for (let v = 0; v < 256; v++) {
            if (!sc[v]) continue;
            acc += sc[v];
            const q = acc / src.length;
            // np.interp(q, tq, tv)
            let val;
            if (q <= tq[0]) val = tv[0];
            else if (q >= tq[tq.length - 1]) val = tv[tv.length - 1];
            else {
                let j = 1;
                while (tq[j] < q) j++;
                const t = (q - tq[j - 1]) / (tq[j] - tq[j - 1]);
                val = tv[j - 1] + t * (tv[j] - tv[j - 1]);
            }
            map[v] = clampU8(Math.trunc(val));
        }
        return map;
    }

    function matchHist(img, ref) {
        const a = asColor(img), b = asColor(ref);
        const out = copy(a);
        const n = a.rows * a.cols, m = b.rows * b.cols;
        for (let c = 0; c < 3; c++) {
            const src = new Uint8Array(n), tm = new Uint8Array(m);
            for (let p = 0; p < n; p++) src[p] = a.data[3 * p + c];
            for (let p = 0; p < m; p++) tm[p] = b.data[3 * p + c];
            const map = matchChannel(src, tm);
            for (let p = 0; p < n; p++) out.data[3 * p + c] = map[src[p]];
        }
        a.delete(); b.delete();
        return out;
    }

    function compare(img, ref, tol) {
        const r2 = new cv.Mat();
        cv.resize(ref, r2, new cv.Size(img.cols, img.rows));
        const g1 = toGray(img), g2 = toGray(r2);
        const out = new cv.Mat(img.rows, img.cols, cv.CV_8UC1);
        const a = g1.data, b = g2.data, d = out.data;
        let same = 0;
        for (let i = 0; i < a.length; i++) {
            const ok = Math.abs(a[i] - b[i]) <= tol;
            d[i] = ok ? 255 : 0;
            if (ok) same++;
        }
        [r2, g1, g2].forEach(m => m.delete());
        return [out, same / a.length * 100];
    }

    // ============================================================== ANALYSIS
    function histogram(img) {
        const g = toGray(img);
        const h = new Array(256).fill(0);
        const d = g.data;
        for (let i = 0; i < d.length; i++) h[d[i]]++;
        g.delete();
        return h;
    }

    const r2 = (v, n) => Math.round(v * Math.pow(10, n)) / Math.pow(10, n);

    function stats(img) {
        const g = toGray(img), d = g.data;
        let lo = 255, hi = 0, sum = 0;
        for (let i = 0; i < d.length; i++) { const v = d[i]; if (v < lo) lo = v; if (v > hi) hi = v; sum += v; }
        const mean = sum / d.length;
        let sq = 0;
        for (let i = 0; i < d.length; i++) sq += (d[i] - mean) * (d[i] - mean);
        g.delete();
        const mich = (hi + lo) > 0 ? (hi - lo) / (hi + lo) : 0;
        return {
            min: lo, max: hi, mean: r2(mean, 2), range: hi - lo,
            michelson: r2(mich, 4), rms: r2(Math.sqrt(sq / d.length), 2)
        };
    }

    function maeMse(a, b) {
        const x = a.data, y = b.data;
        let s = 0, s2 = 0, mx = 0;
        for (let i = 0; i < x.length; i++) {
            const e = Math.abs(x[i] - y[i]);
            s += e; s2 += e * e; if (e > mx) mx = e;
        }
        return [s / x.length, s2 / x.length, mx];
    }

    // ========================================================= run_tool (app.py)
    // Returns [resultMat, noteText]
    function runTool(img, tool, f, ref) {
        const num = (k, d) => (f[k] !== undefined ? parseFloat(f[k]) : d);
        const str = (k, d) => (f[k] !== undefined ? f[k] : d);
        const fmt = v => String(+v);

        switch (tool) {
            // ---------- Enhance ----------
            case "brightness_contrast": return [brightnessContrast(img, num("alpha", 1), num("beta", 0)), ""];
            case "gamma": {
                const g = num("gamma", 1);
                const note = g < 1 ? `gamma = ${fmt(g)} (below 1): dark areas get brighter.`
                    : g > 1 ? `gamma = ${fmt(g)} (above 1): the image gets darker.`
                        : "gamma = 1, so the image is unchanged.";
                return [gamma(img, g), note];
            }
            case "negative": return [negative(img), ""];
            case "stretch": return [contrastStretch(img), ""];
            case "equalize": return [histEqualize(img), ""];
            case "clahe": return [clahe(img, num("clip", 2), Math.trunc(num("tile", 8))), ""];

            // ---------- Transform ----------
            case "crop": return [crop(img, num("x", 0), num("y", 0), num("w", 50), num("h", 50)), ""];
            case "resize": return [resize(img, num("percent", 50), str("interp", "linear")), ""];
            case "rotate": return [rotate(img, str("mode", "cw")), ""];
            case "flip": return [flip(img, str("mode", "h")), ""];

            // ---------- Filters ----------
            case "mean": return [meanFilter(img, num("size", 5)), ""];
            case "gaussian": return [gaussianFilter(img, num("size", 5)), ""];
            case "median": return [medianFilter(img, num("size", 5)), ""];
            case "bilateral": return [bilateralFilter(img, num("sigma", 75)), ""];
            case "noise": return [gaussianNoise(img, num("mean", 0), num("std", 20)), ""];

            // ---------- Edges ----------
            case "sobel": return [sobel(img), ""];
            case "prewitt": return [prewitt(img), ""];
            case "roberts": return [roberts(img), ""];
            case "canny": return [canny(img, num("low", 100), num("high", 200)), ""];

            // ---------- Color ----------
            case "hsi_component": return [hsiComponent(img, str("which", "h")), ""];
            case "hsi_roundtrip": {
                const out = hsiRoundtrip(img);
                const c = asColor(img);
                const [mae, mse, mx] = maeMse(c, out);
                c.delete();
                return [out, `RGB to HSI to RGB again. Reconstruction error: MAE = ${mae.toFixed(4)}, ` +
                    `MSE = ${mse.toFixed(4)}, max error = ${mx.toFixed(0)}. A tiny error means the conversion is correct.`];
            }
            case "colorspace": {
                const space = str("space", "hsv");
                const ch = Math.trunc(num("channel", 0));
                const [out, names] = colorSpace(img, space, ch);
                let note;
                if (space === "gray") note = "Gray = 0.299 R + 0.587 G + 0.114 B. One channel instead of three.";
                else if (ch === 0) note = `Channels are ${names.join(", ")}. All three are shown together, ` +
                    "so the colors look strange. Pick one channel to see it alone.";
                else {
                    const label = { hsv: "HSV", lab: "LAB", ycrcb: "YCrCb" }[space];
                    note = `Showing channel ${names[ch - 1]} of ${label} as a gray image.`;
                }
                return [out, note];
            }
            case "channel": return [rgbChannel(img, str("which", "r")), ""];

            // ---------- Pixels ----------
            case "sample": {
                const [out, sw, sh] = sample(img, num("size", 32));
                return [out, `The image was sampled down to ${sw} x ${sh} pixels, then enlarged back. ` +
                    "Fewer samples means bigger blocks and less detail."];
            }
            case "quantize": {
                const bits = Math.trunc(num("bits", 3));
                return [quantize(img, bits), `${bits} bits per channel = ${Math.pow(2, bits)} intensity levels. ` +
                    "Fewer levels means visible bands (false contours)."];
            }
            case "components": {
                const conn = Math.trunc(num("connectivity", 8));
                const [out, n] = components(img, num("thresh", 128), conn);
                return [out, `Found ${n} separate regions using ${conn}-connectivity. ` +
                    "Each color is one connected group of white pixels."];
            }

            // ---------- Compare ----------
            case "match":
            case "compare": {
                if (!ref) return [copy(img), "Upload a reference image (the box on the left) to use this tool."];
                if (tool === "match") return [matchHist(img, ref),
                    "The result's histogram now follows the reference image's histogram."];
                const [out, pct] = compare(img, ref, num("tol", 5));
                return [out, `${pct.toFixed(2)}% of the pixels are similar (white). The rest are different (black).`];
            }

            // ---------- More tools ----------
            case "log": return [logTransform(img, num("c", 1)),
                "s = c * log(1 + r): brightens dark areas, compresses bright ones."];
            case "bitplane": {
                const bit = Math.trunc(num("bit", 7));
                return [bitPlane(img, bit), `Showing bit ${bit}. Bit 7 (MSB) carries most of the picture, bit 0 (LSB) looks like noise.`];
            }
            case "laplacian": return [laplacian(img),
                "Laplacian uses the second derivative, so it responds to edges in all directions."];
            case "threshold": {
                const [out, t] = threshold(img, str("mode", "otsu"), num("t", 128));
                return [out, t === null ? "Adaptive: each pixel is compared with its local neighborhood."
                    : `Threshold used: ${fmt(t)}. Pixels above it become white, the rest black.`];
            }
            case "kmeans": {
                const k = Math.trunc(num("k", 3));
                return [kmeans(img, k), `K-Means grouped all pixel colors into ${k} clusters and painted each pixel with its cluster color.`];
            }
            case "morph": return [morph(img, str("op", "erode"), num("size", 3)),
                "Erosion shrinks bright areas, dilation grows them. Opening = erode then dilate. Closing = dilate then erode."];
            case "fft": {
                const mode = str("mode", "spectrum");
                const notes = {
                    spectrum: "Fourier spectrum (log scaled). Center = low frequencies, outside = high frequencies.",
                    low: "Low-pass: only low frequencies kept, so the image is smoothed.",
                    high: "High-pass: only high frequencies kept, so only edges and details remain."
                };
                return [fftTool(img, mode, num("radius", 30)), notes[mode]];
            }
        }
        return [copy(img), ""];
    }

    root.DIP = {
        init(c) { cv = c; },
        runTool, histogram, stats,
    };
})(typeof window !== "undefined" ? window : globalThis);
