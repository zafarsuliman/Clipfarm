from pathlib import Path
from clipfarm.qa import technical_qa

def test_qa_missing_file():
    result = technical_qa(Path("does-not-exist.mp4"))
    assert result["passed"] is False
    assert "missing_file" in result["issues"]
