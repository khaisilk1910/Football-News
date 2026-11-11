"""Check the publishable repository layout and version consistency."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "custom_components"
DOMAIN = "football_news"


def main(tag: str | None = None) -> None:
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    assert hacs["name"] == "Football News"
    assert not hacs.get("zip_release"), "Marketplace must not depend on a ZIP asset"
    assert "filename" not in hacs, "Remove filename when zip_release is disabled"

    component_dirs = sorted(p.name for p in COMPONENTS.iterdir() if p.is_dir())
    assert component_dirs == [DOMAIN], f"Expected exactly one integration folder: {component_dirs}"
    component = COMPONENTS / DOMAIN
    for required in ("__init__.py", "manifest.json", "config_flow.py", "strings.json", "translations/vi.json"):
        assert (component / required).is_file(), f"Missing {required}"
    manifest = json.loads((component / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["domain"] == DOMAIN
    assert manifest["name"] == "Football News"
    version = manifest["version"]

    # Do not import const.py: importing the integration may require Home Assistant.
    import ast
    tree = ast.parse((component / "const.py").read_text(encoding="utf-8"))
    versions = [node.value.value for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "VERSION" for t in node.targets)
                and isinstance(node.value, ast.Constant)]
    assert versions == [version], f"const.py VERSION must match manifest: {version}"
    if tag is not None:
        assert tag == f"v{version}", f"Tag {tag} differs from manifest version v{version}"
    print(f"Marketplace repository OK: {DOMAIN} v{version} (source-based install)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default=None)
    args = parser.parse_args()
    main(args.tag)
