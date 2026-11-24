"""Conversão das outorgas extraídas nas entidades do esquema recurso_hidrico.

Sem banco: usa os textos reais de ``test_outorga`` e confere as entidades montadas.
"""

from datetime import date
from decimal import Decimal

import pytest
from langchain_core.runnables import RunnableLambda

from diario_oficial.database.entity import recurso_hidrico as entidades
from diario_oficial.extracao.gravacao_comum import CampoSemColuna
from diario_oficial.extracao.gravacao_outorga import (
    para_outorga,
    para_trechos,
)
from diario_oficial.extracao.modelo_comum import Endereco
from diario_oficial.extracao.modelo_outorga import Outorga, PontoUso
from diario_oficial.extracao.outorga import EXTRACOES, extrair_pela_regex
from tests.test_outorga import (
    AMPLIACAO_15749,
    CANALIZACAO_19067,
    CAPTACAO_EM_BARRAMENTO_22580,
    CAPTACAO_SUBTERRANEA_1156,
    DISPENSADO_22994,
    DUAS_PORTARIAS_24350,
    INTERVENCAO_27768,
    LANCAMENTO_24493,
    LONGITUDE_ANTES_25445,
    PARAGRAFOS_1551,
    VALIDA_ATE_22968,
    VAZAO_MALFORMADA_15493,
    extrair_com_modelo_falso,
    sem_horas,
)


def unica(texto) -> entidades.Outorga:
    [outorga] = extrair_pela_regex(texto).outorgas
    return para_outorga(outorga)


def test_captacao_vira_entidades_com_tipos_do_banco():
    outorga = unica(CAPTACAO_SUBTERRANEA_1156)
    assert outorga.natureza == 'outorga'
    assert outorga.nro_portaria == '20771'
    assert outorga.dt_portaria == date(2020, 6, 8)
    assert outorga.outorgado.nome == 'LAERTE OLIVEIRA BARBOSA'
    assert outorga.outorgado.tipo_documento == 'CPF'
    # CPF só com dígitos, para a pessoa ser única pelo documento.
    assert outorga.outorgado.nro_documento == '24671320568'
    assert outorga.outorgado_nome == 'LAERTE OLIVEIRA BARBOSA'
    assert outorga.endereco_outorgado.logradouro == 'Rua Pé de Limão'
    assert outorga.endereco_outorgado.municipio == 'Barro Alto'
    [uso] = outorga.usos
    assert isinstance(uso, entidades.UsoCaptacao)
    assert uso.modo == 'captacao_subterranea'
    assert uso.area_ha == Decimal('2.5')
    assert uso.finalidades == ['irrigacao']
    assert uso.municipios == ['Barro Alto']
    [ponto] = uso.pontos
    assert ponto.identificacao == 'poço 1'
    assert ponto.latitude and ponto.longitude
    assert ponto.vazao_m3_dia == Decimal('152.0')
    assert ponto.captacao_horas_dia == Decimal('13.0')
    assert ponto.sistema_referencia_espacial == 'SIRGAS 2000'
    assert ponto.ponto.srid == entidades.SRID
    assert ponto.ponto.data == 'POINT(-41.89375 -11.8793333)'


def test_cada_modo_vira_a_sua_entidade():
    usos = unica(PARAGRAFOS_1551).usos
    assert [type(uso) for uso in usos] == [entidades.UsoCaptacao] * 3
    regularizacao, hidreletrica = unica(INTERVENCAO_27768).usos
    assert isinstance(regularizacao, entidades.UsoIntervencao)
    assert regularizacao.tipo_intervencao == 'regularizacao_barramento'
    assert regularizacao.descarga_de_fundo is True
    assert regularizacao.vazao_minima_jusante_m3_s == Decimal('0.69')
    assert hidreletrica.tipo_intervencao == 'aproveitamento_hidreletrico'


def test_lancamento_com_parametros():
    [uso] = unica(LANCAMENTO_24493).usos
    assert isinstance(uso, entidades.UsoLancamento)
    assert uso.vazao_diluicao_m3_dia == Decimal('2076.76')
    dbo, coliformes = uso.parametros
    assert (dbo.nome, dbo.valor_numero, dbo.unidade) == (
        'DBO',
        Decimal('13.94'),
        'mg/L',
    )
    assert coliformes.valor_numero == Decimal('1000.0')


def test_ponto_em_outro_datum_e_convertido_para_sirgas():
    [outorga] = extrair_pela_regex(CAPTACAO_SUBTERRANEA_1156).outorgas
    ponto = outorga.usos[0].pontos[0]
    ponto.sistema_referencia_espacial = 'SAD 69'
    convertido = para_outorga(outorga).usos[0].pontos[0]
    assert convertido.sistema_referencia_espacial == 'SAD 69'
    assert convertido.ponto.data != ponto.ponto


def test_outorga_sem_outorgado_fica_sem_pessoa():
    [outorga] = extrair_pela_regex(CAPTACAO_SUBTERRANEA_1156).outorgas
    outorga.outorgado = None
    entidade = para_outorga(outorga)
    assert entidade.outorgado is None
    assert entidade.outorgado_nome is None
    assert entidade.endereco_outorgado is None


def test_trecho_guarda_o_que_o_modelo_preencheu_e_o_erro_dele():
    def fora_do_ar(_):
        raise ConnectionError('Ollama fora do ar')

    trechos = extrair_com_modelo_falso(
        sem_horas(CAPTACAO_SUBTERRANEA_1156), RunnableLambda(fora_do_ar)
    )
    [trecho] = para_trechos(1156, 'OUT', trechos, 'qwen')
    assert trecho.ato_id == 1156
    assert trecho.sigla_tipo_ato == 'OUT'
    assert trecho.modelo_llm == 'qwen'
    assert trecho.erro is None
    assert 'Ollama fora do ar' in trecho.erro_modelo
    assert trecho.preenchido_pelo_modelo == []
    [outorga] = trecho.outorgas
    assert outorga.usos[0].pontos[0].captacao_horas_dia is None


@pytest.mark.parametrize('sigla', sorted(EXTRACOES))
def test_toda_outorga_grava_em_recurso_hidrico(sigla):
    assert EXTRACOES[sigla].entidade is entidades.Outorga


def registro(texto) -> Outorga:
    [outorga] = extrair_pela_regex(texto).outorgas
    return outorga


# Casos de conversão


def test_par_fora_da_bahia_fica_como_no_texto_e_sem_geometria():
    texto = CAPTACAO_SUBTERRANEA_1156.replace('Lat.11°52’45,6"S', 'Lat.44°52’45,6"S')
    [ponto] = unica(texto).usos[0].pontos
    assert ponto.latitude.startswith('44°52’45,6')
    assert ponto.longitude.startswith('41°53’37,5')
    assert ponto.ponto is None


def test_ponto_sem_coordenada_fica_sem_latitude_longitude_e_geometria():
    outorga = registro(CAPTACAO_SUBTERRANEA_1156)
    outorga.usos[0].pontos[0].coordenada = None
    [ponto] = para_outorga(outorga).usos[0].pontos
    assert (ponto.latitude, ponto.longitude, ponto.ponto) == (None, None, None)
    assert ponto.vazao_m3_dia == Decimal('152.0')


def test_trecho_com_erro_e_trecho_com_duas_outorgas():
    trechos = [
        {'trecho': 'trecho 1', 'registros': [], 'modelos': [], 'erro': 'falhou'},
        {
            'trecho': 'trecho 2',
            'registros': [],
            'modelos': extrair_pela_regex(DUAS_PORTARIAS_24350).outorgas,
        },
    ]
    gravados = para_trechos(24350, 'OUT', trechos, 'qwen')
    assert [(t.trecho, t.erro, len(t.outorgas)) for t in gravados] == [
        ('trecho 1', 'falhou', 0),
        ('trecho 2', None, 2),
    ]
    assert all(t.ato_id == 24350 and t.sigla_tipo_ato == 'OUT' for t in gravados)
    assert all(t.preenchido_pelo_modelo == [] for t in gravados)
    assert [o.nro_portaria for o in gravados[1].outorgas] == ['18324', '18325']
    assert gravados[1].outorgas[1].outorgado.nome == 'ROMEU FRANCIOSI'


def test_trecho_guarda_os_campos_que_o_modelo_preencheu():
    trechos = extrair_com_modelo_falso(
        sem_horas(CAPTACAO_SUBTERRANEA_1156),
        RunnableLambda(lambda _: extrair_pela_regex(CAPTACAO_SUBTERRANEA_1156)),
    )
    [trecho] = para_trechos(1156, 'OUT', trechos)
    assert trecho.preenchido_pelo_modelo == [
        'outorgas.0.usos.0.pontos.0.captacao_horas_dia'
    ]
    assert trecho.erro_modelo is None
    assert trecho.modelo_llm is None
    [ponto] = trecho.outorgas[0].usos[0].pontos
    assert ponto.captacao_horas_dia == Decimal('13.0')


# Colunas


def test_processos_e_prazo_de_outra_portaria():
    outorga = unica(AMPLIACAO_15749)
    assert outorga.natureza == 'ampliacao'
    assert outorga.nro_processo == '2014-005032/OUT/AMPL-0012'
    assert outorga.nro_processo_relacionado == '2011-001001/OUT/AUT-0384'
    [uso] = outorga.usos
    assert uso.nro_portaria_prazo == '2201'
    # Data em texto ISO no Pydantic, date no banco.
    assert uso.dt_publicacao_portaria_prazo == date(2012, 3, 6)
    assert uso.prazo_validade_anos is None
    assert uso.pontos[0].corpo_hidrico == 'rio Grande'


def test_prazo_ate_uma_data_vira_date():
    [uso] = unica(VALIDA_ATE_22968).usos
    assert uso.dt_validade == date(2038, 11, 10)
    assert uso.prazo_validade_anos is None


def test_colunas_comuns_do_uso():
    outorga = unica(CAPTACAO_SUBTERRANEA_1156)
    assert outorga.nro_processo == '2019.001.007825/INEMA/LIC-07825'
    assert outorga.nro_processo_relacionado is None
    [uso] = outorga.usos
    assert uso.prazo_validade_anos == 4
    assert uso.bacia_hidrografica == 'Rio São Francisco'
    assert uso.finalidade_texto
    assert uso.metodos_irrigacao == ['gotejamento']
    assert uso.localidade.startswith('Fazenda Baixa Funda II')
    # A unidade que o texto não trouxe é calculada com 6 casas.
    assert uso.pontos[0].vazao_m3_s == Decimal('0.001759')


@pytest.mark.parametrize(
    'texto, tipos',
    [
        (CAPTACAO_SUBTERRANEA_1156, ['uso_captacao']),
        (LANCAMENTO_24493, ['uso_lancamento']),
        (INTERVENCAO_27768, ['uso_intervencao', 'uso_intervencao']),
    ],
)
def test_tipo_uso_de_cada_especializacao(texto, tipos):
    assert [uso.tipo_uso for uso in unica(texto).usos] == tipos


def test_colunas_da_intervencao():
    regularizacao, _ = unica(INTERVENCAO_27768).usos
    assert regularizacao.volume_maximo_acumulacao_m3 == Decimal('1135126.8')
    assert regularizacao.altura_maxima_m == Decimal('10.0')
    assert regularizacao.vazao_minima_jusante_m3_dia == Decimal('59726.0')
    [canalizacao] = unica(CANALIZACAO_19067).usos
    assert canalizacao.tipo_intervencao == 'canalizacao'
    assert canalizacao.extensao_m == Decimal('2.86')
    assert canalizacao.vazao_projeto_m3_dia == Decimal('587520.0')
    assert float(canalizacao.vazao_projeto_m3_s) == pytest.approx(6.8)
    assert canalizacao.localidade == 'Rua Dantas Bião, Alagoinhas Velha'
    [longitude_antes] = unica(LONGITUDE_ANTES_25445).usos
    assert longitude_antes.comprimento_m == Decimal('640.0')
    assert longitude_antes.pontos[1].vazao_m3_s == Decimal('129.5')


def test_largura_vai_para_a_coluna():
    outorga = registro(CANALIZACAO_19067)
    outorga.usos[0].largura_m = 3.5
    assert para_outorga(outorga).usos[0].largura_m == Decimal('3.5')


def test_colunas_do_lancamento():
    [uso] = unica(LANCAMENTO_24493).usos
    assert uso.vazao_diluicao_m3_s == Decimal('0.024037')
    dbo, _ = uso.parametros
    assert dbo.valor and '13,94' in dbo.valor


def test_ponto_em_barramento_e_barramento_dispensado():
    [ponto] = unica(CAPTACAO_EM_BARRAMENTO_22580).usos[0].pontos
    assert (ponto.barramento, ponto.barramento_dispensado, ponto.corpo_hidrico) == (
        'barramento existente',
        False,
        'Córrego Jequitibá',
    )
    [dispensado] = unica(DISPENSADO_22994).usos[0].pontos
    assert dispensado.barramento_dispensado is True
    assert dispensado.corpo_hidrico == 'rio Piaçava'


def test_endereco_da_sede_com_rodovia():
    sede = unica(VAZAO_MALFORMADA_15493).endereco_outorgado
    assert (sede.localidade, sede.rodovia, sede.municipio) == (
        'Fazenda Renascer',
        'Rod. BR 349',
        'Correntina',
    )


def test_todos_os_campos_do_endereco_vao_para_a_tabela():
    outorga = registro(CAPTACAO_SUBTERRANEA_1156)
    outorga.outorgado.endereco = Endereco(
        localidade='Loteamento Bela Vista',
        logradouro='Rua A',
        numero='12',
        complemento='galpão 2',
        bairro='Centro',
        rodovia='BA 459, km 65',
        cep='44000-000',
        municipio='Feira de Santana',
    )
    sede = para_outorga(outorga).endereco_outorgado
    assert isinstance(sede, entidades.Endereco)
    assert (
        sede.localidade,
        sede.logradouro,
        sede.numero,
        sede.complemento,
        sede.bairro,
        sede.rodovia,
        sede.cep,
        sede.municipio,
    ) == (
        'Loteamento Bela Vista',
        'Rua A',
        '12',
        'galpão 2',
        'Centro',
        'BA 459, km 65',
        '44000-000',
        'Feira de Santana',
    )


# Equivalentes dos testes dos autos


def test_endereco_vazio_nao_vira_linha():
    outorga = registro(CAPTACAO_SUBTERRANEA_1156)
    outorga.outorgado.endereco = Endereco(
        **{campo: None for campo in Endereco.model_fields}
    )
    entidade = para_outorga(outorga)
    assert entidade.endereco_outorgado is None
    assert entidade.outorgado.nome == 'LAERTE OLIVEIRA BARBOSA'


def test_campo_sem_coluna_na_outorga_e_erro():
    class OutorgaComCampoNovo(Outorga):
        campo_novo: str | None = None

    outorga = OutorgaComCampoNovo(**registro(CAPTACAO_SUBTERRANEA_1156).model_dump())
    with pytest.raises(CampoSemColuna, match='campo_novo'):
        para_outorga(outorga)


def test_campo_sem_coluna_no_ponto_e_erro():
    class PontoComCampoNovo(PontoUso):
        campo_novo: str | None = None

    outorga = registro(CAPTACAO_SUBTERRANEA_1156)
    [ponto] = outorga.usos[0].pontos
    outorga.usos[0].pontos = [PontoComCampoNovo(**ponto.model_dump())]
    with pytest.raises(CampoSemColuna, match='campo_novo'):
        para_outorga(outorga)
