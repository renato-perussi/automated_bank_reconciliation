# AGENTS.md — automated_bank_reconciliation

## Commands (venv exists, always use `.venv/bin/`)
- App: `.venv/bin/streamlit run app.py` (entrypoint `app.py:main`).
- All tests: `.venv/bin/python -m pytest -q` (`testpaths = tests`).
- Single file: `.venv/bin/python -m pytest tests/test_matcher.py -q`.
- Coverage: `.venv/bin/python -m pytest --cov=src -q`.
- Lint: `.venv/bin/python -m ruff check src tests app.py ui scripts` — must be clean.
- Lint + tests green before closing any task (per `README.md` / `SPRINT.md`).
- Perf: `.venv/bin/python -m scripts.bench` — asserts 5000×5000 < 30s. Slow, do not run casually.

## Pipeline (read in this order when debugging)
- `src/loader.py`: encoding `utf-8→latin1`, delimiter `,→;`, first Excel sheet via openpyxl, 20 MB reject, `validate_not_empty`. Server limit mirrors it (`.streamlit/config.toml` `maxUploadSize = 20`).
- `src/mapping.py`: `normalize_header` strips accent/case; internals `event_date/description/amount`, display stays `Data/Descrição/Valor`.
- `src/normalize.py` + `src/validate.py:collect_errors`: valid vs `Linha/Motivo/Orientação` split; one bad row never aborts batch.
- `src/matcher.py:find_candidates`: block by `amount ± tolerance + sign`, then date window; `token_set_ratio` fuzzy. Shared bits live in `src/entries.py` (`collect_entries`, ledger/amount index, `is_signal_blocked`), `src/guards.py`, `src/money.py` (`Decimal` only), `src/params.py` (`build_params`, snapshot), `src/labels.py` (pt-BR labels).
- `src/classifier.py` and `src/report.py` are thin facades (93 / 111 lines) — real logic is in `src/classification/` (`rules`, `ambiguity`, `duplicates`, `pending`, `tables`: 5 tables `auto/potential/pending/divergent/duplicate`) and `src/reporting/` (`details`, `errors`, `rule_log`, `workbook`, `exceptions`, `kpis`, `formatting`, `lookups`, `headers`, `snapshots`). Edit the subpackage, keep the facade re-exporting.
- Reports (via `src/reporting/`): xlsx + exceptions csv, both embed params snapshot + `APP_VERSION`. Returns bytes, never writes files.
- `app.py:main` (190 lines) only assembles panels; sections live in `ui/sections/` (`upload`, `params_section`, `results`, `review`, `history`, `export_section`). Pure UI filters in `src/filters.py`, review state in `src/review_state.py`, export bytes in `src/export_service.py`. `ui/components.py`: display only, no engine logic.

## Engine invariants (do not break)
- Value alone never yields `auto`; sign mismatch blocks even if value+date match (`RN-03` → `pending/sinal_bloqueado`).
- `auto` requires: value+sign OK, `day_diff <= date_tolerance_days`, (`score >= threshold` OR `use_fuzzy=False` + 1:1 no ambiguity), no duplicate, exactly 1 candidate.
- Ambiguity (1:N/N:1) never auto → winner is smallest `day_diff`, then highest `score`; losers become `potential` (`RN-07 ambiguidade_multipla`).
- Duplicates are intra-base only, `score >= 95`, never auto (`RN-04`, `match_id = dup-{statement|ledger}-{idx}`).
- Cents: non-zero `value_diff` within tolerance → never `auto`; with `use_fuzzy` + `score < 60` → `divergent`, else `potential` (`RN-08`).
- Money is `Decimal` only, never float. `build_params` ranges: days 0–30 int, fuzzy 0–100 int, tolerance ≥ 0, `use_fuzzy` bool; no-bool-for-int; errors are pt-BR `ValueError`.
- Every decision carries `rule_id` (RN-01…RN-08), english `reason` code, `params_snapshot` + `APP_VERSION`. Status internals stay english; UI labels `auto→Conciliada, potential→Para revisão, pending→Pendente, divergent→Divergente, duplicate→Duplicada`.

## Style (enforced, differs from defaults)
- Code identifiers 100% english; user-visible strings, columns (`Data, Descrição, Valor`), errors 100% pt-BR. Never leak english to UI.
- Single quotes, no comments, no `print` (use `src/logger.py:get_logger`), no dead code, functions ≤ ~30 lines. Ruff `line-length 100`, rules `F,E,W,I`, `quote-style single`.
- Reports: detail columns `Origem, Data original/normalizada, Descrição original, Valor original/normalizado, Sinal, Status, Par ID, Diferença dias/valor, Score descrição, Regra ID, Motivo, Ação manual`; errors tab `Linha, Motivo, Como corrigir`; exceptions csv sorted by `Valor normalizado desc` with `# params` + version header.
- UI: `ui/styles.css` Apple tokens — accent `#0066cc`, canvas `#ffffff`/`#f5f5f7`, ink `#1d1d1f`; body 17px/1.47; primary CTA pill `9999px`; cards 18px radius, hairline `#e0e0e0`, no shadow; `font-weight: 500` forbidden. Manual review (`Confirmar/Rejeitar/Desfazer`) lives only in `st.session_state` with timestamp, never mutates engine tables.

## Data / fixtures
- Manual: `data/examples/extrato.csv`, `data/examples/interno.xlsx`. Edge cases `tests/fixtures/matrix/` (`;`+latin1, lowercase header, `(2500)` parens-negative, ISO date, empty, `invalido.pdf` reject).
- `data/output/` is gitignored — never write reports there in tests; build bytes in memory.
- Deps pinned (`requirements.txt` is source of truth, do not change versions); `src/` is offline (no `requests`/`http` outside Streamlit).
- Specs: `PRD.md` (requirements), `SPRINT.md` (S0–S5 all done, S5 = post-S4 refactor with no rule changes — consult before changing engine rules), `DESIGN.md` (token reference).
