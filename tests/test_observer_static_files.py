import unittest
from pathlib import Path


class ObserverStaticFilesTest(unittest.TestCase):
    def test_observer_ui_files_exist_and_reference_assets_and_websocket(self):
        root = Path("web/observer")
        index = root / "index.html"
        styles = root / "styles.css"
        app = root / "app.js"

        self.assertTrue(index.exists())
        self.assertTrue(styles.exists())
        self.assertTrue(app.exists())

        index_html = index.read_text(encoding="utf-8")
        app_js = app.read_text(encoding="utf-8")

        self.assertIn('/static/styles.css', index_html)
        self.assertIn('/static/app.js', index_html)
        self.assertIn("/ws", app_js)
