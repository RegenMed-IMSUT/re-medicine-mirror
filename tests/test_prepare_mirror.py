import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import prepare_mirror as mirror


class NamingTests(unittest.TestCase):
    def test_wget_query_suffix_is_removed(self):
        self.assertEqual(mirror.sanitized_name('assets/main.css\uf03fts=123.css'), 'assets/main.css')


class ConversionTests(unittest.TestCase):
    def setUp(self):
        Path(__file__).resolve().parents[1].joinpath('_upload_metadata').mkdir(exist_ok=True)

    def test_collision_stops_before_any_public_write(self):
        import tempfile
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '_upload_metadata') as temp:
            source = Path(temp) / 'source'
            source.mkdir()
            (source / 'a.js').write_bytes(b'a')
            (source / 'a.js\uf03fver=1').write_bytes(b'b')
            with self.assertRaisesRegex(ValueError, 'collision'):
                mirror.prepare(source, Path(temp) / 'output')
            self.assertFalse((Path(temp) / 'output').exists())

    def test_css_relative_urls_and_imports_preserve_subpath(self):
        mapping = {'assets/a.css\uf03fv=1.css': 'assets/a.css', 'download_file/18/0': 'download_file/18/0.png'}
        text = '@import "../assets/a.css%3Fv=1.css"; x {background:url(\'../download_file/18/0\')}'
        result = mirror.transform(text, 'assets/main.css', mapping)
        self.assertIn('@import "a.css"', result)
        self.assertIn("url('../download_file/18/0.png')", result)
        self.assertNotIn('url(\'/download_file', result)

    def test_validation_detects_missing_srcset_and_root_paths(self):
        import tempfile
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '_upload_metadata') as temp:
            docs = Path(temp)
            (docs / 'index.html').write_text('<html><head><meta name="robots" content="noindex"></head><body><p class="trial-mirror-notice"></p><img srcset="missing.png 1x, absent.png 2x"><script src="/bad.js"></script></body></html>', encoding='utf-8')
            result = mirror.validate(docs)
            self.assertFalse(result['passed'])
            self.assertEqual(len(result['missing_local']), 2)
            self.assertEqual(len(result['root_absolute']), 1)

    def test_magic_bytes_choose_extensions_and_reject_unknown(self):
        self.assertEqual(mirror.sanitized_name('download_file/18/0', b'\x89PNG\r\n\x1a\n'), 'download_file/18/0.png')
        with self.assertRaises(ValueError):
            mirror.sanitized_name('unknown/0', b'unknown')
        with self.assertRaises(ValueError):
            mirror.sanitized_name('unsafe name.js')

    def test_nested_references_images_noindex_and_readonly_source(self):
        import tempfile
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '_upload_metadata') as temp:
            root = Path(temp)
            source = root / 'source'
            (source / 'nested').mkdir(parents=True)
            (source / 'assets').mkdir()
            (source / 'download_file/17').mkdir(parents=True)
            (source / 'assets/a.js\uf03fver=1').write_bytes(b'const a = 1;')
            (source / 'download_file/17/0').write_bytes(b'\xff\xd8\xfffixture')
            page = '<html><head></head><body><script src="../assets/a.js%3Fver=1"></script><img src="../download_file/17/0" srcset="../download_file/17/0 1x, ../download_file/17/0 2x"><a href="http://https://example.com">old</a></body></html>'
            (source / 'nested/page.html').write_text(page, encoding='utf-8')
            before = mirror.snapshot(source)
            result = mirror.prepare(source, root / 'output')
            self.assertTrue(result['passed'])
            converted = (root / 'output/docs/nested/page.html').read_text(encoding='utf-8')
            self.assertIn('../assets/a.js', converted)
            self.assertNotIn('%3F', converted)
            self.assertIn('../download_file/17/0.jpg 2x', converted)
            self.assertIn('name="robots" content="noindex"', converted)
            self.assertIn('http://https://example.com', converted)
            self.assertEqual(before, mirror.snapshot(source))
            with self.assertRaises(FileExistsError):
                mirror.prepare(source, root / 'output')


if __name__ == '__main__':
    Path(__file__).resolve().parents[1].joinpath('_upload_metadata').mkdir(exist_ok=True)
    unittest.main()
