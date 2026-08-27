import csv
from decimal import Decimal
from pathlib import Path

from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.semantic_handoff import DatasetBinding, DatasetUsage, FieldBinding, SemanticHandoff
from ocl_agent.part2_analysis.context import enrich_with_context, load_context
from ocl_agent.part2_analysis.engine import analyse_records
from ocl_agent.schemas import OCLJudgment, OCLRecord, ReviewStatus, Scope, SourceReference


def _write(path: Path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def test_optional_context_adds_ratios_and_missing_context_does_not_block(tmp_path: Path):
    _write(tmp_path / "revenue.csv", ["Period", "Value"], [["FY25", "1000"]])
    _write(tmp_path / "payroll.csv", ["Period", "Value"], [["FY25", "500"]])
    _write(tmp_path / "expense.csv", ["Period", "Value"], [["FY25", "800"]])
    package = StandardizedPackage(
        tmp_path,
        (tmp_path / "revenue.csv", tmp_path / "payroll.csv", tmp_path / "expense.csv"),
        None,
        None,
        None,
        None,
    )
    handoff = SemanticHandoff("1.0", "CONFIRMED", "x", (
        DatasetBinding("revenue.csv", (DatasetUsage.REVENUE_CONTEXT,), FieldBinding(period="Period", amount="Value")),
        DatasetBinding("payroll.csv", (DatasetUsage.PAYROLL_CONTEXT,), FieldBinding(period="Period", amount="Value")),
        DatasetBinding("expense.csv", (DatasetUsage.EXPENSE_CONTEXT,), FieldBinding(period="Period", amount="Value")),
    ))
    context = load_context(package, handoff)
    assert context["revenue"]["FY25"] == Decimal("1000")
    assert context["expense"]["FY25"] == Decimal("800")
    record = OCLRecord(SourceReference("1"), "FY25", Decimal("200"), "Bonus", OCLJudgment("Bonus", Scope.IN_SCOPE, "Bonus", review_status=ReviewStatus.REVIEWED))
    base = analyse_records([record])
    enriched = enrich_with_context(base, [record], context)
    table = next(item for item in enriched.tables if item.key == "context_ratios")
    assert table.rows[0][3] == 20.0
    assert table.rows[0][5] == 40.0
    assert table.rows[0][7] == 25.0
    assert enrich_with_context(base, [record], {}) == base


def test_shared_context_dataset_applies_filters_independently_per_usage(tmp_path: Path):
    _write(
        tmp_path / "operating_context.csv",
        ["Period", "Operating_Metric", "Amount"],
        [
            ["FY25", "Revenue", "1000"],
            ["FY25", "Shipments", "999999"],
            ["FY25", "Energy Expense", "100"],
            ["FY25", "Maintenance Expense", "200"],
            ["FY25", "Freight Expense", "300"],
            ["FY25", "Payroll Expense", "500"],
        ],
    )
    package = StandardizedPackage(tmp_path, (tmp_path / "operating_context.csv",), None, None, None, None)
    handoff = SemanticHandoff("1.0", "CONFIRMED", "x", (
        DatasetBinding(
            "operating_context.csv",
            (
                DatasetUsage.REVENUE_CONTEXT,
                DatasetUsage.PAYROLL_CONTEXT,
                DatasetUsage.EXPENSE_CONTEXT,
            ),
            FieldBinding(period="Period", amount="Amount"),
            usage_filters={
                DatasetUsage.REVENUE_CONTEXT: {"Operating_Metric": ("Revenue",)},
                DatasetUsage.PAYROLL_CONTEXT: {"Operating_Metric": ("Payroll Expense",)},
                DatasetUsage.EXPENSE_CONTEXT: {
                    "Operating_Metric": ("Energy Expense", "Maintenance Expense", "Freight Expense")
                },
            },
        ),
    ))

    context = load_context(package, handoff)

    assert context == {
        "revenue": {"FY25": Decimal("1000")},
        "payroll": {"FY25": Decimal("500")},
        "expense": {"FY25": Decimal("600")},
    }
