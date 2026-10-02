# Conciliação Bancária Automatizada

Ferramenta simples que compara o extrato do banco com os lançamentos internos da empresa e mostra o que já está certo e o que precisa de revisão.

O objetivo principal é o relatório de exceções: o que conciliou sozinho, o que ficou pendente e o que precisa de olhar humano.

## O que você precisa

- Computador com Python 3.10 ou mais novo (testado no 3.12).
- Os dois arquivos para comparar: extrato e interno, em CSV ou Excel.
- Cerca de 5 minutos para instalar e testar.

## Como instalar

1. Baixe este projeto e entre na pasta dele.
2. Crie um ambiente isolado (recomendado):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Instale os pacotes:

```bash
pip install -r requirements.txt
```

4. Para quem vai desenvolver ou rodar os testes, instale também:

```bash
pip install -r requirements_dev.txt
```

## Como executar

Para abrir a tela de conciliação, rode:

```bash
streamlit run app.py
```

Fluxo em 7 passos:

1. Abra o endereço mostrado no terminal.
2. Envie o extrato bancário em CSV ou Excel.
3. Envie os lançamentos internos em CSV ou Excel.
4. Confira o mapeamento das colunas Data, Descrição e Valor e veja as prévias formatadas abaixo dos cartões.
5. Ajuste a tolerância de dias, a similaridade mínima e a tolerância de valor.
6. Clique em Conciliar e veja os indicadores e as abas Conciliadas, Para revisão, Pendentes, Divergentes, Duplicadas e Erros. Em Para revisão, escolha o par, compare lado a lado e clique em Confirmar ou Rejeitar. Use Desfazer última ação para reverter.
7. Clique em Baixar Excel para o relatório completo e em Baixar CSV de exceções para a lista só com pendências. O cartão mostra o resumo (conciliadas, revisão, pendentes) e o rodapé explica como funciona a conciliação. A versão do motor vai nos relatórios.

Você pode testar com os arquivos de exemplo em `data/examples/`:

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

## Parâmetros padrão

Você poderá ajustar na tela, mas os valores iniciais são:

- Tolerância de dias: 2 (cobre diferenças de até 2 dias, D+2; ex.: 11/09 com 13/09).
- Similaridade mínima da descrição: 85 de 0 a 100. Desligue a chave Usar similaridade para ignorar o texto.
- Tolerância de valor: 0.00 (exige valor exato). Para permitir centavos, digite com ponto, ex.: 0.05.

Limites de segurança: arquivo até 20 MB; acima de 20000 linhas o cálculo pode demorar (aviso no log com Volume alto: resultado pode demorar).

## Relatórios

Na tela, após conciliar, use a seção Exportar relatórios. Os arquivos saem na hora, sem salvar na pasta do projeto:

- `relatorio_conciliacao.xlsx` com abas Resumo, Conciliadas, Para_Revisao, Pendentes, Divergentes, Duplicadas, Erros e Log_Regras. O Resumo traz os indicadores, os parâmetros usados e a versão do motor. As abas de detalhe usam as colunas Origem, Data original, Data normalizada, Descrição original, Valor original, Valor normalizado, Sinal, Status, Par ID, Diferença dias, Diferença valor, Score descrição, Regra ID, Motivo e Ação manual. A aba Erros usa Linha, Motivo e Como corrigir. A aba Log_Regras mostra cada decisão com regra, diferenças, motivo e ação manual com data e hora.
- `relatorio_excecoes.csv` só com o que não conciliou (Para revisão, Pendente, Divergente, Duplicada e Erros), ordenado por Valor normalizado do maior para o menor. O início do arquivo traz os parâmetros e a versão.

Os dois relatórios guardam o retrato dos parâmetros (tolerância de dias, similaridade mínima, tolerância de valor e versão) para auditoria.

## Erros comuns

| Mensagem na tela | O que fazer |
|---|---|
| Formato não suportado. Envie CSV ou Excel. | Envie arquivo .csv, .xls ou .xlsx. PDF e txt não entram. |
| Arquivo vazio. Verifique o modelo com colunas Data, Descrição, Valor. | Confira se o arquivo tem cabeçalho e ao menos 1 linha. |
| Arquivo acima de 20 MB. | Divida o arquivo em meses menores e envie de novo. |
| Coluna obrigatória não encontrada: Valor. Mapeie manualmente. | Nos campos Data, Descrição e Valor, escolha a coluna certa de cada arquivo. |
| Data inválida na linha 7. Use DD/MM/AAAA. | Corrija a data para 10/09/2026 ou 2026-09-10 e reimporte. |
| Valor inválido na linha 9. Ex.: -R$ 2.500,00. | Corrija o valor com número e sinal e reimporte. |
| Nome de arquivo inválido. Verifique o arquivo enviado. | Renomeie sem .. ou pastas e envie de novo. |
| Volume alto: resultado pode demorar. | Acima de 20000 linhas o cálculo demora mais. Aguarde ou divida o lote. |

Uma linha com erro não para o lote. As linhas boas seguem para a conciliação e as ruins ficam na aba Erros.

## Como rodar os testes

```bash
.venv/bin/python -m pytest -q
```

Para ver a cobertura do código:

```bash
.venv/bin/python -m pytest --cov=src -q
```

Para medir o desempenho com 5000 linhas de cada lado:

```bash
.venv/bin/python -m scripts.bench
```

## Como verificar o estilo do código

```bash
.venv/bin/python -m ruff check src tests app.py ui scripts
```

Os dois comandos precisam ficar verdes antes de avançar para a próxima etapa.

## Pastas do projeto

- `app.py`: tela fina (194 linhas) que só monta os painéis e chama as seções.
- `src/`: motor e serviços (leitura, normalização, comparação, classificação e relatórios). Fachadas finas com a lógica em pacotes:
  - `src/display.py`: textos, datas e valores para tela e relatório.
  - `src/normalization/` + `src/normalize.py`: datas, valores, sinais, descrições e tabelas.
  - `src/filtering/` + `src/filters.py`: texto, valor, período e contadores (`result_filters.py` usa na tela).
  - `src/review/` + `src/review_state.py`: confirmação, desfazer e histórico da revisão manual.
  - `src/reporting/`: relatórios (`headers`, `formatting`, `kpis`, `snapshots`, `lookups`, `details`, `errors`, `rule_log`, `workbook`, `exceptions`, `determinism`, `summary`).
  - `src/classification/`: classificação (`rules`, `ambiguity`, `duplicates`, `pending`, `tables`).
  - `src/filters.py`, `src/review_state.py`, `src/export_service.py`: filtros de tela, estado da revisão manual e bytes de exportação.
  - `src/guards.py`, `src/money.py`, `src/params.py`, `src/entries.py`, `src/labels.py`: bases compartilhadas sem duplicação.
- `ui/`: peças visuais da tela (tokens, cabeçalho, cartões e tabelas).
- `ui/sections/`: seções da tela (`upload`, `params_section`, `results`, `result_filters`, `review`, `history`, `export_section`).
- `ui/components/`: base, navegação, KPIs, tabelas e cartões de revisão.
- `scripts/`: apoio como `bench.py` para medir 5000 x 5000 em menos de 30 segundos.
- `tests/`: 207 testes verdes, cobertura 90% (`test_filters.py`, `test_review_state.py`, `test_export_service.py`, `test_reporting_split.py`, `test_classification_split.py` além dos testes S0–S4).
- `tests/fixtures/`: arquivos pequenos de exemplo para testes, incluindo a pasta `matrix/` com variações.
- `data/examples/`: cópia dos exemplos para você testar à mão.
- `data/output/`: onde saem os relatórios se você salvar à mão (esta pasta é ignorada no git).
- `docs/superpowers/plans/`: planos de refatoração pós-S4 (sem mudança de regra de negócio).

## Depois do MVP (não fazer agora)

Estes itens ficam para depois e não estão no programa atual:

- Arquivo CNAB 240 ou 400.
- Conciliação 1:N por soma de valores.
- Tela de login com usuários e permissões.
- Ligação com ERP ou Open Finance.
- Leitura de PDF de extrato ou OCR de imagem.
