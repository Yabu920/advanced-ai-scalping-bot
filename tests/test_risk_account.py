from risk.account import calculate_risk_amount, normalize_account_info


def test_percentage_risk_amount() -> None:
    account = {"equity": 1000, "balance": 900}
    assert calculate_risk_amount(account, 0.5) == 5.0


def test_fixed_risk_amount() -> None:
    account = {"equity": 1000, "balance": 900}
    assert calculate_risk_amount(account, 0.5, True, 7.5) == 7.5


def test_missing_account_safe_behavior() -> None:
    account = normalize_account_info(None)
    assert account["balance"] == 0.0
    assert account["equity"] == 0.0
    assert calculate_risk_amount(account, 1.0) == 0.0
