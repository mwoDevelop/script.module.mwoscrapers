import py_compile
from pathlib import Path
from xml.etree import ElementTree

WRAPPER = Path("wrapper/script.mwoscrapers")


def test_wrapper_is_visible_program_addon_with_module_dependency():
    addon = ElementTree.parse(WRAPPER / "addon.xml").getroot()

    assert addon.attrib["id"] == "script.mwoscrapers"
    assert (
        addon.find("./requires/import[@addon='script.module.mwoscrapers']").attrib[
            "version"
        ]
        == "0.1.3"
    )
    extension = addon.find("./extension[@point='xbmc.python.script']")
    assert extension.attrib["library"] == "default.py"
    assert extension.findtext("provides") == "executable"


def test_wrapper_entrypoint_compiles(tmp_path):
    py_compile.compile(
        WRAPPER / "default.py",
        cfile=tmp_path / "default.pyc",
        doraise=True,
    )
