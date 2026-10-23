"""Reproduction must not replace the observations used in published claims."""

import pytest

from releaselens.benchmark import run as benchmark_run
from releaselens.evaluate import run


@pytest.mark.parametrize("runner", [run, benchmark_run])
def test_evaluate_refuses_existing_evidence_before_running(tmp_path, runner):
    output = tmp_path / "frozen.json"
    output.write_bytes(b"original measured evidence\n")
    with pytest.raises(FileExistsError, match="Choose a new output path"):
        runner(output)
    assert output.read_bytes() == b"original measured evidence\n"
