"""Esquema auto_infracao: gravação pelo repositório, reprocessamento, triggers e views."""

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from diario_oficial.database.entity import auto_infracao as entidades
from diario_oficial.database.entity.ato import Ato
from diario_oficial.database.entity.pessoa import Pessoa
from diario_oficial.database.repository.auto_infracao_repository import (
    AutoInfracaoRepository,
)
from diario_oficial.extracao.gravacao_auto_infracao import para_trechos
from diario_oficial.extracao.modelo_comum import CoordenadaGeografica
from tests.test_gravacao_auto_infracao import _auto

pytestmark = pytest.mark.integracao

PAR = CoordenadaGeografica(
    latitude='S -12,20388º', longitude='W - 41,75649º', fuso_utm=None, tipo='ponto'
)


def gravar(ato_id: int, *autos, sigla: str = 'AIIN') -> None:
    trechos = [{'trecho': f'trecho do ato {ato_id}', 'modelos': list(autos)}]
    AutoInfracaoRepository().gravar_extracao(
        ato_id,
        sigla,
        para_trechos(ato_id, sigla, entidades.AutoInterdicao, trechos, 'qwen'),
    )


def contar(sessao: Session, entidade) -> int:
    return sessao.scalar(select(func.count()).select_from(entidade))


def test_auto_gravado_aparece_nas_views_com_o_ato_e_a_edicao(banco, criar_publicacao):
    _, [ato_id] = criar_publicacao(['AUTO DE INTERDIÇÃO'])
    gravar(ato_id, _auto(coordenada=[PAR]))

    with banco.connect() as conexao:
        [linha] = conexao.execute(
            text(
                'SELECT *, ST_SRID(ponto) AS srid, ST_AsText(ponto) AS wkt '
                'FROM auto_infracao.vw_auto_interdicao'
            )
        ).mappings()
    assert linha['sigla_tipo_ato'] == 'AIIN'
    assert linha['autuado_nome'] == 'ASSOCIAÇÃO DO ABATEDOURO'
    # CNPJ só com dígitos, para a pessoa ser única pelo documento.
    assert linha['autuado_nro_documento'] == '04710537000104'
    assert linha['endereco_autuado'] == 'Rua A, Paulo Afonso'
    assert linha['local_infracao'] == 'Fazenda Boa Vista'
    assert linha['modalidade'] == 'temporaria'
    assert linha['tipo_publicacao'] == 'Portarias'
    assert linha['dt_edicao'] is not None
    assert (linha['srid'], linha['wkt']) == (4674, 'POINT(-41.75649 -12.20388)')


def test_regravar_o_ato_troca_a_extracao_e_apaga_os_enderecos_antigos(
    banco, criar_publicacao
):
    _, [ato_id] = criar_publicacao(['AUTO DE INTERDIÇÃO'])
    gravar(ato_id, _auto(coordenada=[PAR]))
    gravar(ato_id, _auto(modalidade='definitiva'))

    with Session(banco) as sessao:
        assert contar(sessao, entidades.ExtracaoTrecho) == 1
        [auto] = sessao.scalars(select(entidades.AutoInterdicao)).all()
        assert auto.modalidade == 'definitiva'
        assert contar(sessao, entidades.CoordenadaExtraidaTrecho) == 0
        # O endereço do autuado e o local da infração do auto novo; os do auto
        # apagado saíram pelo trigger.
        assert contar(sessao, entidades.Endereco) == 2
        assert contar(sessao, Pessoa) == 1


def test_mesmo_documento_em_atos_diferentes_e_a_mesma_pessoa(banco, criar_publicacao):
    _, [primeiro, segundo] = criar_publicacao(['AUTO 1', 'AUTO 2'])
    gravar(primeiro, _auto())
    gravar(segundo, _auto(), _auto())

    with Session(banco) as sessao:
        assert contar(sessao, Pessoa) == 1
        assert contar(sessao, entidades.AutoInfracao) == 3
        # Uma grafia por auto, a pessoa uma só.
        assert (
            len(set(sessao.scalars(select(entidades.AutoInfracao.endereco_autuado_id))))
            == 3
        )


def test_sem_documento_cada_auto_tem_a_sua_pessoa(banco, criar_publicacao):
    _, [ato_id] = criar_publicacao(['AUTO'])
    sem_documento = _auto()
    sem_documento.autuado.tipo_documento = None
    sem_documento.autuado.nro_documento = None
    gravar(ato_id, sem_documento, sem_documento.model_copy(deep=True))

    with Session(banco) as sessao:
        assert contar(sessao, Pessoa) == 2


def test_extracao_de_outra_sigla_do_mesmo_ato_fica(banco, criar_publicacao):
    _, [ato_id] = criar_publicacao(['AUTO'])
    gravar(ato_id, _auto(), sigla='AIIN')
    gravar(ato_id, _auto(), sigla='AIEM')
    gravar(ato_id, _auto(), sigla='AIIN')

    with Session(banco) as sessao:
        siglas = sessao.scalars(select(entidades.ExtracaoTrecho.sigla_tipo_ato))
        assert sorted(siglas) == ['AIEM', 'AIIN']
    repositorio = AutoInfracaoRepository()
    assert repositorio.get_atos_extraidos('AIIN', [ato_id, ato_id + 1]) == {ato_id}
    assert repositorio.get_atos_extraidos('AIMU', [ato_id]) == set()


def test_apagar_o_ato_apaga_autos_e_enderecos_e_mantem_a_pessoa(
    banco, criar_publicacao
):
    _, [ato_id] = criar_publicacao(['AUTO'])
    gravar(ato_id, _auto(coordenada=[PAR]))
    with Session(banco) as sessao:
        sessao.execute(delete(Ato).where(Ato.id == ato_id))
        sessao.commit()
        for entidade in (
            entidades.ExtracaoTrecho,
            entidades.AutoInfracao,
            entidades.AutoInterdicao,
            entidades.CoordenadaExtraidaTrecho,
            entidades.Endereco,
        ):
            assert contar(sessao, entidade) == 0, entidade.__tablename__
        assert contar(sessao, Pessoa) == 1


def test_pessoa_com_auto_nao_pode_ser_apagada(banco, criar_publicacao):
    _, [ato_id] = criar_publicacao(['AUTO'])
    gravar(ato_id, _auto())
    with Session(banco) as sessao:
        with pytest.raises(IntegrityError, match='autuado_pessoa_id'):
            sessao.execute(delete(Pessoa))
            sessao.commit()


def test_falha_na_gravacao_mantem_a_extracao_anterior(banco, criar_publicacao):
    _, [ato_id] = criar_publicacao(['AUTO'])
    gravar(ato_id, _auto())
    # model_copy não valida: o valor fora da lista só é barrado pelo banco.
    invalido = _auto().model_copy(update={'modalidade': 'invalida'})
    with pytest.raises(IntegrityError, match='ck_auto_interdicao_modalidade'):
        gravar(ato_id, invalido)

    with Session(banco) as sessao:
        [auto] = sessao.scalars(select(entidades.AutoInterdicao)).all()
        assert auto.modalidade == 'temporaria'
