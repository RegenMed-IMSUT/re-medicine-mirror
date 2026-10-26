"""Repair the observed backstretch runtime asset gap, leaving source untouched."""
import hashlib
import json
import posixpath
import re
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
ASSET = 'application/files/9816/6909/3421/header-page.jpg'
URL = 'http://re-medicine.stemcell-imsut.org/' + ASSET


def repair():
    target = ROOT / 'docs' / ASSET
    if not target.exists():
        with urlopen(URL, timeout=30) as response:
            data = response.read()
            if response.status != 200 or not data.startswith(b'\xff\xd8\xff'):
                raise ValueError('Original header response is not a JPEG')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    count = 0
    for page in (ROOT / 'docs').rglob('*.html'):
        text = page.read_text(encoding='utf-8')
        old = "var headerImageFilePath = '/" + ASSET + "';"
        if old in text:
            relative = posixpath.relpath(ASSET, page.parent.relative_to(ROOT / 'docs').as_posix())
            page.write_text(text.replace(old, "var headerImageFilePath = '" + relative + "';"), encoding='utf-8')
            count += 1
    report = dict(asset=ASSET, source_url=URL, bytes=target.stat().st_size,
                  sha256=hashlib.sha256(target.read_bytes()).hexdigest(), pages_repaired=count,
                  reason='wget did not discover the image referenced by inline JavaScript',
                  transport_note='Original HTTPS hostname certificate mismatches; original public HTTP endpoint was used, without disabling TLS validation.')
    (ROOT / '_upload_metadata' / 'runtime-asset-repair.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    repair()
