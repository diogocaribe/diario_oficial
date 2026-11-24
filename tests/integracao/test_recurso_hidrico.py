"""Esquema recurso_hidrico: gravação das outorgas, reprocessamento, trigger e restrições.

Usa os textos reais de ``test_outorga``, extraídos só pela regex (sem Ollama).
"""

from datetime import date

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from diario_oficial.database.entity import recurso_hidrico as entidades
from diario_oficial.database.entity.ato import Ato
from diario_oficial.database.entity.pessoa import Pessoa
from diario_oficial.database.repository.recurso_hidrico_repository import (
    RecursoHidricoRepository,
)
from diario_oficial.extracao.gravacao_outorga import para_trechos
from diario_oficial.extracao.outorga import extrair_pela_regex
from tests.test_outorga import (
    CAPTACAO_SUBTERRANEA_1156,
    DUAS_PORTARIAS_24350,
    INTERVENCAO_27768,
    LANCAMENTO_24493,
    VALIDA_ATE_22968,
)

pytestmark = pytest.mark.integracao


def gravar(ato_id: int, texto: str, sigla: str = 'OUT') -> None:
    trechos = [{'trecho': texto, 'modelos': extrair_pela_regex(texto).outorgas}]
    RecursoHidricoRepository().gravar_extracao(
        ato_id, sigla, para_trechos(ato_id, sigla, trechos, 'qwen')
    )


def contar(sessao: Session, entidade) -> int:
    return sessao.scalar(select(func.count()).select_from(entidade))


def test_captacao_gravada_com_ponto_em_sirgas_na_bahia(banco, criar_publicacao):
    _, [ato_id] = criar_publicacao([CAPTACAO_SUBTERRANEA_1156])
    gravar(ato_id, CAPTACAO_SUBTERRANEA_1156)

    with Session(banco) as sessao:
        [outorga] = sessao.scalars(select(entidades.Outorga)).all()
        assert outorga.nro_portaria == '20771'
        assert outorga.outorgado.nro_documento == '24671320568'
        assert outorga.endereco_outorgado.municipio == 'Barro Alto'
        [uso] = outorga.usos
        assert (uso.tipo_uso, uso.modo) == ('uso_captacao', 'captacao_subterranea')
        assert uso.finalidades == ['irrigacao']
    with banco.connect() as conexao:
        srid, x, y = conexao.execute(
            text(
                'SELECT ST_SRID(ponto), ST_X(ponto), ST_Y(ponto) '
                'FROM recurso_hidrico.ponto_uso'
            )
        ).one()
    assert srid == 4674
    assert -47 < x < -37 and -19 < y < -8


def test_cada_modo_vai_para_a_sua_tabela(banco, criar_publicacao):
    _, [lancamento, intervencao] = criar_publicacao(
        [LANCAMENTO_24493, INTERVENCAO_27768]
    )
    gravar(lancamento, LANCAMENTO_24493)
    gravar(intervencao, INTERVENCAO_27768)

    [outorga_intervencao] = extrair_pela_regex(INTERVENCAO_27768).outorgas
    with Session(banco) as sessao:
        uso = entidades.UsoRecursoHidrico
        tipos = sessao.execute(select(uso.tipo_uso, uso.modo).distinct()).all()
        assert sorted(tipos) == [
            ('uso_intervencao', 'intervencao'),
            ('uso_lancamento', 'lancamento_efluente'),
        ]
        assert contar(sessao, entidades.UsoLancamento) == 1
        assert contar(sessao, entidades.UsoIntervencao) == len(outorga_intervencao.usos)
        assert contar(sessao, entidades.ParametroEfluente) > 0


def test_ato_com_duas_portarias_grava_duas_outorgas(banco, criar_publicacao):
    _, [ato_id] = criar_publicacao([DUAS_PORTARIAS_24350])
    gravar(ato_id, DUAS_PORTARIAS_24350)

    with Session(banco) as sessao:
        portarias = sessao.scalars(
            select(entidades.Outorga.nro_portaria).order_by(entidades.Outorga.id)
        )
        assert list(portarias) == ['18324', '18325']


def test_regravar_o_ato_troca_a_extracao_e_apaga_os_enderecos_antigos(
    banco, criar_publicacao
):
    _, [ato_id] = criar_publicacao([CAPTACAO_SUBTERRANEA_1156])
    gravar(ato_id, CAPTACAO_SUBTERRANEA_1156)
    gravar(ato_id, CAPTACAO_SUBTERRANEA_1156)

    with Session(banco) as sessao:
        assert contar(sessao, entidades.ExtracaoTrecho) == 1
        assert contar(sessao, entidades.Outorga) == 1
        assert contar(sessao, entidades.PontoUso) == 1
        assert contar(sessao, entidades.Endereco) == 1
        assert contar(sessao, Pessoa) == 1
    repositorio = RecursoHidricoRepository()
    assert repositorio.get_atos_extraidos('OUT', [ato_id]) == {ato_id}
    assert repositorio.get_atos_extraidos('ROUT', [ato_id]) == set()


def test_apagar_o_ato_apaga_a_outorga_e_o_endereco_e_mantem_a_pessoa(
    banco, criar_publicacao
):
    _, [ato_id] = criar_publicacao([LANCAMENTO_24493])
    gravar(ato_id, LANCAMENTO_24493)
    with Session(banco) as sessao:
        sessao.execute(delete(Ato).where(Ato.id == ato_id))
        sessao.commit()
        for entidade in (
            entidades.ExtracaoTrecho,
            entidades.Outorga,
            entidades.UsoRecursoHidrico,
            entidades.UsoLancamento,
            entidades.ParametroEfluente,
            entidades.PontoUso,
            entidades.Endereco,
        ):
            assert contar(sessao, entidade) == 0, entidade.__tablename__
        assert contar(sessao, Pessoa) == 1


def test_pessoa_com_outorga_nao_pode_ser_apagada(banco, criar_publicacao):
    _, [ato_id] = criar_publicacao([CAPTACAO_SUBTERRANEA_1156])
    gravar(ato_id, CAPTACAO_SUBTERRANEA_1156)
    with Session(banco) as sessao:
        with pytest.raises(IntegrityError, match='outorgado_pessoa_id'):
            sessao.execute(delete(Pessoa))
            sessao.commit()


# Restrições que o modelo Pydantic não alcança: valem para quem grava direto no banco.

USO = """
    INSERT INTO recurso_hidrico.uso_recurso_hidrico
        (outorga_id, tipo_uso, modo, finalidades, metodos_irrigacao)
    VALUES (:outorga_id, :tipo_uso, :modo, :finalidades, :metodos)
"""


@pytest.mark.parametrize(
    ('tipo_uso', 'modo', 'finalidades', 'metodos', 'restricao'),
    [
        (
            'uso_lancamento',
            'captacao_subterranea',
            [],
            [],
            'ck_uso_recurso_hidrico_modo_do_tipo_uso',
        ),
        (
            'uso_captacao',
            'intervencao',
            [],
            [],
            'ck_uso_recurso_hidrico_modo_do_tipo_uso',
        ),
        (
            'uso_captacao',
            'captacao_superficial',
            ['irrigacao', 'piscicultura'],
            [],
            'ck_uso_recurso_hidrico_finalidades',
        ),
        (
            'uso_captacao',
            'captacao_superficial',
            ['irrigacao'],
            ['inundacao'],
            'ck_uso_recurso_hidrico_metodos_irrigacao',
        ),
    ],
)
def test_uso_incoerente_e_recusado(
    banco, criar_publicacao, tipo_uso, modo, finalidades, metodos, restricao
):
    _, [ato_id] = criar_publicacao([CAPTACAO_SUBTERRANEA_1156])
    gravar(ato_id, CAPTACAO_SUBTERRANEA_1156)
    with Session(banco) as sessao:
        outorga_id = sessao.scalars(select(entidades.Outorga.id)).one()
        with pytest.raises(IntegrityError, match=restricao):
            sessao.execute(
                text(USO),
                {
                    'outorga_id': outorga_id,
                    'tipo_uso': tipo_uso,
                    'modo': modo,
                    'finalidades': finalidades,
                    'metodos': metodos,
                },
            )


# Views: uma por tipo de uso, uma linha por ponto, com a portaria e o DOE.

VIEWS = (
    'vw_outorga_captacao',
    'vw_outorga_lancamento',
    'vw_outorga_intervencao',
)


def linhas(banco, view: str) -> list[dict]:
    with banco.connect() as conexao:
        return [
            dict(linha)
            for linha in conexao.execute(
                text(
                    'SELECT *, ST_SRID(ponto) AS srid '
                    f'FROM recurso_hidrico.{view} ORDER BY uso_recurso_hidrico_id'
                )
            ).mappings()
        ]


def test_captacao_aparece_na_view_com_a_portaria_e_a_edicao(banco, criar_publicacao):
    _, [ato_id] = criar_publicacao([CAPTACAO_SUBTERRANEA_1156])
    gravar(ato_id, CAPTACAO_SUBTERRANEA_1156)

    [linha] = linhas(banco, 'vw_outorga_captacao')
    assert linha['ato_id'] == ato_id
    assert linha['sigla_tipo_ato'] == 'OUT'
    assert linha['nro_portaria'] == '20771'
    assert linha['outorgado_nro_documento'] == '24671320568'
    assert linha['municipio_outorgado'] == 'Barro Alto'
    assert linha['modo'] == 'captacao_subterranea'
    assert linha['finalidades'] == 'irrigacao'
    assert linha['municipios'] == 'Barro Alto'
    assert linha['metodos_irrigacao'] == 'gotejamento'
    assert linha['srid'] == 4674
    assert linha['tipo_publicacao'] == 'Portarias'
    assert linha['dt_edicao'] is not None
    # Portaria de 08/06/2020 com prazo de 4 anos.
    assert linha['dt_vencimento'] == date(2024, 6, 8)


def test_cada_uso_so_na_sua_view_e_a_uniao_da_todos_os_pontos(banco, criar_publicacao):
    _, atos = criar_publicacao(
        [CAPTACAO_SUBTERRANEA_1156, LANCAMENTO_24493, INTERVENCAO_27768]
    )
    for ato_id, texto in zip(
        atos, (CAPTACAO_SUBTERRANEA_1156, LANCAMENTO_24493, INTERVENCAO_27768)
    ):
        gravar(ato_id, texto)

    modos = {view: {linha['modo'] for linha in linhas(banco, view)} for view in VIEWS}
    assert modos == {
        'vw_outorga_captacao': {'captacao_subterranea'},
        'vw_outorga_lancamento': {'lancamento_efluente'},
        'vw_outorga_intervencao': {'intervencao'},
    }
    with Session(banco) as sessao:
        pontos = contar(sessao, entidades.PontoUso)
    assert sum(len(linhas(banco, view)) for view in VIEWS) == pontos


def test_colunas_do_lancamento_e_da_intervencao(banco, criar_publicacao):
    _, [lancamento, intervencao] = criar_publicacao(
        [LANCAMENTO_24493, INTERVENCAO_27768]
    )
    gravar(lancamento, LANCAMENTO_24493)
    gravar(intervencao, INTERVENCAO_27768)

    [linha] = linhas(banco, 'vw_outorga_lancamento')
    assert linha['parametros_efluente'] == (
        'DBO: 13,94 mg/L; Coliformes Termotolerantes: 1x10³ UFC/100mL'
    )
    assert linha['vazao_diluicao_m3_dia'] is not None
    tipos = [
        linha['tipo_intervencao'] for linha in linhas(banco, 'vw_outorga_intervencao')
    ]
    assert tipos == ['regularizacao_barramento', 'aproveitamento_hidreletrico']


def test_uso_sem_ponto_e_outorga_sem_outorgado_continuam_na_view(
    banco, criar_publicacao
):
    _, [ato_id] = criar_publicacao([CAPTACAO_SUBTERRANEA_1156])
    gravar(ato_id, CAPTACAO_SUBTERRANEA_1156)
    with banco.begin() as conexao:
        conexao.execute(text('DELETE FROM recurso_hidrico.ponto_uso'))
        conexao.execute(
            text('UPDATE recurso_hidrico.outorga SET outorgado_pessoa_id = NULL')
        )

    [linha] = linhas(banco, 'vw_outorga_captacao')
    assert linha['ponto_id'] is None and linha['ponto'] is None
    assert linha['outorgado_nro_documento'] is None
    assert linha['nro_portaria'] == '20771'


def test_vencimento_pela_data_valida_ate_do_texto(banco, criar_publicacao):
    _, [ato_id] = criar_publicacao([VALIDA_ATE_22968])
    gravar(ato_id, VALIDA_ATE_22968)

    [linha] = linhas(banco, 'vw_outorga_captacao')
    assert linha['prazo_validade_anos'] is None
    assert linha['dt_vencimento'] == date(2038, 11, 10)
