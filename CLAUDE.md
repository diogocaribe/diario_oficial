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

## Extração de variáveis estruturadas (`diario_oficial/extracao/`)

Separada do pipeline acima: parte do texto dos atos (`processing.ato.conteudo_ato`) e
extrai campos tipados com um LLM local (Ollama + LangChain). Sem conexão com o banco e
sem efeito no import. Quem lê o banco, mostra e grava é
`diario_oficial/extracao_dados_atos.py` (`extrair_dados_atos`), usado por
`Scripts/extrair_dados_atos.py <SIGLA>` (um tipo de ato; grava só com `--save-db`) e pelo
comando `extrair-autos-infracao` da CLI (todos os subtipos de auto; grava por padrão).

- `normalizacao.py` e `utils_geo.py` (coordenadas, UTM, municípios da BA): regras
  comuns, sem LLM.
- `modelo_comum.py`: esquemas Pydantic comuns a todas as extrações (`Endereco`,
  `Pessoa`, `CoordenadaGeografica`).
- `modelo_auto_infracao.py`: os esquemas dos autos de infração, o comum
  (`AutoInfracao`) e os de cada subtipo (`AutoInterdicao`,
  `AutoMulta`, `AutoApreensao`..., cada um com o seu `Extracao<Subtipo>`). Os modelos
  de outros tipos de ato ficam em módulos `modelo_<tipo>.py` próprios.
- `llm.py`: `criar_extrator(esquema, instrucoes, ...)`, a cadeia genérica do ChatOllama.
- `base.py`: o contrato `Extracao` (sigla do tipo de ato, pasta em `dominio.tipo_publicacao`,
  esquema, instruções, `campo_registros`, `separar_trechos`,
  `preencher_vazios_pela_regex`, `conferir`) e `extrair(texto, extracao, extrator)`,
  igual para todas as extrações. `preencher_vazios_pela_regex` grava o valor da regex
  só onde o modelo deixou `null` (no AIIN, a `modalidade`, que o modelo deixava vazia na
  maioria dos autos) e nunca troca o que o modelo preencheu; roda antes de `conferir`.
- `registro.py`: `EXTRACOES`, as extrações pela sigla de `dominio.tipo_ato`; é o que o
  script recebe como parâmetro.
- `auto_infracao.py`: a extração de **todos** os autos de infração (AIIN, AIMU, AIAD,
  AIAP, AIEM, AIDM, AIDF, AIDP). Corte em trechos, instruções e conferência por regex são
  os mesmos para todos; o que muda fica num `SubtipoAuto` (sigla, nome e regex da
  penalidade, esquema, entidade, campos próprios lidos pela regex e os que ela preenche),
  e `auto_infracao.EXTRACOES` vira uma `Extracao` por subtipo. Hoje a regex preenche a
  `modalidade` da interdição e do embargo e só confere o `valor_multa` da multa. Subtipo
  novo: um `SubtipoAuto` em `SUBTIPOS`, o esquema no módulo de modelos e a tabela com a
  migração. Outro tipo de ato (não auto) ganha o próprio módulo, a própria `Extracao`
  registrada em `registro.py` e o próprio arquivo de teste.
- `outorga.py` e `modelo_outorga.py`: as outorgas de recursos hídricos (OUT, ROUT,
  AOUT, AMOUT; PPV/OUT fica de fora). O texto é um modelo fixo, então aqui a ordem se
  inverte: a extração principal é a regex (`extrair_pela_regex`) e o LLM só é chamado
  para os campos obrigatórios que ela deixou vazios (`campos_vazios`), copiando só
  esses (`base.preencher_vazios_pelo_modelo`); se o Ollama falhar, fica a regex e o
  erro vai em `erro_modelo`. A regex ancora os pontos nos pares de coordenadas: o que
  vem antes do par (corpo hídrico, "no poço 2") é do ponto seguinte, o que vem depois
  (datum, vazão, h/d, "do poço 1", finalidade) é do anterior; um uso fecha no ponto
  seguido de "para fins de", num § novo ou quando o modo muda. Esquema: `Outorga` →
  `usos` (`UsoCaptacao`, `UsoLancamento`, `UsoIntervencao`, discriminados por `modo`)
  → `pontos`. Toda vazão tem `_m3_dia` e `_m3_s`: a do texto é copiada e a outra,
  calculada. Grava no esquema `recurso_hidrico` (`entidade=Outorga`), por
  `gravacao_outorga.py` e `RecursoHidricoRepository`.
- `gravacao_<tipo>.py`: um módulo por tipo de ato, que converte os objetos Pydantic
  nas entidades do seu esquema. Os modelos Pydantic (prompt) e as entidades (banco)
  ficam **separados de propósito**: cada campo do esquema tem a coluna de mesmo nome.
  O comum fica em `gravacao_comum.py` (como `modelo_comum.py`): `CampoSemColuna` (campo
  sem coluna é erro), `valor_da_coluna`, `valores_das_colunas`, `para_endereco`,
  `para_pessoa` (CPF/CNPJ só em dígitos) e `para_geometria` (para 4674). Campo novo no
  esquema exige a coluna e a migração.
- `gravacao_auto_infracao.py`: autos → `database/entity/auto_infracao.py` (testado em
  `tests/test_gravacao_auto_infracao.py`). `autuado.endereco` vai para
  `auto_infracao.endereco_autuado_id`. Lista de objetos de um subtipo
  (`bem_apreendido`, `produto_destruido`) vira linhas da tabela filha da relação de
  mesmo nome (`bem_produto_autuado`).
- `gravacao_outorga.py`: outorgas → `database/entity/recurso_hidrico.py`. O
  `outorgado` vira `public.pessoa` + `outorgado_nome` +
  `endereco_outorgado`; cada uso vira a entidade do seu `modo`; a `coordenada` do ponto
  vira `latitude`/`longitude` (o `fuso_utm` não é gravado) e o `ponto` vai para 4674.
  `extracao_dados_atos.repositorio_e_conversao` escolhe repositório e conversão pela
  `entidade` da extração. Testes em `tests/test_gravacao_outorga.py`.

### Esquema `auto_infracao` (PostGIS)

- Tabelas com o nome do tipo de ato: `auto_infracao` (comum) e uma por subtipo
  (`auto_interdicao`, `auto_multa`, `auto_advertencia`, `auto_apreensao`, `auto_embargo`,
  `auto_demolicao`, `auto_destruicao_fornos`, `auto_destruicao_produtos`; herança
  joined-table, PK = FK), `bem_produto_autuado` (bens apreendidos e produtos destruídos),
  mais `extracao_trecho` (um por trecho enviado ao
  modelo, com `erro`, `conferencia` em JSONB e `preenchido_pela_regex`),
  `endereco` e `coordenada_extraida_trecho` (os pares como estão no texto). As
  colunas de cada subtipo ficam só na tabela dele (ex.: `auto_interdicao`): olhar só
  essa tabela parece "poucos autos preenchidos".
- `pessoa` fica em `public` (`d5f9b2c7e3a8`), comum a todas as extrações: a mesma
  pessoa pode aparecer em atos de tipos diferentes. É única por (`tipo_documento`,
  `nro_documento`), com CPF/CNPJ só em dígitos; sem documento, uma pessoa por auto. O endereço é do auto, não da pessoa.
  `auto_infracao.autuado_nome` guarda a grafia de cada auto.
- `ponto` e `poligono` são `geometry` em SIRGAS 2000 (4674), convertidos do datum citado
  no texto (`sistema_referencia_espacial` guarda o original).
- Reprocessar: `--save-db` apaga os `extracao_trecho` do ato para a sigla e grava de novo
  (cascata para autos e coordenadas). O trigger `after_delete_apagar_endereco_do_auto`
  (`c4e8a1d6f2b7`) apaga os endereços de cada auto apagado; a pessoa continua (FK
  `RESTRICT`, pode estar em outros autos), mesmo que fique sem auto.
- Views (`f2b6d8a4c1e9`), uma linha por auto: `auto_infracao.vw_auto_infracao` (colunas
  comuns, autuado, endereços em texto, geometria, ato/publicação/edição do DOE) e uma
  `vw_<tabela do subtipo>` por subtipo (`vw_auto_multa`...), que é `vw_auto_infracao`
  mais as colunas do subtipo; na apreensão e na destruição de produtos os bens vão
  juntos em texto. As de subtipo dependem de `vw_auto_infracao`: mudar uma coluna
  dela exige apagar e recriar todas.
- O banco precisa do PostGIS: o compose usa `postgis/postgis:18-3.6`. O `env.py` ignora
  `spatial_ref_sys` e os esquemas do PostGIS no autogenerate.

### Esquema `recurso_hidrico` (PostGIS)

- Criado em `3a75dc1d4897`, entidades em `database/entity/recurso_hidrico.py`, espelhando
  `modelo_outorga.py` (campo = coluna de mesmo nome, testado em
  `tests/test_tabelas_recurso_hidrico.py`): `extracao_trecho` (com
  `preenchido_pelo_modelo` e `erro_modelo`), `outorga`, `uso_recurso_hidrico` (comum) com
  `uso_lancamento` e `uso_intervencao` (joined-table, PK = FK), `ponto_uso` (`ponto` em
  4674 e o par como está no texto), `parametro_efluente` e `endereco` (sede do
  outorgado).
- A captação não tem tabela própria: `UsoCaptacao` é só uma identidade em
  `uso_recurso_hidrico`. `tipo_uso` diz a especialização e `modo` o modo do texto; a
  restrição `modo_do_tipo_uso` impede combinação errada. `finalidades` e
  `metodos_irrigacao` são `text[]` presos às listas de `modelo_outorga`.
- O outorgado fica em `public.pessoa` (FK `RESTRICT`), como o autuado. O trigger
  `after_delete_apagar_endereco_da_outorga` apaga o endereço da outorga apagada.
- Reprocessar: `--save-db` apaga os `extracao_trecho` do ato para a sigla e grava de
  novo, como nos autos.
- Views (`91d5d19a8321`), uma por tipo de uso e **uma linha por ponto**:
  `vw_outorga_captacao`, `vw_outorga_lancamento` (com vazão de diluição e
  `parametros_efluente` em texto) e `vw_outorga_intervencao`. Cada linha traz ponto
  (geometria), uso (listas em texto por `'; '`), portaria, outorgado e ato/publicação/
  edição do DOE, e `dt_vencimento` ("válida até" do texto ou `dt_portaria` + prazo em
  anos; nula se o prazo é de outra portaria). O ponto entra por LEFT JOIN (uso sem ponto aparece com `ponto_id`
  nulo), então a união das três dá todos os pontos. As três são independentes: o
  SELECT comum é montado na migração.
- Ao importar no `migrations/env.py`, use o módulo inteiro: os nomes (`Endereco`,
  `ExtracaoTrecho`) repetem os de `auto_infracao`.

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
  resultado das regras de auditoria, não uma conferência humana. Desde `7b3d9e5a2c18` tem
  `tipo_ato` e `sigla_tipo_ato`: uma linha por ato, com os tipos de `ato_tipo_ato` juntos
  por `'; '` (NULL se o ato não tem tipo).
- Trigger `after_delete_delete_atos_da_mesma_pubalicacao`: apagar **um** ato apaga todos os
  atos da mesma publicação e volta `publicacao.processada_para_ato` para NULL. É a forma de
  reprocessar uma publicação.
- `dominio.tipo_ato` lista os tipos de ato (nome e sigla, que não é única) e
  `processing.ato_tipo_ato` liga cada ato aos tipos encontrados no texto, gravados por
  `extrair-tipos-de-ato` (regras em `diario_oficial/tipo_ato.py`) só para publicações com
  `auditoria IS TRUE`. Apagar o ato ou o tipo apaga os vínculos; ato que fica sem
  vínculo volta a ser analisado na próxima execução.
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
python diario_oficial/cli.py extrair-tipos-de-ato [--data 12-11-2024] [--no-save-db]  # sem data: todas as edições

# Via container: o ENTRYPOINT do Dockerfile já é `python diario_oficial/cli.py`
docker compose run --rm app raspar-doe-bruto 12-11-2024 --no-save-db

# Pipeline completo em um período (raspagem, publicação, ato, auditoria e tipos de ato); padrão de 3 meses
Scripts/pipeline_periodo.sh -i 01-07-2026

# Extração dos dados de um tipo de ato com o Ollama (siglas AI* e OUT/ROUT/AOUT/AMOUT, pasta Portarias); grava só com --save-db
python Scripts/extrair_dados_atos.py AIIN --data 24-09-2026 [--limite 20] [--silencioso]
python Scripts/extrair_dados_atos.py AIIN --ato-id 5604 --ato-id 1469
python Scripts/extrair_dados_atos.py AIIN --save-db --pular-extraidos --silencioso  # grava no esquema auto_infracao
python Scripts/extrair_dados_atos.py OUT --save-db --pular-extraidos --silencioso   # grava no esquema recurso_hidrico
python diario_oficial/cli.py extrair-autos-infracao [--data 24-09-2026] [--limite 5] [--no-save-db] [--no-pular-extraidos] [--no-silencioso]  # todos os AI*

ruff check . && ruff format .     # linha 88, aspas simples

# Testes: `addopts` em pyproject.toml ignora o teste quebrado (ver Armadilhas) e os de integração.
pytest                                                 # suíte inteira (sem banco)
pytest tests/test_auditoria.py                         # um arquivo
pytest tests/test_auditoria.py::test_ato_cortado_no_meio_da_frase -v # um teste
pytest -m integracao                                   # integração: banco descartável no servidor do .env
```

Nos testes, importe pelo pacote (`from diario_oficial.transformacao import ...`).

Os testes de integração ficam em `tests/integracao/` (marcador `integracao`). O
`conftest.py` cria no servidor do `.env` um banco `teste_diario_oficial_<sufixo>`, aplica
as migrações e o apaga no fim; o banco de trabalho não é lido nem alterado. Os
repositórios usam esse banco porque a fixture `banco` troca o engine de
`connection.py`, e as tabelas de dados são esvaziadas (`TRUNCATE`) depois de cada teste.
Cobrem migrações (diff com os modelos, descer até a base e subir de novo), triggers,
FKs `RESTRICT`/`SET NULL`, restrições `CHECK`, views, a explosão do `doe_json` e a
gravação pelos repositórios. Precisam do `postgres` do compose no ar.

O ambiente local do Poetry fica fora do repositório, em `~/.cache/pypoetry/virtualenvs`, e é
o interpretador usado pelo painel de testes do VS Code. Não crie `.venv` na raiz: o compose
monta a raiz no container e o `poetry run` do `ENTRYPOINT` passaria a usar esse ambiente.

`.vscode/launch.json` tem configurações de debug prontas para cada comando da CLI.

`diario_oficial/main.py` é um script de lote por intervalo de datas: **executa ao ser
importado**, com `data_inicio`/`data_fim` fixos no código. Não importe esse módulo.

## Armadilhas conhecidas

- **Imports mistos.** Os módulos usam dois estilos: `import util`, `import dados`,
  `from raspar_doe import ...` (exigem `diario_oficial/` no `sys.path`, que é o
  que acontece ao rodar `python diario_oficial/cli.py`) **e** `from diario_oficial.settings
  import ...` (exige o pacote instalado pelo `poetry install`). Rodar com `python -m` ou de
  outro diretório quebra. Ao mexer nisso, cuidado com o mesmo módulo de entidade sendo
  carregado duas vezes por nomes diferentes (`database.entity.x` e
  `diario_oficial.database.entity.x`): o SQLAlchemy reclama de tabela/mapper duplicado. Por
  isso o pacote `database` é sempre importado como `diario_oficial.database...`.
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
  (`CREATE OR REPLACE VIEW` não remove colunas), como faz o de `3dabb7927524`.
  `pytest -m integracao` desce todas as migrações e pega esse erro.
- `util.check_word_or_list_exist_in_list` só verifica a **primeira** palavra (o `return False`
  está dentro do loop). Várias regras de nível dependem desse comportamento; não "corrija"
  sem verificar a raspagem.
- `tests/test_diario_oficial.py` importa `scripts.diario_oficial`, que não existe; por isso é
  ignorado via `addopts`. Testes novos devem ser unitários (regex de `separar_ato`, `util`,
  `calcular_profundidade_dict`) e não depender de rede, Selenium ou banco; o que só o
  banco confere (trigger, view, restrição, SQL) vai em `tests/integracao/`.
- `rich` é usado na CLI mas vem como dependência transitiva do Typer.
- `.project` é do DBeaver; `doc/banco_dado/` contém os modelos conceitual (UML/ODS) e lógico
  (drawio).

## Convenções

- Migrações: uma por mudança, mensagem descritiva em português. SQL bruto (views, triggers,
  dados de domínio) vai em `op.execute(sa.text(...))` com `downgrade` correspondente. Toda
  tabela nova precisa de `__table_args__ = {'schema': ...}` e de um import em
  `migrations/env.py` para o autogenerate enxergar. A exceção é `public` (ex.:
  `entity/pessoa.py`): vai **sem** `schema`, porque o Alembic reflete o esquema padrão
  sem nome e `schema='public'` faria o autogenerate propor apagar e recriar a tabela.
- Ao adicionar uma secretaria/órgão novo: (1) incluir na lista de seleção em `raspar_doe.py`,
  (2) criar uma migração que insere o nome exato em `dominio.*`, (3) validar a explosão com
  `Scripts/explode.sql`.
- Ao alterar o regex de `separar_ato`: testar contra publicações reais já salvas
  (`processing.publicacao.conteudo_link`) antes e depois, e reprocessar apagando atos (o
  trigger cuida do resto).
- Commits no estilo Conventional Commits (`feat:`, `refactor:`, `docs:`...).
