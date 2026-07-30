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

Each provider has an optional endpoint setting. Leaving it empty uses the
public default. A private endpoint can point at a self-hosted provider or at
the bundled LAN relay, for example:

```text
http://qnap.lan:18766/torrentio
```

The endpoint setting is deliberately owned by the provider adapter, so adding
another provider does not change Umbrella or the registry contract.
If a configured relay fails at the transport, HTTP, JSON, or stream-contract
boundary, the adapter retries its code-defined public endpoint. A valid empty
response is authoritative and is not duplicated. This keeps QNAP optional;
the public fallback can still be rejected by a provider for a particular VPN
exit address.

## Provider metadata relay

`relay/` contains a separate, credential-free container. It exists for clients
whose VPN exit receives `HTTP 403` from a public provider:

- only fixed `torrentio` and `comet` Stremio stream paths are accepted;
- arbitrary proxy targets, URL credentials, query strings and response bodies
  larger than 2 MiB are rejected;
- only public stream metadata is relayed; Real-Debrid credentials and resolved
  media URLs never pass through it;
- responses are contract-checked and cached briefly in memory;
- the image runs read-only as a non-root user and is built for
  `linux/amd64` plus `linux/arm/v7`.

Release tags named `relay-v*` publish an immutable GHCR manifest. Deploy by
digest and bind the service to the trusted LAN; do not expose it to the
Internet.
