# =============================================================================
# Author: Quan123781 <quannguyen0442@gmail.com>
# Day 10 lab - Evaluation, Observability, Corruption & Integration
# =============================================================================
from __future__ import annotations

from typing import Any

from core.utils import now_utc, write_text

METRIC_KEYS = (
    "samples",
    "retrieval_hit_rate",
    "mean_token_f1",
    "judge_accuracy",
    "mean_judge_score",
)

FRESHNESS_KEYS = (
    "total_rows",
    "latest_published",
    "oldest_published",
    "fresh_rows",
    "stale_rows",
    "unknown_age_rows",
    "max_age_days",
    "is_fresh",
)


def _cell(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, dict):
        return ", ".join(f"{key}={_cell(item)}" for key, item in value.items()) or "n/a"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_cell(item) for item in value) or "none"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _delta(base_value: Any, other_value: Any) -> Any:
    base_number = _number(base_value)
    other_number = _number(other_value)
    if base_number is None or other_number is None:
        return None
    # Counts such as `samples` stay counts; only the rate metrics get decimal places.
    if isinstance(base_value, int) and isinstance(other_value, int):
        return int(other_number - base_number)
    return other_number - base_number


def _kv_table(payload: Any, key_header: str = "Field", value_header: str = "Value") -> list[str]:
    if not isinstance(payload, dict) or not payload:
        return ["_No data provided._", ""]
    lines = [f"| {key_header} | {value_header} |", "| --- | --- |"]
    lines += [f"| `{key}` | {_cell(value)} |" for key, value in payload.items()]
    lines.append("")
    return lines


def _metrics_table(metrics: dict[str, Any]) -> list[str]:
    lines = ["| Metric | Value |", "| --- | ---: |"]
    for key in METRIC_KEYS:
        lines.append(f"| `{key}` | {_cell(metrics.get(key))} |")
    lines.append("")
    return lines


def _quality_section(quality: dict[str, Any], heading: str) -> list[str]:
    lines = [heading, ""]
    if not isinstance(quality, dict) or not quality:
        return lines + ["_No quality payload provided._", ""]

    status = "PASS" if quality.get("success") else "FAIL"
    lines.append(
        f"- Overall: **{status}** "
        f"({_cell(quality.get('passed_checks'))}/{_cell(quality.get('total_checks'))} checks passed)"
    )
    lines.append(f"- Rows checked: {_cell(quality.get('row_count'))}")
    if quality.get("failed_check_names"):
        lines.append(f"- Failed checks: {_cell(quality.get('failed_check_names'))}")
    lines.append("")

    checks = quality.get("checks")
    if isinstance(checks, list) and checks:
        lines += ["| Check | Status | Observed | Expected |", "| --- | --- | --- | --- |"]
        for check in checks:
            lines.append(
                f"| `{_cell(check.get('name'))}` | {_cell(check.get('status'))} "
                f"| {_cell(check.get('observed'))} | {_cell(check.get('expected'))} |"
            )
        lines.append("")
    return lines


def _freshness_section(freshness: dict[str, Any], heading: str) -> list[str]:
    lines = [heading, ""]
    if not isinstance(freshness, dict) or not freshness:
        return lines + ["_No freshness payload provided._", ""]
    lines.append(f"- Fresh: **{'yes' if freshness.get('is_fresh') else 'no'}** "
                 f"(threshold {_cell(freshness.get('threshold_days'))} days)")
    lines.append("")
    lines += ["| Signal | Value |", "| --- | ---: |"]
    for key in FRESHNESS_KEYS:
        lines.append(f"| `{key}` | {_cell(freshness.get(key))} |")
    lines.append("")
    return lines


def _ragas_section(metrics: dict[str, Any]) -> list[str]:
    ragas = metrics.get("ragas")
    if not ragas:
        return []
    lines = ["### Ragas", ""]
    if isinstance(ragas, dict) and "skipped" in ragas:
        return lines + [f"_Skipped: {_cell(ragas['skipped'])}_", ""]
    if isinstance(ragas, dict) and "error" in ragas:
        return lines + [f"_Failed: {_cell(ragas['error'])}_", ""]
    return lines + _kv_table(ragas, "Ragas metric", "Value")


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline markdown report from the artifacts the pipeline just produced."""
    lines: list[str] = [
        "# Phase 1 - Baseline report",
        "",
        f"_Generated at {now_utc().isoformat(timespec='seconds')}_",
        "",
        "Every number below is rendered from the artifacts written by this run; nothing is",
        "typed in by hand.",
        "",
        "## 1. Source",
        "",
    ]
    lines += _kv_table(source_summary, "Source field", "Value")

    lines += ["## 2. Evaluation metrics", ""]
    lines += _metrics_table(metrics if isinstance(metrics, dict) else {})
    lines += _ragas_section(metrics if isinstance(metrics, dict) else {})

    lines += _quality_section(quality, "## 3. Data quality")
    lines += _freshness_section(freshness, "## 4. Freshness")

    lines += [
        "## 5. How to reproduce",
        "",
        "```bash",
        "uv run python script/run_phase1.py",
        "```",
        "",
    ]
    write_text(report_path, "\n".join(lines) + "\n")


def _comparison_table(
    baseline: dict[str, Any],
    corrupted: dict[str, Any],
    repaired: dict[str, Any],
) -> list[str]:
    lines = [
        "| Metric | Baseline | Corrupted | Repaired | Delta corrupted | Delta repaired |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key in METRIC_KEYS:
        base_value = baseline.get(key)
        corrupted_value = corrupted.get(key)
        repaired_value = repaired.get(key)
        delta_corrupted = _delta(base_value, corrupted_value)
        delta_repaired = _delta(base_value, repaired_value)
        lines.append(
            f"| `{key}` | {_cell(base_value)} | {_cell(corrupted_value)} | {_cell(repaired_value)} "
            f"| {_cell(delta_corrupted)} | {_cell(delta_repaired)} |"
        )
    lines.append("")
    return lines


def _sample_count_warning(
    baseline: dict[str, Any],
    corrupted: dict[str, Any],
    repaired: dict[str, Any],
) -> list[str]:
    counts = {
        "baseline": baseline.get("samples"),
        "corrupted": corrupted.get("samples"),
        "repaired": repaired.get("samples"),
    }
    known = {state: value for state, value in counts.items() if value is not None}
    if len(set(known.values())) <= 1:
        return []
    return [
        f"> **Warning:** the three runs scored a different number of samples ({_cell(counts)}). "
        "The comparison below is not valid unless all three use the same test set.",
        "",
    ]


def _recovery_lines(
    baseline: dict[str, Any],
    corrupted: dict[str, Any],
    repaired: dict[str, Any],
) -> list[str]:
    lines: list[str] = []
    for key in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        base_value = _number(baseline.get(key))
        corrupted_value = _number(corrupted.get(key))
        repaired_value = _number(repaired.get(key))
        if base_value is None or corrupted_value is None or repaired_value is None:
            lines.append(f"- `{key}`: not enough data in all three states to compare.")
            continue

        drop = base_value - corrupted_value
        if drop > 0:
            impact = f"dropped by {drop:.4f} under corruption"
        elif drop < 0:
            impact = f"rose by {-drop:.4f} under corruption, which the corruption log has to explain"
        else:
            impact = "did not move under corruption"

        if drop <= 0:
            recovery = (
                f"repaired sits at {repaired_value:.4f} against a baseline of {base_value:.4f}"
            )
        elif repaired_value >= base_value:
            recovery = f"repaired is back at or above baseline ({repaired_value:.4f})"
        else:
            recovered = (repaired_value - corrupted_value) / drop
            recovery = (
                f"repaired recovered {recovered:.0%} of the gap and is still "
                f"{base_value - repaired_value:.4f} below baseline"
            )
        lines.append(f"- `{key}`: {impact}; {recovery}.")
    lines.append("")
    return lines


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write the baseline / corrupted / repaired comparison report."""
    baseline = baseline_metrics if isinstance(baseline_metrics, dict) else {}
    corrupted = corrupted_metrics if isinstance(corrupted_metrics, dict) else {}
    repaired = repaired_metrics if isinstance(repaired_metrics, dict) else {}

    lines: list[str] = [
        "# Corruption impact and recovery report",
        "",
        f"_Generated at {now_utc().isoformat(timespec='seconds')}_",
        "",
        "The three runs below share one test set, one evaluator and one top-k setting, so the",
        "only variable is the state of the data.",
        "",
    ]
    lines += _sample_count_warning(baseline, corrupted, repaired)

    lines += ["## 1. Metric comparison", ""]
    lines += _comparison_table(baseline, corrupted, repaired)

    lines += ["## 2. Reading the deltas", ""]
    lines += _recovery_lines(baseline, corrupted, repaired)

    lines += _quality_section(corrupted_quality, "## 3. Data quality - corrupted")
    lines += _quality_section(repaired_quality, "## 4. Data quality - repaired")
    lines += _freshness_section(corrupted_freshness, "## 5. Freshness - corrupted")
    lines += _freshness_section(repaired_freshness, "## 6. Freshness - repaired")

    lines += [
        "## 7. Limits of this comparison",
        "",
        "- Baseline quality and freshness payloads are reported in `phase1_report.md`; this",
        "  report only carries the corrupted and repaired ones.",
        "- A metric that did not move is evidence that the corruption did not reach it, not",
        "  evidence that the corruption was harmless.",
        "- Recovery is only claimed where the numbers above show it.",
        "",
        "## 8. How to reproduce",
        "",
        "```bash",
        "uv run python script/run_phase1.py",
        "uv run python script/run_corruption_flow.py",
        "```",
        "",
    ]
    write_text(report_path, "\n".join(lines) + "\n")
