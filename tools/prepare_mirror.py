"""Read-only-source GitHub Pages preparation and static validation (stdlib only)."""
import argparse
import csv
import hashlib
import html
import json
import posixpath
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ORIGINAL = 'http://re-medicine.stemcell-imsut.org/'
TILE = 'application/files/3117/7363/3959/RegeneMedLogoSquire.png'
URL_ATTR = re.compile(r'\b(href|src|poster|action|data-src|data-background|srcset)\s*=\s*([\"\'])(.*?)\2', re.I | re.S)
CSS_URL = re.compile(r'url\(\s*([\"\']?)(.*?)\1\s*\)', re.I)
CSS_IMPORT = re.compile(r'(@import\s+)([\"\'])(.*?)\2', re.I)
SAFE = re.compile(r'[A-Za-z0-9._/-]+\Z')


def snapshot(source):
    result = {}
    for path in sorted(source.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symlink not allowed: {path}')
        if path.is_file():
            result[path.relative_to(source).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def sanitized_name(name, data=b''):
    name = name.split('\uf03f', 1)[0]
    if not posixpath.splitext(name)[1]:
        if data.startswith(b'\xff\xd8\xff'):
            name += '.jpg'
        elif data.startswith(b'\x89PNG\r\n\x1a\n'):
            name += '.png'
        else:
            raise ValueError(f'Unrecognized extensionless file: {name}')
    if not SAFE.fullmatch(name) or '..' in name.split('/'):
        raise ValueError(f'Unsafe public name: {name}')
    return name


def build_mapping(source):
    mapping, occupied = {}, {}
    for name in snapshot(source):
        safe = sanitized_name(name, (source / name).read_bytes())
        key = safe.casefold()
        if key in occupied:
            raise ValueError(f'Filename collision: {occupied[key]} and {name} -> {safe}')
        mapping[name] = safe
        occupied[key] = name
    return mapping


def rewrite_url(value, page, mapping):
    decoded = html.unescape(value).strip()
    parts = urlsplit(decoded)
    if parts.scheme or parts.netloc or not parts.path or decoded.startswith('/'):
        return value
    # %3F encodes the wget filename suffix, unlike an actual URL query delimiter.
    old = posixpath.normpath(posixpath.join(posixpath.dirname(page), unquote(parts.path).replace('?', '\uf03f')))
    if old not in mapping or mapping[old] == old:
        return value
    target = posixpath.relpath(mapping[old], posixpath.dirname(page) or '.')
    if parts.query:
        target += '?' + parts.query
    if parts.fragment:
        target += '#' + parts.fragment
    return html.escape(target, quote=True)


def srcset_urls(value):
    # The mirror has no data-URL srcset; retain data URLs without comma splitting.
    if 'data:' in value:
        raise ValueError('Data URL srcset requires explicit review')
    return [part.strip().split()[0] for part in value.split(',') if part.strip()]


def transform(text, page, mapping):
    def attr(match):
        name, quote, value = match.groups()
        if name.lower() == 'srcset':
            value = ', '.join(' '.join([rewrite_url(bits[0], page, mapping)] + bits[1:])
                              for part in value.split(',') if (bits := part.strip().split()))
        else:
            value = rewrite_url(value, page, mapping)
        return f'{name}={quote}{value}{quote}'
    text = URL_ATTR.sub(attr, text)
    text = CSS_URL.sub(lambda m: f'url({m[1]}{rewrite_url(m[2], page, mapping)}{m[1]})', text)
    text = CSS_IMPORT.sub(lambda m: f'{m[1]}{m[2]}{rewrite_url(m[3], page, mapping)}{m[2]}', text)
    if page.endswith('.html'):
        text = re.sub(r'(<head\b[^>]*>)', r'\1\n<meta name="robots" content="noindex">', text, count=1, flags=re.I)
        def tile(match):
            if TILE not in mapping.values():
                raise ValueError('Local replacement TileImage missing')
            local = posixpath.relpath(TILE, posixpath.dirname(page) or '.')
            return re.sub(r'content\s*=\s*([\"\']).*?\1', f'content="{local}"', match[0], flags=re.I)
        text = re.sub(r'<meta\b[^>]*name=[\"\']msapplication-TileImage[\"\'][^>]*>', tile, text, flags=re.I)
        text = re.sub(r'(<iframe\b[^>]*\bsrc\s*=\s*[\"\'])http://(www\.)?youtube\.com/', r'\1https://\2youtube.com/', text, flags=re.I)
        notice = f'<p class="trial-mirror-notice" style="font-size:12px;line-height:1.5;padding:8px 12px;margin:0;">試験ミラー · <a href="{ORIGINAL}">原サイト</a></p>'
        if re.search(r'<div\s+class="footer-box"\s*>', text):
            text = re.sub(r'(<div\s+class="footer-box"\s*>)', r'\1\n' + notice, text, count=1)
        else:
            text = re.sub(r'</body>', notice + '\n</body>', text, count=1, flags=re.I)
    return text


class References(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.robots, self.notices = [], 0, 0
        self.forms, self.bases, self.srcsets = 0, 0, 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.forms += tag == 'form'
        self.bases += tag == 'base'
        self.notices += 'trial-mirror-notice' in attrs.get('class', '').split()
        if tag == 'meta' and attrs.get('name', '').lower() == 'robots' and 'noindex' in attrs.get('content', '').lower().split(','):
            self.robots += 1
        for key in ('href', 'src', 'poster', 'action', 'data-src', 'data-background'):
            if attrs.get(key):
                self.refs.append((tag + ':' + key, attrs[key]))
        if attrs.get('srcset'):
            self.srcsets += 1
            self.refs.extend(('srcset', value) for value in srcset_urls(attrs['srcset']))
        if tag == 'meta' and attrs.get('name') == 'msapplication-TileImage':
            self.refs.append(('TileImage', attrs.get('content', '')))


def validate(docs):
    files = sorted(p for p in docs.rglob('*') if p.is_file())
    names = {p.relative_to(docs).as_posix() for p in files}
    report = dict(public_files=len(files), html_pages=0, local_references_checked=0,
                  srcset_attributes=0, robots_pages=0, notice_pages=0, forms=0, bases=0,
                  missing_local=[], root_absolute=[], unsafe_names=[], http_active=[],
                  old_domain_asset_refs=[], malformed_external=[], external_references=[])
    report['unsafe_names'] = sorted(n for n in names if not SAFE.fullmatch(n))
    for path in files:
        if path.suffix not in ('.html', '.css'):
            continue
        page = path.relative_to(docs).as_posix()
        text = path.read_bytes().decode('utf-8')
        refs = []
        if path.suffix == '.html':
            parser = References()
            parser.feed(text)
            report['html_pages'] += 1
            report['robots_pages'] += parser.robots == 1
            report['notice_pages'] += parser.notices == 1
            report['forms'] += parser.forms
            report['bases'] += parser.bases
            report['srcset_attributes'] += parser.srcsets
            refs.extend(parser.refs)
        refs.extend(('css:url', html.unescape(m[2])) for m in CSS_URL.finditer(text))
        refs.extend(('css:import', html.unescape(m[3])) for m in CSS_IMPORT.finditer(text))
        for kind, value in refs:
            value = value.strip()
            parts = urlsplit(value)
            item = dict(page=page, kind=kind, url=value)
            if value.startswith('http://https://'):
                report['malformed_external'].append(item)
            if parts.scheme or parts.netloc:
                if parts.scheme in ('http', 'https') or parts.netloc:
                    report['external_references'].append(item)
                if parts.scheme == 'http' and kind not in ('a:href', 'form:action'):
                    report['http_active'].append(item)
                if parts.hostname == 're-medicine.stemcell-imsut.org' and kind != 'a:href':
                    report['old_domain_asset_refs'].append(item)
                continue
            if not parts.path:
                continue
            if value.startswith('/'):
                report['root_absolute'].append(item)
                continue
            local = posixpath.normpath(posixpath.join(posixpath.dirname(page), unquote(parts.path)))
            if local not in names and local.rstrip('/') + '/index.html' not in names:
                report['missing_local'].append(dict(item, resolved=local))
            report['local_references_checked'] += 1
    report['passed'] = not any(report[k] for k in ('missing_local', 'root_absolute', 'unsafe_names', 'http_active', 'old_domain_asset_refs')) and report['robots_pages'] == report['html_pages'] == report['notice_pages'] and report['bases'] == 0
    return report


def ccm_audit(source):
    occurrences = []
    definitions = Counter()
    for path in sorted(source.rglob('*')):
        if not path.is_file() or ('.js' not in path.name and path.suffix != '.html'):
            continue
        text = path.read_bytes().decode('utf-8')
        for match in re.finditer(r'\bCCM_[A-Z_]+\b', text):
            prefix = text[max(0, match.start()-10):match.start()]
            if re.search(r'var\s+$', prefix) and re.match(r'\s*=', text[match.end():]):
                definitions[match[0]] += 1
            else:
                occurrences.append(dict(file=path.relative_to(source).as_posix(), token=match[0]))
    return dict(definitions=dict(definitions), nondefinition_uses=occurrences,
                conclusion='Preserved unused Concrete declarations' if not occurrences else 'Review required')


def prepare(source, root):
    source, root = Path(source).resolve(), Path(root).resolve()
    if source == root or source in root.parents or root in source.parents:
        raise ValueError('Source and output must be disjoint')
    docs, metadata = root / 'docs', root / '_upload_metadata'
    if docs.exists() or (metadata / 'original-to-sanitized.tsv').exists():
        raise FileExistsError('Refusing to overwrite an existing mirror; use a fresh work directory')
    before = snapshot(source)
    mapping = build_mapping(source)  # Collision and unsafe-name checks before writing anything.
    metadata.mkdir(parents=True, exist_ok=True)
    (metadata / 'original-sha256.json').write_text(json.dumps(before, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    docs.mkdir(parents=True)
    rows, youtube = [], 0
    for old, new in mapping.items():
        data = (source / old).read_bytes()
        target = docs / new
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix in ('.html', '.css'):
            text = data.decode('utf-8')
            youtube += len(re.findall(r'<iframe\b[^>]*\bsrc\s*=\s*[\"\']http://(?:www\.)?youtube\.com/', text, re.I))
            data = transform(text, old, mapping).encode('utf-8')
        target.write_bytes(data)
        rows.append((old, old.replace('\uf03f', '%3F'), new, before[old], hashlib.sha256(data).hexdigest()))
    (docs / '.nojekyll').write_bytes(b'')
    with (metadata / 'original-to-sanitized.tsv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(('original_path', 'original_url_path', 'sanitized_path', 'original_sha256', 'sanitized_sha256'))
        writer.writerows(rows)
    report = validate(docs)
    audit = ccm_audit(source)
    report.update(source_files=len(before), source_bytes=sum((source / n).stat().st_size for n in before),
                  source_unchanged=before == snapshot(source), renamed_files=sum(a != c for a, b, c, d, e in rows),
                  special_names_renamed=sum('\uf03f' in a for a in before), youtube_iframes_upgraded=youtube,
                  unchanged_non_html_css_assets=sum(Path(c).suffix not in ('.html', '.css') and d == e for a, b, c, d, e in rows),
                  asset_hash_mismatches=[c for a, b, c, d, e in rows if Path(c).suffix not in ('.html', '.css') and d != e],
                  ccm_audit=audit,
                  tile_image_note='Missing original 144px TileImage replaced with the existing local RegeneMedLogoSquire.png; no new image downloaded.',
                  limitations=['HTTP/browser/external availability checks are not performed by this tool.', 'Dynamic JavaScript URLs and anchors require browser review.', 'noindex is not access control.'])
    report['passed'] = report['passed'] and report['source_unchanged'] and not report['asset_hash_mismatches'] and not audit['nondefinition_uses'] and report['public_files'] == len(before) + 1
    (metadata / 'validation-report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (metadata / 'output-sha256.json').write_text(json.dumps(snapshot(docs), indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', type=Path, help='Read-only validation of an existing docs directory')
    args = parser.parse_args()
    if args.check:
        report = validate(args.check)
    elif args.source:
        report = prepare(args.source, args.output)
    else:
        parser.error('--source or --check required')
    print(json.dumps({k: v for k, v in report.items() if k != 'external_references'}, indent=2, ensure_ascii=True))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
