"""Behind the scenes: records what Python really does for one picture.

While run_tool() works, the `dip` module (processing.py) is replaced by a recorder that writes
down every function call with its real parameter values. The page shows this on the back of
the After card ("Behind the scenes").
"""
import inspect
import os
import re
import time

import numpy as np

import explain


class Recorder:
    """Stands in for processing.py during one request and notes every function call."""

    def __init__(self, module):
        self.module = module
        self.calls = []

    def __getattr__(self, name):
        thing = getattr(self.module, name)
        if not callable(thing):
            return thing

        def wrapped(*args, **kwargs):
            self.calls.append((name, thing, args, kwargs))
            return thing(*args, **kwargs)
        return wrapped


def describe(value):
    """A short, readable description of a parameter value."""
    if isinstance(value, np.ndarray):
        h, w = value.shape[:2]
        kind = "colour, 3 channels (B, G, R)" if value.ndim == 3 else "gray, 1 channel"
        return f"image {w} x {h} pixels, {kind}"
    if isinstance(value, float):
        return f"{value:g}"
    return repr(value)


def rgb(img, x, y):
    """[R, G, B] or [gray] as plain numbers, for the colour swatches."""
    if img.ndim == 2:
        return [int(img[y, x])]
    b, g, r = (int(v) for v in img[y, x][:3])
    return [r, g, b]


def pixel(img, x, y):
    """The value of one pixel, written the way people read it."""
    if img.ndim == 2:
        return f"gray {int(img[y, x])}"
    b, g, r = (int(v) for v in img[y, x][:3])
    return f"R {r}, G {g}, B {b}"


def run_tool_lines(app_module, tool):
    """The lines of run_tool() in app.py that handle this tool, and the line number they start on."""
    lines, first = inspect.getsourcelines(app_module.run_tool)
    lines = [l.rstrip("\n") for l in lines]
    start = None
    for i, line in enumerate(lines):
        if re.match(r"\s{4}if tool (==|in) .*" + re.escape(f'"{tool}"'), line):
            start = i
            break
    if start is None:
        return "", 0
    block = [lines[start]]
    for line in lines[start + 1:]:
        if re.match(r"\s{4}(if tool|# -|return )", line) or not line.strip():
            break
        block.append(line)
    return "\n".join(l[4:] for l in block), first + start


def run_with_trace(app_module, img, tool, form, ref):
    """Run the tool like normal, and also return what happened behind the scenes."""
    real = app_module.dip
    recorder = Recorder(real)
    app_module.dip = recorder                      # every dip.xxx() call now goes through the recorder
    start = time.perf_counter()
    try:
        out, note = app_module.run_tool(img, tool, form, ref)
    finally:
        app_module.dip = real
    ms = (time.perf_counter() - start) * 1000

    calls = []
    for name, func, args, kwargs in recorder.calls:
        names = list(inspect.signature(func).parameters)
        params = [{"name": n, "value": describe(a)} for n, a in zip(names, args)]
        params += [{"name": k, "value": describe(v)} for k, v in kwargs.items()]
        code, line = inspect.getsourcelines(func)
        calls.append({"name": name, "params": params, "code": "".join(code), "line": line,
                      "file": os.path.basename(inspect.getsourcefile(func))})

    # example pixel: the one you clicked (sent as _px, _py = 0 ... 1), or the centre
    h, w = img.shape[:2]
    oh, ow = out.shape[:2]
    try:
        fx, fy = float(form.get("_px", 0.5)), float(form.get("_py", 0.5))
    except ValueError:
        fx, fy = 0.5, 0.5
    x = min(max(int(fx * ow), 0), ow - 1)
    y = min(max(int(fy * oh), 0), oh - 1)
    same = out.shape[:2] == img.shape[:2]
    example = {"x": x, "y": y, "picked": "_px" in form,
               "before": pixel(img, x, y) if same else None, "before_rgb": rgb(img, x, y) if same else None,
               "after": pixel(out, x, y), "after_rgb": rgb(out, x, y)}
    steps, mine, real = explain.explain(tool, img, out, form, ref, x, y)
    match = None
    if mine is not None:
        diff = max(abs(int(a) - int(b)) for a, b in zip(mine, real))
        match = "exact" if diff == 0 else ("close" if diff <= 1 else "off")
    example["steps"] = steps
    example["mine"] = [int(v) for v in mine] if mine is not None else None
    example["match"] = match

    settings = {k: v for k, v in form.items() if k != "tool" and not k.startswith("_")}
    run_code, run_line = run_tool_lines(app_module, tool)
    trace = {
        "tool": tool,
        "settings": settings,
        "run_tool": run_code,
        "run_tool_line": run_line,
        "app_file": os.path.basename(inspect.getsourcefile(app_module.run_tool)),
        "calls": calls,
        "example": example,
        "ms": round(ms, 1),
        "size_in": f"{w} x {h}",
        "size_out": f"{out.shape[1]} x {out.shape[0]}",
    }
    return out, note, trace
