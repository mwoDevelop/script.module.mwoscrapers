import mwoscrapers.registry as registry


def test_default_registry_only_returns_enabled(monkeypatch):
    monkeypatch.setattr(registry, "provider_enabled", lambda name: name == "torrentio")
    assert [name for name, _ in registry.sources()] == ["torrentio"]


def test_ret_all_and_folder_filter():
    assert [name for name, _ in registry.sources(("torrents",), ret_all=True)] == [
        "torrentio",
        "comet",
    ]
    assert registry.sources(("missing",), ret_all=True) == []


def test_pack_sources():
    assert registry.pack_sources() == []
