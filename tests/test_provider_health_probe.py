import importlib.util
from pathlib import Path


def _module():
    path = Path("tools/probe_provider_health.py")
    spec = importlib.util.spec_from_file_location("probe_provider_health", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_serializes_only_sanitized_counts_and_timings():
    module = _module()

    class Healthy:
        hasMovies = True
        hasEpisodes = True

        def sources(self, data, _host_dict):
            assert "imdb" in data
            return [{"url": "must-not-leak", "hash": "must-not-leak"}]

    ticks = iter((1.0, 1.25, 2.0, 2.5))
    report = module.probe([("healthy", Healthy)], monotonic=lambda: next(ticks))

    assert report == {
        "schema": 1,
        "healthy": True,
        "providers": [
            {
                "provider": "healthy",
                "healthy": True,
                "checks": [
                    {
                        "capability": "movie",
                        "elapsed_seconds": 0.25,
                        "error_type": None,
                        "healthy": True,
                        "result_count": 1,
                    },
                    {
                        "capability": "episode",
                        "elapsed_seconds": 0.5,
                        "error_type": None,
                        "healthy": True,
                        "result_count": 1,
                    },
                ],
            }
        ],
    }
    assert "must-not-leak" not in str(report)


def test_probe_fails_closed_for_empty_results_and_exceptions():
    module = _module()

    class Empty:
        hasMovies = True
        hasEpisodes = False

        def sources(self, _data, _host_dict):
            return []

    class Broken:
        hasMovies = False
        hasEpisodes = True

        def sources(self, _data, _host_dict):
            raise RuntimeError("sensitive detail")

    report = module.probe(
        [("empty", Empty), ("broken", Broken)], monotonic=lambda: 1.0
    )

    assert report["healthy"] is False
    assert report["providers"][0]["checks"][0]["result_count"] == 0
    assert report["providers"][1]["checks"][0]["error_type"] == "RuntimeError"
    assert "sensitive detail" not in str(report)
