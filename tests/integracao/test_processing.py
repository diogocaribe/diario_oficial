"""Esquema processing: trigger dos atos, FKs do log_erro e explosão do doe_json."""

from datetime import date

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from diario_oficial.database.entity.ato import Ato
from diario_oficial.database.entity.ato_tipo_ato import AtoTipoAto
from diario_oficial.database.entity.doe_bruto import DiarioOficialBruto
from diario_oficial.database.entity.dominio import TipoAto
from diario_oficial.database.entity.log_erro import LogErro
from diario_oficial.database.entity.publicacao import Publicacao
from diario_oficial.database.repository.doe_bruto_repository import (
    DiarioOficialBrutoRepository,
)
from diario_oficial.database.repository.publicacao_repository import (
    PublicacaoRepository,
)
from tests.integracao.conftest import INEMA, SEMA

pytestmark = pytest.mark.integracao


def atos_da_publicacao(sessao: Session, publicacao_id: int) -> list[int]:
    return list(
        sessao.scalars(select(Ato.id).where(Ato.publicacao_id == publicacao_id))
    )


# Trigger after_delete_delete_atos_da_mesma_pubalicacao


def test_apagar_um_ato_apaga_os_da_mesma_publicacao_e_libera_o_reprocessamento(
    banco, criar_publicacao
):
    publicacao_id, [primeiro, *_] = criar_publicacao(['ato 1', 'ato 2', 'ato 3'])
    outra_id, outros_atos = criar_publicacao(['ato da outra publicação'])
    with Session(banco) as sessao:
        sessao.execute(delete(Ato).where(Ato.id == primeiro))
        sessao.commit()

        assert atos_da_publicacao(sessao, publicacao_id) == []
        assert sessao.get(Publicacao, publicacao_id).processada_para_ato is None
        # A outra publicação não muda.
        assert atos_da_publicacao(sessao, outra_id) == outros_atos
        assert sessao.get(Publicacao, outra_id).processada_para_ato is True


def test_apagar_o_ato_apaga_os_tipos_dele(banco, criar_publicacao):
    _, [ato_id] = criar_publicacao(['PORTARIA Nº 1 - Auto de Interdição'])
    with Session(banco) as sessao:
        tipo_id = sessao.scalars(
            select(TipoAto.id).where(TipoAto.sigla == 'AIIN')
        ).first()
        sessao.add(AtoTipoAto(ato_id=ato_id, tipo_ato_id=tipo_id))
        sessao.commit()
        sessao.execute(delete(Ato).where(Ato.id == ato_id))
        sessao.commit()
        assert sessao.scalars(select(AtoTipoAto)).all() == []


# FKs do log_erro


def log(sessao: Session, publicacao_id: int, ato_id: int | None) -> LogErro:
    publicacao = sessao.get(Publicacao, publicacao_id)
    registro = LogErro(
        etapa='auditoria',
        tipo='ato_cortado',
        descricao='ato cortado no meio da frase',
        doe_bruto_id=publicacao.doe_bruto_id,
        publicacao_id=publicacao_id,
        ato_id=ato_id,
    )
    sessao.add(registro)
    sessao.commit()
    return registro


def test_log_sobrevive_ao_reprocessamento_sem_o_ato(banco, criar_publicacao):
    publicacao_id, [ato_id] = criar_publicacao(['ato'])
    with Session(banco) as sessao:
        registro = log(sessao, publicacao_id, ato_id)
        sessao.execute(delete(Ato).where(Ato.id == ato_id))
        sessao.commit()
        sessao.refresh(registro)
        assert registro.ato_id is None
        assert registro.publicacao_id == publicacao_id


@pytest.mark.parametrize('entidade', [Publicacao, DiarioOficialBruto])
def test_log_impede_apagar_publicacao_e_edicao(banco, criar_publicacao, entidade):
    publicacao_id, [ato_id] = criar_publicacao(['ato'])
    with Session(banco) as sessao:
        registro = log(sessao, publicacao_id, ato_id)
        alvo = publicacao_id if entidade is Publicacao else registro.doe_bruto_id
        with pytest.raises(IntegrityError, match='log_erro'):
            sessao.execute(delete(entidade).where(entidade.id == alvo))
            sessao.commit()


def test_etapa_do_log_fora_da_lista_e_recusada(banco, criar_publicacao):
    publicacao_id, _ = criar_publicacao(['ato'])
    with Session(banco) as sessao:
        doe_bruto_id = sessao.get(Publicacao, publicacao_id).doe_bruto_id
        sessao.add(
            LogErro(
                etapa='raspagem', tipo='x', descricao='x', doe_bruto_id=doe_bruto_id
            )
        )
        with pytest.raises(IntegrityError, match='ck_log_erro_etapa'):
            sessao.commit()


# Explosão do doe_json em publicações (DiarioOficialBrutoRepository)


def link(identificador: str, nome: str) -> dict:
    return {
        'link': 'https://dool.egba.ba.gov.br/apifront/portal/edicoes/'
        f'publicacoes_ver_conteudo/{identificador}',
        'nome': nome,
        'identificador': identificador,
    }


# Com a forma dos doe_json reais: SEMA com as pastas da Diretoria Geral, do INEMA e as
# Portarias da própria secretaria (4 níveis); INEMA com a Diretoria Geral (5 níveis).
DOE_JSON_4_NIVEIS = {
    'EXECUTIVO': {
        SEMA: {
            'Portarias': [link('694507', '#640243 - PORTARIA')],
            'Diretoria Geral': {
                'Portarias': [link('677290', '#624130 - Integracao_RHBAHIA_Z500329227')]
            },
            INEMA: {
                'Portarias': [
                    link('700001', '#650001 - PORTARIAS'),
                    link('700002', '#650002 - PORTARIAS'),
                ]
            },
        }
    }
}
DOE_JSON_5_NIVEIS = {
    'EXECUTIVO': {
        SEMA: {
            'Diretoria Geral': {},
            INEMA: {
                'Diretoria Geral': {
                    'Portarias': [
                        link('811471', '#749365 - 05 EDITAIS DE NOTIFICAÇÕES')
                    ]
                }
            },
        }
    }
}

PUBLICACOES_COM_NOMES = """
    SELECT p.identificador_link, po.nome, ad.nome, dad.nome, ai.nome, dai.nome, tp.nome
    FROM processing.publicacao p
    LEFT JOIN dominio.poder po ON po.id = p.poder_id
    LEFT JOIN dominio.adm_direta ad ON ad.id = p.adm_direta_id
    LEFT JOIN dominio.divisao_adm_direta dad ON dad.id = p.divisao_adm_direta_id
    LEFT JOIN dominio.adm_indireta ai ON ai.id = p.adm_indireta_id
    LEFT JOIN dominio.divisao_adm_indireta dai ON dai.id = p.divisao_adm_indireta_id
    LEFT JOIN dominio.tipo_publicacao tp ON tp.id = p.tipo_publicacao_id
    ORDER BY p.identificador_link
"""


def explodir_e_gravar(banco, doe_json: dict) -> set[tuple]:
    dia = date(2023, 1, 14)
    with Session(banco) as sessao:
        sessao.add(
            DiarioOficialBruto(
                nro_edicao=23700, dt_edicao=dia, existe=True, doe_json=doe_json
            )
        )
        sessao.commit()
    dados = DiarioOficialBrutoRepository().explodir_doe_bruto_json(dia.isoformat())
    PublicacaoRepository().save_data(dados)
    with banco.connect() as conexao:
        return {tuple(linha) for linha in conexao.execute(text(PUBLICACOES_COM_NOMES))}


def test_explosao_com_4_niveis_preenche_as_fks_pelos_nomes(banco):
    assert explodir_e_gravar(banco, DOE_JSON_4_NIVEIS) == {
        ('694507', 'EXECUTIVO', SEMA, None, None, None, 'Portarias'),
        ('677290', 'EXECUTIVO', SEMA, 'Diretoria Geral', None, None, 'Portarias'),
        ('700001', 'EXECUTIVO', SEMA, None, INEMA, None, 'Portarias'),
        ('700002', 'EXECUTIVO', SEMA, None, INEMA, None, 'Portarias'),
    }


def test_explosao_com_5_niveis_preenche_a_divisao_da_adm_indireta(banco):
    assert explodir_e_gravar(banco, DOE_JSON_5_NIVEIS) == {
        ('811471', 'EXECUTIVO', SEMA, None, INEMA, 'Diretoria Geral', 'Portarias'),
    }


def test_explosao_de_edicao_sem_publicacoes_nao_devolve_nada(banco):
    dia = date(2023, 5, 19)
    sem_publicacao = {'EXECUTIVO': {SEMA: {INEMA: {'Portarias': []}}}}
    with Session(banco) as sessao:
        sessao.add(
            DiarioOficialBruto(dt_edicao=dia, existe=True, doe_json=sem_publicacao)
        )
        sessao.commit()
    repositorio = DiarioOficialBrutoRepository()
    assert repositorio.explodir_doe_bruto_json(dia.isoformat()) == []
