from foundry.gui.lang import LANGUAGE_OPTIONS


def test_english_is_available():
    assert ('English', './foundry/data/lang/english.json') in LANGUAGE_OPTIONS
