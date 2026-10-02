# Conciliação Bancária Automatizada

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
![Streamlit 1.64.0](https://img.shields.io/badge/streamlit-1.64.0-red)
![Testes 251 verdes](https://img.shields.io/badge/testes-251_verdes-brightgreen)
![Cobertura 93%](https://img.shields.io/badge/cobertura-93%25-green)
![Versão do motor 1.0.0](https://img.shields.io/badge/motor-1.0.0-lightgrey)

Compara o extrato do banco com os lançamentos internos e mostra o que já está certo e o que precisa de revisão humana.

O foco é o relatório de exceções: o que conciliou sozinho, o que ficou pendente e o que precisa de olhar humano. Uma linha com erro nunca para o lote.

## Sumário

- [Funcionalidades](#funcionalidades)
- [Fora de escopo](#fora-de-escopo)
- [Requisitos](#requisitos)
- [Instalação rápida](#instalação-rápida)
- [Como usar](#como-usar)
- [Formato dos arquivos](#formato-dos-arquivos)
- [Parâmetros](#parâmetros)
- [Relatórios](#relatórios)
- [Arquitetura](#arquitetura)
- [Qualidade](#qualidade)
- [Erros comuns](#erros-comuns)
- [Roadmap](#roadmap)
- [Como contribuir](#como-contribuir)
- [Licença e versão](#licença-e-versão)

## Funcionalidades

- Lê extrato e interno em CSV ou XLSX, com prévia formatada antes de conciliar.
- Normaliza datas, valores, sinais e descrições sem abortar o lote em erro isolado.
- Classifica em 5 estados com regra auditável RN-01 a RN-08:
  - Conciliada (`auto`), Para revisão (`potential`), Pendente (`pending`), Divergente (`divergent`), Duplicada (`duplicate`).
- Revisão manual lado a lado em Para revisão, com Confirmar, Rejeitar e Desfazer última ação.
- Filtros de tela por texto, valor, período e contadores, sem alterar o motor.
- Exporta `relatorio_conciliacao.xlsx` com 8 abas e `relatorio_excecoes.csv` ordenado por valor, ambos com retrato de parâmetros e versão do motor para auditoria.

## Fora de escopo

Não faz parte do MVP atual:

- Arquivo CNAB 240 ou 400.
- Conciliação 1:N por soma de valores.
- Tela de login com usuários e permissões.
- Ligação com ERP ou Open Finance.
- Leitura de PDF de extrato ou OCR de imagem.

## Requisitos

| Item | Detalhe |
|---|---|
| Python | 3.12 ou mais novo, testado no 3.12 |
| Entradas | Extrato + interno em `.csv` ou `.xlsx` |
| Tempo | Cerca de 5 minutos para instalar e testar |
| Limites | Arquivo até 20 MB; acima de 20000 linhas o cálculo pode demorar |

Pilha pinada em `requirements.txt`:

| Pacote | Versão |
|---|---|
| `pandas` | 3.0.6 |
| `openpyxl` | 3.1.5 |
| `RapidFuzz` | 3.14.6 |
| `streamlit` | 1.64.0 |

## Instalação rápida

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Para desenvolver ou rodar testes, instale também:

```bash
pip install -r requirements_dev.txt
```

## Como usar

Abra a tela de conciliação:

```bash
.venv/bin/streamlit run app.py
```

Fluxo em 7 passos:

1. Abra o endereço mostrado no terminal.
2. Envie o extrato bancário em CSV ou Excel.
3. Envie os lançamentos internos em CSV ou Excel.
4. Confira o mapeamento das colunas Data, Descrição e Valor e veja as prévias formatadas abaixo dos cartões.
5. Ajuste a tolerância de dias, a similaridade mínima e a tolerância de valor.
6. Clique em Conciliar e veja os indicadores e as abas Conciliadas, Para revisão, Pendentes, Divergentes, Duplicadas e Erros. Em Para revisão, escolha o par, compare lado a lado e clique em Confirmar ou Rejeitar. Use Desfazer última ação para reverter.
7. Clique em Baixar relatório em Excel (8 abas) ou em Baixar só exceções (CSV). O cartão mostra o conteúdo, a versão do motor e as decisões manuais incluídas, e avisa se os parâmetros mudaram após a conciliação. O rodapé explica como funciona a conciliação.

Arquivos de exemplo para testar à mão:

- `data/examples/extrato.csv`
- `data/examples/interno.xlsx`

## Formato dos arquivos

Os dois arquivos precisam ter as mesmas 3 colunas, com os nomes exatamente assim:

| Coluna | Exemplo | Explicação |
|---|---|---|
| Data | 10/09/2026 | Dia da movimentação. Vale 10/09/2026 ou 2026-09-10. |
| Descrição | Pagamento Fornecedor X | Texto livre do lançamento. |
| Valor | -R$ 2.500,00 | Número com sinal. Negativo é saída, positivo é entrada. Vale -2500, (2500) ou R$ 4.800,00. |

Exemplo de `extrato.csv`:

```csv
Data,Descrição,Valor
10/09/2026,Pagamento Fornecedor X,"-R$ 2.500,00"
11/09/2026,Recebimento Cliente Y,"R$ 4.800,00"
```

Dica: no CSV, quando o valor tem vírgula, deixe ele entre aspas. O Excel e o LibreOffice abrem com os acentos corretos se o arquivo estiver em UTF-8.

## Parâmetros

Ajustáveis na tela, com valores iniciais:

| Parâmetro | Padrão | O que faz |
|---|---|---|
| Tolerância de dias | 2 | Cobre diferenças de até 2 dias, D+2. Ex.: 11/09 com 13/09. |
| Similaridade mínima da descrição | 85 de 0 a 100 | Nota de corte do texto. Desligue a chave Usar similaridade para ignorar o texto. |
| Tolerância de valor | 0.00 | Exige valor exato. Para permitir centavos, digite com ponto. Ex.: 0.05. |

Limites de segurança: arquivo até 20 MB; acima de 20000 linhas o cálculo pode demorar, com aviso no log `Volume alto: resultado pode demorar`.

## Relatórios

Na tela, após conciliar, use a seção Exportar relatórios. Os arquivos saem na hora, sem salvar na pasta do projeto:

- `relatorio_conciliacao.xlsx` com abas Resumo, Conciliadas, Para_Revisao, Pendentes, Divergentes, Duplicadas, Erros e Log_Regras. O Resumo traz os indicadores, os parâmetros usados e a versão do motor. As abas de detalhe usam as colunas Origem, Data original, Data normalizada, Descrição original, Valor original, Valor normalizado, Sinal, Status, Par ID, Diferença dias, Diferença valor, Score descrição, Regra ID, Motivo e Ação manual. A aba Erros usa Linha, Motivo e Como corrigir. A aba Log_Regras mostra cada decisão com regra, diferenças, motivo e ação manual com data e hora.
- `relatorio_excecoes.csv` só com o que não conciliou (Para revisão, Pendente, Divergente, Duplicada e Erros), ordenado por Valor normalizado do maior para o menor. O início do arquivo traz os parâmetros e a versão.

Os dois relatórios guardam o retrato dos parâmetros (tolerância de dias, similaridade mínima, tolerância de valor e versão) para auditoria.

## Arquitetura

- `app.py`: tela fina com 99 linhas que só monta os painéis e chama as seções.
- `src/`: motor e serviços (leitura, normalização, comparação, classificação e relatórios). Fachadas finas com a lógica em pacotes:
  - `src/display.py`: textos, datas e valores para tela e relatório.
  - `src/normalization/` + `src/normalize.py`: datas, valores, sinais, descrições e tabelas.
  - `src/filtering/` + `src/filters.py`: texto, valor, período e contadores, consumido na tela por `ui/sections/result_filters.py`.
  - `src/review/` + `src/review_state.py`: confirmação, desfazer e histórico da revisão manual.
  - `src/reporting/`: relatórios (`headers`, `formatting`, `kpis`, `snapshots`, `lookups`, `details`, `errors`, `rule_log`, `workbook`, `exceptions`, `determinism`, `summary`, `display_guards`).
  - `src/classification/`: classificação (`rules`, `ambiguity`, `duplicates`, `pending`, `tables`).
  - `src/filters.py`, `src/review_state.py`, `src/export_service.py`: filtros de tela, estado da revisão manual e bytes de exportação.
  - `src/guards.py`, `src/money.py`, `src/params.py`, `src/entries.py`, `src/labels.py`: bases compartilhadas sem duplicação.
- `ui/`: peças visuais da tela (tokens, cabeçalho, cartões e tabelas).
- `ui/sections/`: seções da tela (`upload/(file_io,mapping_ui,preview_ui,section)`, `params_section`, `results/(kpis,match_tab,pending_tab,duplicate_tab,error_tab,tabs)`, `result_filters`, `review`, `history`, `export_section`).
- `ui/components/`: base, navegação, KPIs, tabelas e cartões de revisão.
- `scripts/`: apoio como `bench.py` para medir 5000 x 5000 em menos de 30 segundos.
- `tests/`: 251 testes verdes, cobertura 93%, incluindo `test_filters.py`, `test_review_state.py`, `test_export_service.py`, `test_reporting_split.py`, `test_classification_split.py`, `test_display_guards.py`, `test_app_thin.py`, `test_guards_edge.py`, `test_loader_edge.py`, `test_filter_nan.py` além dos testes S0–S5.
- `tests/fixtures/`: arquivos pequenos de exemplo para testes, incluindo a pasta `matrix/` com variações.
- `data/examples/`: cópia dos exemplos para testar à mão.
- `data/output/`: saída manual de relatórios quando salvos à mão (pasta ignorada no git).

## Qualidade

```bash
.venv/bin/python -m pytest -q
```

```bash
.venv/bin/python -m pytest --cov=src -q
```

```bash
.venv/bin/python -m scripts.bench
```

Mede o desempenho com 5000 linhas de cada lado. Não rode casualmente, é lento.

```bash
.venv/bin/python -m ruff check src tests app.py ui scripts
```

Testes e estilo precisam ficar verdes antes de avançar para a próxima etapa. Meta de cobertura do motor: 80% ou mais.

## Erros comuns

| Mensagem na tela | O que fazer |
|---|---|
| Formato não suportado. Envie CSV ou Excel. | Envie arquivo .csv ou .xlsx. PDF, txt e xls não entram. |
| Arquivo vazio. Verifique o modelo com colunas Data, Descrição, Valor. | Confira se o arquivo tem cabeçalho e ao menos 1 linha. |
| Arquivo acima de 20 MB. | Divida o arquivo em meses menores e envie de novo. |
| Coluna obrigatória não encontrada: Valor. Mapeie manualmente. | Nos campos Data, Descrição e Valor, escolha a coluna certa de cada arquivo. |
| Data inválida na linha 7. Use DD/MM/AAAA. | Corrija a data para 10/09/2026 ou 2026-09-10 e reimporte. |
| Valor inválido na linha 9. Ex.: -R$ 2.500,00. | Corrija o valor com número e sinal e reimporte. |
| Nome de arquivo inválido. Verifique o arquivo enviado. | Renomeie sem .. ou pastas e envie de novo. |
| Volume alto: resultado pode demorar. | Acima de 20000 linhas o cálculo demora mais. Aguarde ou divida o lote. |

Uma linha com erro não para o lote. As linhas boas seguem para a conciliação e as ruins ficam na aba Erros.

## Roadmap

Depois do MVP, fora do programa atual. Ver `SPRINT.md` para o histórico S0–S6 docs-only:

- Arquivo CNAB 240 ou 400.
- Conciliação 1:N por soma de valores.
- Tela de login com usuários e permissões.
- Ligação com ERP ou Open Finance.
- Leitura de PDF de extrato ou OCR de imagem.

## Como contribuir

1. Crie um ambiente com `.venv` e instale `requirements.txt` + `requirements_dev.txt`.
2. Rode testes e estilo antes de fechar qualquer tarefa.
3. Não mude regras do motor sem consultar `PRD.md` v1.2 e `SPRINT.md`.
4. Não mude versões pinadas em `requirements.txt` sem motivo auditável.

## Licença e versão

- Licença: a definir, sem arquivo `LICENSE` no repositório hoje.
- Versão do motor: `1.0.0` em `src/config.py:APP_VERSION`, gravada em cada decisão e relatório para auditoria.
- Especificações vigentes: `PRD.md` v1.2, `SPRINT.md` S0–S6 concluídos, `DESIGN.md` como referência de tokens.
