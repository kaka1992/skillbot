---
name: bnpl-rule-set-generator
description: Generate BNPL rule sets from a df table and a check table by running a custom XGBoost workflow, extracting tree-path candidate rules, filtering them by train/OOT lift, and greedily selecting a final rule set under a check-table intercept-rate constraint; also supports a parameter-sweep (exploration) mode that scans max_depth and max_intercept and draws comparison curves. Use this skill whenever the user wants to生成规则集、挖掘规则池、筛选最终规则、基于 df 和 check 做贷后规则挖掘、控制 check 拦截率、比较规则效果，或者探索 max_depth/max_intercept 最优参数、画压降率/召回率对比曲线、看规则数随拦截率的变化，尤其当需求包含 train/OOT、lift、规则池、最终规则集、固定分裂特征、自定义 XGBoost、参数扫描或最优参数探索时，即使用户没有明确提到“skill”也应触发。
---

# BNPL Rule Set Generator

## What this skill does

This skill generates BNPL risk rule sets from a sample table (`df`) and a check table (`check`) by using the project script `bnbl.py` as the execution backend.

The core workflow is:

1. Read `df` and `check`
2. Apply optional query filters
3. If `features` is user-provided, cast those feature columns to `float` on both `df` and `check` and fill missing values with `-9999`
4. Split `df` into train and OOT by date
5. Train a custom XGBoost model
6. Extract candidate rules from tree paths
7. Filter the rule pool by train/OOT lift thresholds
8. Greedily select a final rule set under a check-table intercept-rate constraint, using ROI = newly-recalled FPD7 amount / newly-intercepted check count; stop early if the best remaining rule's ROI is 0
9. Output the rule pool file and the final rule set file
10. Return a concise execution summary with key result metrics

This is primarily an **execution skill** for rule-set generation, not a prompt-only reimplementation of the modeling workflow.

In addition to generation, this skill can also handle **lightweight rule-related follow-up analysis**, such as summarizing the rule pool size, selected rule count, cumulative intercept rate, and drop rate.

## Two modes (intent routing)

This skill serves **two kinds of intent**. Before collecting parameters, first decide which mode the user is in, then follow that mode's flow. Both modes share the **same computation backend** (`bnbl.run_once`), so their drop-rate / intercept-rate definitions are always consistent.

### Mode 1 — Generate a rule set (generation mode)
The user wants **one concrete rule set** for a single `(max_depth, max_intercept)`.

- Backend: `${SKILL_DIR}/scripts/bnbl.py` (its `main()` CLI entry, unchanged).
- Output: `rule_pool.csv` + `rule_set.csv`.
- The `rule_set.csv` per-rule detail reports each rule's performance on **full-sample**, **train**, **check**, and **OOT**. The train-side columns are placed **after the full-sample columns and before the check/OOT columns**: `当前规则在train上命中总量`、`当前规则在train上命中黑样本数量`、`当前规则在train上命中 FPD7 金额率`、`当前规则在train上拦截后的 FPD7 金额率`、`累计规则在train上命中的 FPD7 金额率`、`累计规则在train上拦截后的 FPD7 金额率`、`train累计压降率`（train 压降基线为 train 全样本 FPD7 金额率）。
- Trigger signals: 生成规则集、跑一版规则、挖掘规则池、筛选最终规则、控制 check 拦截率不超过 X、给定单个 max_depth / max_intercept、重新跑一版规则、解释这版规则效果。
- This is the **default** mode and its interaction policy is described in the sections below (Required inputs → Interaction policy → Output requirements).

### Mode 2 — Explore optimal parameters (sweep mode)
The user wants to **compare multiple `max_depth` values across a range of `max_intercept`** and see comparison curves, to pick the best parameters.

- Backend: `${SKILL_DIR}/scripts/sweep_and_plot.py`, which **imports `bnbl` and reuses `bnbl.run_once`** — it does not re-implement any modeling / greedy logic.
- Method (方案 A): for each `max_depth`, run `run_once` **once** with `max_intercept` fixed to the **upper bound** of the requested range; each rule set's cumulative columns already form a full curve, so one run = one curve.
- Output: 4 figures + intermediate `rule_set_depth{d}.csv` / `rule_pool_depth{d}.csv`.
  - Figure 1: **train** FPD7 drop rate (column `train累计压降率`) vs check cumulative intercept rate.
  - Figure 2: OOT FPD7 drop rate vs check cumulative intercept rate.
  - Figure 3: cumulative recalled FPD7 amount share vs check cumulative intercept rate.
  - Figure 4: number of rules in the selected set vs check cumulative intercept rate.
  - Figures 1/2/3: each node is annotated with the per-point increase in the y value (`+N` percentage points) relative to the previous node; each curve is one `max_depth`.
- Trigger signals: 探索/寻找最优 max_depth·max_intercept、对比不同 depth、画压降率对比曲线、召回率对比曲线、规则数 vs 拦截率、参数扫描、扫一遍 depth。
- Its dedicated inputs and flow are in "Sweep mode (exploration)" below.

## When to use this skill

Use this skill when the user wants to do one or more of the following:

- Generate a BNPL rule set from `df` and `check`
- Mine a rule pool or candidate rules from model trees
- Select final rules under a check intercept-rate cap
- Run a train / OOT rule-mining workflow
- Filter rules by train/OOT lift
- Apply fixed split-feature constraints in the custom XGBoost
- Disable fixed split-feature constraints explicitly
- Re-run the same rule-generation workflow with different parameters
- Interpret or summarize the result of a BNPL rule-generation run
- Compare rule-generation outputs at a lightweight operational level

This skill should trigger for requests such as:

- “生成规则集”
- “挖掘规则池”
- “筛选最终规则”
- “基于 df 和 check 做贷后规则挖掘”
- “控制 check 拦截率”
- “看一下这版规则效果”
- “重新跑一版规则”
- “固定前几层分裂特征生成规则”

Use it even if the user does not explicitly mention:

- skill
- XGBoost
- tree path
- rule pool

as long as the real intent is BNPL rule-set generation or closely related rule-result interpretation.

## When not to use this skill

Do **not** use this skill when the user only wants:

- Simple SQL querying
- Generic data cleaning
- Pure model tuning without rule extraction
- Chart generation **unrelated** to BNPL rule sweeping (BNPL parameter-sweep comparison curves are handled by sweep mode)
- Rule deployment / online serving / strategy publishing
- Broad exploratory analysis unrelated to rule-set generation

If the request is still clearly centered on rule generation and its immediate results, this skill should handle it.

## Required inputs

The following parameters must be determined before execution.

If any of them is missing, ask follow-up questions instead of executing immediately.

### Required parameters
- `df_path`
- `check_path`
- `oot_start_date`
- `label_col`
- `amount_col`
- `principal_col`
- `date_col`
- `max_intercept`
- `max_depth`
- `fixed_feature_list`
- `rule_pool_path`
- `rule_set_path`
- `lift_threshold_train`
- `lift_threshold_oot`

### Required lift thresholds: `lift_threshold_train` and `lift_threshold_oot`
`lift_threshold_train` and `lift_threshold_oot` are **required** parameters and must be explicitly provided by the user before execution. They no longer have built-in default values — their script defaults are now `None`.

- Always collect both thresholds from the user before running; if either is missing, ask for it instead of executing.
- Never invent, guess, or fall back to a default threshold for them.
- The backend script `bnbl.py` enforces this: it raises an error immediately if `--lift-threshold-train` or `--lift-threshold-oot` is not provided.

### Required: `max_intercept`
`max_intercept` is a **required** parameter and must be explicitly provided by the user before execution. It no longer has a built-in default value — its script default is now `None`.

- Always collect it from the user before running; if missing, ask for it instead of executing.
- Never invent, guess, or fall back to a default (previously `0.1`).
- The backend script `bnbl.py` enforces this: it raises an error immediately if `--max-intercept` is not provided.

### Required output paths: `rule_pool_path` and `rule_set_path`
`rule_pool_path` and `rule_set_path` are **required** parameters and must be explicitly provided by the user before execution. They no longer have built-in default output paths — their script defaults are now empty strings (`""`).

- Always collect both paths from the user before running; if either is missing, ask for it instead of executing.
- Never invent, guess, or fall back to a default output path for them.
- The backend script `bnbl.py` enforces this: it raises an error immediately if `--rule-pool-path` or `--rule-set-path` is empty.

### Column requirements: `df` vs `check` (important)
`label_col`, `amount_col`, `principal_col`, and `date_col` describe columns that must exist **only in the `df` table**. The `check` table does **not** need these columns.

- The `df` table must contain: `date_col`, `label_col`, `amount_col`, `principal_col`, and all feature columns.
- The `check` table only needs to contain the **feature columns** (it is used solely for hit / intercept-rate computation, not for label / amount / principal metrics).

Therefore, do **not** pre-check the `check` table for `label_col` / `amount_col` / `principal_col`, and do **not** warn the user that "the check table is missing the label / amount / principal columns." That is expected and correct — the `check` table is not supposed to have them. Only the `df` table requires those columns.

The backend script `bnbl.py` already enforces exactly this: it validates `label_col` / `amount_col` / `principal_col` / `date_col` against `df` only, and validates just the feature columns against `check`. Any assistant-side pre-execution check must match this behavior and must not flag the missing label / amount / principal columns in `check` as an error.

### Important note on `fixed_feature_list`
`fixed_feature_list` must always be explicitly determined before execution.

It may be:

- a comma-separated feature list, such as  
  `bnpl_trade_model_v2,max_loan_hist_overdue_days`
- or an empty string `""`

If it is `""`, interpret it as:

> do not apply fixed split-feature constraints in the custom XGBoost.

This is valid and should not be treated as an error.

## Optional inputs

These parameters are optional and can use defaults when the user does not specify them:

- `features`
- `df_query`
- `check_query`
- `control_col`
- `control_value`
- `exclude_cols`
- `xgboost_path`

### Default behavior for optional inputs

#### `features`
If `features` is empty, infer features automatically from the common numeric columns of `df` and `check`, excluding label / amount / principal / date / excluded columns.

However, do **not** execute immediately after inference. First show the inferred feature list to the user in the execution summary and wait for confirmation.

##### Feature preprocessing when `features` is user-provided
When the user **explicitly provides** `features` (i.e. `--features` is non-empty), the script performs an extra preprocessing step automatically: after reading `df` and `check` (and after column validation), it casts every provided feature column to `float` on **both** tables and fills missing values with `-9999`.

Details:
- Applies to both `df` and `check`, only to the user-provided feature columns; label / amount / principal / date / other columns are left untouched.
- Non-numeric values in a feature column are coerced to `NaN` first, then filled with `-9999` together with the original missing values, so all feature columns entering the model are clean `float64`.
- This step is **skipped** when `features` is auto-inferred, because inference already selects only existing numeric columns.
- The fill value `-9999` is fixed by design; no extra parameter is exposed for it.

Mention this preprocessing briefly in the execution summary when `features` was user-provided, so the user knows the feature columns will be float-cast and missing-filled with `-9999`.

#### `xgboost_path`
This skill ships the custom XGBoost **Python source** at `${SKILL_DIR}/scripts/xgboost_runtime`. To keep the skill package small enough to pass market review, the large precompiled `libxgboost.so` is **not** bundled; the script downloads it on first run into `xgboost_runtime/xgboost/lib/` and caches it locally (subsequent runs reuse the cache). The script defaults `--xgboost-path` to this bundled runtime automatically.

Use this bundled default unless the user explicitly asks to override it. Do not proactively ask about this parameter in normal cases, and do not point it at any `/home/mira/...` path. The first run needs network access to fetch `libxgboost.so` once.

#### Output paths
`rule_pool_path` and `rule_set_path` are **required** and have no defaults (see "Required output paths" above). Always collect both from the user before running; if either is missing, ask for it instead of executing. Show the confirmed output paths in the execution summary before running.

#### `control_col` / `control_value` (control-group split)
In practice `df` is often split into a control group and a non-control group at roughly **1:9** (control ≈ 10%). When the user wants to run the rule mining **only on the control group**, they provide the column that distinguishes it. This is optional; when `control_col` is empty the whole flow is unchanged.

Parameters:
- `control_col` (`--control-col`, optional) — the column that flags the control group; values are usually `0/1`.
- `control_value` (`--control-value`, optional) — explicitly which value is the control group. Leave empty to auto-detect.
- `control_min_rows` (`--control-min-rows`, optional, int, default `5000`) — the minimum acceptable control-group row count. Only meaningful when `control_col` is set.

Behavior (implemented in `bnbl.resolve_control_query`, runs before `df_query` is applied, in `run_once`, so it covers **both** generation and sweep modes):
1. **Always analyze the distribution** of `control_col` and print each value's share plus the resolved control value — regardless of whether the distribution looks abnormal. Relay this distribution and the resolved control value to the user.
2. **Keep only the control group** (the `1` side). If the column is not clean `0/1`, check whether it is a **binary** label (exactly 2 non-null values); if so, proceed treating it as binary; if it has more than 2 values, raise an error (cannot define the control group).
3. **Resolve which value is control**: if `control_value` is given, use it (must exist in the column); otherwise auto-detect by proportion — since control ≈ 10%, the value with the **fewest** rows (minority) is taken as control.
4. **AND-append** the resolved condition (e.g. `` `control_col` == 1 ``) to any existing `df_query`: `(<df_query>) and (<control_clause>)`. The effective `df_query` is printed.
5. **Small-control-group warning.** The resolved control-group row count is the count on `df` (i.e. **before** the train/OOT split). If it is below `control_min_rows` (default `5000`), `bnbl.resolve_control_query` prints a soft `[告警]` line noting the data may be too small to model reliably on control alone. The script does **not** block on this warning.

**Confirmation flow for a small control group (assistant-side, plan B).** Because the backend is a non-interactive batch script, the *assistant* — not the script — pauses for confirmation. When `control_col` is set, if the assistant can estimate (or the first analysis reveals) that the control group is below `control_min_rows`, it must **stop before running the script**, tell the user the control-group size is small (below the threshold), and ask whether to continue using only the control group. Only run after the user confirms. The soft `[告警]` in the script is a secondary safety net, not the primary gate.

In the execution summary, when `control_col` is set, state that the control group will be split out (only control kept), which value is treated as control (or that it will be auto-detected as the minority), and that the distribution will be reported.

## Sweep mode (exploration)

This section applies **only to Mode 2**. Mode 1 (generation) is unaffected and keeps all the sections above/below.

### What sweep mode produces
For the requested `max_depth` values and `max_intercept` range, it draws 4 comparison figures (see "Two modes" above) plus intermediate per-depth CSVs. Each `max_depth` is one curve; the x-axis is the **actual** check cumulative intercept rate. It also emits a **recommended `(max_depth, max_intercept)` combination** (written to `recommendation.json` and highlighted in red on the figures — see "Recommended (max_depth, max_intercept) combination" below).

It also writes the data behind the 4 figures to a single workbook **`compare_tables.xlsx`** in `out_dir` — one sheet per figure (`train压降率`, `oot压降率`, `召回FPD7金额占比`, `规则数`). The tables use **方案甲**: each depth's each cumulative rule node is one row (columns: `max_depth`, `累计规则数`, `check累计拦截率(%)`, and the figure's y-value), with no cross-depth mark alignment/interpolation. If the `openpyxl` engine is unavailable, it degrades to 4 separate CSVs (`table_train_drop.csv`, `table_oot_drop.csv`, `table_recall_amt.csv`, `table_rule_count.csv`). This applies to sweep mode only.

At the end of the run the script also prints a structured artifact manifest — one line per output as `[ARTIFACT] <kind> <absolute_path>` (kinds: `figure_triptych`, `figure_rule_count`, `tables_xlsx` or `tables_csv`). Parse these lines to locate the files for the mandatory in-conversation display (see "In-conversation display" under "Sweep-mode result reply").

### Sweep-mode required parameters
All of the following must be explicitly provided; if any is missing, ask instead of executing.

**Shared data parameters (same meaning as generation mode):**
- `df_path`, `check_path`
- `date_col`, `label_col`, `amount_col`, `principal_col`
- `oot_start_date`
- `lift_threshold_train`, `lift_threshold_oot`
- `fixed_feature_list` (may be `""` to disable fixed split-feature constraint)

**Sweep-specific parameters (required, no defaults — the user must give them explicitly):**
- `depth_list` — the `max_depth` values to compare, comma-separated, e.g. `3,4,5`.
- `intercept_range` — the intercept range as `min,max,step`, e.g. `0.10,0.20,0.02` (decimals; `0.10` = 10%). The curve is drawn up to `max`; the split points are x-axis reference marks.
- `out_dir` — output directory for the figures and intermediate CSVs.

Per the product decision, `depth_list` and `intercept_range` are **required with no defaults**: the backend `sweep_and_plot.py` raises an error immediately if `--depth-list` or `--intercept-range` is empty. Never invent, guess, or fall back to defaults like `3,4,5` or `0.10,0.20,0.02`.

**Note on `max_intercept` in sweep mode:** the user does **not** pass a single `max_intercept`. The sweep fixes `max_intercept` to the **upper bound** of `intercept_range` and reads the cumulative curve (方案 A), so one run per depth yields a full curve.

### Sweep-mode optional parameters
Same as generation mode: `features`, `df_query`, `check_query`, `control_col`, `control_value`, `exclude_cols`, `xgboost_path`. `features` behavior (auto-infer + float-cast/fill when user-provided) is identical. The control-group split (`control_col` / `control_value`) works the same as in generation mode and applies to every depth in the sweep.

### Sweep-mode confirmation summary
Before running, show a concise summary including: `df_path`, `check_path`, `date_col`, `label_col`, `amount_col`, `principal_col`, `oot_start_date`, `features` (or inferred), `fixed_feature_list`, `lift_threshold_train`, `lift_threshold_oot`, `depth_list`, `intercept_range`, `out_dir`. State explicitly that `max_intercept` will be fixed to the range upper bound and one run per depth is used. Then ask for confirmation.

### Sweep-mode execution
Backend: `${SKILL_DIR}/scripts/sweep_and_plot.py`. It imports `bnbl` and reuses `bnbl.run_once`; do not re-implement modeling/greedy logic. Because it imports `bnbl`, run it from the `scripts/` directory (or add that dir to `PYTHONPATH`) so `import bnbl` resolves.

Example command shape:

```bash
cd "${SKILL_DIR}/scripts" && python3 sweep_and_plot.py \
  --df-path "<df_path>" \
  --check-path "<check_path>" \
  --df-query "<df_query>" \
  --check-query "<check_query>" \
  --control-col "<control_col>" \
  --control-value "<control_value>" \
  --control-min-rows <control_min_rows> \
  --features "<features>" \
  --exclude-cols "<exclude_cols>" \
  --date-col "<date_col>" \
  --label-col "<label_col>" \
  --amount-col "<amount_col>" \
  --principal-col "<principal_col>" \
  --oot-start-date "<oot_start_date>" \
  --lift-threshold-train <lift_threshold_train> \
  --lift-threshold-oot <lift_threshold_oot> \
  --fixed-feature-list "<fixed_feature_list>" \
  --xgboost-path "<xgboost_path>" \
  --depth-list "<depth_list>" \
  --intercept-range "<intercept_range>" \
  --out-dir "<out_dir>"
```

### Sweep-mode result reply
Return: the two figure paths (`compare_drop_recall.png` three-panel figure + `compare_rule_count.png`), the per-depth final rule counts, and 1–2 lines of interpretation (e.g. which depth gives the best drop rate per intercept, whether higher depth mainly buys more rules or more drop). Also report the **recommended `(max_depth, max_intercept)` combination** (see below), read from `recommendation.json` / the script's `===== 推荐组合 =====` log; state whether it came from strong dominance or the a*0.95 fallback, and whether the intercept degraded to the peak point.

#### In-conversation display (sweep mode only — MANDATORY)
After the script finishes and the files are saved to `out_dir`, in **sweep mode** you MUST additionally show the outputs in the conversation. (Generation mode does not produce figures or `compare_tables`, so it only reports the saved paths and skips this whole subsection.)

Parse the script stdout for the structured manifest lines — each is `[ARTIFACT] <kind> <absolute_path>`:
- `figure_triptych` — the three-panel drop/recall comparison figure.
- `figure_rule_count` — the rule-count comparison figure.
- `tables_xlsx` — `compare_tables.xlsx` (or `tables_csv` entries if it degraded to CSVs).

Then:
1. **Show the two figures inline.** Upload each figure file via the file-upload tool to get a URL, then render it inline with `![figure](url)`. Do not paste the raw local path as the image; always upload first and use the returned URL. Show both figures.
2. **Show the tables inline.** Read `compare_tables.xlsx` (e.g. with pandas / openpyxl) and render the **first 3 sheets — `train压降率`, `oot压降率`, `召回FPD7金额占比` — in full** as Markdown tables (all rows, no truncation). Do **not** display the 4th sheet (`规则数`). If the run degraded to CSVs, read the three corresponding CSVs (`table_train_drop.csv`, `table_oot_drop.csv`, `table_recall_amt.csv`) instead and render them the same way.
3. Do **not** attach extra download links for the figures or xlsx beyond the inline rendering; the saved paths already reported are sufficient.

### Recommended (max_depth, max_intercept) combination
`sweep_and_plot.py` emits one recommended combination, written to `recommendation.json` in `--out-dir` and printed under `===== 推荐组合 =====`. It is highlighted on the figures (red circle on the OOT-drop panel + red vertical line marking the recommended intercept on all panels). The algorithm (pure post-processing over the cumulative curves; `bnbl.py` is untouched):

**Step 1 — optimal `max_depth` D.** For each depth take its **in-range OOT-drop peak point** (the point with the highest `oot累计压降率` whose `check表累计拦截率` falls inside the given `[min, max]` intercept range). Score two dimensions: OOT drop rate (higher is better) and the depth's total rule count (fewer is better).
- **Strong dominance:** if one depth's peak is no worse than every other depth on both dimensions and strictly better on at least one, that depth is D (`depth_reason = dominance`).
- **Fallback:** otherwise let `a` = the max in-range OOT-drop peak across depths; among depths whose peak `>= a * 0.95`, pick the **lowest** depth as D (`depth_reason = a95`).

**Step 2 — optimal `max_intercept`.** On curve D restricted to the `[min, max]` intercept range, compute each adjacent-pair **local slope = Δ(OOT drop rate) / Δ(intercept rate)**, and their average `s_avg`. Starting from the in-range peak point (right end ≈ `max`), walk left: while the segment entering the current point has local slope `< s_avg`, move left; stop at the right endpoint of the first segment whose slope `>= s_avg`. The stopping point's intercept is the recommended `max_intercept`. If the in-range subsequence has fewer than 2 points, degrade to the peak point and set `intercept_degraded = true` (note this to the user).

The recommendation uses **OOT drop rate** as the quality metric throughout (consistent with the user-confirmed spec).

### Sweep-mode failure handling
- Missing `depth_list` / `intercept_range` / `out_dir` (or any shared required data param) → ask, do not execute.
- A single depth failing or yielding an empty rule pool does **not** abort the sweep: `sweep_and_plot.py` logs a warning, skips that curve, and continues; the figures simply omit that depth. Only when **all** depths are empty/failed does it raise and no figure is produced.
- xgboost import/download failure is an environment/platform/network issue, not a data-quality problem (see "Environment requirements").

## Interaction policy

Follow this interaction order.

### Step 1: Collect parameters
Read the user request and extract as many parameters as possible.

Support both:
- natural language input
- semi-structured parameter input

If required parameters are missing, ask focused follow-up questions.

Do not over-question optional parameters unless they materially affect execution or the user explicitly wants to customize them.

### Step 2: Resolve defaults
Fill optional parameters with defaults where appropriate.

For `features`:
- if provided, use them directly
- if empty, infer them automatically, then show them to the user

For output paths:
- `rule_pool_path` and `rule_set_path` are required and have no defaults; if either is missing, ask the user for it instead of executing

For `xgboost_path`:
- use the default path unless the user explicitly requests another one

### Step 3: Summarize execution plan
Before execution, always provide a concise execution summary and wait for user confirmation.

The summary should include at least:

- `df_path`
- `check_path`
- `date_col`
- `label_col`
- `amount_col`
- `principal_col`
- `oot_start_date`
- `features` or inferred feature list
- `fixed_feature_list`
- `max_intercept`
- `max_depth`
- `lift_threshold_train`
- `lift_threshold_oot`
- `rule_pool_path`
- `rule_set_path`

If `features` was inferred automatically, say so explicitly.

If `fixed_feature_list` is empty, explicitly state that no fixed split-feature constraint will be applied.

### Step 4: Execute the script
After the user confirms, run the project script to generate:

- the filtered rule pool file
- the final selected rule set file

Use the existing project script interface instead of re-implementing the workflow inside the prompt.

#### Execution backend
The execution backend is the bundled project script shipped inside this skill:

- `${SKILL_DIR}/scripts/bnbl.py`

`${SKILL_DIR}` is this skill's own base directory (resolve it at runtime, e.g. from the SKILL.md location). Always invoke the bundled copy under `scripts/`, never a hard-coded `/home/mira/...` path, so the skill works in any user's environment after it is published to the market.

Invoke it through Python with explicit CLI arguments.
Do not manually recreate the rule-mining logic inside the skill unless debugging is required.

#### Execution mapping
Map user-confirmed parameters to script arguments as follows:

- `df_path` -> `--df-path`
- `check_path` -> `--check-path`
- `df_query` -> `--df-query`
- `check_query` -> `--check-query`
- `control_col` -> `--control-col`
- `control_value` -> `--control-value`
- `control_min_rows` -> `--control-min-rows`
- `features` -> `--features`
- `exclude_cols` -> `--exclude-cols`
- `date_col` -> `--date-col`
- `label_col` -> `--label-col`
- `amount_col` -> `--amount-col`
- `principal_col` -> `--principal-col`
- `oot_start_date` -> `--oot-start-date`
- `lift_threshold_train` -> `--lift-threshold-train`
- `lift_threshold_oot` -> `--lift-threshold-oot`
- `max_intercept` -> `--max-intercept`
- `fixed_feature_list` -> `--fixed-feature-list`
- `max_depth` -> `--max-depth`
- `xgboost_path` -> `--xgboost-path`
- `rule_pool_path` -> `--rule-pool-path`
- `rule_set_path` -> `--rule-set-path`

#### Execution rules
- Always use the confirmed parameter set, not partially inferred assumptions.
- If `features` was auto-inferred, pass the final confirmed feature list explicitly.
- If `fixed_feature_list` is an empty string, still pass it explicitly so that the run is unambiguous.
- Always pass user-provided `rule_pool_path` and `rule_set_path` explicitly; they are required and have no defaults.
- Prefer one direct script invocation over multi-step manual reconstruction.

#### Pre-execution checklist
Before running, make sure all of the following are true:

1. Required parameters are complete.
2. Auto-inferred `features` have been shown to the user.
3. `rule_pool_path` and `rule_set_path` have been explicitly provided by the user.
4. The user has explicitly confirmed execution.

### Step 5: Validate outputs
Check whether the expected output files were generated successfully.

If execution fails, explain the failure in plain language and point to the most likely issue:

- missing fields
- empty data after filtering
- invalid date split
- no valid train/OOT samples
- script or environment failure

### Step 6: Return the result
Return a concise result summary with output paths, key metrics, and brief interpretation.

## Output requirements

The final reply should include:

### Must include
1. Rule pool file path
2. Final rule set file path
3. Check-table cumulative intercept rate
4. Drop rate / 压降率

### Should also include
- Whether `features` were user-provided or auto-inferred
- Whether fixed split-feature constraints were applied
- Rule pool size and/or final selected rule count, if available
- A short operational interpretation of the result

Keep the interpretation brief. The user mainly needs an execution result plus a small amount of useful explanation.

## Failure handling

Handle these cases explicitly and clearly.

### Missing required parameters
Ask follow-up questions instead of guessing.

### Empty or invalid data
If the script reports empty `df`, empty `check`, missing columns, empty train/OOT split, or invalid date parsing, tell the user which input is invalid and what to check next.

Note on missing columns: only treat it as an error when the script itself raises `df 缺少必要字段`, `df 缺少特征列`, or `check 缺少特征列`. A `check` table that lacks `label_col` / `amount_col` / `principal_col` is **not** an error — those columns are required on `df` only, so never surface it as a missing-column problem for `check`.

### Empty rule pool
If no rules satisfy the train/OOT lift thresholds, explain that the workflow completed but no valid candidate rules remained after filtering.

Still report output paths if files were generated.

### Greedy early stop (ROI = 0)
The greedy selector ranks candidate rules by **ROI = newly-recalled FPD7 amount / newly-intercepted check count**. If, on some round, the best remaining rule's ROI is 0 — meaning any further rule would only add check-table interception without recalling any new FPD7 bad-debt amount — the selector **stops early**: it does **not** add that ROI=0 rule, and takes the current selected set as the final rule set. This is the intended behavior, not an error.

When this happens the script prints a `[提前停止]` line and the final `check` cumulative intercept rate (which is typically **below** the `max_intercept` cap, since the run ended before hitting the cap). Surface this to the user explicitly: tell them the rule-set generation stopped early because the best remaining ROI was 0, and report the intercept rate actually reached. Also note the final set may be smaller than a run that hits the `max_intercept` cap.

### No fixed split-feature constraint
If `fixed_feature_list=""`, explicitly state that the run used no fixed split-feature constraint.

### Script or environment failure
If the custom XGBoost import or script execution fails, distinguish execution-layer failure from data-quality failure.

## Response style

Use a concise, teammate-friendly, execution-oriented style.

- Be direct
- Keep follow-up questions minimal and targeted
- Prefer short structured summaries
- After execution, return:
  - chosen parameters
  - output paths
  - key metrics
  - 1–2 lines of interpretation

If the user asks a closely related rule-analysis follow-up question, answer it briefly without drifting into unrelated broad analysis.

## Execution templates

Use the following templates to keep execution behavior stable.

### Parameter confirmation template
Use a short structured summary before execution. Adapt field values, but keep the structure clear.

Example:

- 本次将执行 BNPL 规则集生成任务
- df_path: `...`
- check_path: `...`
- date_col: `...`
- label_col: `...`
- amount_col: `...`
- principal_col: `...`
- oot_start_date: `...`
- features: `...`
- fixed_feature_list: `...`
- max_intercept: `...`
- max_depth: `...`
- lift_threshold_train: `...`
- lift_threshold_oot: `...`
- rule_pool_path: `...`
- rule_set_path: `...`

If `features` was auto-inferred, explicitly say:

- `features` 未显式提供，以上为自动推断结果，请确认是否按此执行。

If `fixed_feature_list` is empty, explicitly say:

- `fixed_feature_list` 为空，本次执行将不做固定分裂特征约束。

End the confirmation step with a direct confirmation question such as:

- 请确认是否按以上参数执行。

### Command execution template
Prefer one direct script invocation.

Example command shape:

```bash
python3 "${SKILL_DIR}/scripts/bnbl.py" \
  --df-path "<df_path>" \
  --check-path "<check_path>" \
  --df-query "<df_query>" \
  --check-query "<check_query>" \
  --control-col "<control_col>" \
  --control-value "<control_value>" \
  --control-min-rows <control_min_rows> \
  --features "<features>" \
  --exclude-cols "<exclude_cols>" \
  --date-col "<date_col>" \
  --label-col "<label_col>" \
  --amount-col "<amount_col>" \
  --principal-col "<principal_col>" \
  --oot-start-date "<oot_start_date>" \
  --lift-threshold-train <lift_threshold_train> \
  --lift-threshold-oot <lift_threshold_oot> \
  --max-intercept <max_intercept> \
  --fixed-feature-list "<fixed_feature_list>" \
  --max-depth <max_depth> \
  --xgboost-path "<xgboost_path>" \
  --rule-pool-path "<rule_pool_path>" \
  --rule-set-path "<rule_set_path>"
```

Notes:
- If an optional string parameter is empty but the script should still receive it explicitly, pass an empty string.
- If `features` was inferred, pass the confirmed inferred list explicitly.
- Do not omit `fixed_feature_list` when it is intentionally empty.

### Result reply template
After execution, return a concise operational summary.

Example structure:

- 已完成本次 BNPL 规则集生成。
- 规则池文件：`...`
- 最终规则集文件：`...`
- check 累计拦截率：`...`
- 压降率：`...`

If available, also include:
- 规则池数量：`...`
- 最终选中规则数：`...`
- features 来源：用户提供 / 自动推断
- 固定分裂特征约束：已启用 / 未启用

If the script printed a `[提前停止]` line, you **must** tell the user:
- 已提前停止：剩余规则最优 ROI 为 0，规则集生成提前结束。
- 此时 check 累计拦截率：`...`（通常低于 max_intercept 上限）。

Then add 1–2 short interpretation lines, for example:

- 本次规则池规模较小，说明在当前阈值下可保留的候选规则不多。
- 当前 check 拦截率控制在目标范围内，压降率可作为本轮规则效果的快速参考。

## Example prompts

### Example 1
帮我基于这两个表生成一版 BNPL 规则集。  
df_path 是 `/path/a.parquet`，check_path 是 `/path/b.parquet`，  
日期列是 `loan_date`，标签列是 `fpd7_flag`，金额列是 `fpd7_ovd_num`，本金列是 `fpd7_principal_den`，  
oot 从 `2026-05-20` 开始，check 累计拦截率不超过 `0.1`，max_depth=5，fixed_feature_list=""。

### Example 2
用 df 和 check 跑一版规则池，先自动推断 features，但执行前先告诉我你推断出了哪些特征。  
oot_start_date 是 `2026-05-20`，label_col 是 `fpd7_flag`，amount_col 是 `fpd7_ovd_num`，principal_col 是 `fpd7_principal_den`，date_col 是 `loan_date`，max_intercept=0.08，max_depth=4，fixed_feature_list="bnpl_trade_model_v2,max_loan_hist_overdue_days"。

### Example 3
帮我重新跑一版最终规则集，df_query 改成 `xxx`，check_query 改成 `yyy`。  
规则池输出到 `/path/rule_pool.csv`，最终规则输出到 `/path/final_rules.csv`，你先把最终执行参数给我确认。

### Example 4
这版规则已经跑完了，帮我简短解释一下为什么最终规则集只有几条，以及当前 check 拦截率和压降率大概意味着什么。

### Example 5 (sweep mode)
帮我探索 max_depth 和 max_intercept 的最优取值。max_depth 对比 `3,4,5`，max_intercept 从 10% 到 20% 每 2% 取一个分割点（即 `0.10,0.20,0.02`）。  
df_path 是 `/path/a.parquet`，check_path 是 `/path/b.parquet`，date_col 是 `loan_date`，label_col 是 `fpd7_flag`，amount_col 是 `fpd7_ovd_num`，principal_col 是 `fpd7_principal_den`，oot 从 `2026-05-20` 开始，lift 阈值都用 2.5，fixed_feature_list=""，图输出到 `/path/sweep_out`。  
输出 train 压降、OOT 压降、FPD7 金额召回三条对比曲线（每个节点标注较上一节点的百分点增量），再加一张规则数 vs 拦截率的对比图。

## Implementation note

Use the bundled project script `${SKILL_DIR}/scripts/bnbl.py` as the execution backend (generation mode). Sweep mode uses `${SKILL_DIR}/scripts/sweep_and_plot.py`, which imports `bnbl` and reuses its `run_once` — the two modes therefore share one computation path. Both ship together with the custom XGBoost Python source under `${SKILL_DIR}/scripts/xgboost_runtime`. The large `libxgboost.so` is downloaded on first run and cached locally, so the skill package stays small and no file from `/home/mira/files` is required at runtime.

Do not duplicate the full modeling workflow inside the skill instructions unless debugging requires it.

## Environment requirements

The custom XGBoost relies on a precompiled `libxgboost.so` that is fetched on first run. It is loaded via `ctypes` (no per-Python-version C extension), so it tolerates different Python minor versions, but it is still platform-specific.

- **Platform**: Linux **x86_64** only. It will not load on arm64 or other architectures.
- **Python**: `>= 3.8` (the bundled XGBoost is 2.0.3). Best tested on Python 3.13.
- **Network**: the first run downloads `libxgboost.so` (~3.4MB) once; later runs use the local cache.
- **Failure isolation**: if downloading or importing `xgboost` fails, treat it as an environment/platform/network issue (wrong arch, no network, incompatible numpy/pandas), not a data-quality problem, and report it as such.
