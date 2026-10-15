from releaselens.evaluate import percentile, wilson


def test_metric_edge_cases():
    assert percentile([1, 2, 3], 0.5) == 2
    assert wilson(0, 0) is None
    assert wilson(0, 8)[0] == 0
    assert wilson(0, 8)[1] > 0  # Zero observed leaks does not prove zero risk.
    assert wilson(3, 3)[0] < 1
