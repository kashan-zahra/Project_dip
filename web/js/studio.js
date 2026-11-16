// Image Lab - the studio: opening images, running tools, history (Keep / Undo), Lab Data, pixel inspector.

// ============ STATE ============
const CATEGORIES = [...new Set(Object.values(TOOLS).map(t => t.group))];
let currentCategory = CATEGORIES[0];
let currentTool = null;      // nothing picked at the start
let originalMat = null;      // the image the user opened (cv.Mat, RGB)
let steps = [];              // history: [{ name, mat }], steps[0] is the original
let compareOriginal = false; // Before shows: false = last kept step, true = the original photo
let currentMat = null;       // the image we are working on now
let referenceMat = null;     // second image (for Compare tools)
let resultMat = null;        // last result (cv.Mat)
let lastResult = null;       // result picture (data URL)
let lastData = null;         // everything we computed last time
let cv = null;               // OpenCV.js, set when it has loaded
let viewMode = "split";      // split, before or after
let timer = null;
let requestId = 0;

const $ = id => document.getElementById(id);

// ============ TWO PAGES ============
function setPage(name) {
    const studio = name === "studio";
    $("viewStudio").classList.toggle("hidden", !studio);
    $("viewData").classList.toggle("hidden", studio);
    $("navStudio").classList.toggle("active", studio);
    $("navData").classList.toggle("active", !studio);
    document.documentElement.classList.toggle("on-data", !studio);
    if ($("tTitle")) $("tTitle").textContent = studio ? "Image Lab" : "Lab Data";
}
$("navStudio").onclick = () => setPage("studio");
$("navData").onclick = () => setPage("data");
$("goData").onclick = () => setPage("data");

// ============ UPLOAD (the big drop area) ============
const drop = $("drop");
drop.addEventListener("click", () => $("file").click());
$("newImage").addEventListener("click", () => $("file").click());
["file", "camFile"].forEach(id => $(id).addEventListener("change", () => {
    if ($(id).files[0]) newImage($(id).files[0]);
    $(id).value = "";
}));
drop.addEventListener("dragover", e => { e.preventDefault(); drop.classList.add("over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", e => {
    e.preventDefault();
    drop.classList.remove("over");
    const f = e.dataTransfer.files[0];
    if (f && f.type.startsWith("image/")) newImage(f);
    else toast("Please drop an image file.");
});

let waitingFile = null;      // picked before the engine finished loading

async function newImage(file) {
    if (!cv) {
        waitingFile = file;
        $("dropBig").textContent = "Got your image!";
        $("dropSub").textContent = "Still loading the image engine, it will open by itself in a moment...";
        return;
    }
    $("dropBig").textContent = "Opening image...";
    if (window.onOpeningImage) window.onOpeningImage();
    await nextFrame();
    let mat;
    try {
        mat = await fileToMat(file);
    } catch (err) {
        console.error(err);
        $("dropBig").textContent = "Drop an image here";
        toast("Could not read this image: " + (err && err.message ? err.message : err));
        return;
    }
    steps.forEach(st => free(st.mat));
    free(currentMat);
    steps = [{ name: "Original", mat: mat }];
    originalMat = mat;
    currentMat = copyMat(mat);
    currentTool = null;
    renderCrumbs();
    drop.classList.add("hidden");
    $("views").classList.remove("hidden");
    $("toolbar").classList.remove("hidden");
    $("geekLink").classList.remove("hidden");
    document.querySelector(".stage").classList.add("sticky");
    renderTools();
    buildControls();
    run();
}

// ============ IMAGE <-> cv.Mat (what app.py did with cv2) ============
function free(m) { if (m && !m.isDeleted()) m.delete(); }

function copyMat(m) { const o = new cv.Mat(); m.copyTo(o); return o; }

// always 3-channel RGB, and never bigger than 1000 px (same as shrink() in app.py)
function normalizeMat(m) {
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
}

function loadImg(url) {
    return new Promise((resolve, reject) => {
        const im = new Image();
        im.onload = () => resolve(im);
        im.onerror = reject;
        im.src = url;
    });
}

async function fileToMat(file) {
    const url = URL.createObjectURL(file);
    try {
        const im = await loadImg(url);
        const W = im.naturalWidth, H = im.naturalHeight;
        if (!W || !H) throw new Error("empty image");
        // big phone photos: shrink while drawing (same 1000 px limit as app.py)
        const s = Math.min(1, 1000 / Math.max(W, H));
        const c = document.createElement("canvas");
        c.width = Math.max(1, Math.round(W * s));
        c.height = Math.max(1, Math.round(H * s));
        const ctx = c.getContext("2d", { willReadFrequently: true });
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = "high";
        ctx.drawImage(im, 0, 0, c.width, c.height);
        const rgba = cv.matFromImageData(ctx.getImageData(0, 0, c.width, c.height));
        const m = normalizeMat(rgba);
        rgba.delete();
        return m;
    } finally {
        URL.revokeObjectURL(url);
    }
}

const encCanvas = document.createElement("canvas");
function encode(m) {
    cv.imshow(encCanvas, m);
    return encCanvas.toDataURL("image/png");
}

// ============ SAMPLE PHOTOS (free CC0 pictures in /samples) ============
async function loadSample(name) {
    try {
        const blob = await (await fetch(`samples/${name}.jpg`)).blob();
        newImage(new File([blob], name + ".jpg", { type: "image/jpeg" }));
    } catch (err) {
        toast("Could not open the sample photo.");
    }
}
document.querySelectorAll("[data-sample]").forEach(b => b.addEventListener("click", e => {
    e.stopPropagation();                     // don't open the file picker behind it
    loadSample(b.dataset.sample);
}));

// ============ REFERENCE IMAGE ============
$("refFile").addEventListener("change", () => {
    const f = $("refFile").files[0];
    if (!f) return;
    fileToMat(f).then(m => {
        free(referenceMat);
        referenceMat = m;
        schedule();
    }).catch(() => toast("Could not read this image"));
    const thumb = $("refThumb");
    thumb.src = URL.createObjectURL(f);
    thumb.classList.remove("hidden");
});

// ============ VIEW SWITCH: split / before / after ============
function setMode(mode) {
    viewMode = mode;
    document.querySelectorAll("#seg button").forEach(b => {
        b.classList.toggle("active", b.dataset.mode === mode);
    });
    $("views").classList.toggle("split", mode === "split");
    $("views").classList.toggle("compare", mode === "compare");
    $("paneBefore").classList.toggle("off", mode === "after");
    $("paneAfter").classList.toggle("off", mode === "before");
}
document.querySelectorAll("#seg button").forEach(b => {
    b.onclick = () => setMode(b.dataset.mode);
});

// ============ TABS AND TOOL BUTTONS ============
function renderTabs() {
    const box = $("tabs");
    box.innerHTML = "";
    CATEGORIES.forEach(cat => {
        const b = document.createElement("button");
        b.className = "tab" + (cat === currentCategory ? " active" : "");
        b.textContent = CAT_NAMES[cat] || cat;
        b.onclick = () => { currentCategory = cat; renderTabs(); renderTools(); };
        box.appendChild(b);
    });
}

function renderTools() {
    const box = $("toolList");
    box.innerHTML = "";
    Object.keys(TOOLS).forEach(key => {
        if (TOOLS[key].group !== currentCategory) return;
        const b = document.createElement("button");
        b.className = "tool" + (key === currentTool ? " active" : "");
        const t = TOOLS[key];
        b.innerHTML = `<span class="tl">${t.label}</span>` + (t.simple ? `<span class="ts2">${t.simple}</span>` : "");
        b.title = t.help || "";
        b.onclick = () => selectTool(key);
        box.appendChild(b);
    });
}

function selectTool(key) {
    currentTool = key;
    renderTools();
    buildControls();
    renderCrumbs();
    schedule();
}

// ============ SLIDERS AND DROPDOWNS ============
function buildControls() {
    const box = $("controls");
    const about = $("about");
    box.innerHTML = "";

    // show the reference box only for tools that need it
    const needsRef = currentTool && TOOLS[currentTool].needsRef;
    $("refCard").classList.toggle("hidden", !needsRef);

    if (!currentTool) {
        about.classList.add("hidden");
        box.innerHTML = '<div class="hint">Pick a tool to see its settings.</div>';
        return;
    }

    const tool = TOOLS[currentTool];
    about.innerHTML = "";
    const plain = document.createElement("div");
    plain.className = "plain";
    plain.textContent = tool.help || tool.info;
    about.appendChild(plain);
    if (tool.help) {
        const d = document.createElement("details");
        const sm = document.createElement("summary");
        sm.textContent = "For the curious: how it works";
        const f = document.createElement("div");
        f.textContent = tool.info;
        d.appendChild(sm);
        d.appendChild(f);
        about.appendChild(d);
    }
    if (window.LEARN && LEARN[currentTool]) {
        const lb = document.createElement("button");
        lb.className = "learnBtn";
        lb.textContent = "\uD83D\uDCD6 Learn more: theory, formula and Python code";
        lb.onclick = () => openLearn(currentTool);
        about.appendChild(lb);
    }
    about.classList.remove("hidden");

    if (tool.controls.length === 0) {
        box.innerHTML = '<div class="hint">This tool has no settings. Just look at the result.</div>';
        return;
    }

    tool.controls.forEach(c => {
        const label = document.createElement("label");
        label.textContent = c.label;
        let input;

        if (c.type === "range") {
            const span = document.createElement("b");
            span.textContent = ": " + c.value;
            label.appendChild(span);
            input = document.createElement("input");
            input.type = "range";
            input.min = c.min;
            input.max = c.max;
            input.step = c.step;
            input.value = c.value;
            input.addEventListener("input", () => {
                span.textContent = ": " + input.value;
                schedule();
            });
        } else {
            input = document.createElement("select");
            c.options.forEach(o => {
                const opt = document.createElement("option");
                opt.value = o[0];
                opt.textContent = o[1];
                input.appendChild(opt);
            });
            input.addEventListener("change", schedule);
        }

        input.name = c.name;
        label.appendChild(input);
        box.appendChild(label);

        // in the Android app: tappable choice pills instead of the system dropdown
        if (c.type !== "range" && document.documentElement.classList.contains("app")) {
            input.classList.add("hidden");          // the hidden dropdown still holds the value
            const chips = document.createElement("div");
            chips.className = "choice";
            chips.setAttribute("role", "radiogroup");
            chips.setAttribute("aria-label", c.label);
            c.options.forEach(o => {
                const b = document.createElement("button");
                b.type = "button";
                b.textContent = o[1];
                b.setAttribute("role", "radio");
                const on = o[0] === input.value;
                b.classList.toggle("on", on);
                b.setAttribute("aria-checked", on);
                b.onclick = () => {
                    if (input.value === o[0]) return;
                    input.value = o[0];
                    chips.querySelectorAll("button").forEach(x => {
                        x.classList.toggle("on", x === b);
                        x.setAttribute("aria-checked", x === b);
                    });
                    schedule();
                };
                chips.appendChild(b);
            });
            box.appendChild(chips);
        }
    });
    const reset = document.createElement("button");
    reset.className = "resetBtn";
    reset.textContent = "\u21BA Reset settings";
    reset.onclick = () => { buildControls(); schedule(); };
    box.appendChild(reset);
}

// wait a moment after the last slider move, then send
function schedule() {
    clearTimeout(timer);
    timer = setTimeout(run, 200);
}

// ============ PROCESS THE IMAGE (in the browser, see processing.js) ============
const nextFrame = () => new Promise(r => requestAnimationFrame(() => setTimeout(r, 0)));

async function run() {
    if (!currentMat || !cv) return;
    const myId = ++requestId;
    $("loading").classList.add("on");
    await nextFrame();                       // let "Processing..." appear first
    if (myId !== requestId) return;          // a newer request came in, skip this one

    const form = {};
    $("controls").querySelectorAll("input, select").forEach(el => { form[el.name] = el.value; });
    const tool = currentTool || "none";
    const ref = (currentTool && TOOLS[currentTool].needsRef) ? referenceMat : null;
    const base = (compareOriginal && steps.length > 1) ? steps[0].mat : currentMat;
    document.querySelector("#paneBefore .cap").textContent =
        (compareOriginal && steps.length > 1) ? "Before (original)" : (steps.length > 1 ? "Before (last step)" : "Before");

    try {
        const [out, note] = DIP.runTool(currentMat, tool, form, ref);
        free(resultMat);
        resultMat = out;
        show({
            original: encode(base),
            result: encode(out),
            note: note,
            size_original: `${base.cols} x ${base.rows}`,
            size_result: `${out.cols} x ${out.rows}`,
            hist_original: DIP.histogram(base),
            hist_result: DIP.histogram(out),
            stats_original: DIP.stats(base),
            stats_result: DIP.stats(out),
        });
    } catch (err) {
        console.error(err);
        toast("Something went wrong with this tool: " + (err.message || err));
    } finally {
        if (myId === requestId) $("loading").classList.remove("on");
    }
}

function show(data) {
    lastData = data;
    lastResult = data.result;
    const toolName = currentTool ? TOOLS[currentTool].label : null;

    // ----- Studio page -----
    $("imgOriginal").src = data.original;
    $("imgResult").src = data.result;
    $("sizeOriginal").textContent = data.size_original;
    $("sizeResult").textContent = data.size_result;
    $("afterCap").textContent = toolName ? "After: " + toolName : "After (pick a tool)";
    $("download").href = data.result;
    if (!$("learn").classList.contains("hidden")) {
        $("lBefore").src = data.original;
        $("lAfter").src = data.result;
    }

    const appMode = document.documentElement.classList.contains("app");
    const tip = !currentTool
        ? (steps.length > 1
            ? "Effect kept. Pick another tool to add on top, or save the picture."
            : "Pick a tool " + (appMode ? "from the list below" : "from the list on the left") +
              " to change your picture. Each tool says in simple words what it does.")
        : "";
    $("noteCard").classList.toggle("tip", !!tip);
    $("noteLabel").textContent = tip ? "Next step:" : "What happened:";
    if (data.note || tip) {
        $("noteText").textContent = data.note || tip;
        $("noteCard").classList.remove("hidden");
    } else {
        $("noteCard").classList.add("hidden");
    }

    // ----- Lab Data page (filled quietly in the background) -----
    $("dataSub").textContent = "Numbers behind the picture. Tool: " + (toolName || "none selected yet");
    $("dataBody").classList.remove("hidden");
    $("facts").innerHTML =
        `<div><span>Original size:</span> ${data.size_original}</div>` +
        `<div><span>Result size:</span> ${data.size_result}</div>` +
        `<div><span>Tool:</span> ${toolName || "none"}</div>`;
    drawHist($("histOriginal"), data.hist_original, "#8b95a1");
    drawHist($("histResult"), data.hist_result, "#2563eb");
    showStats(data.stats_original, data.stats_result);
}

// ============ HISTOGRAM (256 bars) ============
function drawHist(canvas, hist, color) {
    canvas.width = 512;
    canvas.height = 200;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, 512, 200);
    const max = Math.max(...hist) || 1;
    ctx.fillStyle = color;
    for (let i = 0; i < 256; i++) {
        const h = (hist[i] / max) * 190;
        ctx.fillRect(i * 2, 200 - h, 2, h);
    }
}

// ============ NUMBERS TABLE ============
function showStats(a, b) {
    let html = "<tr><th>Measure</th><th>Original</th><th>Result</th></tr>";
    STAT_LABELS.forEach(s => {
        html += `<tr><td>${s[1]}<div class="sdesc">${s[2]}</div></td><td>${a[s[0]]}</td><td>${b[s[0]]}</td></tr>`;
    });
    $("statsTable").innerHTML = html;
}

// ============ BUTTONS ============
// make the result the new starting image, so tools can be chained
// ============ STEP HISTORY: Original -> tool -> tool ... ============
function renderCrumbs() {
    const box = $("crumbs");
    box.classList.toggle("hidden", steps.length === 0);
    box.innerHTML = "";
    if (steps.length > 1) {
        const sw = document.createElement("span");
        sw.className = "cmpwith";
        sw.innerHTML = '<span>Compare with</span>';
        [["Last step", false], ["Original", true]].forEach(([txt, val]) => {
            const b = document.createElement("button");
            b.textContent = txt;
            b.className = compareOriginal === val ? "on" : "";
            b.onclick = () => { compareOriginal = val; renderCrumbs(); run(); };
            sw.appendChild(b);
        });
        box.appendChild(sw);
    }
    box.insertAdjacentHTML("beforeend", '<span class="lbl">Steps:</span>');
    steps.forEach((st, i) => {
        if (i > 0) box.insertAdjacentHTML("beforeend", '<span class="arrow">&#8594;</span>');
        const b = document.createElement("button");
        b.textContent = st.name;
        b.title = i === steps.length - 1 ? "Your picture right now" : "Go back to this step";
        if (i === steps.length - 1) b.className = "cur";
        b.onclick = () => goToStep(i);
        box.appendChild(b);
    });
    if (currentTool) {
        box.insertAdjacentHTML("beforeend",
            `<span class="arrow">&#8594;</span><span class="trying">trying: ${TOOLS[currentTool].label}</span>`);
    }
    const canUndo = steps.length > 1;
    $("undoBtn").disabled = !canUndo;
    $("undoBtn").style.opacity = canUndo ? "" : "0.45";
    box.scrollLeft = box.scrollWidth;
}

function goToStep(i) {
    if (!steps.length) return;
    while (steps.length > i + 1) free(steps.pop().mat);
    free(currentMat);
    currentMat = copyMat(steps[i].mat);
    currentTool = null;
    renderTools();
    buildControls();
    renderCrumbs();
    run();
}

// keep the result and stack another tool on top
$("useResult").addEventListener("click", () => {
    if (!resultMat) return;
    if (!currentTool) { toast("Pick a tool first, then keep its result."); return; }
    const m = normalizeMat(resultMat);
    steps.push({ name: TOOLS[currentTool].label, mat: copyMat(m) });
    if (steps.length > 12) free(steps.splice(1, 1)[0].mat);     // keep memory small on phones
    free(currentMat);
    currentMat = m;
    currentTool = null;
    renderTools();
    buildControls();
    renderCrumbs();
    run();
    toast("Kept! Now pick another tool to add on top.", true);
});

$("undoBtn").addEventListener("click", () => {
    if (steps.length > 1) goToStep(steps.length - 2);
    else if (currentTool) goToStep(0);
});

$("startOver").addEventListener("click", () => goToStep(0));

// in the Android app, save the picture to the phone's gallery
$("download").addEventListener("click", e => {
    if (window.AndroidBridge && lastResult) {
        e.preventDefault();
        AndroidBridge.saveImage(lastResult);
    }
});
// called back by the Android app after saving
window.onImageSaved = (ok, msg) => toast(msg, ok);

// ============ SMALL POP-UP MESSAGE ============
function toast(msg, good) {
    const t = $("toast");
    t.textContent = msg;
    t.style.background = good ? "#067647" : "#b42318";
    t.style.display = "block";
    setTimeout(() => { t.style.display = "none"; }, 3000);
}

// ============ PIXEL INSPECTOR ============
// reads the pixel under the mouse from the picture that is on screen
function pixelCanvas(img) {
    if (img._src !== img.src) {
        const c = document.createElement("canvas");
        c.width = img.naturalWidth;
        c.height = img.naturalHeight;
        c.getContext("2d", { willReadFrequently: true }).drawImage(img, 0, 0);
        img._cv = c;
        img._src = img.src;
    }
    return img._cv;
}

// which image pixel is under the finger / mouse (works with object-fit: contain too)
function imgXY(img, e) {
    const r = img.getBoundingClientRect();
    const W = img.naturalWidth, H = img.naturalHeight;
    const s = Math.min(r.width / W, r.height / H);
    const ox = r.left + (r.width - W * s) / 2, oy = r.top + (r.height - H * s) / 2;
    return [Math.floor((e.clientX - ox) / s), Math.floor((e.clientY - oy) / s)];
}

function inspect(img, label, e) {
    if (!inspectOn) return;
    if (!img.complete || !img.naturalWidth) return;
    const [x, y] = imgXY(img, e);
    if (x < 0 || y < 0 || x >= img.naturalWidth || y >= img.naturalHeight) return;

    const ctx = pixelCanvas(img).getContext("2d", { willReadFrequently: true });
    const gray = (d, i) => Math.round(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]);

    // the 5 x 5 block around the mouse
    const block = ctx.getImageData(x - 2, y - 2, 5, 5).data;
    let rows = "";
    for (let j = 0; j < 5; j++) {
        rows += "<tr>";
        for (let i = 0; i < 5; i++) {
            const k = (j * 5 + i) * 4;
            const inside = (x + i - 2 >= 0 && y + j - 2 >= 0 &&
                x + i - 2 < img.naturalWidth && y + j - 2 < img.naturalHeight);
            const g = inside ? gray(block, k) : "";
            const bg = inside ? `rgb(${g},${g},${g})` : "transparent";
            const fg = g !== "" && g < 128 ? "#fff" : "#1f2933";
            rows += `<td class="${i === 2 && j === 2 ? "mid" : ""}" style="background:${bg};color:${fg}">${g}</td>`;
        }
        rows += "</tr>";
    }
    $("pixGrid").innerHTML = rows;

    const c = block.slice(12 * 4 - 0, 12 * 4 + 4);   // centre pixel = index 12
    $("pixReadout").innerHTML =
        `<b>${label}</b> image, pixel (x = ${x}, y = ${y}): ` +
        `R = ${c[0]}, G = ${c[1]}, B = ${c[2]}, gray = ${gray(c, 0)}`;
}
$("imgOriginal").addEventListener("pointermove", e => inspect($("imgOriginal"), "Before", e));
$("imgResult").addEventListener("pointermove", e => inspect($("imgResult"), "After", e));
$("imgOriginal").addEventListener("pointerdown", e => inspect($("imgOriginal"), "Before", e));
$("imgResult").addEventListener("pointerdown", e => inspect($("imgResult"), "After", e));

// ============ MICROSCOPE (magnifier that follows the mouse) ============
const lens = $("lens");
let inspectOn = false;
$("toggleInspect").onclick = () => {
    inspectOn = !inspectOn;
    $("inspector").classList.toggle("hidden", !inspectOn);
    $("toggleInspect").textContent = "Pixel Inspector: " + (inspectOn ? "On" : "Off");
    $("toggleInspect").classList.toggle("main", inspectOn);
    document.body.classList.toggle("inspecting", inspectOn);
    if (!inspectOn) lens.style.display = "none";
};

const lctx = lens.getContext("2d");
const N = 7, CELL = 24;          // 7 x 7 pixels, each one drawn 24 px wide

function microscope(img, e) {
    if (!inspectOn) return;
    if (!img.complete || !img.naturalWidth) return;
    const [x, y] = imgXY(img, e);
    if (x < 0 || y < 0 || x >= img.naturalWidth || y >= img.naturalHeight) {
        lens.style.display = "none";
        return;
    }

    const half = (N - 1) / 2;
    const ctx = pixelCanvas(img).getContext("2d", { willReadFrequently: true });
    const data = ctx.getImageData(x - half, y - half, N, N).data;

    lctx.clearRect(0, 0, lens.width, lens.height);
    lctx.font = "10px Segoe UI, Arial";
    lctx.textAlign = "center";
    lctx.textBaseline = "middle";

    for (let j = 0; j < N; j++) {
        for (let i = 0; i < N; i++) {
            const k = (j * N + i) * 4;
            const px = x + i - half, py = y + j - half;
            const inside = px >= 0 && py >= 0 && px < img.naturalWidth && py < img.naturalHeight;
            if (!inside) {
                lctx.fillStyle = "#e5e9ee";
                lctx.fillRect(i * CELL, j * CELL, CELL, CELL);
                continue;
            }
            const R = data[k], G = data[k + 1], B = data[k + 2];
            const gray = Math.round(0.299 * R + 0.587 * G + 0.114 * B);
            lctx.fillStyle = `rgb(${R},${G},${B})`;       // the real pixel color
            lctx.fillRect(i * CELL, j * CELL, CELL, CELL);
            lctx.fillStyle = gray < 128 ? "#fff" : "#000";
            lctx.fillText(gray, i * CELL + CELL / 2, j * CELL + CELL / 2);   // its gray value
        }
    }
    // outline the pixel that is exactly under the mouse
    lctx.strokeStyle = "#2563eb";
    lctx.lineWidth = 2;
    lctx.strokeRect(half * CELL + 1, half * CELL + 1, CELL - 2, CELL - 2);

    // put the lens next to the mouse, flip it if it would leave the window
    let lx = e.clientX + 20, ly = e.clientY + 20;
    if (e.pointerType === "touch") ly = e.clientY - 200;   // keep it above the finger
    if (lx + 172 > window.innerWidth) lx = e.clientX - 192;
    if (lx < 4) lx = 4;
    if (ly + 172 > window.innerHeight) ly = e.clientY - 192;
    if (ly < 4) ly = e.clientY + 40;
    lens.style.left = lx + "px";
    lens.style.top = ly + "px";
    lens.style.display = "block";
}

["imgOriginal", "imgResult"].forEach(id => {
    $(id).addEventListener("pointermove", e => microscope($(id), e));
    $(id).addEventListener("pointerdown", e => microscope($(id), e));
    ["pointerleave", "pointerup", "pointercancel"].forEach(ev =>
        $(id).addEventListener(ev, () => { lens.style.display = "none"; }));
});
