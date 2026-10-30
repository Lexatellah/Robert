import os, pathlib, subprocess, sys, tempfile, zipfile
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from robert.verify import verify_bundle

ADDR = "0x28C6c06298d514Db089934071355E5743bf21d60"
IBAN = "DE89370400440532013000"


@pytest.mark.skipif(os.environ.get("ROBERT_INTEGRATION") != "1",
                    reason="set ROBERT_INTEGRATION=1 to run")
def test_pipeline_end_to_end_on_real_address():
    out = pathlib.Path(tempfile.mkdtemp()) / "bundle.zip"
    cmd = [sys.executable, "-m", "robert.cli", "report",
           "--address", ADDR, "--chain", "1",
           "--iban", IBAN, "--amount", "100",
           "--when", "1730000000", "--window-hours", "8760",
           "--out", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr
    assert out.exists(), "bundle not written"

    z = zipfile.ZipFile(out)
    assert "manifest.json" in z.namelist()
    assert "audit.jsonl" in z.namelist()

    result = verify_bundle(out)
    assert result.ok, [c for c in result.checks if not c["passed"]]

    sent_to = 0
    for n in z.namelist():
        if n.startswith("assertions/"):
            body = z.read(n).decode()
            if '"predicate": "sent_to"' in body:
                sent_to += 1
    assert sent_to >= 1, "no sent_to assertions in bundle"
