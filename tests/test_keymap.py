"""Regression checks for the CT-90405 profile instead of generic Toshiba codes."""

from custom_components.toshiba_legacy.const import KEYS


def test_ct90405_menu_and_navigation():
    # MENU 0x5b is from the CT-90405 table and was confirmed on the physical TV.
    assert KEYS["menu"] == "40bf5b"
    assert KEYS["info"] == "40bf16"
    assert KEYS["exit"] == "40bf43"
    assert KEYS["input"] == "40bf14"
    assert [KEYS[key] for key in ["up", "right", "down", "left", "ok", "back"]] == [
        "40bf19",
        "40bf40",
        "40bf1d",
        "40bf42",
        "40bf21",
        "40bf64",
    ]
