from pathlib import Path

from tools.validate_addon import validate


def test_addon_and_registry_validate():
    root = Path(__file__).parents[1]
    assert validate(root) == ["torrentio", "comet"]
