# Benchmark: configuration comparison (ablation)

Each configuration adds **one more helper** to the previous one (cumulative). The configurations only switch *quality*
features on and off. The safety layers (SQL validator, read-only connection, 100-row limit, timeout, hidden sensitive
columns) and the "cannot answer / ask for clarification" rule are **on in every configuration**. The app (UI and CLI)
always runs the `full` configuration; the others exist so that this comparison can be reproduced with `eval/run_eval.py`.

## Configurations

| Configuration | Feature added | In short |
|---|---|---|
| `baseline` | none | The model sees only the full schema and the question. One attempt. |
| `fewshot` | `few_shot` | The 3 most similar solved examples (question + correct SQL) are added to the prompt. |
| `repair` | `repair` | If the SQL fails or the validator rejects it, the error goes back to the model; up to 3 attempts. |
| `values` | `value_dict` + `value_linking` | Value lists of categorical columns and a small glossary are added to the schema; misspelled values in the question are linked to real ones ("Seafod" -> `Seafood`). |
| `tables` | `table_select` | The model first picks the tables it needs; only their schema is sent (bridge tables are added automatically). |
| `full` | `memory` | A follow-up question is rewritten into a standalone one using the previous questions. **This is what the app runs.** |

## Setup

- Data: the Northwind sample database (`northwind_small.db`: 100 orders; `northwind_full.db`: 830 orders).
- Models: `gemini-3.5-flash-lite` and `claude-haiku-5-5` (embeddings for few-shot retrieval: `gemini-embedding-001`).
- Question set: `eval/questions.yaml`, 90 questions in total. 36 are `train` (the few-shot pool) and **54 are `test`**
  (only these are scored). The test set has 8 easy, 21 medium and 18 hard SQL questions (47 in total), plus 4
  unanswerable and 3 ambiguous questions.
- Metric: *execution accuracy*. The result of the generated SQL must equal the result of the reference SQL (row order and
  column order do not matter; small rounding differences are tolerated). For unanswerable and ambiguous questions the
  correct behaviour is to decline or to ask a clarifying question without running any SQL.
- To reproduce:

```bash
python eval/run_eval.py --db small --configs baseline,fewshot,repair,values,tables
python eval/run_eval.py --db full  --configs baseline,fewshot,repair,values,tables
python eval/run_eval.py --db small --provider anthropic --configs baseline,fewshot,repair,values,tables
```

## Results with Gemini (54 test questions, single run)

Accuracy with 95% confidence interval, average tokens per question and attempts per question:

| Configuration | Small DB | Full DB | Tokens/question (small) | Attempts/question (small) |
|---|---|---|---|---|
| `baseline` | 89% (48/54; 78-95%) | 87% (47/54; 76-94%) | 2398 | 1.00 |
| `fewshot` | 94% (51/54; 85-98%) | 89% (48/54; 78-95%) | 2523 | 1.00 |
| `repair` | 94% (51/54; 85-98%) | 91% (49/54; 80-96%) | 2523 | 1.00 |
| `values` | 96% (52/54; 87-99%) | 94% (51/54; 85-98%) | 3694 | 1.02 |
| `tables` | 96% (52/54; 87-99%) | 96% (52/54; 87-99%) | 1493 | 1.04 |
| `full` | not measured | not measured | | |

Correct answers by question type (full DB):

| Configuration | Easy (8) | Medium (21) | Hard (18) | Unanswerable (4) | Ambiguous (3) |
|---|---|---|---|---|---|
| `baseline` | 7 | 20 | 13 | 4 | 3 |
| `fewshot` | 7 | 19 | 16 | 3 | 3 |
| `repair` | 7 | 20 | 16 | 3 | 3 |
| `values` | 7 | 20 | 17 | 4 | 3 |
| `tables` | 7 | 21 | 17 | 4 | 3 |

On the small DB the distribution is: `baseline` 7/20/14/4/3, `fewshot` and `repair` 7/20/17/4/3, `values` and `tables`
7/21/17/4/3.

Security set (`eval/run_security.py`, poisoned database, 15 attack scenarios): 15/15 passed.

## How to read the Gemini results

- The ordering is as expected (`baseline` lowest, `tables` highest), but the confidence intervals overlap. With a single
  run this is a direction, not proof.
- `fewshot` made the biggest jump on hard questions (full DB: 13 -> 16).
- `repair` was almost never triggered (about 1.00 attempts per question): the model rarely produces SQL that fails. Its
  effect cannot be measured with this question set.
- `values` helped on value-mapping questions (for example `UK`, `Sales Representative`) but made the prompt larger
  (2523 -> 3694 tokens).
- `tables` roughly halved the tokens (3694 -> 1493) but adds one more LLM call.
- `full` was not measured separately: the eval asks questions one by one, so the effect of memory does not show up.

## Claude Haiku 5.5 compared with Gemini (small DB, 54 test questions, single run)

Same pipeline and same questions; only the model that writes the SQL was changed (`--provider anthropic`, model
`claude-haiku-5-5`). Few-shot example retrieval uses Gemini embeddings for both models.

### Table 1: strict execution accuracy

The generated query must return the same rows **and the same set of columns** as the reference query.

![Strict accuracy](img/table1_strict_accuracy.png)

| Configuration | Gemini 3.5 Flash-Lite | Claude Haiku 5.5 | Tokens/question (Haiku) |
|---|---|---|---|
| `baseline` | 89% (48/54) | 70% (38/54; 57-81%) | 3763 |
| `fewshot` | 94% (51/54) | 80% (43/54; 67-88%) | 3928 |
| `repair` | 94% (51/54) | 80% (43/54; 67-88%) | 3928 |
| `values` | 96% (52/54) | 81% (44/54; 69-90%) | 5652 |
| `tables` | 96% (52/54) | 78% (42/54; 65-87%) | 2503 |

### Table 2: answer accuracy with extra columns tolerated

A result counts as correct if it contains every reference value in the right number of rows, even with additional
columns. This is a post-hoc analysis (`eval/lenient_report.py` re-runs the saved SQL); it is not the primary metric.

![Tolerant accuracy](img/table2_tolerant_accuracy.png)

| Configuration | Gemini (tolerant) | Haiku (tolerant) | Haiku answers lost only to extra columns |
|---|---|---|---|
| `baseline` | 51/54 | 51/54 | 13 |
| `fewshot` | 51/54 | 52/54 | 9 |
| `repair` | 51/54 | 52/54 | 9 |
| `values` | 52/54 | 52/54 | 8 |
| `tables` | 53/54 | 52/54 | 10 |

### What happened

- Haiku tends to add "helpful" columns next to what was asked (a price next to a product name, a count next to a city).
  The rows are right, but the extra column makes the strict metric reject the result. Gemini adds extra columns far less
  often (0-3 questions versus 8-13 for Haiku).
- When extra columns are tolerated, the two models are very close (51-53 out of 54).
- For Haiku, the jump from `baseline` to `fewshot` in the strict metric (70% -> 80%) mostly comes from the examples
  teaching the model to return only the requested columns. In the tolerant metric the gain is small (+1 question).
- Haiku's remaining errors in the tolerant metric: `u01` (it asked a clarifying question instead of declaring the
  question unanswerable, which is defensible but not what the metric expects), `v04` with `tables` (table selection
  dropped `Customers`, a real weakness), and single misses on `s22` (self-join), `h02`, `v05`, `v06`.
- Haiku model calls are fast: 1.5-2.7 s median per question in these runs (fresh calls, no cache), 2.4-5.2 s at p95.
  Gemini timings from the same runs are not comparable (they were recorded while the API was slow and are not reported
  here). Token counts cannot be compared directly because the two models use different tokenizers.
- Claude models reject the `temperature` parameter, so it is not sent. Haiku was not run on the full database.

## Things to keep in mind

- **The test set was adjusted twice after the first results were seen:** two ambiguous question wordings were clarified
  (it was unclear which columns were wanted) and the number comparison was made tolerant to rounding boundary errors.
  The changes were applied equally to all configurations, but because of them `baseline` went from 77% in the first run
  to 88-89%.
- **Single run:** Gemini ignores the `temperature` setting, so results can vary a little between runs. LLM responses are
  cached on disk, so re-runs return the same result; change `LLM_CACHE_SALT` for genuinely fresh samples.
- **Latency columns are not reliable for Gemini:** the cached call times mix different runs, so they are not reported.
- **The few-shot pool lives in the same file as the eval questions** (the questions marked `train`); test questions never
  enter the pool (enforced by a test).
- **Northwind is small and well known:** the numbers are an optimistic upper bound for real, messy company databases.
