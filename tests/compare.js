// Step 2 of the parity test: run the same tools with the JavaScript port (web/js/processing.js)
// and compare every pixel with the Python results.
//
//   npm install @techstark/opencv-js
//   node tests/compare.js
const fs = require("fs");
const path = require("path");
require(path.join(__dirname, "..", "web", "js", "processing.js"));

(async () => {
    let cv = require("@techstark/opencv-js");
    if (cv instanceof Promise) cv = await cv;
    else if (!cv.Mat) await new Promise(r => (cv.onRuntimeInitialized = r));
    DIP.init(cv);

    const out = path.join(__dirname, "out");
    const py = JSON.parse(fs.readFileSync(path.join(out, "py.json")));
    const load = f => {
        const m = new cv.Mat(py.h, py.w, cv.CV_8UC3);
        m.data.set(fs.readFileSync(path.join(out, f)));
        return m;
    };
    const img = load("in.rgb"), ref = load("ref.rgb");
    const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "cases.json")));
    let exact = 0;

    cases.forEach(([tool, form], i) => {
        const [res, note] = DIP.runTool(img, tool, form, ref);
        const shape = res.channels() === 1 ? [res.rows, res.cols] : [res.rows, res.cols, 3];
        const a = fs.readFileSync(path.join(out, `py${i}.raw`)), b = res.data;
        let line;
        if (JSON.stringify(shape) !== JSON.stringify(py.cases[i].shape)) {
            line = `shape differs ${shape} vs ${py.cases[i].shape}`;
        } else {
            let mx = 0, off = 0;
            for (let k = 0; k < a.length; k++) {
                const e = Math.abs(a[k] - b[k]);
                if (e > mx) mx = e;
                if (e > 1) off++;
            }
            if (mx <= 1) exact++;
            line = `max difference ${mx}, pixels off by more than 1: ${(off / a.length * 100).toFixed(2)}%`;
        }
        const noteOk = note === py.cases[i].note ? "" : "  (note text differs)";
        console.log(`${tool.padEnd(20)} ${JSON.stringify(form).padEnd(40)} ${line}${noteOk}`);
        res.delete();
    });
    console.log(`\n${exact} of ${cases.length} cases match the Python version within 1 gray level.`);
})();
