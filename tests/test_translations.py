from __future__ import annotations

import os
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QTranslator


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "translations" / "novaprofiles_pt_BR.ts"
COMPILED_CATALOG = CATALOG.with_suffix(".qm")
PLACEHOLDER = re.compile(r"%\d+|\{[A-Za-z_][A-Za-z0-9_]*\}")
QT_APP = QCoreApplication.instance() or QCoreApplication([])


class TranslationTests(unittest.TestCase):
    def test_catalog_is_complete_and_preserves_placeholders(self):
        root = ET.parse(CATALOG).getroot()
        messages = root.findall(".//message")
        self.assertGreaterEqual(len(messages), 150)
        for message in messages:
            source = message.findtext("source", default="")
            translation_node = message.find("translation")
            self.assertIsNotNone(translation_node, source)
            self.assertNotIn(
                translation_node.attrib.get("type"),
                {"unfinished", "vanished", "obsolete"},
                source,
            )
            translation = "".join(translation_node.itertext())
            self.assertTrue(translation.strip(), source)
            self.assertEqual(
                sorted(PLACEHOLDER.findall(source)),
                sorted(PLACEHOLDER.findall(translation)),
                source,
            )

    def test_compiled_catalog_loads_qml_and_backend_translations(self):
        self.assertTrue(COMPILED_CATALOG.is_file())
        translator = QTranslator()
        self.assertTrue(translator.load(str(COMPILED_CATALOG)))
        self.assertTrue(QT_APP.installTranslator(translator))
        try:
            self.assertEqual(
                QCoreApplication.translate("Main", "Settings"),
                "Configurações",
            )
            self.assertEqual(
                QCoreApplication.translate("AppController", "Open Nova Profiles"),
                "Abrir Nova Profiles",
            )
        finally:
            QT_APP.removeTranslator(translator)


if __name__ == "__main__":
    unittest.main()
