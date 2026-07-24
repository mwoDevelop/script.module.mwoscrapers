# MwoScrapers

Auditable external-provider module for Kodi 21/Omega and Umbrella.

The project implements the provider contract independently and keeps provider
selection, network parsing, normalization, provenance, and health isolation in
small modules. It never calls a debrid service.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest
python tools/validate_addon.py .
```

## Kodi contract

Umbrella loads:

```python
mwoscrapers.sources(specified_folders=None, ret_all=False)
```

The result is a list of `(provider_name, provider_class)` pairs. Cross-provider
merging, filtering, sorting, and resolver behavior remain Umbrella's
responsibility.

## Providers

- `torrentio`: enabled by default.
- `comet`: opt-in until its live behavior is qualified on the target device.

Both adapters are original implementations against the Stremio-compatible JSON
contract. No source file from CocoScrapers, ViperScrapers, or Magneto is
copied.
