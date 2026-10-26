import unittest
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1] / 'docs'


class RuntimeAssetTests(unittest.TestCase):
    def test_all_backstretch_headers_have_local_relative_image(self):
        import re
        pages = list(ROOT.rglob('*.html'))
        checked = 0
        for page in pages:
            text = page.read_text(encoding='utf-8')
            for value in re.findall(r"var headerImageFilePath = ['\"]([^'\"]+)", text):
                self.assertFalse(value.startswith('/'), str(page))
                self.assertTrue((page.parent / value).is_file(), str(page))
                checked += 1
        self.assertEqual(checked, 46)


if __name__ == '__main__':
    unittest.main()
