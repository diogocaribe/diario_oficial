"""Consulta da edição do dia. A resposta do site é simulada: nenhum teste usa a rede."""

from datetime import date

import pytest
import requests

from diario_oficial import edicao
from diario_oficial.edicao import buscar_edicao


class Resposta:
    def __init__(self, dados, status=200):
        self.dados = dados
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f'{self.status_code}')

    def json(self):
        return self.dados


@pytest.fixture
def site(monkeypatch):
    """Simula o site: guarda os endereços consultados e devolve a resposta definida."""
    chamadas = []

    def responder(resposta):
        def get(url, **kwargs):
            chamadas.append(url)
            return resposta

        monkeypatch.setattr(edicao.requests, 'get', get)
        return chamadas

    return responder


def item(id_edicao, numero, suplemento=0):
    return {'id': id_edicao, 'numero': numero, 'suplemento': suplemento}


def test_edicao_existente(site):
    chamadas = site(Resposta({'erro': False, 'msg': '', 'itens': [item('16970', '23784')]}))

    resultado = buscar_edicao(date(2023, 11, 8))

    assert resultado.nro_edicao == 23784
    assert resultado.url == (
        'https://dool.egba.ba.gov.br/portal/visualizacoes/html/16970#/p:1/e:16970'
    )
    # A data vai no formato da consulta do site, e não no da CLI
    assert chamadas == [
        'https://dool.egba.ba.gov.br/apifront/portal/edicoes/edicoes_from_data/2023-11-08'
    ]


def test_data_sem_edicao(site):
    site(Resposta({'erro': True, 'msg': 'Edição não existente!', 'itens': []}))

    assert buscar_edicao(date(2023, 11, 5)) is None


def test_mais_de_uma_edicao_no_dia_usa_a_primeira(site):
    """Caso real de 15-07-2020: o suplemento vem antes da edição normal."""
    itens = [item('10350', '22943', suplemento=1), item('10342', '22943')]
    site(Resposta({'erro': False, 'msg': '', 'itens': itens}))

    assert buscar_edicao(date(2020, 7, 15)).url.endswith('/html/10350#/p:1/e:10350')


def test_erro_desconhecido_nao_vira_data_sem_edicao(site):
    site(Resposta({'erro': True, 'msg': 'Serviço indisponível', 'itens': []}))

    with pytest.raises(RuntimeError, match='Serviço indisponível'):
        buscar_edicao(date(2023, 11, 8))


def test_falha_http_nao_vira_data_sem_edicao(site):
    site(Resposta({}, status=503))

    with pytest.raises(requests.HTTPError):
        buscar_edicao(date(2023, 11, 8))
