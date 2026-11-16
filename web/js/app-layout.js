// Image Lab - Android app layout: start screen, top bar and the one-thing-at-a-time dock.
// Only runs when <html> has class "app" (inside the Android app, or ?app=1 in a browser).

// ============ ANDROID APP LAYOUT: one thing at a time ============
const IS_APP = document.documentElement.classList.contains("app");
if (IS_APP) {
    const root = document.documentElement;
    const studio = $("viewStudio");
    document.body.insertBefore($("appTop"), document.body.firstChild);

    // picture area
    const stageEl = document.querySelector(".stage");
    const stageBox = document.createElement("div");
    stageBox.className = "app-stage";
    stageBox.appendChild(stageEl);
    stageEl.appendChild($("seg"));
    stageEl.appendChild($("lensBtn"));
    stageEl.appendChild($("inspector"));
    studio.appendChild($("appStart"));
    studio.appendChild($("crumbs"));
    studio.appendChild(stageBox);
    studio.appendChild($("dock"));
    $("geekLink").classList.add("hidden");

    // pieces of the tool panel (re-used, same elements as the website)
    const settingsCard = $("controls").parentElement;
    const parts = { settings: settingsCard, note: $("noteCard"), ref: $("refCard") };

    // ----- top bar -----
    $("tBack").onclick = () => setPage("studio");
    $("tUndo").onclick = () => { $("undoBtn").click(); dockTo("groups"); };
    $("tData").onclick = () => setPage("data");
    $("tHelp").onclick = openGuide;
    $("tSave").onclick = () => $("download").click();

    // ----- start screen -----
    $("sGallery").onclick = () => $("file").click();
    $("sCamera").onclick = () => {
        if (window.AndroidBridge && AndroidBridge.takePhoto) AndroidBridge.takePhoto();
        else $("camFile").click();
    };
    $("sHow").onclick = openGuide;
    window.onOpeningImage = () => { $("sStatus").textContent = "Opening your photo..."; };
    const statusTick = setInterval(() => {
        if (root.classList.contains("has-img")) return;
        if (!engineOn) $("sStatus").textContent = waitingFile
            ? "Got your photo! It opens as soon as the tools are ready..."
            : "Getting the tools ready... you can already pick a photo.";
        else if ($("sStatus").textContent.startsWith("Getting")) $("sStatus").textContent = "";
    }, 500);

    // the Android app hands over the camera photo here
    window.openImageFromApp = async dataUrl => {
        const blob = await (await fetch(dataUrl)).blob();
        newImage(new File([blob], "camera.jpg", { type: blob.type || "image/jpeg" }));
    };

    // ----- the dock -----
    const ICONS = {
        Enhance: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
        Transform: '<path d="M6 2v14a2 2 0 0 0 2 2h14"/><path d="M18 22V8a2 2 0 0 0-2-2H2"/>',
        Filters: '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
        Edges: '<path d="M3 17l4-8 4 6 4-10 6 12"/>',
        Color: '<circle cx="12" cy="12" r="9"/><circle cx="8" cy="10" r="1.3"/><circle cx="12" cy="7.5" r="1.3"/><circle cx="16" cy="10" r="1.3"/><path d="M12 21c-1.5 0-2-1-2-2s1-2 2-2h2a3 3 0 0 0 3-3"/>',
        Pixels: '<path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z"/>',
        Segment: '<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor"/>',
        Morphology: '<path d="M3 13h8v8H3z"/><circle cx="16" cy="8" r="5"/>',
        Frequency: '<path d="M2 12c2-6 4-6 6 0s4 6 6 0 4-6 6 0"/>',
        Compare: '<path d="M3 5h8v14H3zM13 5h8v14h-8z"/>'
    };
    const TINT = {
        Enhance: ["#fff1cc", "#b45309"], Transform: ["#e5e8ff", "#4338ca"], Filters: ["#dceaff", "#1d4ed8"],
        Edges: ["#f1e6ff", "#7e22ce"], Color: ["#ffe3ef", "#be185d"], Pixels: ["#dcf7e6", "#15803d"],
        Segment: ["#ececec", "#374151"], Morphology: ["#ffe9d6", "#c2410c"], Frequency: ["#d6f5ef", "#0f766e"],
        Compare: ["#dff1fd", "#0369a1"]
    };
    const BACK = '<svg viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg>';
    const XI = '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    const OKI = '<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>';
    let dockMode = "groups";
    const dock = $("dock");

    function el(tag, cls, html) {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (html !== undefined) e.innerHTML = html;
        return e;
    }

    function dockTo(mode) {
        // leaving a tool without keeping it = cancel it
        if (dockMode === "tool" && mode !== "tool" && currentTool) {
            currentTool = null;
            buildControls();
            renderCrumbs();
            run();
        }
        dockMode = mode;
        renderDock();
    }
    window.dockTo = dockTo;

    function renderDock() {
        // park the shared parts back in the hidden page before rebuilding
        const park = document.querySelector("#viewStudio > aside");
        Object.values(parts).forEach(p => park.appendChild(p));
        dock.innerHTML = "";
        const wrap = el("div", "anim");
        wrap.style.cssText = "display:flex;flex-direction:column;min-height:0;flex:1";

        if (dockMode === "groups") {
            wrap.appendChild(el("div", "dhead", "<b>Pick a group of tools</b>"));
            const row = el("div", "drow");
            CATEGORIES.forEach(cat => {
                const t = TINT[cat] || ["#eee", "#333"];
                const b = el("button", "gtile",
                    `<i style="background:${t[0]};color:${t[1]}"><svg viewBox="0 0 24 24">${ICONS[cat] || ""}</svg></i>${CAT_NAMES[cat] || cat}`);
                b.onclick = () => { currentCategory = cat; dockTo("tools"); };
                row.appendChild(b);
            });
            wrap.appendChild(row);
        } else if (dockMode === "tools") {
            const head = el("div", "dhead");
            const back = el("button", "backbtn", BACK + "Groups");
            back.onclick = () => dockTo("groups");
            head.appendChild(back);
            head.appendChild(el("b", "", "&nbsp;" + (CAT_NAMES[currentCategory] || currentCategory)));
            wrap.appendChild(head);
            const row = el("div", "drow");
            Object.keys(TOOLS).forEach(key => {
                const t = TOOLS[key];
                if (t.group !== currentCategory) return;
                const b = el("button", "ttile");
                b.appendChild(el("b", "", t.label));
                b.appendChild(el("span", "", t.simple || ""));
                b.onclick = () => { selectTool(key); dockTo("tool"); };
                row.appendChild(b);
            });
            wrap.appendChild(row);
        } else {
            const t = TOOLS[currentTool];
            const head = el("div", "dhead");
            const back = el("button", "backbtn", BACK + "Tools");
            back.onclick = () => dockTo("tools");
            head.appendChild(back);
            head.appendChild(el("b", "", "&nbsp;" + t.label));
            wrap.appendChild(head);
            const panel = el("div", "dpanel");
            panel.appendChild(parts.settings);
            panel.appendChild(parts.ref);
            panel.appendChild(parts.note);
            wrap.appendChild(panel);
            const btns = el("div", "dbtns");
            const cancel = el("button", "cancel", XI + "Cancel");
            const keep = el("button", "keep", OKI + "Keep");
            cancel.onclick = () => dockTo("tools");
            keep.onclick = () => {
                $("useResult").click();
                dockMode = "groups";
                renderDock();
            };
            btns.appendChild(cancel);
            btns.appendChild(keep);
            wrap.appendChild(btns);
        }
        dock.appendChild(wrap);
    }
    renderDock();

    // ----- Android back button -----
    window.appBack = () => {
        if (!$("learn").classList.contains("hidden")) { closeLearn(); return true; }
        if (!$("guide").classList.contains("hidden")) { closeGuide(); return true; }
        if (root.classList.contains("on-data")) { setPage("studio"); return true; }
        if (dockMode === "tool") { dockTo("tools"); return true; }
        if (dockMode === "tools") { dockTo("groups"); return true; }
        return false;
    };

    // ----- magnifier on the picture -----
    $("lensBtn").onclick = () => {
        $("toggleInspect").click();
        $("lensBtn").classList.toggle("on", inspectOn);
    };

    // ----- Before / After slider -----
    const views = $("views");
    let cut = 50, dragging = false;
    const setCut = e => {
        const r = views.getBoundingClientRect();
        cut = Math.max(0, Math.min(100, (e.clientX - r.left) / r.width * 100));
        views.style.setProperty("--cut", cut + "%");
    };
    const nearHandle = e => {
        const r = views.getBoundingClientRect();
        return Math.abs(e.clientX - (r.left + r.width * cut / 100)) < 30;
    };
    const inspectAt = e => {
        const r = views.getBoundingClientRect();
        const before = e.clientX < r.left + r.width * cut / 100;
        const img = before ? $("imgOriginal") : $("imgResult");
        inspect(img, before ? "Before" : "After", e);
        microscope(img, e);
    };
    views.addEventListener("pointerdown", e => {
        if (viewMode !== "compare") return;
        views.setPointerCapture(e.pointerId);
        dragging = !inspectOn || nearHandle(e);
        if (dragging) setCut(e); else inspectAt(e);
    });
    views.addEventListener("pointermove", e => {
        if (viewMode !== "compare" || !views.hasPointerCapture(e.pointerId)) return;
        if (dragging) setCut(e); else inspectAt(e);
    });
    ["pointerup", "pointercancel"].forEach(ev => views.addEventListener(ev, () => {
        dragging = false;
        $("lens").style.display = "none";
    }));

    // ----- keep the top bar and steps bar in sync -----
    const sync = () => {
        const has = !$("views").classList.contains("hidden");
        root.classList.toggle("has-img", has);
        $("tUndo").disabled = steps.length < 2 && !currentTool;
        $("crumbs").classList.toggle("single", steps.length < 2);
        if (has) $("sStatus").textContent = "";
    };
    sync();
    new MutationObserver(sync).observe($("views"), { attributes: true, attributeFilter: ["class"] });
    new MutationObserver(sync).observe($("crumbs"), { childList: true });

    // new photo -> start at the groups row
    const origNew = newImage;
    newImage = async file => { await origNew(file); if (engineOn) { dockMode = "groups"; renderDock(); } };
}
