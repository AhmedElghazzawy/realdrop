---
name: add-eval-case
description: How to add or change eval cases (golden queries, retrieval judgments, extractor labels, assistant scenarios, pricing series) and record baselines for RealDrop's AI components. Use whenever AI behaviour is added or changed, or a bug is found.
---

# Add an eval case

Rule: **the failing case comes first, then the fix.**

1. **Pick the suite:** `parser` (`evals/golden/queries.jsonl`), `retrieval` (`retrieval.jsonl`),
   `extractor` (`extractor.jsonl`), `assistant` (`assistant/*.yaml` scenarios), or `pricing` (pytest).
2. **Write the case** in the format in `docs/EVALS.md`:
   - Parser: `id` (next number), `query`, `lang`, `expect` (only fields that must match), optional
     `expect_absent`, `hard`, `notes`. Prices are kurus. Use Turkish-safe spellings exactly as users type them.
   - Extractor: label the product **by hand**, not by the model. Keep a 20-product held-out slice that is never used for tuning.
   - Assistant: a scripted conversation, a fake tool backend with fixed outputs, and assertions
     (which tool is called, every number appears in tool output, required wording for insufficient history).
   - Pricing: a synthetic daily price series plus the expected status and flags.
3. **Run it and see it fail** (or confirm it passes if it documents existing behaviour):
   `cd apps/api && uv run python -m realdrop.evals.run --suite <name>`.
4. **Fix the code or prompt**, bump the prompt version if a prompt changed, rerun the whole suite.
5. **Record the result:** baseline on first creation of a suite; afterwards report before/after scores in the commit message.
6. **Never** change an expected value just to make a case pass. If a label was wrong, say so explicitly in the commit message.
7. LLM suites are noisy: run with `n=3`, report the mean, investigate flaky cases instead of deleting them.
8. Commit: `test(evals): <case or reason>`. Tell the owner in 2-4 sentences what this case protects against.
