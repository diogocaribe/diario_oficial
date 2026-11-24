"""As tabelas do esquema recurso_hidrico cobrem todos os campos de modelo_outorga.

Sem banco: compara os campos dos esquemas Pydantic com as colunas e relações das
entidades. Campo novo no esquema sem coluna faz este teste falhar.
"""

import pytest
from sqlalchemy import inspect

from diario_oficial.database.entity import recurso_hidrico as entidades
from diario_oficial.extracao import modelo_outorga

# Campos que não são colunas com o mesmo nome: viram outra coluna ou outra tabela.
FORA_DA_TABELA = {
    # outorgado_pessoa_id (public.pessoa), outorgado_nome e endereco_outorgado
    entidades.Outorga: {'outorgado'},
    # latitude e longitude da coordenada viram colunas do ponto
    entidades.PontoUso: {'coordenada'},
}


def campos(esquema: type) -> set[str]:
    return set(esquema.model_fields) | set(esquema.model_computed_fields)


def colunas_e_relacoes(entidade: type) -> set[str]:
    mapa = inspect(entidade)
    return {coluna.key for coluna in mapa.columns} | set(mapa.relationships.keys())


@pytest.mark.parametrize(
    'esquema, entidade',
    [
        (modelo_outorga.Outorga, entidades.Outorga),
        (modelo_outorga.UsoCaptacao, entidades.UsoCaptacao),
        (modelo_outorga.UsoLancamento, entidades.UsoLancamento),
        (modelo_outorga.UsoIntervencao, entidades.UsoIntervencao),
        (modelo_outorga.PontoUso, entidades.PontoUso),
        (modelo_outorga.ParametroEfluente, entidades.ParametroEfluente),
    ],
)
def test_todo_campo_tem_coluna_ou_relacao(esquema, entidade):
    faltando = campos(esquema) - FORA_DA_TABELA.get(entidade, set())
    assert faltando - colunas_e_relacoes(entidade) == set()


def test_outorgado_e_coordenada_tem_onde_ficar():
    assert {'outorgado', 'outorgado_nome', 'endereco_outorgado'} <= (
        colunas_e_relacoes(entidades.Outorga)
    )
    assert {'latitude', 'longitude'} <= colunas_e_relacoes(entidades.PontoUso)


def test_especializacao_de_cada_modo():
    identidade = {
        entidade: inspect(entidade).polymorphic_identity
        for entidade in (
            entidades.UsoCaptacao,
            entidades.UsoLancamento,
            entidades.UsoIntervencao,
        )
    }
    assert identidade == {
        entidades.UsoCaptacao: 'uso_captacao',
        entidades.UsoLancamento: 'uso_lancamento',
        entidades.UsoIntervencao: 'uso_intervencao',
    }
    # A captação não tem tabela própria; lançamento e intervenção têm.
    assert inspect(entidades.UsoCaptacao).local_table.name == 'uso_recurso_hidrico'
    assert inspect(entidades.UsoLancamento).local_table.name == 'uso_lancamento'
    assert inspect(entidades.UsoIntervencao).local_table.name == 'uso_intervencao'


def test_listas_fechadas_iguais_no_modelo_e_no_banco():
    restricoes = {
        restricao.name: str(restricao.sqltext)
        for restricao in entidades.UsoRecursoHidrico.__table__.constraints
        if hasattr(restricao, 'sqltext')
    }
    for valor in modelo_outorga.FINALIDADES:
        assert repr(valor) in restricoes['ck_uso_recurso_hidrico_finalidades']
    for valor in modelo_outorga.METODOS_IRRIGACAO:
        assert repr(valor) in restricoes['ck_uso_recurso_hidrico_metodos_irrigacao']
