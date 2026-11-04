"""Command-line interface (CLI) for SCOR-Py."""

import json
import click
import pandas as pd
from scorpy import __version__
from scorpy.reliability import ReliabilityMetrics
from scorpy.responsiveness import ResponsivenessMetrics
from scorpy.asset_efficiency import AssetMetrics
from scorpy.cost import CostMetrics
from scorpy.simulator import SupplyChainSimulator


@click.group()
@click.version_option(__version__, prog_name="scorpy")
def main():
    """SCOR-Py CLI: Supply Chain Operations Reference calculation & simulation toolkit."""
    pass


@main.command(name="evaluate-orders")
@click.option(
    "--data", "-d", required=True, type=click.Path(exists=True), help="Path to orders CSV."
)
@click.option("--group-by", "-g", default=None, help="Optional column to group results by.")
@click.option("--grace-days", default=0, type=int, help="Allowed late delivery grace days.")
@click.option(
    "--in-full-tol", default=0.0, type=float, help="Tolerance fraction for In-Full delivery."
)
@click.option(
    "--format", "-f", "output_format", type=click.Choice(["table", "json"]), default="table"
)
def evaluate_orders(data, group_by, grace_days, in_full_tol, output_format):
    """Calculate SCOR Reliability & Responsiveness metrics from an orders log."""
    df = pd.read_csv(data)
    rel = ReliabilityMetrics(
        data=df,
        on_time_grace_days=grace_days,
        in_full_tolerance=in_full_tol,
    )
    resp = ResponsivenessMetrics(data=df)

    if group_by:
        rel_summary = rel.evaluate_all(group_by=group_by)
        ofct_summary = resp.order_fulfillment_cycle_time(group_by=group_by)
        combined = rel_summary.join(ofct_summary)

        if output_format == "json":
            click.echo(combined.to_json(orient="index", indent=2))
        else:
            click.echo(f"\n--- SCOR METRICS GROUPED BY: {group_by} ---")
            click.echo(combined.to_string())
    else:
        rel_summary = rel.evaluate_all()
        ofct_summary = resp.order_fulfillment_cycle_time()
        combined = {**rel_summary, **ofct_summary}

        if output_format == "json":
            click.echo(json.dumps(combined, indent=2))
        else:
            click.echo("\n================ SCOR EVALUATION SUMMARY ================")
            click.echo(
                f"  Perfect Order Fulfillment (RL.1.1) : {combined['Perfect_Order_Fulfillment'] * 100:.2f}%"
            )
            click.echo(f"  On-Time In-Full (OTIF)             : {combined['OTIF_rate'] * 100:.2f}%")
            click.echo(
                f"  On-Time Delivery Rate              : {combined['On_Time_rate'] * 100:.2f}%"
            )
            click.echo(
                f"  In-Full Delivery Rate              : {combined['In_Full_rate'] * 100:.2f}%"
            )
            click.echo(
                f"  Damage-Free Rate                   : {combined['Damage_Free_rate'] * 100:.2f}%"
            )
            click.echo(
                f"  Documentation Accuracy             : {combined['Doc_Accurate_rate'] * 100:.2f}%"
            )
            click.echo("---------------------------------------------------------")
            click.echo(f"  OFCT Mean (RS.1.1)                 : {combined['mean_days']:.1f} days")
            click.echo(f"  OFCT Median (P50)                  : {combined['median_days']:.1f} days")
            click.echo(f"  OFCT P90                           : {combined['p90_days']:.1f} days")
            click.echo("=========================================================\n")


@main.command(name="evaluate-c2c")
@click.option("--cogs", required=True, type=float, help="Annual Cost of Goods Sold.")
@click.option("--revenue", required=True, type=float, help="Annual Revenue.")
@click.option("--inventory", required=True, type=float, help="Average Inventory Value.")
@click.option("--ar", required=True, type=float, help="Accounts Receivable balance.")
@click.option("--ap", required=True, type=float, help="Accounts Payable balance.")
@click.option("--days", default=365, type=int, help="Days in financial year (365 or 360).")
def evaluate_c2c(cogs, revenue, inventory, ar, ap, days):
    """Calculate SCOR Cash-to-Cash Cycle Time (AM.1.1)."""
    assets = AssetMetrics(
        annual_cogs=cogs,
        annual_revenue=revenue,
        avg_inventory_value=inventory,
        accounts_receivable=ar,
        accounts_payable=ap,
        days_in_year=days,
    )
    c2c = assets.cash_to_cash_cycle()
    click.echo("\n=========== CASH-TO-CASH CYCLE TIME (AM.1.1) ===========")
    click.echo(f"  Inventory Days of Supply (IDS) : {c2c['IDS']:.1f} days")
    click.echo(f"  Days Sales Outstanding (DSO)   : {c2c['DSO']:.1f} days")
    click.echo(f"  Days Payable Outstanding (DPO) : {c2c['DPO']:.1f} days")
    click.echo("---------------------------------------------------------")
    click.echo(f"  C2C Net Cycle Time             : {c2c['C2C_days']:.1f} days")
    click.echo("=========================================================\n")


@main.command(name="evaluate-financials")
@click.option(
    "--financials",
    "-f",
    required=True,
    type=click.Path(exists=True),
    help="Path to financials CSV.",
)
def evaluate_financials(financials):
    """Evaluate Total SCM Cost (CO.1.1) from financial records."""
    df = pd.read_csv(financials)
    cost = CostMetrics.from_dataframe(df)
    summary = cost.evaluate_all()
    click.echo("\n============= SUPPLY CHAIN COST (CO.1.1) =============")
    click.echo(f"  Total Revenue        : Rp {summary['revenue']:,.0f}")
    click.echo(f"  Total SCM Cost       : Rp {summary['total_scm_cost']:,.0f}")
    click.echo(f"  SCM Cost % Revenue   : {summary['scm_cost_pct_revenue']:.2f}%")
    click.echo("---------------------------------------------------------")
    click.echo("  Breakdown:")
    for comp, val in summary["breakdown"].items():
        click.echo(
            f"    - {comp.capitalize():14}: Rp {val['amount']:,.0f} ({val['pct_of_scm_cost']:.1f}%)"
        )
    click.echo("=======================================================\n")


@main.command(name="simulate")
@click.option(
    "--data", "-d", required=True, type=click.Path(exists=True), help="Path to orders CSV."
)
@click.option("--lead-shift", default=3, type=float, help="Supplier lead time shift in days.")
@click.option("--runs", default=1000, type=int, help="Number of Monte Carlo iterations.")
@click.option("--seed", default=42, type=int, help="Random seed for reproducibility.")
def simulate(data, lead_shift, runs, seed):
    """Run Monte Carlo disruption simulation on orders."""
    df = pd.read_csv(data)
    sim = SupplyChainSimulator.from_orders(df, seed=seed)
    result = sim.run(n_runs=runs, scenario={"supplier_lead_time_shift_days": lead_shift})
    click.echo(f"\n======== MONTE CARLO SIMULATION ({runs:,} RUNS) ========")
    click.echo(f"Scenario: Supplier Lead Time Shift = {lead_shift:+.1f} days\n")
    summary = result.summary()
    click.echo(summary.to_string(index=False))
    click.echo("========================================================\n")


if __name__ == "__main__":
    main()
