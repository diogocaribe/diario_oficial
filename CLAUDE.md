# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão geral

Raspagem e estruturação do **Diário Oficial do Estado da Bahia (DOE-BA)**, em
`https://dool.egba.ba.gov.br/`. Hoje o foco está em **EXECUTIVO → SECRETARIA DO MEIO AMBIENTE**
(SEMA/INEMA). O sistema transforma a árvore do sumário HTML do DOE em registros relacionais
(PostgreSQL) até chegar ao nível de **ato** (portaria, edital, resolução, extrato...).

Idioma do projeto: **português**. Nomes de variáveis, docstrings, comentários, mensagens de
commit e de migração ficam em português.

## Stack

- Python 3.12, Poetry
- Selenium (Chrome remoto via `selenium/standalone-chrome`) para navegar no sumário do DOE
- requests + BeautifulSoup para baixar o texto de cada publicação
- SQLAlchemy 2.0 + psycopg 3 + PostgreSQL (JSONB, CTEs, triggers, views)
- Alembic para migrações
- Typer (+ rich) para a CLI
- pytest e ruff no grupo dev

## Pipeline de dados (3 etapas)

```
DOE (site) ──Selenium──▶ processing.doe_bruto (doe_json JSONB, uma linha por edição/data)
            ──SQL CTE (explodir_doe_bruto_json)──▶ processing.publicacao (um link por linha)
            ──requests+BS4 (get_conteudo_texto_link)──▶ publicacao.conteudo_link
            ──regex (separar_ato)──▶ processing.ato (um ato por linha)
```

1. **Raspagem** — `raspar_doe.raspar_diario_oficial(data)` abre o sumário HTML, expande as
   pastas por níveis (1 = Poder, 2 = Secretaria, 3 = Superintendência/Instituto/tipo de ato,
   4/5 = Diretoria/Diretoria Geral → atos) e devolve um dict aninhado salvo em
   `doe_bruto.doe_json`. As pastas coletadas são controladas pelas listas
   `selecao_pasta_nivel_1`, `selecao_pasta_nivel_2_executivo`, `tipo_ato`, `tipo_adm_direta`,
   `tipo_adm_indireta` no topo do módulo. O comentário lá avisa: selecionar muitas secretarias
   quebra a renderização da árvore.
2. **doe_bruto → publicacao** — `DiarioOficialBrutoRepository.explodir_doe_bruto_json` mede a
   profundidade do JSON (4 ou 5 níveis) e roda uma CTE com `jsonb_object_keys` que cruza as
   chaves com as tabelas `dominio.*` para preencher as FKs. `Scripts/explode.sql` é a versão
   de rascunho/depuração dessa consulta. Depois marca `doe_bruto_para_publicacao = True`.
3. **publicacao → ato** — baixa o HTML de cada link (`conteudo_link IS NULL`), extrai o texto
   e divide em atos com o regex de `transformacao.separar_ato`. Marca
   `processada_para_ato = True`.

## Modelo de dados

- Schema `processing`: `doe_bruto`, `publicacao`, `ato`
- Schema `dominio`: `poder`, `adm_direta`, `adm_indireta`, `divisao_adm_direta`,
  `divisao_adm_indireta`, `tipo_publicacao`. São tabelas de lookup preenchidas por migração
  (`a70574a135a5`, `9e09149daa8d`...). **O nome da pasta no DOE precisa existir exatamente
  igual em `dominio.*.nome`**, senão a FK fica NULL na explosão.
- View `vw_publicacao` no schema `public` (sem prefixo), criada em `e5c2ecd42738` e recriada
  em `3dabb7927524`.
- View `vw_ato` no schema `public`, criada em `bcd56ebfe8e3`: atos das publicações com
  `auditoria IS TRUE`, com os dados da publicação, do DOE e dos domínios. O critério é o
  resultado das regras de auditoria, não uma conferência humana.
- Trigger `after_delete_delete_atos_da_mesma_pubalicacao`: apagar **um** ato apaga todos os
  atos da mesma publicação e volta `publicacao.processada_para_ato` para NULL. É a forma de
  reprocessar uma publicação.
- Colunas de controle do pipeline: `doe_bruto.doe_bruto_para_publicacao`,
  `publicacao.conteudo_link`, `publicacao.processada_para_ato`.
- `publicacao.auditoria` é gravada por `auditar-publicacao-ato` (regras em
  `diario_oficial/auditoria.py`): `true` se todos os atos da publicação foram separados
  corretamente, `false` caso contrário, `NULL` se não foi auditada. Reprocessar uma publicação
  não limpa a coluna: rode a auditoria de novo depois.
- `processing.log_erro` guarda os erros de `transformar-publicacao-ato` (`etapa =
  'separacao'`) e os achados de `auditar-publicacao-ato` (`etapa = 'auditoria'`). É histórico:
  cada ocorrência é gravada uma vez (`etapa`, `tipo`, `descricao`, `trecho`, `doe_bruto_id` e
  `publicacao_id` iguais não geram linha nova), e `criado_em` é a primeira detecção. As
  FKs para `doe_bruto` e `publicacao` são `RESTRICT` (esses dados não devem ser apagados); a
  de `ato` é `SET NULL`, para o log sobreviver ao reprocessamento.
- Entidades em `diario_oficial/database/entity/`, repositórios em
  `diario_oficial/database/repository/`, conexão em `database/configs/connection.py`
  (`DBConnectionHandler`, context manager que abre/fecha a sessão).
- Todas as entidades herdam o `Base` de `database/configs/base.py`, que define a
  `naming_convention` das constraints (`pk_`, `fk_`, `uq_`...). Entidade nova usa esse `Base`.
- Para saber o head do Alembic, rode `alembic heads` (não confie em valor fixo neste arquivo).

## Comandos

```bash
cp .env-dist .env                 # depois ajuste DATABASE_URL, SELENIUM_ADDRESS (ex.: http://localhost), SELENIUM_PORT
poetry install
source $(poetry env info --path)/bin/activate

alembic upgrade head              # cria o banco (sqlalchemy_utils) e aplica as migrações
alembic revision --autogenerate -m "descrição em português"

docker compose up -d selenium     # Chrome remoto na porta 4444 (rede externa 'inema' precisa existir)

# CLI (rodar SEMPRE a partir da raiz do repo; data no formato DD-MM-YYYY)
python diario_oficial/cli.py raspar-doe-bruto 12-11-2024 [--no-save-db]
python diario_oficial/cli.py transformar-doe-bruto-publicacao 12-11-2024 [--no-transformar-publicacao] [--no-save-db]
python diario_oficial/cli.py transformar-publicacao-ato
python diario_oficial/cli.py auditar-publicacao-ato 12-11-2024 [--no-save-db]
python diario_oficial/cli.py reprocessar-publicacoes-reprovadas [--no-save-db]  # todas as datas: apaga os atos com auditoria = false, separa e audita de novo

# Via container: o ENTRYPOINT do Dockerfile já é `python diario_oficial/cli.py`
docker compose run --rm app raspar-doe-bruto 12-11-2024 --no-save-db

# Pipeline completo em um período (raspagem, publicação, ato e auditoria); padrão de 3 meses
Scripts/pipeline_periodo.sh -i 01-07-2026

ruff check . && ruff format .     # linha 88, aspas simples

# Testes: `addopts` em pyproject.toml ignora o teste quebrado (ver Armadilhas).
pytest                                                 # suíte inteira
pytest tests/test_auditoria.py                         # um arquivo
pytest tests/test_auditoria.py::test_ato_cortado_no_meio_da_frase -v # um teste
```

Nos testes, importe pelo pacote (`from diario_oficial.transformacao import ...`).

O ambiente local do Poetry fica fora do repositório, em `~/.cache/pypoetry/virtualenvs`, e é
o interpretador usado pelo painel de testes do VS Code. Não crie `.venv` na raiz: o compose
monta a raiz no container e o `poetry run` do `ENTRYPOINT` passaria a usar esse ambiente.

`.vscode/launch.json` tem configurações de debug prontas para cada comando da CLI.

`diario_oficial/main.py` é um script de lote por intervalo de datas: **executa ao ser
importado**, com `data_inicio`/`data_fim` fixos no código. Não importe esse módulo.

## Armadilhas conhecidas

- **Imports mistos.** Os módulos usam dois estilos: `from database.repository...`,
  `import util`, `from raspar_doe import ...` (exigem `diario_oficial/` no `sys.path`, que é o
  que acontece ao rodar `python diario_oficial/cli.py`) **e** `from diario_oficial.settings
  import ...` (exige o pacote instalado pelo `poetry install`). Rodar com `python -m` ou de
  outro diretório quebra. Ao mexer nisso, cuidado com o mesmo módulo de entidade sendo
  carregado duas vezes por nomes diferentes (`database.entity.x` e
  `diario_oficial.database.entity.x`): o SQLAlchemy reclama de tabela/mapper duplicado.
- `Settings()` lê `.env` do diretório atual. Sem `.env`, qualquer import de repositório falha.
- `raspar_doe.py` executa código no import (cria `ChromeOptions`, listas de seleção) e
  `dados.py` instancia os repositórios no import.
- O SQL de `explodir_doe_bruto_json` monta a data com f-string. A data vem da CLI; para
  qualquer entrada nova, use parâmetros bind (`text(...).bindparams`).
- Links de PDF ficam fora do pipeline: `get_conteudo_texto_link` os identifica pelo
  `Content-Type` e devolve `None`, e a coleta apaga a publicação do banco
  (`apagar_publicacao_pdf`).
- `get_conteudo_texto_link` usa `verify=False` (certificado do site) e devolve `""` em caso de
  erro, então uma string vazia em `conteudo_link` significa falha na coleta, não "sem
  conteúdo". Como a coleta só pega `conteudo_link IS NULL`, essas falhas **nunca são
  tentadas de novo**: para refazer, volte a coluna para `NULL` e rode
  `transformar-doe-bruto-publicacao <data> --no-transformar-publicacao` (a etapa de coleta de
  links roda sempre, independente da flag).
- `separar_ato` compila o padrão com `re.VERBOSE`, que **ignora espaços literais**:
  `ERRATA REFERENTE` vira `ERRATAREFERENTE` e nunca casa com o texto real. Em termos com
  várias palavras use `\s+`. A ordem das alternativas importa (`PORTARIA` e `RESUMO` sozinhos
  aparecem antes das variantes mais longas e as escondem). Termos colados ao texto anterior
  ou depois de uma palavra de `PALAVRAS_DE_CITACAO` ("nomeados pela PORTARIA Nº ...") são
  citações e não iniciam ato, assim como termos depois de `Onde se lê:`, `Leia-se:`,
  `Finalidade:` ou `Art. 1º -`. Título que só vale na abertura da publicação vai em
  `TITULOS_DE_ABERTURA`. Os preâmbulos antes de `PORTARIA` (`A DIRETORA GERAL`, inclusive em
  exercício, `O SECRETÁRIO`, `O DIRETOR GERAL, EM EXERCÍCIO`) ficam fora dos atos, e a
  auditoria os aceita em `TEXTO_FORA_DOS_ATOS`; já o `O DIRETOR GERAL DO INSTITUTO ...`
  continua abrindo o ato seguinte.
- `raspar-doe-bruto` envolve a raspagem em `redirect_stdout(StringIO())`: os `print` de
  `raspar_doe` somem. Para depurar, chame `raspar_diario_oficial` direto ou remova o redirect.
- `SELENIUM_ADDRESS` precisa incluir o esquema (`http://...`); a URL é montada como
  `f'{SELENIUM_ADDRESS}:{SELENIUM_PORT}'`. Dentro da rede `inema` use o nome do serviço
  (`http://selenium`), e `HOST` do banco também não pode ser `localhost` no container.
- Views dependem de colunas: para remover uma coluna exposta em `vw_publicacao`, o
  `downgrade` precisa dar `DROP VIEW` antes e recriar a definição anterior
  (`CREATE OR REPLACE VIEW` não remove colunas). O `downgrade` de `3dabb7927524` hoje falha por
  isso.
- `util.check_word_or_list_exist_in_list` só verifica a **primeira** palavra (o `return False`
  está dentro do loop). Várias regras de nível dependem desse comportamento; não "corrija"
  sem verificar a raspagem.
- `tests/test_diario_oficial.py` importa `scripts.diario_oficial`, que não existe; por isso é
  ignorado via `addopts`. Testes novos devem ser unitários (regex de `separar_ato`, `util`,
  `calcular_profundidade_dict`) e não depender de rede, Selenium ou banco.
- `rich` é usado na CLI mas vem como dependência transitiva do Typer.
- `.project` é do DBeaver; `doc/banco_dado/` contém os modelos conceitual (UML/ODS) e lógico
  (drawio).

## Convenções

- Migrações: uma por mudança, mensagem descritiva em português. SQL bruto (views, triggers,
  dados de domínio) vai em `op.execute(sa.text(...))` com `downgrade` correspondente. Toda
  tabela nova precisa de `__table_args__ = {'schema': ...}` e de um import em
  `migrations/env.py` para o autogenerate enxergar.
- Ao adicionar uma secretaria/órgão novo: (1) incluir na lista de seleção em `raspar_doe.py`,
  (2) criar uma migração que insere o nome exato em `dominio.*`, (3) validar a explosão com
  `Scripts/explode.sql`.
- Ao alterar o regex de `separar_ato`: testar contra publicações reais já salvas
  (`processing.publicacao.conteudo_link`) antes e depois, e reprocessar apagando atos (o
  trigger cuida do resto).
- Commits no estilo Conventional Commits (`feat:`, `refactor:`, `docs:`...).
