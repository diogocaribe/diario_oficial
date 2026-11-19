from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy import inspect

from diario_oficial.database.entity import auto_infracao as entidades
from diario_oficial.extracao.gravacao import (
    CAMPOS_ANINHADOS,
    CampoSemColuna,
    para_auto,
    para_trechos,
)
from diario_oficial.extracao.modelo_auto_infracao import AutoInterdicao
from diario_oficial.extracao.modelo_comum import (
    CoordenadaGeografica,
    Endereco,
    Pessoa,
)
from diario_oficial.extracao.normalizacao import normalizar_documento
from diario_oficial.extracao.utils_geo import wkt_em_sirgas


def _endereco(**campos) -> Endereco:
    return Endereco(**{**dict.fromkeys(Endereco.model_fields), **campos})


def _auto(**campos) -> AutoInterdicao:
    padrao = dict(
        nro_processo='2017-009301/TEC/AIIN-0222',
        natureza='homologacao',
        resultado_recurso=None,
        nro_ato_decisorio='4.817',
        autuado=Pessoa(
            nome='ASSOCIAÇÃO DO ABATEDOURO',
            tipo_documento='CNPJ',
            nro_documento='04.710.537/0001-04',
            endereco=_endereco(logradouro='Rua A', municipio='Paulo Afonso'),
        ),
        dt_homologacao='01/04/2019',
        modalidade='temporaria',
        conduta='funcionamento de matadouro sem licença',
        atividade_interditada='matadouro',
        local_infracao=_endereco(localidade='Fazenda Boa Vista'),
        dt_constatacao='2017-08-02',
        hr_constatacao='14h30',
        coordenada=[],
        sistema_referencia_espacial=None,
        area_hectare=2.5,
        excecao_interdicao=None,
        condicao='obtenção da licença',
        gravidade='grave',
        nro_lacre=['0029770'],
        especie_citada=['aroeira'],
    )
    return AutoInterdicao(**{**padrao, **campos})


def test_todo_campo_do_esquema_tem_coluna_na_entidade():
    colunas = inspect(entidades.AutoInterdicao).columns
    campos = set(AutoInterdicao.model_fields) - CAMPOS_ANINHADOS
    assert campos - set(colunas.keys()) == set()
    coluna_coordenada = inspect(entidades.CoordenadaExtraidaTrecho).columns
    assert set(CoordenadaGeografica.model_fields) <= set(coluna_coordenada.keys())
    assert set(Endereco.model_fields) <= set(inspect(entidades.Endereco).columns.keys())


def test_auto_vira_entidade_com_tipos_do_banco():
    auto = para_auto(_auto(), entidades.AutoInterdicao)

    assert isinstance(auto, entidades.AutoInterdicao)
    assert auto.dt_homologacao == date(2019, 4, 1)
    assert auto.hr_constatacao == time(14, 30)
    assert auto.area_hectare == Decimal('2.5')
    assert auto.nro_lacre == ['0029770']
    assert auto.especie_citada == ['aroeira']
    assert auto.modalidade == 'temporaria'
    assert auto.condicao == 'obtenção da licença'
    assert auto.ponto is None and auto.poligono is None


def test_endereco_do_autuado_fica_no_auto_e_nao_na_pessoa():
    auto = para_auto(_auto(), entidades.AutoInterdicao)

    assert auto.autuado.nome == auto.autuado_nome == 'ASSOCIAÇÃO DO ABATEDOURO'
    assert auto.autuado.nro_documento == '04710537000104'
    assert auto.endereco_autuado.logradouro == 'Rua A'
    assert auto.endereco_autuado.municipio == 'Paulo Afonso'
    assert auto.local_infracao.localidade == 'Fazenda Boa Vista'


def test_endereco_vazio_nao_vira_linha():
    auto = para_auto(_auto(local_infracao=_endereco()), entidades.AutoInterdicao)
    assert auto.local_infracao is None


def test_coordenadas_como_no_texto_e_ponto_em_sirgas():
    par = CoordenadaGeografica(
        latitude='S -12,20388º',
        longitude='W - 41,75649º',
        fuso_utm=None,
        tipo='ponto',
    )
    auto = para_auto(_auto(coordenada=[par]), entidades.AutoInterdicao)

    assert [(c.latitude, c.tipo) for c in auto.coordenada] == [
        ('S -12,20388º', 'ponto')
    ]
    assert auto.ponto.srid == entidades.SRID
    assert auto.ponto.data == 'POINT(-41.75649 -12.20388)'


def test_wkt_em_outro_datum_e_convertido_para_sirgas():
    assert wkt_em_sirgas('POINT(-41.7 -12.2)', None) == 'POINT(-41.7 -12.2)'
    convertido = wkt_em_sirgas('POINT(-41.7 -12.2)', 'SAD 69')
    longitude, latitude = map(float, convertido[6:-1].split())
    assert convertido != 'POINT(-41.7 -12.2)'
    assert abs(longitude + 41.7) < 0.001 and abs(latitude + 12.2) < 0.001


def test_campo_sem_coluna_e_erro():
    class AutoComCampoNovo(AutoInterdicao):
        campo_novo: str | None = None

    registro = AutoComCampoNovo(**_auto().model_dump(exclude={'ponto', 'poligono'}))
    with pytest.raises(CampoSemColuna, match='campo_novo'):
        para_auto(registro, entidades.AutoInterdicao)


def test_trechos_com_erro_e_com_varios_autos():
    trechos = [
        {'trecho': 'trecho 1', 'registros': [], 'modelos': [], 'erro': 'falhou'},
        {'trecho': 'trecho 2', 'registros': [], 'modelos': [_auto(), _auto()]},
    ]
    gravados = para_trechos(5604, 'AIIN', entidades.AutoInterdicao, trechos, 'qwen')

    assert [(t.trecho, t.erro, len(t.autos)) for t in gravados] == [
        ('trecho 1', 'falhou', 0),
        ('trecho 2', None, 2),
    ]
    assert all(t.ato_id == 5604 and t.sigla_tipo_ato == 'AIIN' for t in gravados)


def test_normalizar_documento():
    assert normalizar_documento('CPF', '012.219.575-20') == '01221957520'
    assert normalizar_documento('RG', ' 12.345 SSP ') == '12.345 SSP'
    assert normalizar_documento('CNPJ', 'não informado') is None
    assert normalizar_documento(None, None) is None


def test_trecho_grava_conferencia_e_campos_preenchidos_pela_regex():
    conferencia = {
        'faltantes': [],
        'divergencias': {'modalidade': ['definitiva', 'temporaria']},
    }
    trechos = [
        {
            'trecho': 'trecho 1',
            'registros': [],
            'modelos': [_auto()],
            'preenchido_pela_regex': ['modalidade'],
            'conferencia': conferencia,
        },
        {'trecho': 'trecho 2', 'registros': [], 'modelos': [], 'erro': 'falhou'},
    ]
    gravados = para_trechos(5604, 'AIIN', entidades.AutoInterdicao, trechos)

    assert gravados[0].conferencia == conferencia
    assert gravados[0].preenchido_pela_regex == ['modalidade']
    assert gravados[1].conferencia is None
    assert gravados[1].preenchido_pela_regex == []
