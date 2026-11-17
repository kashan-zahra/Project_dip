// Image Lab - help: the "Learn more" page (theory, formula, Python code, live preview) and the "How to use" guide.

// ============ LEARN MORE: theory + formula + code + live preview ============
function highlightPython(code) {
    const esc = t => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const KW = /^(import|from|as|def|return|if|elif|else|for|in|while|not|and|or|is|None|True|False|lambda|with|try|except|class|pass)$/;
    const re = /(#[^\n]*)|("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')|\b(\d+\.?\d*(?:e-?\d+)?)\b|\b([A-Za-z_]\w*)\b(\s*\()?/g;
    let out = "", last = 0, m;
    while ((m = re.exec(code))) {
        out += esc(code.slice(last, m.index));
        if (m[1]) out += `<span class="c">${esc(m[1])}</span>`;
        else if (m[2]) out += `<span class="s">${esc(m[2])}</span>`;
        else if (m[3]) out += `<span class="n">${m[3]}</span>`;
        else if (KW.test(m[4])) out += `<span class="k">${m[4]}</span>` + (m[5] || "");
        else if (m[5]) out += `<span class="f">${m[4]}</span>${m[5]}`;
        else out += m[4];
        last = re.lastIndex;
    }
    return out + esc(code.slice(last));
}

let learnFrom = null;        // where the sliders normally live
function openLearn(key) {
    const L = LEARN[key], t = TOOLS[key];
    if (!L || !t) return;
    if (currentTool !== key) selectTool(key);
    $("learnTitle").innerHTML = "";
    $("learnTitle").append(t.label);
    const sm = document.createElement("small");
    sm.textContent = t.simple || "";
    $("learnTitle").appendChild(sm);
    $("lWhat").textContent = L.what;
    $("lHow").textContent = L.how;
    $("lFormula").textContent = L.formula;
    $("lUses").textContent = L.uses;
    $("lCode").innerHTML = highlightPython(L.code);
    const hasImg = !!currentImg;
    $("lThumbs").classList.toggle("hidden", !hasImg);
    $("lNone").classList.toggle("hidden", hasImg);
    if (hasImg) {
        $("lBefore").src = $("imgOriginal").src;
        $("lAfter").src = $("imgResult").src;
        learnFrom = $("controls").parentElement;
        $("lControls").appendChild($("controls"));       // same sliders, so the photo updates live
    }
    $("learn").classList.remove("hidden");
    $("learn").querySelector(".gbox").scrollTop = 0;
}
function closeLearn() {
    if (learnFrom) { learnFrom.appendChild($("controls")); learnFrom = null; }
    $("learn").classList.add("hidden");
}
window.closeLearn = closeLearn;
$("learnClose").onclick = closeLearn;
$("learn").addEventListener("click", e => { if (e.target === $("learn")) closeLearn(); });
document.addEventListener("keydown", e => {
    if (e.key === "Escape") { closeLearn(); if (typeof closeGuide === "function") closeGuide(); }
});
$("lCopy").onclick = async () => {
    const text = LEARN[currentTool] ? LEARN[currentTool].code : "";
    try {
        await navigator.clipboard.writeText(text);
    } catch (e) {
        const ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
    }
    $("lCopy").textContent = "Copied";
    setTimeout(() => { $("lCopy").textContent = "Copy"; }, 1500);
};

// ============ HOW TO USE GUIDE ============
function openGuide() { $("guide").classList.remove("hidden"); }
function closeGuide() {
    $("guide").classList.add("hidden");
    try { localStorage.setItem("imagelab-guide-seen", "1"); } catch (e) { }
}
$("helpBtn").onclick = openGuide;
if (document.documentElement.classList.contains("app")) $("helpBtn").textContent = "? Help";
$("guideOk").onclick = closeGuide;
$("guide").addEventListener("click", e => { if (e.target === $("guide")) closeGuide(); });
let seenGuide = false;
try { seenGuide = localStorage.getItem("imagelab-guide-seen") === "1"; } catch (e) { }
if (!seenGuide) openGuide();


// ============ BEHIND THE SCENES (Flask versions): flip the After card ============
// app.py records every processing.py call with its real values (behind.py) and sends it
// as data.trace. The back of the After card shows it, live, while you move the sliders.
let behindOn = false;
let lastTrace = null;
let pickedPixel = null;      // [0 ... 1, 0 ... 1] on the picture, or null = the centre

function escapeHtml(t) {
    return String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// code with its real line numbers down the side, and "file · line N" on top
function numberedCode(code, file, start) {
    const lines = highlightPython(code.replace(/\n+$/, "")).split("\n");
    const rows = lines.map((l, i) => `<span class="ln">${start + i}</span>${l}`).join("\n");
    return `<div class="bfile">&#128196; ${escapeHtml(file)} &middot; line ${start}</div><pre class="numbered"><code>${rows}</code></pre>`;
}

function renderTrace() {
    const t = lastTrace, box = $("behindBack");
    if (!t) { box.innerHTML = '<p class="bhint">Pick a tool to see what Python does.</p>'; return; }
    const label = TOOLS[t.tool] ? TOOLS[t.tool].label : t.tool;
    const settings = Object.entries(t.settings);
    let html = `<div class="bhead"><b>Behind the scenes</b><span>${escapeHtml(label)} · Python</span>
        <button class="bflip" id="behindClose">&#8634; Show picture</button></div>`;

    html += `<div class="bstep"><span class="bn">1</span>Your settings (sent to <code>POST /process</code>)</div>`;
    html += settings.length
        ? '<div class="bchips">' + settings.map(([k, v]) => `<span><b>${escapeHtml(k)}</b> = ${escapeHtml(v)}</span>`).join("") + "</div>"
        : '<p class="bhint">This tool has no settings.</p>';

    if (t.run_tool) {
        html += `<div class="bstep"><span class="bn">2</span><code>app.py</code> → <code>run_tool()</code> reads them</div>`;
        html += numberedCode(t.run_tool, t.app_file || "app.py", t.run_tool_line || 1);
    }
    t.calls.forEach(c => {
        const sig = c.params.map(p => p.name === "img" ? "img" : `${p.name}=${escapeHtml(p.value)}`).join(", ");
        html += `<div class="bstep"><span class="bn">3</span><code>processing.py</code> runs <code class="bcall">${escapeHtml(c.name)}(${sig})</code></div>`;
        html += '<div class="bparams">' + c.params.map(p =>
            `<div><b>${escapeHtml(p.name)}</b><span>${escapeHtml(p.value)}</span></div>`).join("") + "</div>";
        html += numberedCode(c.code, c.file || "processing.py", c.line || 1);
    });
    html += renderPixelMath(t.example);
    html += `<p class="bfoot">Took ${t.ms} ms in Python · picture ${t.size_in} → ${t.size_out}</p>
        <p class="bfoot">Tip: click anywhere on this card to flip back to the picture.</p>`;
    box.innerHTML = html;
    $("behindClose").onclick = toggleBehind;
    if ($("useCentre")) $("useCentre").onclick = ev => { ev.stopPropagation(); pickedPixel = null; schedule(); };
    placePickMark();
}

// ----- step 4: the full calculation for one pixel -----
function swatch(rgbv) {
    if (!rgbv) return "";
    const c = rgbv.length === 1 ? `rgb(${rgbv[0]},${rgbv[0]},${rgbv[0]})` : `rgb(${rgbv.join(",")})`;
    return `<i class="swatch" style="background:${c}"></i>`;
}

function mathGrid(g) {
    const rows = g.rows.map((r, i) => "<tr>" + r.map((v, j) =>
        `<td${g.mark && g.mark[0] === i && g.mark[1] === j ? ' class="mk"' : ""}>${escapeHtml(v)}</td>`).join("") + "</tr>").join("");
    return `<div class="bgrid"><div class="bglabel">${escapeHtml(g.label)}</div><table>${rows}</table></div>`;
}

function renderPixelMath(e) {
    const where = e.picked ? `the pixel you picked (x = ${e.x}, y = ${e.y})` : `the pixel in the centre (x = ${e.x}, y = ${e.y})`;
    let h = `<div class="bstep"><span class="bn">4</span>The calculation for ${where}</div>
        <p class="bhint">Click any spot on the <b>Before</b> picture to explain that pixel instead${
            e.picked ? ' · <a href="#" id="useCentre">use the centre again</a>' : ""}.</p>
        <div class="bpixel">${e.before ? `<span>${swatch(e.before_rgb)}${escapeHtml(e.before)}</span><b>&#8594;</b>` : ""}
            <span>${swatch(e.after_rgb)}${escapeHtml(e.after)}</span></div>`;
    (e.steps || []).forEach(s => {
        h += `<div class="msub">${escapeHtml(s.title)}</div>`;
        if (s.grids && s.grids.length) h += `<div class="bgrids">${s.grids.map(mathGrid).join("")}</div>`;
        const lines = (s.lines || []).filter(l => l !== "");
        if (lines.length) h += `<pre class="math">${escapeHtml(lines.join("\n"))}</pre>`;
    });
    if (e.mine) {
        const names = e.after_rgb.length === 1 ? ["gray"] : ["R", "G", "B"];
        const mine = e.mine.map((v, i) => `${names[i] === "gray" ? "gray" : names[i]} ${v}`).join(", ");
        const msg = {
            exact: "&#10004; Exactly the same. The maths above is what the computer really did.",
            close: "&#8776; 1 off at most: OpenCV rounds with whole numbers inside to be faster.",
            off: "&#9888; Different: this tool does extra steps inside OpenCV that the summary above skips.",
        }[e.match];
        h += `<div class="bcheck ${e.match}"><b>Check</b><br>our calculation: ${escapeHtml(mine)}<br>
            real result from OpenCV: ${escapeHtml(e.after)}<br>${msg}</div>`;
    }
    return h;
}

// small cross on the Before picture where the explained pixel is
function placePickMark() {
    const m = $("pickMark"), img = $("imgOriginal");
    if (!behindOn || !lastTrace || !img.naturalWidth) { m.classList.add("hidden"); return; }
    const fx = pickedPixel ? pickedPixel[0] : 0.5, fy = pickedPixel ? pickedPixel[1] : 0.5;
    const r = img.getBoundingClientRect(), pr = img.parentElement.getBoundingClientRect();
    const W = img.naturalWidth, H = img.naturalHeight;
    const s = Math.min(r.width / W, r.height / H);
    m.style.left = (r.left - pr.left + (r.width - W * s) / 2 + fx * W * s) + "px";
    m.style.top = (r.top - pr.top + (r.height - H * s) / 2 + fy * H * s) + "px";
    m.classList.remove("hidden");
}
window.addEventListener("resize", placePickMark);

function toggleBehind() {
    behindOn = !behindOn;
    if (behindOn && viewMode === "before") setMode("split");
    $("paneAfter").classList.toggle("flipped", behindOn);
    $("behindBtn").classList.toggle("main", behindOn);
    if (behindOn) renderTrace(); else placePickMark();
}

if (SERVER_MODE && !document.documentElement.classList.contains("app")) {
    $("behindBtn").classList.remove("hidden");
    $("behindBtn").onclick = toggleBehind;
    $("paneAfter").classList.add("clickflip");

    // click the card itself to flip it back and forth (the buttons still work too)
    $("paneAfter").addEventListener("click", e => {
        if (inspectOn) return;                                   // the Pixel Inspector uses clicks
        if (!behindOn && !$("imgResult").getAttribute("src")) return;   // nothing to explain yet
        if (e.target.closest("button, a, input")) return;
        if (String(window.getSelection())) return;               // selecting code to copy, not flipping
        toggleBehind();
    });

    // while the card shows Behind the scenes: click the Before picture to choose the pixel to explain
    $("imgOriginal").addEventListener("click", e => {
        if (!behindOn || inspectOn) return;
        const img = $("imgOriginal");
        const [x, y] = imgXY(img, e);
        if (x < 0 || y < 0 || x >= img.naturalWidth || y >= img.naturalHeight) return;
        pickedPixel = [(x + 0.5) / img.naturalWidth, (y + 0.5) / img.naturalHeight];
        schedule();
    });
}
