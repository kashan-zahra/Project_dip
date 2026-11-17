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

function escapeHtml(t) {
    return String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
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
        html += `<pre><code>${highlightPython(t.run_tool)}</code></pre>`;
    }
    t.calls.forEach(c => {
        const sig = c.params.map(p => p.name === "img" ? "img" : `${p.name}=${escapeHtml(p.value)}`).join(", ");
        html += `<div class="bstep"><span class="bn">3</span><code>processing.py</code> runs <code class="bcall">${escapeHtml(c.name)}(${sig})</code></div>`;
        html += '<div class="bparams">' + c.params.map(p =>
            `<div><b>${escapeHtml(p.name)}</b><span>${escapeHtml(p.value)}</span></div>`).join("") + "</div>";
        html += `<pre><code>${highlightPython(c.code)}</code></pre>`;
    });
    const e = t.example;
    html += `<div class="bstep"><span class="bn">4</span>Example: the pixel in the centre (x = ${e.x}, y = ${e.y})</div>
        <div class="bpixel"><span>${escapeHtml(e.before)}</span><b>&#8594;</b><span>${escapeHtml(e.after)}</span></div>`;
    html += `<p class="bfoot">Took ${t.ms} ms in Python · picture ${t.size_in} → ${t.size_out}</p>`;
    box.innerHTML = html;
    $("behindClose").onclick = toggleBehind;
}

function toggleBehind() {
    behindOn = !behindOn;
    if (behindOn && viewMode === "before") setMode("split");
    $("paneAfter").classList.toggle("flipped", behindOn);
    $("behindBtn").classList.toggle("main", behindOn);
    if (behindOn) renderTrace();
}

if (SERVER_MODE && !document.documentElement.classList.contains("app")) {
    $("behindBtn").classList.remove("hidden");
    $("behindBtn").onclick = toggleBehind;
}
