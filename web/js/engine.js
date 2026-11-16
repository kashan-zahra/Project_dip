// Image Lab - image engines. The page talks to images only through IMG, so the same
// interface works with two different engines:
//
//   BrowserEngine  the website and the Android app: OpenCV.js runs in the browser (js/processing.js)
//   PythonEngine   the Flask version: every image is sent to app.py and processed by processing.py
//
// The Flask server sets window.IMAGE_LAB_SERVER = true, which switches to the Python engine.

const SERVER_MODE = !!window.IMAGE_LAB_SERVER;
let engineOn = false;        // true once images can be processed
let cv = null;               // OpenCV.js (browser engine only)

function loadImg(url) {
    return new Promise((resolve, reject) => {
        const im = new Image();
        im.onload = () => resolve(im);
        im.onerror = reject;
        im.src = url;
    });
}

// ======================================================================
// Browser engine: images are cv.Mat objects (3-channel RGB)
// ======================================================================
const BrowserEngine = {
    name: "browser",

    // open a picture file: at most 1000 px (same as shrink() in app.py), always RGB
    async fromFile(file) {
        const url = URL.createObjectURL(file);
        try {
            const im = await loadImg(url);
            const W = im.naturalWidth, H = im.naturalHeight;
            if (!W || !H) throw new Error("empty image");
            const s = Math.min(1, 1000 / Math.max(W, H));
            const c = document.createElement("canvas");
            c.width = Math.max(1, Math.round(W * s));
            c.height = Math.max(1, Math.round(H * s));
            const ctx = c.getContext("2d", { willReadFrequently: true });
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = "high";
            ctx.drawImage(im, 0, 0, c.width, c.height);
            const rgba = cv.matFromImageData(ctx.getImageData(0, 0, c.width, c.height));
            const m = BrowserEngine.normalize(rgba);
            rgba.delete();
            return m;
        } finally {
            URL.revokeObjectURL(url);
        }
    },

    // always 3-channel RGB, never bigger than 1000 px
    normalize(m) {
        let rgb = new cv.Mat();
        if (m.channels() === 4) cv.cvtColor(m, rgb, cv.COLOR_RGBA2RGB);
        else if (m.channels() === 1) cv.cvtColor(m, rgb, cv.COLOR_GRAY2RGB);
        else m.copyTo(rgb);
        const limit = 1000, h = rgb.rows, w = rgb.cols;
        if (Math.max(h, w) > limit) {
            const s = limit / Math.max(h, w), small = new cv.Mat();
            cv.resize(rgb, small, new cv.Size(0, 0), s, s, cv.INTER_AREA);
            rgb.delete();
            rgb = small;
        }
        return rgb;
    },

    copy(m) { const o = new cv.Mat(); m.copyTo(o); return o; },     // Mat.clone() shares memory in OpenCV.js 5
    free(m) { if (m && !m.isDeleted()) m.delete(); },
    keep(result) { return BrowserEngine.normalize(result); },       // a result becomes the next starting image

    _canvas: document.createElement("canvas"),
    encode(m) {
        cv.imshow(BrowserEngine._canvas, m);
        return BrowserEngine._canvas.toDataURL("image/png");
    },

    // run one tool. base = what the Before side shows (last step or original)
    async process(cur, base, tool, form, ref) {
        const [out, note] = DIP.runTool(cur, tool, form, ref);
        return {
            result: out,
            data: {
                original: BrowserEngine.encode(base),
                result: BrowserEngine.encode(out),
                note: note,
                size_original: `${base.cols} x ${base.rows}`,
                size_result: `${out.cols} x ${out.rows}`,
                hist_original: DIP.histogram(base),
                hist_result: DIP.histogram(out),
                stats_original: DIP.stats(base),
                stats_result: DIP.stats(out),
            },
        };
    },
};

// ======================================================================
// Python engine: images are PNG/JPEG Blobs, processing happens in app.py
// ======================================================================
const dataUrlToBlob = async url => (await fetch(url)).blob();

const PythonEngine = {
    name: "python",

    async post(fields) {
        const fd = new FormData();
        Object.entries(fields).forEach(([k, v]) => { if (v !== null && v !== undefined) fd.append(k, v); });
        let res;
        try {
            res = await fetch("/process", { method: "POST", body: fd });
        } catch (err) {
            throw new Error("Could not reach the Python server. Is app.py still running?");
        }
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        return data;
    },

    // the server shrinks the picture once (shrink() in app.py); we keep the small PNG it sends back
    async fromFile(file) {
        const data = await PythonEngine.post({ image: file, tool: "none" });
        return dataUrlToBlob(data.original);
    },

    copy(b) { return b; },        // Blobs never change, so sharing them is safe
    free() { },
    keep(result) { return result; },

    async process(cur, base, tool, form, ref) {
        const data = await PythonEngine.post(Object.assign({
            image: cur,
            base: base !== cur ? base : null,
            reference: ref,
            tool: tool,
        }, form));
        return { result: await dataUrlToBlob(data.result), data: data };
    },
};

const IMG = SERVER_MODE ? PythonEngine : BrowserEngine;

if (SERVER_MODE) {
    const small = document.querySelector(".brand small");
    if (small) small.textContent = "Digital Image Processing · running on Python";
}
