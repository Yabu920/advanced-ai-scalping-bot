from risk.margin_check import estimate_margin_requirement


def plan() -> dict:
    return {"lot_size": 0.5}


def test_missing_margin_info_returns_known_false_warning() -> None:
    result = estimate_margin_requirement(plan(), {}, {"margin_free": 1000})
    assert result["known"] is False
    assert result["valid"] is True
    assert result["warnings"]


def test_margin_initial_estimates_margin() -> None:
    result = estimate_margin_requirement(plan(), {"margin_initial": 100}, {"margin_free": 1000})
    assert result["known"] is True
    assert result["estimated_margin"] == 50


def test_free_margin_too_low_fails() -> None:
    result = estimate_margin_requirement(plan(), {"margin_initial": 100}, {"margin_free": 10})
    assert result["valid"] is False
    assert result["issues"]
