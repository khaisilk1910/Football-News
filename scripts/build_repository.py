"""Package a clean GitHub upload, including dotfiles and workflows."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / 'Football-News-repository.zip'
SKIP = {'__pycache__', '.git', '.pytest_cache', '.ruff_cache', '.mypy_cache', '.venv'}
with ZipFile(OUT, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or any(part in SKIP for part in path.parts) or path.suffix in ('.pyc','.pyo'):
            continue
        if path.name in ('football_news.zip', 'Football-News-repository.zip'):
            continue
        archive.write(path, f'Football-News/{path.relative_to(ROOT).as_posix()}')
with ZipFile(OUT) as archive:
    names = set(archive.namelist())
    for required in ('Football-News/.gitignore','Football-News/LICENSE','Football-News/README.md',
                     'Football-News/FEATURES.md','Football-News/hacs.json',
                     'Football-News/.github/workflows/release.yml',
                     'Football-News/custom_components/football_news/manifest.json',
                     'Football-News/custom_components/football_news/predictions.py'):
        assert required in names, f'Missing {required}'
    assert archive.testzip() is None
    assert not any('__pycache__' in name or name.endswith('.pyc') for name in names)
print(f'Repository ready: {OUT.name} ({OUT.stat().st_size:,} bytes, {len(names)} files)')
