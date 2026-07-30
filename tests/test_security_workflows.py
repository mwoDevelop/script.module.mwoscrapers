from pathlib import Path


ROOT = Path(__file__).parents[1]
PIN = "28f29307987e277836cb610c944c120d60638ba4"


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
