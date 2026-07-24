"""Runtime validation for the stable Umbrella provider contract."""

REQUIRED_CLASS_ATTRIBUTES = ("hasMovies", "hasEpisodes", "pack_capable", "priority")
REQUIRED_RESULT_FIELDS = (
    "provider",
    "source",
    "hash",
    "name",
    "quality",
    "language",
    "url",
    "direct",
    "debridonly",
)


def validate_provider_class(provider_class):
    missing = [name for name in REQUIRED_CLASS_ATTRIBUTES if not hasattr(provider_class, name)]
    if not callable(getattr(provider_class, "sources", None)):
        missing.append("sources")
    if missing:
        raise TypeError("provider contract missing: %s" % ", ".join(sorted(missing)))
    return True


def validate_result(item):
    missing = [name for name in REQUIRED_RESULT_FIELDS if name not in item]
    if missing:
        raise ValueError("provider result missing: %s" % ", ".join(sorted(missing)))
    if item["source"] != "torrent":
        raise ValueError("only normalized torrent results are supported")
    return True
