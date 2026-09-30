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
4. Confira as colunas Data, Descrição e Valor e veja a prévia de 5 linhas.
5. Ajuste a tolerância de dias, a similaridade mínima e a tolerância de valor.
6. Clique em Conciliar e veja os indicadores e as abas Conciliadas, Para revisão, Pendentes, Divergentes e Erros.
7. Em Para revisão, escolha o par, compare lado a lado e clique em Confirmar ou Rejeitar. Use Desfazer última ação para reverter.

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

- Tolerância de dias: 2 (cobre compensação de 1 dia, ex.: 11/09 com 12/09).
- Similaridade mínima da descrição: 85 de 0 a 100.
- Tolerância de valor: R$ 0,00 (exige valor exato).

Limites de segurança: arquivo até 20 MB, aviso se passar de 20000 linhas.

## Como rodar os testes

```bash
.venv/bin/python -m pytest -q
```

Para ver a cobertura do código:

```bash
.venv/bin/python -m pytest --cov=src -q
```

## Como verificar o estilo do código

```bash
.venv/bin/python -m ruff check src tests
```

Os dois comandos precisam ficar verdes antes de avançar para a próxima etapa.

## Pastas do projeto

- `src/`: código principal (configurações, leitura, comparação e classificação).
- `ui/`: peças visuais da tela (tokens, cabeçalho, cartões e tabelas da S3).
- `tests/fixtures/`: arquivos pequenos de exemplo para testes, incluindo a pasta `matrix/` com variações.
- `data/examples/`: cópia dos exemplos para você testar à mão.
- `data/output/`: onde saem os relatórios (esta pasta é ignorada no git).
