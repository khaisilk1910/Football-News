"""Build HACS/Marketplace release asset with component files in ZIP root."""
from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "football_news"
MANIFEST = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
assert MANIFEST["domain"] == "football_news", "Wrong domain"
assert (COMPONENT / "__init__.py").is_file(), "Missing integration entry point"
OUT = ROOT / "football_news.zip"
with ZipFile(OUT, "w", ZIP_DEFLATED, compresslevel=9) as archive:
    for path in COMPONENT.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        archive.write(path, path.relative_to(COMPONENT).as_posix())
with ZipFile(OUT) as archive:
    assert "manifest.json" in archive.namelist()
    assert "__init__.py" in archive.namelist()
    assert archive.testzip() is None
print(f"Release ready: {OUT.name} ({OUT.stat().st_size:,} bytes, v{MANIFEST['version']})")
