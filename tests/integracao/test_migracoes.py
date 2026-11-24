"""As migrações do Alembic num banco descartável: subir, descer e bater com os modelos."""

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import bindparam, create_engine, inspect, text

# Registra todas as tabelas no metadata, como o migrations/env.py.
import diario_oficial.database.entity.ato_tipo_ato  # noqa: F401
import diario_oficial.database.entity.auto_infracao  # noqa: F401
import diario_oficial.database.entity.log_erro  # noqa: F401
import diario_oficial.database.entity.recurso_hidrico  # noqa: F401
from diario_oficial.database.configs.base import Base
from tests.integracao.conftest import migrar

pytestmark = pytest.mark.integracao

ESQUEMAS = {'processing', 'dominio', 'auto_infracao', 'recurso_hidrico'}
ESQUEMAS_DO_POSTGIS = {'topology', 'tiger', 'tiger_data'}


def ignorar_postgis(objeto, nome, tipo, refletido, comparado_com):
    """O mesmo filtro do migrations/env.py: as tabelas do PostGIS não são do projeto."""
    if tipo == 'table' and refletido and comparado_com is None:
        if nome == 'spatial_ref_sys' or objeto.schema in ESQUEMAS_DO_POSTGIS:
            return False
    return True


def test_migracoes_criam_o_que_os_modelos_descrevem(banco_vazio):
    migrar(banco_vazio)
    engine = create_engine(banco_vazio)
    try:
        with engine.connect() as conexao:
            contexto = MigrationContext.configure(
                conexao,
                opts={'include_schemas': True, 'include_object': ignorar_postgis},
            )
            # Vazio: nenhuma migração faltando (o mesmo que `alembic check`).
            assert compare_metadata(contexto, Base.metadata) == []
            assert ESQUEMAS <= set(inspect(conexao).get_schema_names())
    finally:
        engine.dispose()


def test_migracoes_preenchem_os_dominios(banco_vazio):
    migrar(banco_vazio)
    engine = create_engine(banco_vazio)
    try:
        with engine.connect() as conexao:
            for tabela in ('poder', 'adm_direta', 'adm_indireta', 'tipo_publicacao'):
                quantidade = conexao.scalar(
                    text(f'SELECT count(*) FROM dominio.{tabela}')
                )
                assert quantidade > 0, tabela
            siglas = set(conexao.scalars(text('SELECT sigla FROM dominio.tipo_ato')))
            assert {'AIIN', 'AIMU', 'OUT', 'ROUT', 'AOUT', 'AMOUT'} <= siglas
    finally:
        engine.dispose()


TABELAS_DO_PROJETO_QUE_SOBRARAM = """
    SELECT table_schema || '.' || table_name
    FROM information_schema.tables
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
      AND table_schema NOT IN :postgis
      AND table_name NOT IN
          ('alembic_version', 'spatial_ref_sys', 'geometry_columns', 'geography_columns')
"""


def test_descer_todas_as_migracoes_e_subir_de_novo(banco_vazio):
    migrar(banco_vazio)
    migrar(banco_vazio, 'base', descer=True)
    engine = create_engine(banco_vazio)
    try:
        with engine.connect() as conexao:
            # Nenhuma tabela ou view do projeto; o PostGIS fica de propósito.
            consulta = text(TABELAS_DO_PROJETO_QUE_SOBRARAM).bindparams(
                bindparam('postgis', expanding=True)
            )
            sobras = conexao.scalars(
                consulta, {'postgis': sorted(ESQUEMAS_DO_POSTGIS)}
            ).all()
            assert sobras == []
    finally:
        engine.dispose()
    migrar(banco_vazio)
