from pathlib import Path

ROOT = Path(__file__).parents[1]
PIN = "304964cf75011827758dfb994f9811367cab89f3"


def test_provider_code_is_scanned_before_tests_execute():
    workflow = (ROOT / ".github/workflows/test.yml").read_text(encoding="utf-8")
    assert "test:\n    needs: malware-scan" in workflow
    assert "git archive HEAD" in workflow
    assert (
        "mwoDevelop/kodi/.github/actions/upstream-malware-scan@" + PIN
    ) in workflow


def test_downloaded_provider_artifacts_are_scanned_without_importing_them():
    workflow = (
        ROOT / ".github/workflows/check-provider-upstreams.yml"
    ).read_text(encoding="utf-8")
    download = workflow.index("Download pinned artifacts")
    scan = workflow.index("Scan downloaded immutable provider artifacts")
    upload = workflow.index("actions/upload-artifact")
    assert download < scan < upload
    assert "candidate-path: upstream-audit" in workflow


def test_relay_dockerfile_is_scanned_before_the_build():
    workflow = (ROOT / ".github/workflows/relay-image.yml").read_text(
        encoding="utf-8"
    )
    scan = workflow.index("Scan exact head before executing the Docker build")
    build = workflow.index("docker/build-push-action")
    assert scan < build
    assert "git archive HEAD" in workflow
