"""Run an eval suite and write a report.

    uv run python -m realdrop.evals.run --suite tagger --tagger rules
    uv run python -m realdrop.evals.run --suite tagger --tagger llm --model qwen3:4b --runs 3

Reports go to `evals/runs/<timestamp>-<suite>/` (gitignored): `summary.json` and
`failures.jsonl` (one line per case and field that missed). Dev and held-out splits are scored
separately; prompts are tuned on dev only.
"""

import argparse
import asyncio
import json
import statistics
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from realdrop.ai.llm import LLMClient
from realdrop.ai.style_tagger import tag_styles
from realdrop.pipeline.tagger import tag

EVALS_DIR = Path(__file__).resolve().parents[3] / "evals"  # apps/api/evals
GOLDEN = EVALS_DIR / "golden"


@dataclass
class SetScore:
    """Micro-averaged precision and recall over tag sets."""

    tp: int = 0
    fp: int = 0
    fn: int = 0

    def add(self, predicted: Iterable[str], expected: Iterable[str]) -> None:
        p, e = set(predicted), set(expected)
        self.tp += len(p & e)
        self.fp += len(p - e)
        self.fn += len(e - p)

    def f1(self) -> float:
        if not (self.tp or self.fp or self.fn):
            return 1.0
        return 2 * self.tp / (2 * self.tp + self.fp + self.fn)

    def as_dict(self) -> dict[str, float]:
        precision = self.tp / (self.tp + self.fp) if self.tp + self.fp else 1.0
        recall = self.tp / (self.tp + self.fn) if self.tp + self.fn else 1.0
        return {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(self.f1(), 3),
        }


@dataclass
class SplitScore:
    styles: SetScore = field(default_factory=SetScore)
    colors: SetScore = field(default_factory=SetScore)
    fit_right: int = 0
    cases: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "cases": self.cases,
            "style_tags": self.styles.as_dict(),
            "colors": self.colors.as_dict(),
            "fit_accuracy": round(self.fit_right / self.cases, 3) if self.cases else None,
        }


def load_cases(name: str) -> list[dict[str, Any]]:
    lines = (GOLDEN / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


async def predict(
    cases: list[dict[str, Any]], tagger: str, model: str | None
) -> list[dict[str, Any]]:
    """Predictions per case: rules always; the LLM replaces style tags when asked.

    `llm` asks the model for every case; `hybrid` only where the rules found no style, which is
    what the production pass (pipeline/llm_styles.py) does.
    """
    rules = [tag(**case["input"]) for case in cases]
    predictions = [
        {"style_tags": list(r.style_tags), "colors": list(r.colors), "fit": r.fit} for r in rules
    ]
    if tagger in ("llm", "hybrid"):
        async with LLMClient(model=model) as client:
            semaphore = asyncio.Semaphore(4)

            async def one(i: int) -> None:
                case = cases[i]
                if tagger == "hybrid" and rules[i].style_tags:
                    return
                async with semaphore:
                    result = await tag_styles(
                        client,
                        title=case["input"]["title"],
                        category_raw=case["input"]["category_raw"],
                        category=case["input"]["category"],
                        brand=case["brand"],
                        rules=rules[i],
                    )
                predictions[i]["style_tags"] = list(result.style_tags)

            await asyncio.gather(*(one(i) for i in range(len(cases))))
    return predictions


def score(
    cases: list[dict[str, Any]], predictions: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    splits: dict[str, SplitScore] = {
        "dev": SplitScore(),
        "holdout": SplitScore(),
        "all": SplitScore(),
    }
    failures: list[dict[str, Any]] = []
    for case, got in zip(cases, predictions, strict=True):
        want = case["expect"]
        for split in (case["split"], "all"):
            s = splits[split]
            s.cases += 1
            s.styles.add(got["style_tags"], want["style_tags"])
            s.colors.add(got["colors"], want["colors"])
            s.fit_right += got["fit"] == want["fit"]
        for name in ("style_tags", "colors"):
            if set(got[name]) != set(want[name]):
                failures.append(
                    {
                        "id": case["id"],
                        "field": name,
                        "title": case["input"]["title"],
                        "expected": sorted(want[name]),
                        "got": sorted(got[name]),
                    }
                )
        if got["fit"] != want["fit"]:
            failures.append(
                {
                    "id": case["id"],
                    "field": "fit",
                    "title": case["input"]["title"],
                    "expected": want["fit"],
                    "got": got["fit"],
                }
            )
    return {name: split.as_dict() for name, split in splits.items()}, failures


async def run_tagger(tagger: str, model: str | None, runs: int) -> dict[str, Any]:
    cases = load_cases("tagger")
    reports, all_failures, seconds = [], [], []
    for _ in range(runs):
        started = time.perf_counter()
        predictions = await predict(cases, tagger, model)
        seconds.append(time.perf_counter() - started)
        report, failures = score(cases, predictions)
        reports.append(report)
        all_failures = failures  # the last run's misses; scores below are the mean over runs
    mean_f1 = {
        split: round(statistics.mean(r[split]["style_tags"]["f1"] for r in reports), 3)
        for split in ("dev", "holdout", "all")
    }
    return {
        "suite": "tagger",
        "tagger": tagger,
        "model": model if tagger == "llm" else None,
        "runs": runs,
        "labels": sorted({c["labeled_by"] for c in cases}),
        "style_f1_mean": mean_f1,
        "last_run": reports[-1],
        "seconds_per_case": round(statistics.mean(seconds) / len(cases), 2),
        "_failures": all_failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--suite", choices=["tagger"], required=True)
    parser.add_argument("--tagger", choices=["rules", "llm", "hybrid"], default="rules")
    parser.add_argument("--model", help="LLM model (default: LLM_MODEL_FAST)")
    parser.add_argument("--runs", type=int, default=1, help="LLM suites are noisy: use 3")
    args = parser.parse_args()

    summary = asyncio.run(run_tagger(args.tagger, args.model, args.runs))
    failures = summary.pop("_failures")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = EVALS_DIR / "runs" / f"{stamp}-{args.suite}-{args.tagger}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "failures.jsonl").write_text(
        "".join(json.dumps(f, ensure_ascii=False) + "\n" for f in failures), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    print(f"report: {out}")


if __name__ == "__main__":
    main()
