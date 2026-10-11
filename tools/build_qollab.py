"""Build the Qollab version of the game (a "JS / Qiskit" project) from the same sources as the prototype.

    python tools/build_qollab.py          # writes qollab/ and dist/quantrain-qollab.zip

Qollab runs a project with index.html + main.js at the top level as a JS project, in a sandboxed frame:
index.html is body markup only (no <script>), main.css is the only stylesheet, three.js is built in, and
main.js can import Python modules by dotted name. Python runs on Pyodide with Qiskit installed.

  index.html    the page markup                     (from prototype/src/app.html)
  main.css      the styles + web fonts              (from prototype/src/app.html)
  main.js       the game, engine and levels inlined (same script as prototype/index.html)
                + `import * as quantrainBridge from 'quantrain.qollab'` for real shots on Qollab's backend
  quantrain/    the Python package (translator, scoring, the bridge)
  README.md     becomes the project card on Qollab
"""
from __future__ import annotations

import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_prototype import build_body, check_script   # noqa: E402

OUT = ROOT / "qollab"
ZIP = ROOT / "dist" / "quantrain-qollab.zip"
FONTS = "https://fonts.googleapis.com/css2?family=Figtree:wght@500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap"
PY_FILES = ["__init__.py", "level.py", "circuit.py", "reference.py", "score.py", "qollab.py"]

# In Qollab the page sits in a frame above the console: make sure it has a height even if the frame sizes itself
# to its content (everything in the game is positioned over the map, so the body would otherwise be empty).
EXTRA_CSS = """
/* Qollab: the game fills its frame; give the frame something to size to */
html, body { min-height: 640px; }
"""


def main() -> None:
    body = build_body()
    check_script(body)
    css = body.split("<style>", 1)[1].split("</style>", 1)[0]
    markup = body.split("</style>", 1)[1].split('<script type="importmap">', 1)[0].strip() + "\n"
    script = body.split('<script type="module">', 1)[1].rsplit("</script>", 1)[0]
    assert "import * as THREE from 'three';" in script and "three/addons/controls/OrbitControls.js" in script
    main_js = ("// Quantrain on Qollab: the Python bridge sends real shots to the backend picked in Select QPU.\n"
               "import * as quantrainBridge from 'quantrain.qollab';\n" + script.lstrip("\n"))

    if OUT.exists():
        shutil.rmtree(OUT, ignore_errors=True)
    (OUT / "quantrain").mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(markup, encoding="utf-8")
    (OUT / "main.css").write_text(f"@import url('{FONTS}');\n" + css.strip("\n") + "\n" + EXTRA_CSS, encoding="utf-8")
    (OUT / "main.js").write_text(main_js, encoding="utf-8")
    for name in PY_FILES:
        shutil.copy(ROOT / "quantrain" / name, OUT / "quantrain" / name)
    shutil.copy(ROOT / "LICENSE", OUT / "LICENSE")
    (OUT / "requirements.txt").write_text("qiskit>=2.5.2,<3.0.0\n", encoding="utf-8")
    shutil.copy(ROOT / "docs" / "QOLLAB_README.md", OUT / "README.md")

    for f in OUT.rglob("*"):
        if f.is_file() and f.stat().st_size > 2 * 1024 * 1024:
            raise SystemExit(f"{f} is over Qollab's 2 MB file limit")
    ZIP.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(OUT).as_posix())
    files = [f for f in OUT.rglob("*") if f.is_file()]
    print(f"wrote {OUT.relative_to(ROOT)}/ ({len(files)} files) and {ZIP.relative_to(ROOT)} ({ZIP.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
