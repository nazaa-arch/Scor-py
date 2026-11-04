"""Unit tests for the scorpy CLI interface."""

from click.testing import CliRunner
from scorpy.cli import main


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "scorpy" in result.output


def test_cli_evaluate_orders():
    runner = CliRunner()
    result = runner.invoke(main, ["evaluate-orders", "--data", "data/sample_orders.csv"])
    assert result.exit_code == 0
    assert "Perfect Order Fulfillment" in result.output
    assert "OTIF" in result.output


def test_cli_evaluate_orders_json():
    runner = CliRunner()
    result = runner.invoke(
        main, ["evaluate-orders", "--data", "data/sample_orders.csv", "--format", "json"]
    )
    assert result.exit_code == 0
    assert '"Perfect_Order_Fulfillment"' in result.output


def test_cli_evaluate_orders_group_by():
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["evaluate-orders", "--data", "data/sample_orders.csv", "--group-by", "customer_segment"],
    )
    assert result.exit_code == 0
    assert "Enterprise" in result.output
    assert "Retail" in result.output


def test_cli_evaluate_c2c():
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "evaluate-c2c",
            "--cogs",
            "15000000000",
            "--revenue",
            "22500000000",
            "--inventory",
            "2100000000",
            "--ar",
            "1800000000",
            "--ap",
            "1400000000",
        ],
    )
    assert result.exit_code == 0
    assert "46.2 days" in result.output


def test_cli_evaluate_financials():
    runner = CliRunner()
    result = runner.invoke(
        main, ["evaluate-financials", "--financials", "data/sample_financials.csv"]
    )
    assert result.exit_code == 0
    assert "Total SCM Cost" in result.output


def test_cli_simulate():
    runner = CliRunner()
    result = runner.invoke(
        main, ["simulate", "--data", "data/sample_orders.csv", "--lead-shift", "2", "--runs", "50"]
    )
    assert result.exit_code == 0
    assert "MONTE CARLO SIMULATION" in result.output
    assert "OTIF_rate" in result.output
