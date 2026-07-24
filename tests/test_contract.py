from mwoscrapers import PROVIDER_API_VERSION, sources
from mwoscrapers.contract import validate_provider_class, validate_result


def test_all_registered_providers_implement_contract():
    assert PROVIDER_API_VERSION == 1
    providers = sources(ret_all=True)
    assert [name for name, _ in providers] == ["torrentio", "comet"]
    for _, provider_class in providers:
        assert validate_provider_class(provider_class)


def test_contract_rejects_incomplete_result():
    try:
        validate_result({"provider": "x"})
    except ValueError as exc:
        assert "provider result missing" in str(exc)
    else:
        raise AssertionError("incomplete result accepted")
