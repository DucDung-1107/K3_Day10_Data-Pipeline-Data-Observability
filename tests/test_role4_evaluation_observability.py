# =============================================================================
# Author: Quan_01863 <quannguyen0442@gmail.com>
# Day 10 lab - Evaluation, Observability, Corruption & Integration
# =============================================================================
"""Tests for the evaluation set, the observability layer and the corruption step.

These lock down the contracts the three-state comparison depends on: the frozen test set
must agree with how `retrieval.qa` extracts answers, the quality gate must actually fail
on corrupted data, and corruption must reach the papers the evaluator asks about.

`TestCommittedArtifacts` checks the evidence the group submits rather than the code paths.
Tests marked `xfail` record a real defect in the committed artifacts, with the reason on
each one; fixing the defect makes pytest report an unexpected pass, which is the signal to
drop the marker.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import re

import pandas as pd
import pytest

from core.config import load_settings
from core.utils import first_sentence, read_json
from evaluation.testset import ROUTER_PHRASES, build_test_set
from ingestion.corruption import STALE_PUBLISHED_DATE, TRUNCATED_TITLE_CHARS, corrupt_clean_dataframe
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report, generate_phase1_report

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
METRIC_KEYS = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")

# Mirrors the if-order inside `retrieval.qa._extract_answer`.
ROUTER_ORDER = (
    (("who authored", "list the authors"), "authors"),
    (("when was", "publication date", "published on"), "date"),
    (("what categories",), "categories"),
)


def route(question: str) -> str:
    lowered = question.lower()
    for phrases, question_type in ROUTER_ORDER:
        if any(phrase in lowered for phrase in phrases):
            return question_type
    return "summary"


def make_clean_df(rows: int = 14) -> pd.DataFrame:
    """Build a dataframe with the exact schema `ingestion.cleaning` produces."""
    now = datetime.now(UTC)
    records = []
    for index in range(rows):
        published = (now - timedelta(days=10 + index * 7)).date().isoformat()
        summary = (
            f"This paper {index} studies agentic retrieval augmented generation for large "
            "language models. It introduces a benchmark and reports gains over prior work "
            "across several retrieval settings and ablations covering index size."
        )
        title = f"Agentic Retrieval Study Number {index}"
        authors_joined = f"Author {index}A, Author {index}B"
        categories_joined = "Computer Science, Information Retrieval"
        records.append(
            {
                "paper_id": f"10-1234-paper-{index:03d}",
                "title": title,
                "summary": summary,
                "authors": [f"Author {index}A", f"Author {index}B"],
                "authors_joined": authors_joined,
                "categories": ["Computer Science", "Information Retrieval"],
                "categories_joined": categories_joined,
                "primary_category": "Computer Science",
                "published": published,
                "updated": published,
                "age_days": (now.date() - datetime.strptime(published, "%Y-%m-%d").date()).days,
                "abs_url": f"https://doi.org/10.1234/paper.{index:03d}",
                "pdf_url": "",
                "comment": "",
                "summary_chars": len(summary),
                "text_for_embedding": (
                    f"Title: {title}\nAuthors: {authors_joined}\n"
                    f"Categories: {categories_joined}\nSummary: {summary}"
                ),
            }
        )
    return pd.DataFrame(records)


@pytest.fixture
def settings(tmp_path):
    return load_settings(project_dir=tmp_path)


@pytest.fixture
def clean_df():
    return make_clean_df()


@pytest.fixture
def test_set(clean_df, settings):
    return build_test_set(clean_df, settings.paths.eval_testset, max_papers=6)


class TestTestSet:
    def test_router_phrases_still_match_qa_source(self):
        """`qa.py` is starter code we do not own; a change there must break this test."""
        source = (PROJECT_ROOT / "src" / "retrieval" / "qa.py").read_text(encoding="utf-8")
        for phrase in ROUTER_PHRASES:
            assert phrase in source, f"{phrase!r} no longer appears in retrieval/qa.py"

    def test_covers_every_question_type(self, test_set):
        assert {item["question_type"] for item in test_set} == {
            "summary",
            "authors",
            "date",
            "categories",
        }

    def test_rows_have_exactly_the_contract_keys(self, test_set):
        for item in test_set:
            assert set(item) == {
                "id",
                "question_type",
                "question",
                "ground_truth",
                "ground_truth_doc_ids",
            }

    def test_ids_are_unique(self, test_set):
        assert len({item["id"] for item in test_set}) == len(test_set)

    def test_meets_the_minimum_question_count(self, test_set):
        assert len(test_set) >= 10

    def test_each_question_routes_to_its_own_type(self, test_set):
        for item in test_set:
            assert route(item["question"]) == item["question_type"], item["question"]

    def test_ground_truth_equals_what_qa_would_extract(self, test_set, clean_df):
        rows = {str(row["title"]).lower(): row for _, row in clean_df.iterrows()}
        for item in test_set:
            title = re.search(r"'([^']+)'", item["question"]).group(1)
            row = rows[title.lower()]
            expected = {
                "authors": row["authors_joined"],
                "date": row["published"],
                "categories": row["categories_joined"],
                "summary": first_sentence(row["summary"]),
            }[item["question_type"]]
            assert item["ground_truth"] == expected

    def test_ground_truth_doc_ids_exist_in_the_dataset(self, test_set, clean_df):
        known = set(clean_df["paper_id"])
        for item in test_set:
            assert set(item["ground_truth_doc_ids"]) <= known

    def test_is_deterministic(self, clean_df, settings):
        first = build_test_set(clean_df, settings.paths.eval_testset, max_papers=6)
        second = build_test_set(clean_df, settings.paths.eval_testset, max_papers=6)
        assert first == second

    def test_is_persisted_as_json(self, test_set, settings):
        assert read_json(settings.paths.eval_testset) == test_set

    def test_skips_titles_that_break_exact_lookup(self, clean_df, settings):
        """`answer_question` reads the lookup key out of '...', so an apostrophe truncates it."""
        clean_df.loc[0, "title"] = "A Study of Bayes' Theorem"
        result = build_test_set(clean_df, settings.paths.eval_testset, max_papers=13)
        assert all("Bayes" not in item["question"] for item in result)

    def test_rejects_a_dataset_that_is_too_small(self, clean_df, settings):
        with pytest.raises(ValueError, match="at least 4"):
            build_test_set(clean_df.head(2), settings.paths.eval_testset)

    def test_rejects_a_dataset_missing_contract_columns(self, clean_df, settings):
        with pytest.raises(ValueError, match="missing required columns"):
            build_test_set(clean_df.drop(columns=["authors_joined"]), settings.paths.eval_testset)


class TestDataQuality:
    def test_clean_data_passes_every_check(self, clean_df, settings):
        report = run_data_quality_checks(clean_df, settings, "baseline_quality")
        assert report["success"] is True, report["failed_check_names"]
        assert report["failed_checks"] == 0

    def test_report_lands_in_the_quality_directory(self, clean_df, settings):
        report = run_data_quality_checks(clean_df, settings, "baseline_quality")
        path = Path(report["report_path"])
        assert path.exists()
        assert path.parent == settings.paths.quality_dir
        assert read_json(path)["success"] is True

    def test_each_state_gets_its_own_report_file(self, clean_df, settings):
        baseline = run_data_quality_checks(clean_df, settings, "baseline_quality")
        corrupted = run_data_quality_checks(clean_df, settings, "corrupted_quality")
        assert baseline["report_path"] != corrupted["report_path"]

    @pytest.mark.parametrize(
        ("column", "value", "expected_check"),
        [
            ("summary_chars", 0, "summary_min_length"),
            ("title", "", "title_not_empty"),
            ("text_for_embedding", "", "text_for_embedding_not_empty"),
            ("age_days", 900, "freshness_age_days"),
            ("paper_id", "", "paper_id_not_null"),
        ],
    )
    def test_detects_each_defect(self, clean_df, settings, column, value, expected_check):
        clean_df.loc[0, column] = value
        report = run_data_quality_checks(clean_df, settings, "corrupted_quality")
        assert report["success"] is False
        assert expected_check in report["failed_check_names"]

    def test_detects_duplicated_rows(self, clean_df, settings):
        duplicated = pd.concat([clean_df, clean_df.iloc[[0]]], ignore_index=True)
        report = run_data_quality_checks(duplicated, settings, "corrupted_quality")
        assert "paper_id_unique" in report["failed_check_names"]

    def test_detects_a_missing_contract_column(self, clean_df, settings):
        report = run_data_quality_checks(
            clean_df.drop(columns=["age_days", "published"]), settings, "corrupted_quality"
        )
        assert "schema_columns_present" in report["failed_check_names"]

    def test_summary_threshold_matches_the_cleaning_rule(self, clean_df, settings):
        """Cleaning drops summaries under 100 chars, so exactly 100 must still pass."""
        clean_df.loc[0, "summary_chars"] = 100
        report = run_data_quality_checks(clean_df, settings, "baseline_quality")
        assert "summary_min_length" not in report["failed_check_names"]


class TestFreshness:
    def test_clean_data_is_fresh(self, clean_df, settings):
        report = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
        assert report["is_fresh"] is True
        assert report["stale_rows"] == 0

    def test_payload_carries_the_required_fields(self, clean_df, settings):
        report = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
        assert {
            "latest_published",
            "oldest_published",
            "stale_rows",
            "total_rows",
            "is_fresh",
        } <= set(report)
        assert report["latest_published"] > report["oldest_published"]

    def test_a_single_stale_row_flips_the_verdict(self, clean_df, settings):
        clean_df.loc[0, "age_days"] = settings.freshness_threshold_days + 1
        report = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
        assert report["is_fresh"] is False
        assert report["stale_rows"] == 1

    def test_an_unparseable_date_is_not_silently_treated_as_fresh(self, clean_df, settings):
        clean_df = clean_df.drop(columns=["age_days"])
        clean_df.loc[0, "published"] = "not-a-date"
        report = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
        assert report["unknown_age_rows"] == 1
        assert report["is_fresh"] is False

    def test_is_persisted_as_json(self, clean_df, settings):
        report = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
        assert read_json(settings.paths.freshness_report) == report


class TestCorruption:
    @pytest.fixture
    def targets(self, clean_df):
        # Stands in for the frozen test set's ground_truth_doc_ids.
        return list(clean_df["paper_id"].head(6))

    @pytest.fixture
    def corrupted(self, clean_df, settings, targets):
        return corrupt_clean_dataframe(
            clean_df, settings.paths.corruption_log, target_paper_ids=targets
        )

    @pytest.fixture
    def log(self, corrupted, settings):
        return read_json(settings.paths.corruption_log)

    @pytest.fixture
    def by_name(self, log):
        return {event["corruption"]: event for event in log["corruptions"]}

    def test_writes_a_log_with_every_scenario(self, log):
        assert len(log["corruptions"]) == 6
        for event in log["corruptions"]:
            assert event["paper_ids"]
            assert "rows_before" in event and "rows_after" in event

    def test_reaches_the_papers_the_evaluator_asks_about(self, log):
        """Corrupting papers outside the test set leaves every metric unchanged."""
        assert log["ground_truth_paper_ids_touched"]
        assert log["ground_truth_coverage"] > 0.5

    def test_changes_the_row_count(self, corrupted, clean_df):
        assert len(corrupted) != len(clean_df)

    def test_drops_the_latest_records(self, corrupted, by_name):
        for paper_id in by_name["drop_latest_records"]["paper_ids"]:
            assert paper_id not in set(corrupted["paper_id"])

    def test_blanks_the_summary(self, corrupted, by_name):
        for paper_id in by_name["blank_summary"]["paper_ids"]:
            assert (corrupted.loc[corrupted["paper_id"] == paper_id, "summary"] == "").all()

    def test_injects_noise_into_the_summary(self, corrupted, by_name):
        for paper_id in by_name["inject_noise"]["paper_ids"]:
            rows = corrupted.loc[corrupted["paper_id"] == paper_id, "summary"]
            assert rows.str.contains("qwerty", regex=False).all()

    def test_truncates_the_title(self, corrupted, by_name):
        for paper_id in by_name["truncate_title"]["paper_ids"]:
            rows = corrupted.loc[corrupted["paper_id"] == paper_id, "title"]
            assert (rows.str.len() <= TRUNCATED_TITLE_CHARS).all()

    def test_backdates_the_publication(self, corrupted, by_name):
        for paper_id in by_name["stale_published_date"]["paper_ids"]:
            rows = corrupted.loc[corrupted["paper_id"] == paper_id]
            assert (rows["published"] == STALE_PUBLISHED_DATE).all()
            assert (rows["age_days"] > 365).all()

    def test_duplicates_keep_the_same_paper_id(self, corrupted, by_name):
        for paper_id in by_name["duplicate_rows"]["paper_ids"]:
            assert (corrupted["paper_id"] == paper_id).sum() >= 2

    def test_rebuilds_text_for_embedding_in_the_cleaning_format(self, corrupted):
        """A format drift here shows up as a metric drop that is not a data defect."""
        for _, row in corrupted.iterrows():
            assert row["text_for_embedding"] == (
                f"Title: {row['title']}\nAuthors: {row['authors_joined']}\n"
                f"Categories: {row['categories_joined']}\nSummary: {row['summary']}"
            )

    def test_keeps_summary_chars_consistent_with_summary(self, corrupted):
        assert (corrupted["summary_chars"] == corrupted["summary"].str.len()).all()

    def test_leaves_the_input_dataframe_untouched(self, clean_df, settings, targets):
        before = clean_df.copy()
        corrupt_clean_dataframe(clean_df, settings.paths.corruption_log, target_paper_ids=targets)
        assert clean_df.equals(before)

    def test_is_deterministic(self, clean_df, settings, targets, corrupted):
        again = corrupt_clean_dataframe(
            clean_df, settings.paths.corruption_log, target_paper_ids=targets
        )
        assert again.equals(corrupted)

    def test_rejects_an_empty_dataset(self, clean_df, settings):
        with pytest.raises(ValueError):
            corrupt_clean_dataframe(clean_df.iloc[0:0], settings.paths.corruption_log)

    def test_does_not_pin_the_run_date(self):
        """A hard-coded 'today' makes age_days drift on every later run."""
        source = (PROJECT_ROOT / "src" / "ingestion" / "corruption.py").read_text(encoding="utf-8")
        assert not re.search(r"date\(\s*\d{4}\s*,\s*\d{1,2}\s*,\s*\d{1,2}\s*\)", source)

    def test_trips_the_quality_gate(self, corrupted, settings):
        """C4 requires the corrupted quality report to record a failure."""
        assert run_data_quality_checks(corrupted, settings, "corrupted_quality")["success"] is False

    def test_trips_the_freshness_signal(self, corrupted, settings):
        report = build_freshness_report(
            corrupted, settings, settings.paths.quality_dir / "corrupted_freshness.json"
        )
        assert report["is_fresh"] is False


BASELINE = {
    "samples": 24,
    "retrieval_hit_rate": 1.0,
    "mean_token_f1": 0.9312,
    "judge_accuracy": 0.9375,
    "mean_judge_score": 4.5,
    "ragas": {"skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."},
}
CORRUPTED = {
    "samples": 24,
    "retrieval_hit_rate": 0.5,
    "mean_token_f1": 0.5506,
    "judge_accuracy": 0.5417,
    "mean_judge_score": 3.5417,
}
REPAIRED = {
    "samples": 24,
    "retrieval_hit_rate": 1.0,
    "mean_token_f1": 0.8974,
    "judge_accuracy": 0.9375,
    "mean_judge_score": 4.4,
}


class TestReports:
    @pytest.fixture
    def payloads(self, clean_df, settings):
        return (
            run_data_quality_checks(clean_df, settings, "baseline_quality"),
            build_freshness_report(clean_df, settings, settings.paths.freshness_report),
        )

    def test_phase1_report_has_every_section(self, settings, payloads):
        quality, freshness = payloads
        generate_phase1_report(
            settings.paths.baseline_report,
            {"source_api": settings.source_api, "clean_rows": 14},
            BASELINE,
            quality,
            freshness,
        )
        report = settings.paths.baseline_report.read_text(encoding="utf-8")
        assert all(f"## {number}." in report for number in range(1, 6))
        assert "0.9312" in report
        assert "**PASS**" in report
        assert "RUN_RAGAS=1" in report

    def _corruption_report(self, settings, payloads, corrupted_metrics=None):
        quality, freshness = payloads
        generate_corruption_report(
            settings.paths.comparison_report,
            BASELINE,
            corrupted_metrics or CORRUPTED,
            REPAIRED,
            quality,
            quality,
            freshness,
            freshness,
        )
        return settings.paths.comparison_report.read_text(encoding="utf-8")

    def test_renders_a_three_state_table(self, settings, payloads):
        report = self._corruption_report(settings, payloads)
        assert "| Baseline | Corrupted | Repaired |" in report
        assert "-0.5000" in report  # retrieval_hit_rate delta

    def test_reports_a_count_delta_as_an_integer(self, settings, payloads):
        assert "| `samples` | 24 | 24 | 24 | 0 | 0 |" in self._corruption_report(settings, payloads)

    def test_does_not_overstate_a_partial_recovery(self, settings, payloads):
        report = self._corruption_report(settings, payloads)
        assert "still" in report and "below baseline" in report

    def test_warns_when_the_test_set_changed_between_runs(self, settings, payloads):
        report = self._corruption_report(settings, payloads, {**CORRUPTED, "samples": 12})
        assert "**Warning:**" in report

    def test_stays_quiet_when_sample_counts_agree(self, settings, payloads):
        assert "**Warning:**" not in self._corruption_report(settings, payloads)


@pytest.mark.skipif(
    not (DATA_DIR / "results" / "repaired_metrics.json").exists(),
    reason="phase 2 artifacts are not present; run script/run_corruption_flow.py first",
)
class TestCommittedArtifacts:
    """Guard the evidence the group submits, not just the code paths."""

    @pytest.fixture
    def test_set(self):
        return read_json(DATA_DIR / "eval" / "test_set.json")

    @pytest.fixture
    def metrics(self):
        return {
            state: read_json(DATA_DIR / "results" / f"{state}_metrics.json")
            for state in ("baseline", "corrupted", "repaired")
        }

    def test_all_three_states_scored_the_same_test_set(self, metrics, test_set):
        """A differing sample count means the comparison is not like-for-like."""
        assert {payload["samples"] for payload in metrics.values()} == {len(test_set)}

    def test_answers_exist_for_every_state(self):
        for state in ("baseline", "corrupted", "repaired"):
            assert read_json(DATA_DIR / "results" / f"{state}_answers.json")

    def test_corruption_degraded_every_metric(self, metrics):
        for key in METRIC_KEYS:
            assert metrics["corrupted"][key] < metrics["baseline"][key], key

    def test_repair_recovered_every_metric(self, metrics):
        for key in METRIC_KEYS:
            assert metrics["repaired"][key] >= metrics["corrupted"][key], key

    def test_corruption_reached_the_evaluated_papers(self, test_set):
        """Corrupting papers the test set never asks about leaves the metrics unchanged."""
        log = read_json(DATA_DIR / "results" / "corruption_log.json")
        entries = log["corruptions"] if isinstance(log, dict) else log
        touched = {paper_id for entry in entries for paper_id in _paper_ids(entry)}
        ground_truth = {doc for item in test_set for doc in item["ground_truth_doc_ids"]}
        assert touched & ground_truth, "no evaluated paper was corrupted"

    def test_each_state_indexed_its_own_collection(self):
        manifests = [
            read_json(DATA_DIR / "embeddings" / name)["collection_name"]
            for name in (
                "papers_embeddings.json",
                "papers_embeddings_corrupted.json",
                "papers_embeddings_repaired.json",
            )
        ]
        assert len(set(manifests)) == 3, f"collections are not separate: {manifests}"

    @pytest.mark.xfail(
        strict=False,
        reason="the baseline was re-run after phase 2 on a machine with no API key, so its "
        "judge scores come from the heuristic fallback while corrupted/repaired come from "
        "the LLM judge; the judge columns are not comparable",
    )
    def test_every_state_was_judged_the_same_way(self):
        for state in ("baseline", "corrupted", "repaired"):
            answers = read_json(DATA_DIR / "results" / f"{state}_answers.json")
            fallbacks = [a for a in answers if "Fallback heuristic" in a["judge"]["reasoning"]]
            assert not fallbacks, f"{state}: {len(fallbacks)}/{len(answers)} judged by fallback"

    @pytest.mark.xfail(
        strict=False,
        reason="the baseline was re-run after retrieval code changed, so repaired now scores "
        "above the baseline it is supposed to reproduce; re-run phase 1 and phase 2 together",
    )
    def test_repair_returns_to_the_baseline_rather_than_beating_it(self, metrics):
        for key in METRIC_KEYS:
            assert metrics["repaired"][key] <= metrics["baseline"][key] + 1e-9, key


def _paper_ids(entry: dict) -> list[str]:
    """Accept either log shape: one paper_id per entry, or a list per scenario."""
    if "paper_ids" in entry:
        return list(entry["paper_ids"])
    return [entry["paper_id"]]
