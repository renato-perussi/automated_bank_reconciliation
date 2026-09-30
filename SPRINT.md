# SPRINT.md — Conciliação Bancária Automatizada
## `automated_bank_reconciliation`

| Campo | Valor |
|---|---|
| Origem | `PRD.md` v1.0 + `DESIGN.md` |
| Idioma docs/dados/UI | pt-BR obrigatório |
| Idioma código | 100% inglês (variáveis, constantes, funções, classes, módulos) |
| Estilo código | aspas simples + sem comentários + funções ≤ ~30 linhas + `ruff` |
| Design | Obrigatório `DESIGN.md` (Apple minimalista, 1 acento `#0066cc`) |
| Execução | `pip install -r requirements.txt` + `streamlit run app.py` |

---

## Convenções

- Sprint: `S0` … `S4`. Task: `S{N}-T{NN}`. Subtask: checkbox `- [ ]`.
- Todo identificador de código nos exemplos está em inglês. Todo label/UI/coluna/mensagem está em pt-BR.
- Mapeamento interno obrigatório: coluna pt-BR → variável em inglês → exibição pt-BR.
  - `Data` → `normalized_date` / `day_diff` / `date_tolerance_days`
  - `Descrição` → `normalized_description` / `description_score` / `fuzzy_threshold`
  - `Valor` → `normalized_value` / `value_diff` / `value_tolerance`
  - `Regra ID` → `rule_id`, `Par ID` → `match_id`, `Motivo` → `reason`
- Padrão de código (vale para todas as sprints):
  - `'aspas simples'`, sem `print` debug (usar `logging`), sem código morto.
  - Sem comentários; código limpo e autoexplicativo.
  - Exemplo válido:
  ```python
  def normalize_value(raw):
      if raw is None or raw == '':
          return None
      txt = str(raw).strip().replace('R$', '').strip()
      if txt.startswith('(') and txt.endswith(')'):
          txt = '-' + txt[1:-1]
      return Decimal(txt)
  ```
- Padrão DESIGN (vale para toda UI):
  - Cores: `{colors.primary}` `#0066cc` único acento, `{colors.canvas}` `#ffffff`, `{colors.canvas-parchment}` `#f5f5f7`, `{colors.ink}` `#1d1d1f`.
  - Tipo: `{typography.body}` 17px/400/1.47, headlines 600 com tracking negativo, weight 500 proibido.
  - Formas: `{rounded.pill}` 9999px para CTA primário, `{rounded.lg}` 18px para cards, tiles full-bleed sem radius.
  - Sem sombra em cards/botões. Sombra única só em render de produto.
  - Componentes: `{component.global-nav}`, `{component.sub-nav-frosted}`, `{component.button-primary}`, `{component.store-utility-card}`, `{component.search-input}`, `{component.floating-sticky-bar}`, `{component.footer}`.

---

## Visão das sprints

| Sprint | Foco | RFs | RNs | Entrega verificável |
|---|---|---|---|---|
| S0 | Base, config, fixtures, qualidade | — | — | Pastas + `config.py` + fixtures + `pytest`/`ruff` verdes |
| S1 | Ingestão + normalização + validação | RF-001 – RF-007 | RN-02, RN-03 (base), RN-09 (erros) | `loader.py` + `normalize.py` + preview 5 linhas + tabela de erros |
| S2 | Motor: matching + classificação | RF-008 – RF-016 | RN-01 – RN-08, RN-10 (base) | `matcher.py` + `classifier.py` + Casos A–D verdes + sem auto por valor isolado |
| S3 | UI Streamlit + DESIGN.md | RF-017, RF-018, RF-022, T-01 – T-06 | — | App navegável 7 cliques, KPIs, revisão lado a lado, responsivo |
| S4 | Relatórios + auditoria + hardening + DoD | RF-019 – RF-021, T-07 – T-08 | RN-09, RN-10 | `relatorio_conciliacao.xlsx` + `relatorio_excecoes.csv` + DoD 100% |

Ordem de execução: `S0 → S1 → S2 → S3 → S4`. S3 pode iniciar mockada após S1, mas só fecha após S2.

---

## S0 — Base e fundação

Objetivo: repositório executável, determinístico e com gates de qualidade antes de qualquer regra de negócio.

### S0-T01 — Estrutura, dependências e config

Depende de: nada. RF/RN: NFR-011, NFR-013. NFR-013a.

- [x] Criar pastas conforme `PRD.md §18`: `src/`, `ui/`, `tests/fixtures/`, `data/examples/`, `data/output/`.
- [x] Criar `src/__init__.py`, `ui/__init__.py` vazios com `'...'` ou docstring mínima.
- [x] Conferir `requirements.txt` (fonte da verdade, somente dependências diretas de prod — não downgradear): `pandas==3.0.6`, `openpyxl==3.1.5`, `RapidFuzz==3.14.6`, `streamlit==1.64.0`.
- [x] Preencher `requirements_dev.txt`: `ruff==0.16.9` + `pytest==9.1.1` + `pytest-cov`.
- [x] Criar `src/config.py` com constantes em inglês:
  - [x] `DATE_TOLERANCE_DAYS = 2` # default tolerância de dias
  - [x] `FUZZY_THRESHOLD = 85` # default fuzzy 0-100
  - [x] `VALUE_TOLERANCE = Decimal('0.00')` # default tolerância de valor
  - [x] `MAX_FILE_SIZE_MB = 20` # limite por arquivo
  - [x] `MAX_ROWS_WARNING = 20000` # aviso de volume
  - [x] `SUPPORTED_EXTENSIONS = ('.csv', '.xls', '.xlsx')` # formatos aceitos
  - [x] `PT_REQUIRED_COLUMNS = ('Data', 'Descrição', 'Valor')` # colunas pt-BR obrigatórias
  - [x] `APP_VERSION = '1.0.0'` # versão do motor p/ snapshot
- [x] Criar `src/logger.py` ou bloco em `config.py` com `get_logger(name)` via `logging` (sem `print`).
- [x] Atualizar `.gitignore`: `.venv/`, `data/output/*`, `*.pyc`, `.pytest_cache/`, `.streamlit/secrets.toml`.
- [x] Validar `python -m compileall src` + `pip install -r requirements.txt` em ambiente limpo.

Critério de aceite: `pip install -r requirements.txt` instala sem erro em Python 3.10+; `import src.config` expõe os 8 nomes acima; nenhum identificador em português em `src/`.

### S0-T02 — Fixtures de dados pt-BR + exemplos mínimos

Depende de: S0-T01. RF: RF-001, RF-002. RN: —.

- [x] Criar `tests/fixtures/extrato.csv` exatamente:
  ```csv
  Data,Descrição,Valor
  10/09/2026,Pagamento Fornecedor X,-R$ 2.500,00
  11/09/2026,Recebimento Cliente Y,R$ 4.800,00
  ```
- [x] Criar `tests/fixtures/interno.xlsx` (aba única) com header `Data | Descrição | Valor` e linhas `10/09/2026 | Fornecedor X NF 1254 | -2500` e `12/09/2026 | Cliente Y | 4800`.
- [x] Copiar os dois para `data/examples/` como exemplo de uso.
- [x] Criar `tests/fixtures/matrix/` com variações: `latin1_ponto_virgula.csv` (`;` + latin1), `header_minusculo.csv` (`data,descricao,valor`), `valor_parenteses.csv` (`(2500)`), `data_iso.csv` (`2026-09-10`), `vazio.csv`, `invalido.pdf` (para rejeição).
- [x] Criar `tests/fixtures/duplicadas.csv` com 2 linhas idênticas de `-1500` para RN-04.

Critério de aceite: fixtures abrem em Excel/LibreOffice com acentos corretos; `extrato.csv` e `interno.xlsx` reproduzem o exemplo do PRD §2.3.

### S0-T03 — Qualidade: ruff single-quote + pytest + idempotência base

Depende de: S0-T01. RF: —. NFR: NFR-013, NFR-014, NFR-016.

- [x] Configurar `ruff` (pyproject ou `ruff.toml`): `quote-style = 'single'`, `line-length = 100`, regras `F,E,W,I`.
- [x] Criar `tests/test_config.py`: asserts de defaults (`DATE_TOLERANCE_DAYS == 2`, `FUZZY_THRESHOLD == 85`, `VALUE_TOLERANCE == Decimal('0.00')`).
- [x] Criar `tests/conftest.py` com fixtures `sample_config` e `fixture_paths`.
- [x] Rodar `ruff check src tests` + `pytest -q` verdes antes de S1.
- [x] Documentar comandos no `README.md` (instalação + `streamlit run app.py` + `pytest` + `ruff`), tudo em pt-BR, sem jargão.

Critério de aceite: `ruff` sem erro (reprova aspas duplas e identificador pt); `pytest` verde; README permite setup em ≤ 5 min.

DoD S0: estrutura pronta, requirements fixados, fixtures pt-BR criadas, gates verdes. ✅ Concluída.

---

## S1 — Ingestão, mapeamento e normalização (RF-001 – RF-007)

Objetivo: dois arquivos heterogêneos viram duas tabelas limpas `statement` x `ledger` com erros isolados.

### S1-T01 — Loader: leitura CSV/Excel + limites + preview (RF-001, RF-002, RF-004)

Arquivo: `src/loader.py`. Funções em inglês, mensagens pt-BR.

- [x] Implementar `detect_encoding(path)` tentando `'utf-8'` → `'latin1'`.
- [x] Implementar `detect_delimiter(path, encoding)` tentando `','` → `';'` (amostra 5 linhas).
- [x] Implementar `load_table(path)`:
  - [x] validar extensão em `SUPPORTED_EXTENSIONS`, senão erro pt-BR `'Formato não suportado. Envie CSV ou Excel.'`
  - [x] validar tamanho `<= MAX_FILE_SIZE_MB`, senão erro pt-BR `'Arquivo acima de 20 MB.'`
  - [x] CSV via `pandas.read_csv` com encoding/delimiter detectados; Excel via `pandas.read_excel(engine='openpyxl')` primeira aba
  - [x] retornar `DataFrame` bruto + metadados (`encoding`, `delimiter`, `sheet`)
- [x] Implementar `get_preview(df, n=5)` retornando 5 primeiras linhas para UI.
- [x] Implementar `validate_not_empty(df)` gerando erro bloqueante pt-BR `'Arquivo vazio. Verifique o modelo com colunas Data, Descrição, Valor.'`
- [x] Sanitizar nome de arquivo contra path traversal (NFR-006).
- [x] Testar com `matrix/` do S0-T02 + arquivo 20 MB (preview < 3s, NFR-002).

Critério de aceite: RF-001/RF-002 — 3 formatos abrem, preview 5 linhas, `.pdf` rejeitado com mensagem pt-BR clara; arquivo vazio bloqueia.

### S1-T02 — Mapeamento de colunas pt-BR → variáveis em inglês (RF-003)

Arquivo: `src/loader.py` (continuação) ou `src/mapping.py`.

- [x] Implementar `normalize_header(name)` removendo acento, caixa, espaços (`'Descrição'` → `'descricao'`, `'Valor'` → `'valor'`, `'Data'` → `'data'`, `'Historico'` → `'historico'`, `'Amount'` → `'valor'`).
- [x] Implementar `auto_map_columns(df)` com dicionário:
  - [x] data: `{'data', 'date', 'dt', 'data_lancamento'}`
  - [x] descrição: `{'descricao', 'descrição', 'historico', 'histórico', 'description', 'memo'}`
  - [x] valor: `{'valor', 'value', 'amount', 'montante'}`
- [x] Implementar `apply_mapping(df, mapping)` retornando colunas internas `event_date`, `description`, `amount` preservando originais `Data`, `Descrição`, `Valor`.
- [x] Se alguma obrigatória ausente, levantar erro pt-BR `'Coluna obrigatória não encontrada: Valor. Mapeie manualmente.'` e bloquear execução.
- [x] Expor `get_mapping_options(df)` para os `selectbox` da UI (T-02).

Critério de aceite: RF-003 — auto-detecção acerta `data/descricao/valor` e minúsculas; correção manual possível; sem mapeamento completo não executa matching.

### S1-T03 — Normalização: data, valor+sinal, descrição (RF-005, RF-006, RF-007 + RN-03)

Arquivo: `src/normalize.py`.

- [x] `normalize_date(raw)`:
  - [x] aceita `DD/MM/YYYY`, `YYYY-MM-DD`, `DD-MM-YYYY`, `datetime` Excel → `date` ISO `YYYY-MM-DD`
  - [x] inválida → `None` + código `'DATA_INVALIDA'`
- [x] `normalize_amount(raw)`:
  - [x] trata `'R$ 2.500,00'`, `'2500.00'`, `'(2500)'` → negativo, `'-2500'`, `'2.500 D'` → negativo, `'2.500 C'` → positivo
  - [x] retorna `Decimal` + preserva `raw`; inválido → `None` + `'VALOR_INVALIDO'`
- [x] `detect_sign(normalized_value, raw_text)`:
  - [x] débito: `'-'`, `'D'`, `'DEB'`, `'SAIDA'`, `'(...)'` → `-1`; crédito: `'+'`, `'C'`, `'CRED'`, `'ENTRADA'` → `+1`
  - [x] documentar precedência: sinal explícito vence; parênteses sempre débito
- [x] `normalize_description(raw)`:
  - [x] lower, remove acento, pontuação, espaços duplos → forma canônica; preserva original para exibição
  - [x] ex.: `'Pagamento Fornecedor X'` e `'fornecedor x nf 1254'` viram formas comparáveis sem perder original
- [x] `normalize_table(df_mapped)` aplicando as 3 + `sign`, gerando `normalized_date`, `normalized_amount`, `normalized_description`, `sign`, `row_hash`, `source` (`'statement'` | `'ledger'`).
- [x] Linhas com `None` vão para tabela de erros com `error_code` (`'DATA_INVALIDA'`, `'VALOR_INVALIDO'`, `'COLUNA_AUSENTE'`), não participam do matching.

Critério de aceite: RF-005/006/007 — matriz de formatos do S0 passa; `10/09/2026` vira `2026-09-10`; `-R$ 2.500,00` vira `Decimal('-2500')` + `sign=-1`; descrições preservam original.

### S1-T04 — Validação linha a linha + testes (RF-004 + NFR-015)

Arquivos: `src/validate.py` (ou dentro de `normalize.py`) + `tests/test_loader.py` + `tests/test_normalize.py`.

- [x] `collect_errors(df_normalized)` separando `valid_df` x `error_df` com colunas pt-BR `Linha`, `Motivo`, `Orientação`.
- [x] Mensagens pt-BR acionáveis: `'Data inválida na linha 7. Use DD/MM/AAAA.'`, `'Valor inválido na linha 9. Ex.: -R$ 2.500,00.'`
- [x] Garantir 1 linha corrompida não aborta lote (NFR-015).
- [x] Testes `test_loader.py`: 3 formatos, `;`+latin1, rejeição pdf, vazio bloqueante, limite 20 MB.
- [x] Testes `test_normalize.py`: datas (4 formatos + inválida), valores (6 formatos + inválido), sinais D/C/parênteses, descrição canônica.
- [x] Cobertura `normalize` + `loader` ≥ 80%.

Critério de aceite: RF-004 — erros listados por linha com motivo; linhas com erro fora do matching; 1 linha ruim não quebra lote.

DoD S1: fixtures do PRD normalizam sem erro; `pytest tests/test_loader.py tests/test_normalize.py` verdes; `ruff` limpo; nenhum label inglês vaza para erro. ✅ Concluída.

---

## S2 — Motor de conciliação (RF-008 – RF-016 + RN-01 – RN-08)

Objetivo: regra composta valor+sinal+data+fuzzy com zero auto por valor isolado e desempate determinístico.

### S2-T01 — Parâmetros + bloqueio por valor+sinal + janela de data (RF-008, RF-010, RF-011, RF-012, RF-013)

Arquivo: `src/matcher.py`. Constantes de `src/config.py`.

- [x] `build_params(date_tolerance_days=2, fuzzy_threshold=85, value_tolerance=Decimal('0.00'), use_fuzzy=True)` validando ranges `0–30`, `0–100`, `>=0`.
- [x] `find_candidates(statement_df, ledger_df, params)`:
  - [x] bloqueio (blocking) por `normalized_amount (± value_tolerance)` + `sign` igual — nunca comparar tudo contra tudo
  - [x] filtro `abs((statement_date - ledger_date).days) <= date_tolerance_days`
  - [x] RN-03: `sign` diferente bloqueia, mesmo com valor/data iguais (Caso D)
  - [x] RN-01: valor igual sozinho nunca gera `auto`; no máx. `potential`
  - [x] retornar lista de tuplas `(statement_idx, ledger_idx, day_diff, value_diff)`
- [x] `calc_value_diff(a, b)` com `Decimal` (sem float).
- [x] Teste Caso B: `11/09 +4800` x `12/09 +4800` com default casa (`day_diff=1`); com `date_tolerance_days=0` não casa.
- [x] Teste Caso D: `-2500` x `+2500` nunca casa.
- [x] Benchmark 5k x 5k < 30s via blocking (NFR-001); se > 20k linhas emitir aviso pt-BR.

Critério de aceite: RF-011/012/013 — exato casa, tolerância respeitada, sinal oposto bloqueia; performance com blocking.

### S2-T02 — Fuzzy de descrição com rapidfuzz (RF-015 + RN-05)

Arquivo: `src/matcher.py` (continuação).

- [x] `score_description(a_norm, b_norm)` usando `rapidfuzz.fuzz.token_set_ratio` (fallback `WRatio` documentado).
- [x] Respeitar `fuzzy_threshold` default 85 e `use_fuzzy=False` (descrição ignorada).
- [x] Anexar `description_score` 0–100 a cada candidato de S2-T01.
- [x] Caso A: `Pagamento Fornecedor X` x `Fornecedor X NF 1254` gera score < 85 → não auto (vai para revisão); se threshold reduzido ou fuzzy off + 1:1 → pode auto.
- [x] Garantir execução local sem rede (NFR-005).

Critério de aceite: RF-015 — score exibido na revisão; abaixo do threshold não eleva para automática.

### S2-T03 — Classificador 5 estados + desempate + duplicadas (RF-014, RF-016 + RN-04, RN-06, RN-07, RN-08)

Arquivo: `src/classifier.py`.

- [x] `detect_duplicates(df, params)`:
  - [x] mesmo `normalized_amount` + `sign` + `day_diff <= date_tolerance_days` + `description_score >= 95` na mesma base → `duplicada_suspeita`
  - [x] duplicada nunca auto, exige revisão
- [x] `classify_match(candidate, params, has_ambiguity, is_duplicate)`:
  - [x] `auto` sse: valor+sinal OK **E** data dentro tolerância **E** (fuzzy ≥ threshold **OU** fuzzy off + 1:1 sem ambiguidade) **E** sem duplicidade **E** 1 candidato (RN-06)
  - [x] senão: `potential` se ≥1 candidato próximo (data limite ou fuzzy 60–threshold ou múltiplos); `pending` se nenhum; `divergent` se `value_diff <= value_tolerance` mas ≠ 0 (ex.: `2500.00` x `2500.04` com `0.05` → `potential` motivo `'divergencia_centavos'`)
  - [x] status internos em inglês: `'auto'`, `'potential'`, `'pending'`, `'divergent'`, `'duplicate'`; UI exibe pt-BR `Conciliada`, `Para revisão`, `Pendente`, `Divergente`, `Duplicada`
- [x] `resolve_ambiguity(candidates)` (RN-07): 1:N/N:1 escolhe menor `day_diff`, depois maior `description_score`; demais viram `potential` motivo `'ambiguidade_multipla'`; nunca auto em ambiguidade.
- [x] `build_result_tables(...)` retornando 5 DataFrames + `reason` (`rule_id` RN-01…RN-08 + snapshot params).
- [x] Caso C: dois `-1500` distintos → nunca auto + alerta ambiguidade.

Critério de aceite: RF-014/RF-016 — 5 estados corretos; duplicada bloqueia auto; ambiguidade nunca auto; centavos viram revisão, não auto.

### S2-T04 — Testes do motor + armadilhas (RN-01, RN-06, NFR-007, NFR-014)

Arquivos: `tests/test_matcher.py`, `tests/test_classifier.py`.

- [x] Teste Caso A (exato com descrição divergente): `day_diff=0`, `value_diff=0` → `potential` se fuzzy < 85, `auto` se ≥ 85.
- [x] Teste Caso B (tolerância): `day_diff=1` → `auto` com default.
- [x] Teste armadilha valor (NFR-007): 2 transações distintas mesmo valor, datas fora ou múltiplos candidatos → zero `auto`.
- [x] Teste sinal (Caso D): bloqueado.
- [x] Teste duplicidade: fixture `duplicadas.csv` → `duplicate` + sem `auto`.
- [x] Teste tolerância valor: `2500.00` x `2500.04` com `0.05` → `potential` + `'divergencia_centavos'`; com `0.00` → sem match de valor.
- [x] Teste idempotência: mesmos arquivos + params → mesmo resultado (hash).
- [x] Cobertura motor ≥ 80% (`pytest --cov=src --cov-report=term`).

Critério de aceite: todos os Casos A–D do PRD §9.1 reproduzidos; `pytest` verde; < 30s para 5k x 5k.

DoD S2: motor determinístico, auditável, sem falso positivo por valor isolado, com `rule_id` em toda decisão. ✅ Concluída.

---

## S3 — UI Streamlit + DESIGN.md (RF-017, RF-018, RF-022 + T-01 – T-06)

Objetivo: fluxo em ≤ 7 cliques, todo em pt-BR, todo dentro dos tokens Apple.

### S3-T01 — Fundação visual: styles.css com tokens (NFR-009, NFR-010)

Arquivos: `ui/styles.css`, `ui/components.py`.

- [x] Criar `ui/styles.css` com variáveis:
  - [x] `--primary: #0066cc` (`{colors.primary}`), `--primary-focus: #0071e3`, `--canvas: #ffffff`, `--parchment: #f5f5f7`, `--ink: #1d1d1f`
  - [x] fonte `SF Pro Display, SF Pro Text, system-ui, -apple-system, Inter, sans-serif`; body 17px/1.47, `-0.374px` em display
  - [x] `.btn-primary { background: var(--primary); border-radius: 9999px; padding: 11px 22px; }` + `:active { transform: scale(0.95); }` + `:focus { outline: 2px solid var(--primary-focus); }`
  - [x] `.card { background: #fff; border: 1px solid #e0e0e0; border-radius: 18px; padding: 24px; }` sem `box-shadow`
  - [x] `.nav-global { background: #000; height: 44px; }`, `.nav-sub { background: rgba(245,245,247,0.8); backdrop-filter: saturate(180%) blur(20px); height: 52px; }`
  - [x] `.search { border-radius: 9999px; height: 44px; }`, `.footer { background: #f5f5f7; }`
- [x] Criar helpers em `ui/components.py`: `render_header()`, `render_kpi_card(label, value)`, `render_status_table(df)`, todos com aspas simples e sem comentários.
- [x] Checklist proibições: sem segunda cor, sem gradiente, sem `font-weight: 500`, sem sombra em card/botão, tiles sem radius.

Critério de aceite: `styles.css` usa só tokens; botão primário pill azul 11×22px; cards brancos hairline sem sombra; body 17px.

### S3-T02 — T-01 Header + T-02 Upload + T-03 Parâmetros

Arquivo: `app.py` (etapas 1–3).

- [x] T-01 Header: `{component.global-nav}` 44px preta + `{component.sub-nav-frosted}` com steps pt-BR `'1 Upload → 2 Parâmetros → 3 Resultados'`; título `'Conciliação Bancária'` em `{typography.display-lg}`.
- [x] T-02 Upload (`{component.store-utility-card}`):
  - [x] dois `st.file_uploader` lado a lado: `'Extrato bancário (CSV ou Excel)'` e `'Lançamentos internos (CSV ou Excel)'`
  - [x] 3 `selectbox` por arquivo para `Data`, `Descrição`, `Valor` (default auto-mapeado de S1-T02)
  - [x] preview 5 linhas por arquivo (`st.dataframe`)
  - [x] erros de S1-T04 em tabela pt-BR + botão `{component.button-primary}` `'Conciliar'`
- [x] T-03 Parâmetros (`{component.configurator-option-chip}` + `{component.search-input}`):
  - [x] `st.slider('Tolerância de dias', 0, 30, 2)` → `date_tolerance_days`
  - [x] `st.slider('Similaridade mínima (%)', 0, 100, 85)` + `st.toggle('Usar similaridade de descrição', True)` → `fuzzy_threshold` + `use_fuzzy`
  - [x] `st.number_input('Tolerância de valor (R$)', 0.00, 10.00, 0.00, step=0.01)` → `value_tolerance`
  - [x] textos de ajuda em `{colors.ink-muted-48}` pt-BR, ex.: `'2 dias cobre compensação D+1.'`
- [x] Manter estado em `st.session_state` (`statement_df`, `ledger_df`, `params`, `results`).

Critério de aceite: upload → mapeamento → parâmetros → `Conciliar` em ≤ 4 cliques; labels 100% pt-BR; variáveis internas em inglês.

### S3-T03 — T-04 KPIs + T-05 Resultados + T-06 Revisão (RF-017, RF-018, RF-022)

Arquivo: `app.py` (etapas 4–6).

- [x] T-04 KPIs (5 `{component.store-utility-card}` sem sombra, fundo `{colors.surface-pearl}`):
  - [x] `'Total extrato'`, `'Total interno'`, `'% Conciliado'`, `'% Para revisão'`, `'% Pendente/Divergente'` + barra `st.progress`
  - [x] `'Taxa de exceção'` em destaque (= `1 - % auto`)
- [x] T-05 Resultados (`{component.product-tile-light}` + abas pt-BR):
  - [x] `st.tabs(['Conciliadas', 'Para revisão', 'Pendentes', 'Divergentes', 'Erros'])`
  - [x] cada aba `st.dataframe` com colunas pt-BR + filtros `st.text_input('Buscar descrição')` (`{component.search-input}` pill) + `st.slider('Valor')` + `st.date_input('Período')`
  - [x] RF-017: `'Extrato sem par'` e `'Interno sem par'` em tabelas separadas na aba Pendentes
- [x] T-06 Revisão lado a lado:
  - [x] `st.columns(2)`: esquerda extrato, direita interno + `day_diff`, `value_diff`, `description_score`, `rule_id` traduzidos: `'Diferença dias'`, `'Diferença valor'`, `'Score'`, `'Regra'`
  - [x] botões `{component.button-primary}` `'Confirmar'` e `{component.button-secondary-pill}` `'Rejeitar'` (44×44 mín)
  - [x] confirmar → `'conciliada_manual'` + log (`review_action` + timestamp); rejeitar → volta para pendente; reversível na sessão (RN-10)

Critério de aceite: RF-017/018/022 — sem par listado dos dois lados com filtros; par sugerido mostra diffs+score+regra; confirmar/rejeitar atualiza tabelas + log.

### S3-T04 — Responsivo + acessibilidade (NFR-008, NFR-010)

- [x] Breakpoints 1440/1068/833/734/640/480: ≤734px upload e KPIs empilham 1 coluna, tabelas com scroll horizontal, hero 56→28px.
- [x] Alvos ≥ 44×44, labels em todos os inputs, contraste `#1d1d1f` sobre `#fff`, navegação por teclado no Streamlit.
- [x] Teste manual: 390px (mobile) e 1440px (desktop) sem sobreposição; Lighthouse a11y sem erro crítico.

Critério de aceite: fluxo completo em ≤ 7 cliques mobile e desktop; nenhum texto inglês visível; DESIGN checklist §11 passa.

DoD S3: app roda `streamlit run app.py`, fluxo fim-a-fim com fixtures, visual reprova se fora dos tokens. ✅ Concluída.

Nota S3: `global-nav`/`sub-nav` removidos por decisão do produto (seções já numeradas dispensam steps); aba `Duplicadas` incluída além das 5 previstas.

---

## S4 — Relatórios, auditoria, hardening e DoD final

Objetivo: fechar o valor principal (relatório de exceções) e provar NFRs + DoD.

### S4-T01 — Report: KPIs + Excel/CSV pt-BR (RF-019, RF-020, RF-022)

Arquivo: `src/report.py`.

- [x] `calc_kpis(results)` retornando dict inglês (`total_statement`, `total_ledger`, `pct_auto`, `pct_review`, `pct_pending`, `pct_divergent`, `exception_rate`) exibido em pt-BR.
- [x] `build_conciliation_workbook(results, params)` gerando `relatorio_conciliacao.xlsx` com abas pt-BR: `Resumo` (KPIs + snapshot params + `APP_VERSION`), `Conciliadas`, `Para_Revisao`, `Pendentes`, `Divergentes`, `Erros`, `Log_Regras` via `openpyxl`.
- [x] `build_exceptions_csv(results)` gerando `relatorio_excecoes.csv` só com não conciliados, ordenado por `Valor normalizado desc`, header pt-BR do §10.2.
- [x] `format_brl(value)` para exibição (`R$ 4.800,00`), mantendo `Decimal` interno.
- [x] Snapshot obrigatório em ambos: `date_tolerance_days`, `fuzzy_threshold`, `value_tolerance`, `APP_VERSION`.
- [x] Testes `tests/test_report.py`: abas existem, headers pt-BR, ordenação, snapshot presente.

Critério de aceite: RF-019/020 — Excel com 7 abas + CSV só exceções, ambos com snapshot; headers 100% pt-BR.

### S4-T02 — Log de regras + T-07 Exportação + T-08 Erros (RF-021 + RN-09, RN-10)

Arquivos: `src/report.py` + `app.py`.

- [x] `build_rule_log(results)` com por decisão: `rule_id` (RN-01…), `match_id`, `day_diff`, `value_diff`, `description_score`, `params_snapshot`, `reason`, `error_code` quando aplicável.
- [x] T-07 Exportação: botões download `st.download_button('Baixar Excel', ...)` + `'Baixar CSV de exceções'` (`{component.button-pearl-capsule}` secundário) + `{component.floating-sticky-bar}` com KPIs persistentes + `{component.footer}` parchment com versão.
- [x] T-08 Erros: tabela pt-BR `Linha | Motivo | Como corrigir` + `{component.icon-circular}`; sem vermelho de marca (usar ink + texto).
- [x] RN-10: ação manual registra `review_action` + timestamp, sobrescreve auto, reversível na sessão, visível no log.
- [x] Teste: cada linha `auto`/`potential` tem `rule_id`; confirmação manual aparece no log.

Critério de aceite: RF-021 — 100% das decisões com regra; log visível e exportável; ação manual auditada.

### S4-T03 — Hardening NFRs: performance, resiliência, segurança, portabilidade

- [x] NFR-001/NFR-003: script `scripts/bench.py` gerando 5k x 5k sintéticos, assert < 30s; > 20k emitir aviso pt-BR `'Volume alto: resultado pode demorar.'`
- [x] NFR-002: preview 20 MB < 3s (medir com `time`).
- [x] NFR-004/NFR-005: provar offline (desconectar rede, rodar matching); `grep -r 'requests|http' src` vazio exceto Streamlit.
- [x] NFR-006: teste path traversal (`'../../etc/passwd.csv'`) rejeitado; > 20 MB rejeitado.
- [x] NFR-015: teste linha corrompida no meio do CSV não aborta lote.
- [x] NFR-016: teste idempotência (2 runs mesmos arquivos+params → DataFrames iguais).
- [x] NFR-011/NFR-012: matriz `matrix/` passa em Linux; documentar Windows/macOS (`pip install` + `streamlit run`).
- [x] NFR-008: contagem de cliques upload→relatório ≤ 7.

Critério de aceite: todos os NFRs com evidência (tempo, log, teste).

### S4-T04 — DoD final + README + verificação ponta a ponta

- [x] Rodar checklist `PRD.md §15` item a item:
  - [x] exemplos §10 reproduzem Casos A–D §9.1 com defaults
  - [x] valor isolado nunca auto; duplicidade bloqueia; sinal oposto nunca casa
  - [x] relatórios + KPIs corretos
  - [x] 5k x 5k < 30s; offline; `pip install` + `streamlit run` OK
  - [x] código inglês + aspas simples + sem comentários + `ruff` limpo + funções ≤ ~30 linhas
  - [x] `pytest --cov=src` verde, motor ≥ 80%
  - [x] visual DESIGN.md (body 17px, `#0066cc` único, pill, sem sombra, responsivo)
- [x] Finalizar `README.md` pt-BR: o que é, como instalar, como usar (7 passos), formato `Data,Descrição,Valor`, parâmetros, relatórios, solução de erros comuns.
- [x] `git status` limpo para `data/output/` (ignorado), fixtures versionadas.
- [x] Registro de decisão: o que fica para pós-MVP (CNAB, 1:N por soma, login, ERP/Open Finance, PDF/OCR) — não implementar.

Critério de aceite: DoD 100% marcado com evidência (logs de `pytest`, `ruff`, bench, screenshots 390px/1440px).

DoD S4 (release MVP): app instalável, conciliando exemplos do PRD, com relatório de exceções exportável e log auditável. ✅ Concluída.

---

## Rastreabilidade RF → Sprint

| RF | Sprint | Task |
|---|---|---|
| RF-001, RF-002 | S1 | S1-T01 |
| RF-003 | S1 | S1-T02 |
| RF-004 | S1 | S1-T01, S1-T04 |
| RF-005, RF-006, RF-007 | S1 | S1-T03 |
| RF-008, RF-009, RF-010 | S2 | S2-T01, S2-T02 |
| RF-011, RF-012, RF-013 | S2 | S2-T01 |
| RF-014 | S2 | S2-T03 |
| RF-015 | S2 | S2-T02 |
| RF-016 | S2 | S2-T03 |
| RF-017, RF-018, RF-022 | S3 | S3-T03 |
| RF-019, RF-020 | S4 | S4-T01 |
| RF-021 | S4 | S4-T02 |

RN-01 – RN-08 em S2-T01/T02/T03; RN-09/RN-10 em S1-T03/S4-T02; NFR-009/DESIGN em S3-T01/T04; demais NFRs em S4-T03.

---

## Riscos por sprint + mitigação

- S1 RT-02/RT-03 (encoding, header deslocado): mitigado por `detect_encoding/delimiter` + `auto_map_columns` + remapeamento manual + matriz de fixtures.
- S2 RT-01/RT-04 (O(n²), falso positivo): mitigado por blocking valor+sinal + janela data + `resolve_ambiguity` nunca auto + teste armadilha.
- S3 RNisco-01 (confiança cega no auto): mitigado por separação visual auto vs revisão + taxa de exceção em destaque + `rule_id` visível.
- S4 RNisco-02 (tolerância ampla): mitigado por defaults conservadores (2, 85, 0.00) + alerta ao ampliar + snapshot nos relatórios.

---

## Ordem de execução sugerida (checklist)

- [x] S0-T01 → S0-T02 → S0-T03 (gates verdes)
- [x] S1-T01 → S1-T02 → S1-T03 → S1-T04 (tabelas limpas)
- [x] S2-T01 → S2-T02 → S2-T03 → S2-T04 (motor + Casos A–D)
- [x] S3-T01 → S3-T02 → S3-T03 → S3-T04 (UI + DESIGN)
- [x] S4-T01 → S4-T02 → S4-T03 → S4-T04 (relatórios + DoD)

Cada task só fecha com `pytest` da sua área verde + `ruff check` limpo + aceite da seção marcado.

---

## S5 — Refatoração pós-S4 (sem mudança de regra)

Objetivo: reduzir arquivos grandes a fachadas finas com pacotes testáveis, sem alterar RF-001–RF-022, RN-01–RN-10, NFRs nem Casos A–D. S0–S4 seguem congeladas acima.

- [x] S5-T01 — Bases compartilhadas: `src/guards.py`, `src/money.py`, `src/params.py`, `src/entries.py`, `src/labels.py` eliminando duplicação de `matcher`/`classifier`/`report`.
- [x] S5-T02 — `app.py` 962→190 linhas: `src/filters.py`, `src/review_state.py`, `src/export_service.py` + `ui/sections/` (`upload`, `params_section`, `results`, `review`, `history`, `export_section`). Wrappers compat preservados, `main` com 7 `render_*`.
- [x] S5-T03 — `src/report.py` 791→111 e `src/classifier.py` 553→93: `src/reporting/` (`headers`, `formatting`, `kpis`, `snapshots`, `lookups`, `details`, `errors`, `rule_log`, `workbook`, `exceptions`) + `src/classification/` (`rules`, `ambiguity`, `duplicates`, `pending`, `tables`). Bytes xlsx/csv e 5 tabelas idênticos.
- [x] S5-T04 — Testes: 167→201 verdes, cobertura 93% (`test_filters`, `test_review_state`, `test_export_service`, `test_reporting_split`, `test_classification_split`). Planos em `docs/superpowers/plans/`.

Critério de aceite: `ruff check src tests app.py ui scripts` limpo + `pytest -q` 201 verdes + auditoria `PASS` + invariantes (valor isolado nunca auto, sinal bloqueia RN-03, ambiguidade nunca auto RN-07, centavos nunca auto RN-08) preservadas.
