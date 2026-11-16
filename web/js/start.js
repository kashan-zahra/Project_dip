// Image Lab - start-up: draw the tool list and load OpenCV.js.

// ============ START ============
renderTabs();
renderTools();
buildControls();
setMode(IS_APP ? "compare" : "split");

// ============ LOAD OPENCV.JS (about 13 MB, cached after the first visit) ============
function engineReady(c) {
    cv = c;
    window.cv = c;
    DIP.init(c);
    drop.classList.remove("wait");
    $("dropBig").textContent = IS_APP ? "Tap to open an image" : "Drop an image here";
    $("dropSub").textContent = IS_APP ? "or use the Camera button below" : "or click to choose one";
    clearInterval(loadTicker);
    if (waitingFile) { const f = waitingFile; waitingFile = null; newImage(f); }
}
const loadStart = Date.now();
const loadTicker = setInterval(() => {
    if (cv || waitingFile) return;
    $("dropSub").textContent = "This takes a few seconds the first time (" +
        Math.round((Date.now() - loadStart) / 1000) + " s). You can already tap to pick an image.";
}, 1000);
window.addEventListener("error", e => toast("Error: " + (e.message || "unknown")));
window.addEventListener("unhandledrejection", e => toast("Error: " + (e.reason && e.reason.message || e.reason)));
(function loadEngine() {
    const s = document.createElement("script");
    s.src = "vendor/opencv.js";
    s.async = true;
    s.onload = () => {
        const c = window.cv;
        if (c && c.Mat) engineReady(c);
        else if (c instanceof Promise) c.then(engineReady);
        else if (c) c.onRuntimeInitialized = () => engineReady(c);
        else toast("Image engine failed to start.");
    };
    s.onerror = () => {
        $("dropBig").textContent = "Could not load the image engine";
        $("dropSub").textContent = "Check your internet connection and reload the page.";
    };
    document.body.appendChild(s);
})();
