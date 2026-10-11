"""Build the browser prototype: inline the engine and the level files into one HTML page.

    python tools/build_prototype.py                       # writes prototype/index.html
    python tools/build_prototype.py --artifact out.html   # also writes a body-only copy for publishing
    python tools/build_prototype.py --public-url https://you.github.io/quantrain/   # base of shared puzzle links

Sources: prototype/src/app.html (page), prototype/src/engine.mjs (engine), prototype/src/vendor/qrcode.js (QR codes),
levels/*.json (levels). The public URL can also live in prototype/public_url.txt (one line); share links
use it when the game runs inside a frame (Qollab, an artifact) and cannot see its own address.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEAD = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')


def public_url(given: str | None = None) -> str:
    if given is None:
        f = ROOT / "prototype/public_url.txt"
        given = f.read_text(encoding="utf-8").strip() if f.exists() else ""
    assert not given or re.fullmatch(r"https://[^\s'\"<>\\]+", given), f"public URL must be https://…: {given!r}"
    return given


def build_body(url: str | None = None) -> str:
    app = (ROOT / "prototype/src/app.html").read_text(encoding="utf-8")
    qr = (ROOT / "prototype/src/vendor/qrcode.js").read_text(encoding="utf-8")
    qr = qr[: qr.index("(function (factory)")]       # drop the UMD tail: the page only needs the qrcode() function
    engine = (ROOT / "prototype/src/engine.mjs").read_text(encoding="utf-8")
    engine = re.sub(r"^export (?=(const|function|class|let) )", "", engine, flags=re.M)
    levels = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "levels").glob("*.json"))]
    for marker in ("/*@ENGINE@*/", "/*@LEVELS@*/[]", "/*@QRCODE@*/", "/*@PUBLIC_URL@*/''"):
        assert app.count(marker) == 1, f"marker {marker} missing in app.html"
    return (app.replace("/*@ENGINE@*/", engine)
            .replace("/*@LEVELS@*/[]", json.dumps(levels, ensure_ascii=False, indent=1))
            .replace("/*@QRCODE@*/", qr.strip())
            .replace("/*@PUBLIC_URL@*/''", json.dumps(public_url(url))))


def check_script(body: str) -> None:
    """Syntax-check the page's module script with Node, if it is installed (catches duplicate names etc.)."""
    import shutil, subprocess, tempfile
    node = shutil.which("node")
    if not node:
        return
    src = body.split('<script type="module">', 1)[1].split("</script>", 1)[0]
    src = re.sub(r"^import .*$", "", src, flags=re.M)
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as f:
        f.write(src)
    res = subprocess.run([node, "--check", f.name], capture_output=True, text=True)
    if res.returncode:
        raise SystemExit("page script has a syntax error:\n" + res.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", help="also write the page body (no <html>/<head>) to this path")
    ap.add_argument("--public-url", help="https address of the published game, for shared puzzle links")
    args = ap.parse_args()
    body = build_body(args.public_url)
    cut = body.index("</style>") + len("</style>")
    page = HEAD + body[:cut] + "\n</head>\n<body>\n" + body[cut:].lstrip("\n") + "</body>\n</html>\n"
    check_script(body)
    out = ROOT / "prototype/index.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({len(page) // 1024} KB)")
    if args.artifact:
        Path(args.artifact).write_text(body, encoding="utf-8")
        print(f"wrote {args.artifact}")


if __name__ == "__main__":
    main()
