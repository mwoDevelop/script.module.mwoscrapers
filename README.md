# MwoScrapers

Audytowalny moduł zewnętrznych providerów dla Kodi 21/Omega i Umbrella.

Projekt implementuje kontrakt providerów niezależnie, a wybór źródeł, parsowanie
sieciowe, normalizację, pochodzenie i izolację błędów utrzymuje w małych modułach.
Nigdy nie wywołuje usługi debrid.

## Rozwój

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest
python tools/validate_addon.py .
```

## Kontrakt Kodi

Umbrella ładuje:

```python
mwoscrapers.sources(specified_folders=None, ret_all=False)
```

Wynikiem jest lista par `(provider_name, provider_class)`. Scalanie wyników wielu
providerów, filtrowanie, sortowanie i działanie resolvera pozostają
odpowiedzialnością Umbrella.

## Providerzy

- `torrentio`: podstawowy adapter Stremio JSON;
- `comet`: niezależny publiczny fallback Stremio JSON;
- `torz`: tryb P2P StremThru bez magazynu debrid;
- `mediafusion`: tryb Direct P2P bez danych debrid;
- `eztv`: strukturalne źródło JSON dla odcinków;
- `piratebay`: strukturalne API JSON dla filmów i odcinków.

Wszystkie sześć adapterów jest domyślnie włączonych i przeszło tę samą macierz
kwalifikacyjną na BlueStacks oraz X88 Pro. Implementacje są własne i korzystają
wyłącznie z publicznych kontraktów JSON. Żaden plik źródłowy CocoScrapers,
ViperScrapers ani Magneto nie został skopiowany.

Codzienny audyt artefaktów śledzi obecnie dostępne obserwacje CocoScrapers i
ViperScrapers. Dawna obserwacja Magneto jest zachowana w
`.upstream/retired-observations.json`; przypięty artefakt repozytorium został
usunięty upstream i nie jest aktywną zależnością runtime.

Każdy provider ma opcjonalne ustawienie endpointu. Pusta wartość wybiera publiczną
wartość domyślną. Prywatny endpoint może wskazywać self-hosted provider lub dołączony
relay LAN, na przykład:

```text
http://qnap.lan:18766/torrentio
```

Ustawienie endpointu celowo należy do adaptera, dzięki czemu dodanie kolejnego
providera nie zmienia Umbrella ani kontraktu registry. Jeżeli skonfigurowany relay
zawiedzie na granicy transportu, HTTP, JSON lub kontraktu stream, adapter ponawia
próbę z publicznym endpointem zapisanym w kodzie. Poprawna pusta odpowiedź jest
wiążąca i nie jest duplikowana. QNAP pozostaje opcjonalny; publiczny fallback może
nadal zostać odrzucony przez providera dla konkretnego adresu wyjściowego VPN.
Pozostałe niezależne źródła zapobiegają uzależnieniu całego wyszukiwania od relay
QNAP albo jednej usługi publicznej.

## Dzienna kontrola dostępności

Workflow `probe-provider-health.yml` wywołuje publiczne kontrakty bez relay i bez
credentiali. Artefakt zawiera wyłącznie nazwę providera, typ próby, czas, status
błędu i liczbę wyników. Nazwy źródeł, magnety, infohashe i URL-e treści nie są
zapisywane. Trzy kolejne udane dzienne próby są bramką promocji zbiorczego wydania
z testing do stable.

## Relay metadanych providerów

`relay/` zawiera oddzielny kontener bez credentiali. Służy klientom, których wyjście
VPN otrzymuje `HTTP 403` od publicznego providera:

- akceptowane są wyłącznie stałe ścieżki stream Stremio `torrentio` i `comet`;
- dowolne cele proxy, credentiale w URL, query string oraz odpowiedzi powyżej 2 MiB
  są odrzucane;
- przekazywane są tylko publiczne metadane; credentiale Real-Debrid i rozwiązane
  URL-e mediów nigdy nie przechodzą przez relay;
- odpowiedzi są sprawdzane kontraktowo i krótko buforowane w pamięci;
- obraz działa tylko do odczytu jako użytkownik bez roota i jest budowany dla
  `linux/amd64` oraz `linux/arm/v7`.

Tagi wydań `relay-v*` publikują niezmienny manifest GHCR. Wdrażaj po digescie i
wiąż usługę wyłącznie z zaufaną siecią LAN; nie wystawiaj jej do Internetu.
