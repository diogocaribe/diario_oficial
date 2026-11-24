"""Extração das outorgas de recursos hídricos pela regex, com textos reais do DOE.

Cada texto é o cabeçalho e o Art. 1º de uma portaria publicada (o id do ato está no
nome da constante); o resto da portaria não muda a extração.
"""

import pytest
from langchain_core.runnables import RunnableLambda

from diario_oficial.extracao.base import (
    extrair,
    preencher_vazios_pelo_modelo,
    regex_com_modelo,
)
from diario_oficial.extracao.modelo_outorga import (
    FINALIDADES,
    METODOS_IRRIGACAO,
    ExtracaoOutorga,
    ParametroEfluente,
    PontoUso,
    vazao_nas_duas_unidades,
)
from diario_oficial.extracao.normalizacao import normalizar_municipio
from diario_oficial.extracao.outorga import (
    EXTRACOES,
    campos_vazios,
    classificar_finalidade,
    classificar_intervencao,
    extrair_pela_regex,
)
from diario_oficial.extracao.registro import EXTRACOES as REGISTRO

PREAMBULO = (
    'O INSTITUTO DO MEIO AMBIENTE E RECURSOS HÍDRICOS - INEMA, com fulcro nas '
    'atribuições e competências que lhe foram delegadas pela Lei Estadual n° 12.212/11 '
    'e Leis Estaduais n° 10.431/06 e 11.612/09, e suas alterações, regulamentadas pelo '
    'Decreto Estadual n° 14.024/12 e, tendo em vista o que consta do Processo nº '
)
FIM = (
    ' mediante o cumprimento da legislação vigente, dos condicionantes e do parágrafo '
    'único deste artigo que constam na íntegra da Portaria, no referido processo. '
    'Art. 2º - Esta portaria não dispensa nem substitui a obtenção, pelo autorizado, '
    'de certidões. Art. 3º - Esta Portaria entrará em vigor na data de sua publicação. '
    'MÁRCIA CRISTINA TELLES DE ARAÚJO LIMA - Diretora Geral'
)

CAPTACAO_SUBTERRANEA_1156 = (
    'PORTARIA\r\nNº 20.771 DE 08 DE JUNHO DE 2020. O\r\n'
    + PREAMBULO
    + '2019.001.007825/INEMA/LIC-07825, RESOLVE: Art. 1.º -\r\nAutorizar o direito de '
    'uso dos recursos hídricos, válido pelo prazo de 04\r\n(quatro) anos, a LAERTE '
    'OLIVEIRA BARBOSA, inscrito no CPF n°\r\n246.713.205-68, com sede na Rua Pé de '
    'Limão, nº 9999, Zona Rural, no município\r\nde Barro Alto, para captação '
    'subterrânea, na Bacia Hidrográfica do Rio São\r\nFrancisco, nas coordenadas '
    'Lat.11°52’45,6"S e Long.41°53’37,5"W,\r\ndatum Sirgas 2000, do poço 1, de vazão '
    '152 m³/dia, durante 13 h/d, para fins de\r\nirrigação por gotejamento, área 2,5 '
    'ha, localizado na Fazenda Baixa Funda II,\r\nComunidade Pé de Limão, Zona Rural, '
    'no município de Barro Alto,' + FIM
)

# Dois parágrafos: no § 1º dois pontos com finalidades e áreas diferentes (dois usos),
# no § 2º um poço.
PARAGRAFOS_1551 = (
    'PORTARIA Nº 21.122 DE 28 DE JULHO DE 2020. '
    + PREAMBULO
    + '2019.001.001234/INEMA/LIC-01234, RESOLVE: Art. 1º - Autorizar a renovação do '
    'direito de uso dos recursos hídricos, válida pelo prazo de 4 (quatro) anos, a '
    'MARIA EDNA DE SOUZA, inscrita no CPF n° 890.043.371-72, com sede na Rua José '
    'Bonifácio, nº 103, Centro, no município de Barreiras, § 1º - captação '
    'superficial, na Bacia Hidrográfica do Rio Grande, no Rio de Ondas, no Ponto P1, '
    'nas coordenadas Lat.12°18\'21,5"S e Long.45°30\'10"W, datum Sirgas 2000, de vazão '
    '81.729 m³/dia, durante 20 h/d, para fins de irrigação por pivô central lepa, '
    'área 1.400 ha; e no Ponto P2, nas coordenadas Lat.12°18\'09"S e '
    'Long.45°31\'12,5"W, datum Sirgas 2000, de vazão 147 m³/dia, durante 01 h/d, para '
    'fins de irrigação por micro aspersão, área 2,5 ha, localizado nas Fazendas Buriti '
    'Paulista e Santa Bárbara, Zona Rural, no município de Barreiras, § 2º - captação '
    'subterrânea, na Bacia Hidrográfica do Rio Grande, nas coordenadas '
    'Lat.12°16\'15,3"S e Long.45°30\'25,2"W, datum Sirgas 2000, do poço 1, de vazão '
    '9.000 m3/dia, durante 18 h/d, para fins de irrigação por pivô central lepa, área '
    '166,5 ha, localizado nas Fazendas Buriti Paulista e Santa Bárbara, Zona Rural, no '
    'município de Barreiras,' + FIM
)

# Cada parágrafo com o seu prazo; o § 2º sem datum e sem h/d no poço 2.
SUZANO_3626 = (
    'PORTARIA Nº 22.631 DE 30 DE MARÇO DE 2021. '
    + PREAMBULO
    + '2018.001.002849/INEMA/LIC-02849, RESOLVE: Art. 1º - Autorizar a renovação do '
    'direito de uso dos recursos hídricos, válida pelo prazo de 04 (quatro) anos, a '
    'SUZANO S.A., inscrito no CNPJ n° 16.404.287/0001-55, com sede na Avenida '
    'Professor Magalhães Neto, nº 1752, Pituba, no município de Salvador, para:§1º - '
    'Captação Superficial, na Bacia Hidrográfica do Rio Peruípe, no Rio Peruípe Norte, '
    'nas coordenadas Lat.17°47’37,9”S e Long.39°36’31,5”W, datum Sirgas 2000, de vazão '
    '1.098m³/dia, durante 18h/d, para fins de irrigação por aspersão, área 6,3 ha e '
    'outros usos, localizado na Unidade de Produção de Mudas Helvécia, Helvécia, no '
    'município de Nova Viçosa. §2º - Captação Subterrânea, na Bacia Hidrográfica do '
    'Extremo Sul, no poço 2, nas coordenadas Lat.17°47’42,2’’S e Long.39°36’52,9’’W, '
    'de vazão 100 m³/dia; e no poço 3, nas coordenadas Lat.17°47’42,2’’S e '
    'Long.39°37’53’’W, datum Sirgas 2000, de vazão 25 m³/dia, durante 10 h/d, para '
    'fins de irrigação por gotejamento, área 1,73 ha, localizado na Unidade de '
    'Produção de Mudas Helvécia, Helvécia, no município de Nova Viçosa,' + FIM
)

# Intervenção com prazo por parágrafo e vazão para jusante nas duas unidades.
INTERVENCAO_27768 = (
    'PORTARIA Nº 30.978 DE 02 DE MAIO DE 2024. '
    + PREAMBULO
    + '2021.001.002313/INEMA/LIC-02313, RESOLVE: Art. 1º - Autorizar o direito de uso '
    'dos recursos hídricos, à NORFIL AGRO LTDA, inscrita no CNPJ nº '
    '06.213.692/0001-32, com sede na Avenida Ermano Marchetti, n° 928, sala 02, Água '
    'Branca, no município de São Paulo - SP, para: § 1º - intervenção, válido pelo '
    'prazo de 35 (trinta e cinco) anos, na Bacia Hidrográfica do Rio Grande, no Rio da '
    'Estiva ou Galheirão, nas coordenadas Lat.12°52\'52,7"S e Long.45°46\'22,9"W, datum '
    'Sirgas 2000, para fins de regularização de barramento existente, com volume '
    'máximo de acumulação de 1.135.126,8 m³ e altura máxima de 10 m. Deverá ser '
    'mantida uma descarga de fundo, no barramento, capaz de permitir uma vazão mínima '
    'para jusante de 0,69 m³/s ou 59.726,0 m³/dia no TVR, localizado nas Fazendas Vila '
    'Velha e Maracanã, Zona Rural, no município de São Desidério. § 2º - intervenção, '
    'válido pelo prazo de 08 (oito) anos, na Bacia Hidrográfica do Rio Grande, no Rio '
    'da Estiva ou Galheirão, em barramento existente, autorizado por meio desta '
    'Portaria, nas coordenadas Lat.12°52\'52,7"S e Long.45°46\'22,9"W, datum Sirgas '
    '2000, para fins de aproveitamento hidrelétrico, com volume máximo de acumulação '
    'de 1.135.126,8 m³, altura máxima de 10 m, potência instalada de 450 kw. Deverá '
    'ser mantida uma vazão mínima para jusante da barragem de 0,69 m³/s ou 59.726,0 '
    'm³/dia no TVR, localizado nas Fazendas Vila Velha e Maracanã, Zona Rural, no '
    'município de São Desidério. Os atos autorizados no Art. 1º estão condicionados ao '
    'cumprimento da legislação vigente, do parágrafo § 4º deste artigo.'
)

LANCAMENTO_24493 = (
    'PORTARIA Nº 18.432 DE 22 DE MAIO DE 2019. '
    + PREAMBULO
    + '2013. 001.001144/ INEMA/LIC- 01144, RESOLVE: Art. 1º - Autorizar o direito de '
    'uso dos recursos hídricos, válido pelo prazo de 4 (quatro) anos, ao SERVIÇO '
    'AUTÔNOMO DE ÁGUA E ESGOTO, inscrito no CNPJ nº 13.644.919/0001-60, com sede no '
    'Largo da Independência, s/n, Centro, no município de Alagoinhas, para lançamento '
    'de efluente, na Bacia Hidrográfica do Rio Pojuca, no Rio Aramari, nas coordenadas '
    'Lat.12°09\'05,04"S e Long.38°26\'36"W, datum Sirgas 2000, com vazão de lançamento '
    'de 929,2 m³/dia, para fins de Diluição, com vazão de diluição de 2.076,76 m³/dia, '
    'concentrações de 13,94 mg/L para DBO e 1x10³UFC/100mL para Coliformes '
    'Termotolerantes, durante 24 h/d, localizado no SES do Barreiro/Mangalô, no '
    'município de Alagoinhas,' + FIM
)

ALTERACAO_26019 = (
    'PORTARIA Nº 19.494 DE 05 DE NOVEMBRO DE 2019. '
    + PREAMBULO
    + '2019.001.006028/INEMA/LIC-06028, RESOLVE: Art. 1.º - Autorizar a alteração da '
    'outorga do direito de uso dos recursos hídricos, relacionada ao processo nº '
    '1880/99, válida pelo prazo da Portaria nº 205, publicada no D.O.E em 26/04/00, à '
    'EMPRESA BAIANA DE ÁGUAS E SANEAMENTO S.A., inscrita no CNPJ nº '
    '13.504.675/0001-10, com sede na Avenida Luis Viana, n° 420, Edifício SEDUR, '
    'Centro Administrativo da Bahia, no município de Salvador, para captação '
    'superficial, na Bacia Hidrográfica do Rio Pojuca, no Rio Pojuca, nas coordenadas '
    'Lat.12º34’07,2”S e Long.38º02’49,10 W, datum Sirgas 2000, de vazão 58.368,4 '
    'm³/dia, durante 21 h/d, para fins de abastecimento humano, localizado no SIAA '
    'Barra do Pojuca, no município de Camaçari,' + FIM
)

# Sem "a/à" antes do nome, "para fins" sem "de" e "no mesmo local e município".
SEM_CONECTIVO_601 = (
    'PORTARIA Nº 20.321 DE 30 DE MARÇO DE 2020. '
    + PREAMBULO
    + '2018.001.001013/INEMA/LIC-01013, RESOLVE: Art. 1º - Autorizar a renovação do '
    'direito de uso dos recursos hídricos, válido pelo prazo de 04 (quatro) anos, ALEX '
    'FAZOLLO SOSSAI, inscrito no CPF sob nº 960.874.045-20 com sede na Rua Correios, '
    'nº 131, Zona Rural, no município de Medeiros Neto, para captação superficial, na '
    'Bacia Hidrográfica do Rio dos Frades, no Rio Jacarandá Braço Norte, nas '
    'coordenadas Lat.16º33’15”S e Long.39º35’16”W, datum Sirgas 2000, de vazão 1.540 '
    'm³/dia, durante 11 h/d para fins irrigação por microaspersão, área 44 ha, '
    'localizado no mesmo local e município,' + FIM
)

EDITAL_10206 = (
    'EDITAL DE NOTIFICAÇÃO O INSTITUTO DO MEIO AMBIENTE E RECURSOS HÍDRICOS - INEMA '
    'FAZ SABER ao Autuado: CLENILTON MARTINS DOS ANJOS, CPF nº 927.642.405-97 nos '
    'autos do processo administrativo nº 2016-003984/TEC/AIAD-0220, foi homologado o '
    'Auto de Infração de ADVERTÊNCIA, “por realizar captação de água superficial sem a '
    'respectiva outorga ou dispensa de outorga de direito de uso do recurso hídrico”.'
)


def unica(texto):
    resposta = extrair_pela_regex(texto)
    assert len(resposta.outorgas) == 1
    return resposta.outorgas[0]


def test_captacao_subterranea():
    outorga = unica(CAPTACAO_SUBTERRANEA_1156)
    assert outorga.natureza == 'outorga'
    assert outorga.nro_portaria == '20771'
    assert outorga.dt_portaria == '2020-06-08'
    assert outorga.nro_processo == '2019.001.007825/INEMA/LIC-07825'
    assert outorga.outorgado.nome == 'LAERTE OLIVEIRA BARBOSA'
    assert outorga.outorgado.tipo_documento == 'CPF'
    assert outorga.outorgado.nro_documento == '246.713.205-68'
    assert outorga.outorgado.endereco.logradouro == 'Rua Pé de Limão'
    assert outorga.outorgado.endereco.numero == '9999'
    assert outorga.outorgado.endereco.municipio == 'Barro Alto'
    [uso] = outorga.usos
    assert uso.modo == 'captacao_subterranea'
    assert uso.prazo_validade_anos == 4
    assert uso.bacia_hidrografica == 'Rio São Francisco'
    assert uso.finalidades == ['irrigacao']
    assert uso.metodos_irrigacao == ['gotejamento']
    assert uso.area_ha == 2.5
    assert uso.localidade.startswith('Fazenda Baixa Funda II')
    assert uso.municipios == ['Barro Alto']
    [ponto] = uso.pontos
    assert ponto.identificacao == 'poço 1'
    assert ponto.corpo_hidrico is None
    assert ponto.sistema_referencia_espacial == 'SIRGAS 2000'
    assert ponto.vazao_m3_dia == 152
    assert ponto.vazao_m3_s == pytest.approx(152 / 86_400, abs=1e-6)
    assert ponto.captacao_horas_dia == 13
    assert ponto.ponto == 'POINT(-41.89375 -11.8793333)'


def test_paragrafos_e_pontos_com_finalidades_diferentes_viram_usos():
    outorga = unica(PARAGRAFOS_1551)
    assert outorga.natureza == 'renovacao'
    assert [uso.modo for uso in outorga.usos] == [
        'captacao_superficial',
        'captacao_superficial',
        'captacao_subterranea',
    ]
    assert [uso.area_ha for uso in outorga.usos] == [1400, 2.5, 166.5]
    assert [uso.metodos_irrigacao for uso in outorga.usos] == [
        ['pivo_central'],
        ['microaspersao'],
        ['pivo_central'],
    ]
    p1, p2 = outorga.usos[0].pontos[0], outorga.usos[1].pontos[0]
    assert (p1.identificacao, p1.corpo_hidrico, p1.vazao_m3_dia) == (
        'Ponto P1',
        'Rio de Ondas',
        81729,
    )
    # O P2 está no mesmo rio, citado só antes do P1.
    assert (p2.identificacao, p2.corpo_hidrico, p2.captacao_horas_dia) == (
        'Ponto P2',
        'Rio de Ondas',
        1,
    )
    # O primeiro uso fica com o local do segundo, citado uma vez no fim do § 1º.
    assert outorga.usos[0].municipios == ['Barreiras']
    assert outorga.usos[2].pontos[0].identificacao == 'poço 1'


def test_datum_e_horas_do_ultimo_ponto_valem_para_o_uso():
    outorga = unica(SUZANO_3626)
    superficial, subterranea = outorga.usos
    assert superficial.municipios == ['Nova Viçosa']
    assert subterranea.bacia_hidrografica == 'Extremo Sul'
    poco_2, poco_3 = subterranea.pontos
    assert (poco_2.identificacao, poco_2.vazao_m3_dia) == ('poço 2', 100)
    assert (poco_3.identificacao, poco_3.vazao_m3_dia) == ('poço 3', 25)
    assert poco_2.captacao_horas_dia == poco_3.captacao_horas_dia == 10
    assert poco_2.sistema_referencia_espacial == 'SIRGAS 2000'


def test_intervencao_com_prazo_por_paragrafo_e_vazao_nas_duas_unidades():
    outorga = unica(INTERVENCAO_27768)
    assert outorga.outorgado.nome == 'NORFIL AGRO LTDA'
    regularizacao, hidreletrica = outorga.usos
    assert regularizacao.modo == hidreletrica.modo == 'intervencao'
    assert regularizacao.tipo_intervencao == 'regularizacao_barramento'
    assert hidreletrica.tipo_intervencao == 'aproveitamento_hidreletrico'
    assert regularizacao.prazo_validade_anos == 35
    assert hidreletrica.prazo_validade_anos == 8
    assert regularizacao.volume_maximo_acumulacao_m3 == 1_135_126.8
    assert regularizacao.altura_maxima_m == 10
    assert regularizacao.descarga_de_fundo is True
    # O texto traz as duas unidades: nenhuma é calculada.
    assert regularizacao.vazao_minima_jusante_m3_s == 0.69
    assert regularizacao.vazao_minima_jusante_m3_dia == 59_726.0
    assert hidreletrica.vazao_minima_jusante_m3_s == 0.69
    assert regularizacao.municipios == ['São Desidério']
    assert hidreletrica.pontos[0].barramento.startswith('barramento existente')


def test_lancamento_de_efluente():
    outorga = unica(LANCAMENTO_24493)
    assert outorga.nro_processo == '2013.001.001144/INEMA/LIC-01144'
    assert outorga.outorgado.endereco.numero == 's/n'
    [uso] = outorga.usos
    assert uso.modo == 'lancamento_efluente'
    assert uso.finalidades == ['diluicao_efluente']
    assert uso.vazao_diluicao_m3_dia == 2076.76
    assert uso.pontos[0].vazao_m3_dia == 929.2
    assert uso.pontos[0].corpo_hidrico == 'Rio Aramari'
    dbo, coliformes = uso.parametros
    assert (dbo.nome, dbo.valor_numero, dbo.unidade) == ('DBO', 13.94, 'mg/L')
    assert coliformes.nome == 'Coliformes Termotolerantes'
    assert coliformes.valor_numero == 1000


def test_alteracao_com_processo_relacionado_e_prazo_de_outra_portaria():
    outorga = unica(ALTERACAO_26019)
    assert outorga.natureza == 'alteracao'
    assert outorga.nro_processo_relacionado == '1880/99'
    [uso] = outorga.usos
    assert uso.prazo_validade_anos is None
    assert uso.nro_portaria_prazo == '205'
    assert uso.dt_publicacao_portaria_prazo == '2000-04-26'
    assert uso.finalidades == ['abastecimento_humano']
    assert uso.pontos[0].vazao_m3_dia == 58_368.4


def test_nome_sem_conectivo_finalidade_sem_de_e_mesmo_local_da_sede():
    outorga = unica(SEM_CONECTIVO_601)
    assert outorga.outorgado.nome == 'ALEX FAZOLLO SOSSAI'
    [uso] = outorga.usos
    assert uso.finalidade_texto == 'irrigação por microaspersão'
    assert uso.municipios == ['Medeiros Neto']
    assert campos_vazios(extrair_pela_regex(SEM_CONECTIVO_601)) == []


def test_ato_que_so_cita_outorga_nao_tem_outorga():
    assert extrair_pela_regex(EDITAL_10206).outorgas == []


@pytest.mark.parametrize(
    'texto, finalidades, metodos',
    [
        (
            'consumo humano e dessedentação animal',
            ['abastecimento_humano', 'dessedentacao_animal'],
            [],
        ),
        ('irrigação por aspersão com pivô central', ['irrigacao'], ['pivo_central']),
        (
            'irrigação por aspersão convencional',
            ['irrigacao'],
            ['aspersao_convencional'],
        ),
        ('irrigação por aspersão', ['irrigacao'], ['aspersao']),
        ('fabricação de concreto e argamassas', ['obra_infraestrutura'], []),
        ('lavagem de veículos', ['outro'], []),
    ],
)
def test_classificar_finalidade(texto, finalidades, metodos):
    assert classificar_finalidade(texto) == (finalidades, metodos)


def test_vazao_calcula_so_a_unidade_que_falta():
    assert vazao_nas_duas_unidades(86_400, None) == (86_400, 1.0)
    assert vazao_nas_duas_unidades(None, 0.5) == (43_200.0, 0.5)
    assert vazao_nas_duas_unidades(59_726.0, 0.69) == (59_726.0, 0.69)
    assert vazao_nas_duas_unidades(None, None) == (None, None)


def test_ponto_converte_a_vazao_do_modelo():
    ponto = PontoUso(
        identificacao=None,
        corpo_hidrico=None,
        barramento=None,
        barramento_dispensado=False,
        coordenada=None,
        sistema_referencia_espacial='Sirgas2000',
        vazao_m3_dia=None,
        vazao_m3_s=2.0,
        captacao_horas_dia=None,
    )
    assert ponto.vazao_m3_dia == 172_800.0
    assert ponto.sistema_referencia_espacial == 'SIRGAS 2000'
    assert ponto.ponto is None


@pytest.mark.parametrize(
    'grafia, oficial',
    [
        ('Santa Luz', 'Santaluz'),
        ('Luiz Eduardo Magalhães', 'Luís Eduardo Magalhães'),
        ('do Salvador', 'Salvador'),
        ('Maragojipe', 'Maragogipe'),
    ],
)
def test_grafias_de_municipio_do_doe(grafia, oficial):
    assert normalizar_municipio(grafia) == oficial


def sem_horas(texto):
    return texto.replace(', durante 13 h/d', '')


def test_modelo_preenche_so_os_campos_vazios():
    resposta = extrair_pela_regex(sem_horas(CAPTACAO_SUBTERRANEA_1156))
    assert campos_vazios(resposta) == ['outorgas.0.usos.0.pontos.0.captacao_horas_dia']
    do_modelo = extrair_pela_regex(CAPTACAO_SUBTERRANEA_1156)
    # O modelo devolve outra vazão e outro nome: não entram, só as horas.
    do_modelo.outorgas[0].usos[0].pontos[0].vazao_m3_dia = 1.0
    do_modelo.outorgas[0].outorgado.nome = 'OUTRO NOME'
    preenchida, preenchidos = preencher_vazios_pelo_modelo(
        resposta, do_modelo, campos_vazios(resposta)
    )
    assert preenchidos == ['outorgas.0.usos.0.pontos.0.captacao_horas_dia']
    ponto = preenchida.outorgas[0].usos[0].pontos[0]
    assert (ponto.captacao_horas_dia, ponto.vazao_m3_dia) == (13, 152)
    assert preenchida.outorgas[0].outorgado.nome == 'LAERTE OLIVEIRA BARBOSA'


def test_caminho_que_o_modelo_nao_tem_fica_vazio():
    resposta = extrair_pela_regex(sem_horas(CAPTACAO_SUBTERRANEA_1156))
    _, preenchidos = preencher_vazios_pelo_modelo(
        resposta, ExtracaoOutorga(outorgas=[]), campos_vazios(resposta)
    )
    assert preenchidos == []


def test_latitude_sem_ponto_depois_de_lat():
    # Ato 34509: "Lat12°42’56.93"S", sem o ponto; o "1" do grau não pode sumir.
    texto = CAPTACAO_SUBTERRANEA_1156.replace('Lat.11°52’45,6"S', 'Lat11°52’45,6"S')
    [ponto] = unica(texto).usos[0].pontos
    assert ponto.coordenada.latitude.startswith('11°52’45,6')
    assert ponto.ponto is not None


def test_par_fora_da_bahia_nao_chama_o_modelo():
    # Ato 34509: "Lat.44°34’39.34"S" é erro do DOE; o modelo copiaria o mesmo valor.
    texto = CAPTACAO_SUBTERRANEA_1156.replace('Lat.11°52’45,6"S', 'Lat.44°52’45,6"S')
    resposta = extrair_pela_regex(texto)
    [ponto] = resposta.outorgas[0].usos[0].pontos
    assert ponto.ponto is None
    assert ponto.coordenada.latitude.startswith('44°52’45,6')
    assert campos_vazios(resposta) == []


def extrair_com_modelo_falso(texto, modelo):
    extracao = EXTRACOES['OUT']
    extrator = RunnableLambda(
        lambda entrada: regex_com_modelo(entrada['trecho'], extracao, modelo)
    )
    return extrair(texto, extracao, extrator)


def test_extrair_so_chama_o_modelo_quando_falta_campo():
    chamadas = []

    def modelo(entrada):
        chamadas.append(entrada)
        return extrair_pela_regex(CAPTACAO_SUBTERRANEA_1156)

    [completo] = extrair_com_modelo_falso(
        CAPTACAO_SUBTERRANEA_1156, RunnableLambda(modelo)
    )
    assert chamadas == []
    assert completo['preenchido_pelo_modelo'] == []
    [incompleto] = extrair_com_modelo_falso(
        sem_horas(CAPTACAO_SUBTERRANEA_1156), RunnableLambda(modelo)
    )
    assert len(chamadas) == 1
    assert incompleto['preenchido_pelo_modelo'] == [
        'outorgas.0.usos.0.pontos.0.captacao_horas_dia'
    ]
    assert incompleto['modelos'][0].usos[0].pontos[0].captacao_horas_dia == 13


def test_falha_do_modelo_mantem_a_resposta_da_regex():
    def fora_do_ar(_):
        raise ConnectionError('Ollama fora do ar')

    [trecho] = extrair_com_modelo_falso(
        sem_horas(CAPTACAO_SUBTERRANEA_1156), RunnableLambda(fora_do_ar)
    )
    assert 'erro' not in trecho
    assert 'Ollama fora do ar' in trecho['erro_modelo']
    assert trecho['modelos'][0].outorgado.nome == 'LAERTE OLIVEIRA BARBOSA'


def test_outorgas_registradas():
    assert {'OUT', 'ROUT', 'AOUT', 'AMOUT'} <= set(REGISTRO)
    assert 'PPV/OUT' not in REGISTRO
    assert REGISTRO['OUT'].pasta == 'Portarias'


# --- Casos achados nos atos reais do banco -----------------------------------------
# Os textos abaixo são o Art. 1º de cada ato (o id está no nome), montados com
# ``portaria``: o preâmbulo e o fim padrão não mudam a extração.


def portaria(cabecalho: str, processo: str, artigo_1: str) -> str:
    return f'{cabecalho} {PREAMBULO}{processo}, RESOLVE: Art. 1º - {artigo_1}{FIM}'


AMPLIACAO_15749 = portaria(
    'PORTARIA Nº 11.239 DE 29 DE JANEIRO DE 2016.',
    '2014-005032/OUT/AMPL-0012',
    'Autorizar a ampliação da outorga do direito de uso dos recursos hídricos, '
    'relacionada ao Processo nº 2011-001001/OUT/AUT-0384, válida pelo prazo da '
    'Portaria nº 2201, publicada no D.O.E em 06/03/2012, à CARACOL AGROPECUÁRIA LTDA, '
    'inscrita no CNPJ sob nº 09.098.053/0001-61, com sede na Av. Carlos Gomes, nº '
    '1200, Sala 502, Auxiliadora, no município de Porto Alegre - RS, para captação '
    'superficial, na Bacia Hidrográfica do Rio São Francisco, no rio Grande, nas '
    'coordenadas Lat. 11° 44\' 00" S e Long. 44° 34\' 00" W, datum SIRGAS2000, com '
    'vazão de até 68,00 m³/dia, durante 2 horas/dia, para fins de dessedentação '
    'animal, sendo 1360 bovinos de corte, na Fazenda Umuarama, Zona Rural, localizada '
    'no município de Cotegipe,',
)

# Ampliação só da vazão, sem par de coordenadas: a regex não monta uso nenhum.
AMPLIACAO_SEM_PONTO_1174 = portaria(
    'PORTARIA Nº 20.788 DE 10 DE JUNHO DE 2020.',
    '2019.001.005039/INEMA/LIC-05039',
    'Autorizar a ampliação da outorga do direito de uso dos recursos hídricos, '
    'relacionada ao processo nº 2011-000859/OUT/RENOV-0113, válida pelo prazo da '
    'Portaria nº 14.913, publicada no D.O.E em 27/09/2017 à JBS S/A, inscrita no CNPJ '
    'nº 02.916.265/0112-85, com sede na Rodovia BA 263, KM 167, s/n, Zona Rural, no '
    'município de Itapetinga, para vazão de 2.000 m³/dia, durante 16 h/d, localizado '
    'no mesmo local e município,',
)

VALIDA_ATE_22968 = portaria(
    'PORTARIA Nº 17.201 DE 01 DE NOVEMBRO DE 2018.',
    '2017.001.003059/INEMA/LIC-03059',
    'Autorizar a renovação do direito de uso dos recursos hídricos, válida até '
    '10/11/2038, à EMPRESA BAIANA DE ÁGUAS E SANEAMENTO S.A. inscrita no CNPJ nº '
    '13.504.675/0001-10, com sede à Avenida Luís Viana, n°420, Edif. SEDUR, Centro '
    'Administrativo da Bahia, no município de Salvador, para captação subterrânea, na '
    'Bacia Hidrográfica do Rio Paraguaçu, nas coordenadas Lat.12°53\'38,5"S e '
    'Long.38°53\'23,3"W, datum Sirgas 2000, do Poço 1, de vazão 542 m³/dia, durante '
    '24 h/d, para fins de abastecimento humano, localizado no SAA Maragogipe - São '
    'Roque do Paraguaçu, no município de Maragogipe,',
)

# Início e fim da canalização em dois pares; o datum só vem depois do segundo.
CANALIZACAO_19067 = portaria(
    'PORTARIA Nº 14.078 DE 23 DE MAIO DE 2017.',
    '2017.001.001772/INEMA/LIC-01772',
    'Autorizar o direito de uso dos recursos hídricos, válido pelo prazo de 4 '
    '(quatro) anos, à BN E JP EMPREENDIMENTO IMOBILIÁRIO SPE LTDA, inscrito no CNPJ '
    'nº 23.300.045/0001-87, com sede na Rua Frederico Simões, N° 98, Caminho das '
    'Arvores, no município de Salvador, para Intervenção, na bacia hidrográfica do '
    'Recôncavo Norte, em afluente do Rio Catu, localizado na Rua Dantas Bião, '
    'Alagoinhas Velha, município de Alagoinhas, nas coordenadas Lat.12º08\'24,6"S e '
    'Long.38º24\'40,8"W, para o início da intervenção, e Lat.12º08\'33,9"S e '
    'Long.38º24\'42,97" W, datum SIRGAS 2000 para o final da intervenção para fins de '
    'canalização, em seção geométrica circular, em concreto, bueiro tubular duplo com '
    'diâmetro de 1 m, com extensão de 2,86 m, com vazão de projeto de 587.520 m³/dia '
    'para o tempo de recorrência de 25 anos,',
)

EXTENSAO_EM_KM_14938 = portaria(
    'PORTARIA Nº 10.571 DE 08 DE OUTUBRO DE 2015.',
    '2015.001.001023/INEMA/LIC-01023',
    'Autorizar o direito de uso dos recursos hídricos, válido pelo prazo de 04 '
    '(quatro) anos, à CIBRAFÉRTIL - COMPANHIA BRASILEIRA DE FERTILIZANTES, inscrita '
    'no CNPJ sob nº 00.117.842/0001-28, com sede na Rua Alfa, Área Industrial Norte, '
    'Polo Petroquímico, no município de Camaçari, para intervenção, na Bacia '
    'Hidrográfica do Recôncavo Norte, em rio sem denominação, localizado na Rua Alfa, '
    'Área Industrial Norte, Polo Petroquímico, no município de Camaçari, nas '
    'coordenadas Lat. 12º38\'47,8" S e Long. 38º19\'39,0"\r\nW, para o início da '
    'intervenção, e Lat. 12º38\'44,9" S e Long.\r\n38º19\'30,7" W, datum SIRGAS 2000 '
    'para o final da intervenção para fins de canalização (e/ou) retificação de '
    'canal, em seção geométrica trapezoidal, a céu aberto, sem revestimento do canal, '
    'com 1,5 m de altura, 6 m de base maior e 3 m de base menor, com extensão de 1,5 '
    'km, com vazão de projeto de 316.224 m³/d para o tempo de recorrência de 25 anos,',
)

# Longitude antes da latitude. O ato tem nove trechos de canalização; ficam os dois
# primeiros e o fim ("tempo de recorrência ..., para fins de canalização").
LONGITUDE_ANTES_25445 = portaria(
    'PORTARIA Nº 19.134 DE 16 DE SETEMBRO DE 2019.',
    '2018.001.007766/INEMA/LIC-07766',
    'Autorizar a renovação do direito de uso dos recursos hídricos, válido pelo prazo '
    'de 4 (quatro) anos, à COMPANHIA DE DESENVOLVIMENTO URBANO DO ESTADO DA BAHIA - '
    'CONDER, inscrito no CNPJ nº 13.595.251/0001-08, com sede na Avenida Edgar '
    'Santos, s/n, Narandiba, no município de Salvador, para intervenção, na Bacia '
    'Hidrográfica do Recôncavo Norte e Inhambupe, no Rio Jaguaribe, localizado no '
    'trecho entre o seu cruzamento com a Av. Luiz Viana Filho, Paralela e a sua foz, '
    'no município de Salvador, nas coordenadas Long.38°23\'34.26"W e '
    'Lat.12°57\'39.72"S para início da intervenção e Long.38°23\'33.74"W e '
    'Lat.12°57\'29.53"S para fim da intervenção, datum\nSirgas 2000, seção '
    'trapezoidal aberta, base 22,5 m, altura 3 m, comprimento 640 m, laterais com '
    'gabião revestido e concreto projetado, fundo com leito natural regularizado, '
    'vazão 129,5 m3/s; nas coordenadas Long.38°23\'33.74"W e Lat.12°57\'29.53"S para '
    'início da intervenção e Long. 38°23\'23.96"W e Lat.12°57\'23.99"S para fim da '
    'intervenção, datum Sirgas 2000, seção trapezoidal aberta, base 22,5 m, altura 3 '
    'm, comprimento 340 m, laterais com gabião revestido e concreto projetado, fundo '
    'com leito natural regularizado, vazão 129,5 m3/s; tempo de recorrência 25 anos, '
    'para fins de canalização,',
)

LANCAMENTO_DE_CARGA_26314 = portaria(
    'PORTARIA Nº 19.738 DE 05 DE DEZEMBRO DE 2019.',
    '2018.001.002313/INEMA/LIC-02313',
    'Autorizar a renovação do direito de uso dos recursos hídricos, válida pelo '
    'prazo de 4 (quatro) anos, à INÊS SERRANO BATINGA, inscrita no CPF nº '
    '263.722.235-20, com sede na Avenida Juracy Magalhães Júnior, n° 1889, Horto '
    'Florestal, no município de Salvador, para lançamento de carga poluidora, na '
    'Bacia Hidrográfica do Rio Paraguaçu, no Rio Paraguaçu, no lago da Barragem de '
    'Pedra do Cavalo, no entorno das coordenadas Lat.12°30\'23"S e Long.39°08\'39"W, '
    'datum Sirgas 2000, para diluição de 89,4 kg/dia de fósforo e ocupação de área de '
    'espelho d’água de 8.000 m², para fins de piscicultura em tanques-rede, '
    'localizado na Fazenda Lago Dourado, Estrada do Povoado do Gurunga, Geolândia, no '
    'município de Cabaceiras do Paraguaçu,',
)

# Barramento dispensado de outorga e local igual ao da sede, que é uma fazenda.
DISPENSADO_22994 = portaria(
    'PORTARIA Nº 17.289 DE 19 DE NOVEMBRO DE 2018.',
    '2016.001.003024/INEMA/LIC-03024',
    'Autorizar o direito de uso dos recursos hídricos, válido pelo prazo de 4 '
    '(quatro) anos, a LAERTE GRASSI, inscrito no CPF sob nº 527.488.987-53, com sede '
    'na Fazenda Muqui, s/n, Zona Rural, município de Itabela,\xa0 para captação '
    'superficial, na Bacia Hidrográfica do\xa0 Rio Caraiva, no lago formado pelo '
    'barramento dispensado de outorga, no rio Piaçava, nas coordenadas '
    'Lat.16º42\'13"S e Long.39º28\'43"W, datum Sirgas 2000, de vazão 4.311 m³/dia, '
    'durante 11 h/d, para fins de irrigação por gotejamento de 112 ha, localizado no '
    'mesmo local e município,',
)

CAPTACAO_EM_BARRAMENTO_22580 = portaria(
    'PORTARIA Nº 16.931 DE 20 DE SETEMBRO DE 2018.',
    '2018.001.003339/INEMA/LIC-03339',
    'Autorizar o direito de uso dos recursos hídricos, válido pelo prazo de 4 '
    '(quatro) anos, à BAHIA ETANOL HOLDING S.A, inscrita no CNPJ sob nº '
    '24.870.441/0002-93, com sede na Rodovia BA 693, KM 09, Estrada '
    'Ibirapuã-Medeiros Neto, no município de Ibirapuã, para captação em barramento '
    'existente, autorizado por meio da Portaria INEMA nº 16.254/18, na Bacia '
    'Hidrográfica do Rio Peruípe, no Córrego Jequitibá, nas coordenadas '
    'Lat.17°37\'45,15"S e Long.40°10\'27,82"W, datum Sirgas 2000, com vazão de 4.200 '
    'm³/dia, durante 21 h/d, para fins de abastecimento industrial, localizado no '
    'mesmo local e município,',
)

# Datum SAD 69 e local antes das coordenadas.
SAD69_15243 = portaria(
    'PORTARIA Nº 10.861 DE 02 DE DEZEMBRO DE 2015.',
    '2011-001700/OUT/AUT-0563',
    'Autorizar o direito de uso dos recursos hídricos, válido pelo prazo de 04 '
    '(quatro) anos, a EDILSON RAMOS DIAS, inscrito no CPF sob nº 452.174.755-87, com '
    'sede na Fazenda Poções, s/n, Zona Rural, no município de Igaporã, para captação '
    'subterrânea, na Bacia Hidrográfica do Rio São Francisco, localizado na Fazenda '
    "Poções, s/n, Zona Rural, no município de Igaporã, nas coordenadas Lat. 13º 56' "
    "06,4'' S e Long. 42º 35' 10,9'' W, datum Sad 69, do poço 01, de vazão 192 "
    'm³/dia, durante 12 h/dia, para fins de abastecimento industrial,',
)

SEM_LAT_822 = portaria(
    'PORTARIA Nº 20.473 DE 17 DE ABRIL DE 2020.',
    '2019.001.005710/INEMA/LIC-05710',
    'Autorizar o direito de uso dos recursos hídricos, válido pelo prazo de 04 '
    '(quatro) anos, a JOSÉ SIQUEIRA AMORIM, inscrito no CPF n° 164.295.245-15, com '
    'sede na Rua Mandacaru, s/n, Taquarendi, no município de Mirangaba, para captação '
    'subterrânea, na Bacia Hidrográfica do Rio Itapicuru, nas coordenadas '
    '10°53’48,5”S e Long.40°41’07,5”W, datum Sirgas 2000, do poço 4, de vazão 210 '
    'm³/dia, durante 7 h/d, para fins de irrigação por microaspersão, área 4 ha, '
    'localizado na Fazenda Praça Nova, Taquarendi, no município de Mirangaba,',
)

# Aspas repetidas no fim da latitude: "11,79”S”".
ASPAS_REPETIDAS_517 = portaria(
    'PORTARIA Nº 20.237 DE 16 DE MARÇO DE 2020.',
    '2015.001.002531/INEMA/LIC-02531',
    'Autorizar o direito de uso dos recursos hídricos, válido pelo prazo de 4 '
    '(quatro) anos, à EMPRESA BAIANA DE ÁGUAS E SANEAMENTO S.A., inscrita no CNPJ nº '
    '13.504.675/0001-10, com sede na Avenida Luis Viana, n° 420, Edifício SEDUR, '
    'Centro Administrativo da Bahia, município de Salvador, para \xa0lançamento de '
    'efluente, na \xa0Bacia Hidrográfica do \xa0Rio Mucuri, no afluente sem nome do '
    'Rio Mucurizinho, nas coordenadas Lat.18°01’11,79”S” e Long.39°51’15,79”W, datum '
    'Sirgas 2000, para fins de Destinação Final, com vazão do efluente de 2.794,37 '
    'm³/dia, concentrações iniciais de 88,33 mg/L para DBO e 1,46E+06 CT/100mL para '
    'Coliformes Termotolerantes, durante 24 h/d, localizado no SES Itabatã, no '
    'município de Itabatã,',
)

# Duas portarias coladas num ato só (erro de separação do DOE): duas outorgas.
DUAS_PORTARIAS_24350 = portaria(
    'PORTARIA Nº 18.324 DE 03 DE MAIO DE 2019.',
    '2018.001.004971/INEMA/LIC-04971',
    'Autorizar o direito de uso dos recursos hídricos, válido pelo prazo de 4 '
    '(quatro) anos a ROMEU FRANCIOSI, inscrito no CPF nº 646.994.040-49, com sede na '
    'Avenida Luís Eduardo Magalhães, s/n, Jardim das Acácias, no município de Luís '
    'Eduardo Magalhães, para captação subterrânea, na Bacia Hidrográfica do Rio São '
    'Francisco, no poço 2, nas coordenadas Lat.11º22\'11,06"S e Long.45°37\'59,54"W, '
    'datum Sirgas 2000, de vazão 9.000 m³/dia, durante 18 h/d; e no poço 3, nas '
    'coordenadas Lat.11°23\'14,48"S e Long.45°39\'19,44"W, datum Sirgas 2000,\xa0 de '
    'vazão 9.000 m³/dia, durante 18 h/d, para fins de irrigação por pivô central, '
    'área 280 ha, localizado nas Fazendas São Jose IV e V, Zona Rural, no município '
    'de Formosa do Rio Preto,',
).replace(
    ' Art. 2º',
    ' PORTARIA Nº 18.325 DE 03 DE MAIO DE 2019. '
    + PREAMBULO
    + (
        '2018.001.005165/INEMA/LIC-05165, RESOLVE: Art. 1.º - Autorizar o direito de uso '
        'dos recursos hídricos, válido pelo prazo de 4 (quatro) anos a ROMEU '
        'FRANCIOSI,inscrito no CPF nº 646.994.040-49, com sede na Avenida Luís Eduardo '
        'Magalhães, s/n, Jardim das Acácias, no município de Luís Eduardo Magalhães, para '
        'captação subterrânea, na Bacia Hidrográfica do Rio São Francisco, no poço 4, nas '
        'coordenadas Lat.11°24\'36"S e Long.45°39\'17"W, datum Sirgas 2000, de vazão '
        '9.000 m³/dia, durante 18 h/d; e no poço 9, nas coordenadas Lat.11°25\'55,4"S e '
        'Long.45°38\'58,8"W, datum Sirgas 2000, de vazão 9.000 m³/dia, durante 18 h/d, '
        'para fins de irrigação, por pivô central, área 280 ha, localizado nas Fazendas '
        'São José I e V, Zona Rural, no município de Formosa do Rio Preto,'
        + FIM
        + ' Art. 2º'
    ),
    1,
)

VARIOS_MUNICIPIOS_534 = portaria(
    'PORTARIA Nº 20.249 DE 19 DE MARÇO DE 2020.',
    '2017.001.007180/INEMA/LIC-07180',
    'Autorizar o direito de uso dos recursos hídricos, válido pelo prazo de 4 '
    '(quatro) anos, à SUZANO S.A., inscrito no CNPJ nº 16.404.287/0001-55, com sede '
    'na Avenida Professor Magalhães Neto, nº 1752, Pituba, no município de Salvador, '
    'para captação superficial, na Bacia Hidrográfica do Rio Mucuri, no Rio '
    'Mucurizinho, nas coordenadas Lat.18º00’05,4”S e Long.39º55’56,3”W, datum Sirgas '
    '2000, de vazão 200 m³/dia, durante 8 h/d, para fins de irrigação e pulverização '
    'agrícola, área de 45 ha, por caminhão pipa, localizado no Complexo de Fazendas '
    'do Bloco IX, nos municípios de Mucuri e Nova Viçosa,',
)

PRAZO_DA_PORTARIA_INEMA_395 = portaria(
    'PORTARIA Nº 20.153 DE 20 DE FEVEREIRO DE 2020.',
    '2019.001.006939/INEMA/LIC-06939',
    'Autorizar a alteração da outorga do direito de uso dos recursos hídricos, '
    'relacionada ao processo nº 2017.001.001937/INEMA/LIC-01937, válida pelo prazo da '
    'Portaria INEMA n° 19.257, publicada no D.O.E em 01/10/2019, à SUELI ROZINDO '
    'OLIVEIRA, inscrita no CPF nº 353.415.997-72, com sede na Avenida das Palmeiras, '
    'n° 75, Morumbi, no município de Itapetinga, para captação superficial, na Bacia '
    'Hidrográfica do Rio Pardo, no Rio Catolé Grande, nas coordenadas '
    'Lat.15°14\'00"S e Long.40°16\'45"W, datum Sirgas 2000, de vazão 5.725 m³/dia, '
    'durante 21 h/d, para fins de irrigação por aspersão, área 90 ha, localizado na '
    'Fazenda Bela Vista, Zona Rural, no município de Itapetinga,',
)

# Vazão malformada ("81,347,0"), prazo "vigente da portaria" e sede com rodovia.
VAZAO_MALFORMADA_15493 = portaria(
    'PORTARIA Nº 11.016 DE 23 DE DEZEMBRO DE 2015.',
    '2013-002525/OUT/AMPL-0015',
    'Autorizar a ampliação da outorga do direito de uso dos recursos hídricos, '
    'relacionada ao Processo nº 2012-001454/OUT/RENOV-0068, válida pelo prazo vigente '
    'da portaria nº 6504, publicada no D.O.E. em 06/12/2013, à GEACIR CELESTINO '
    'DAMIANI, inscrito no CPF sob nº 401.936.679-91, com sede na Fazenda Renascer, '
    'Rod. BR 349, km 258, s/n, Zona Rural, no município de Correntina, para captação '
    'superficial, na Bacia Hidrográfica do Rio Corrente, no Rio Arrojado, nas '
    'coordenadas Lat. 13º 45\' 58,0" S e Long. 45º 34\' 37,0" W, localizado na '
    'Fazenda Renascer, Rod. BR 349, km 258, s/n, Zona Rural, no município de '
    'Correntina, de vazão 81,347,0 m³/dia, durante 20 h/dia, para fins de irrigação '
    'por aspersão por pivô central, cultura feijão, soja, milho e algodão e a área '
    'irrigada de 1.396,9 ha,',
)

NUMERO_NO_LOGRADOURO_5492 = portaria(
    'PORTARIA Nº 23.985 DE 03 DE SETEMBRO DE 2021.',
    '2019.001.006610/INEMA/LIC-06610',
    'Autorizar o direito de uso dos recursos hídricos, válido pelo prazo de 04 '
    '(quatro) anos, a AGRÍCOLA CANTAGALO LTDA, inscrito no CNPJ nº '
    '13.574.512/0001-03, com sede na Rua Torquato Bahia nº 3, Comércio, no município '
    'de Salvador, para captação superficial, na Bacia Hidrográfica do Rio de Contas, '
    'no Rio Serra D’Água, nas coordenadas Lat.14º22’32,01”S e Long.39º10’27,92”W, '
    'datum Sirgas 2000, de vazão 1.636 m³/dia, durante 17 h/d, para fins de irrigação '
    'por gotejamento, área 44,1 ha, localizado na Fazenda Santa Cruz, Zona Rural, no '
    'município de Itacaré,',
)


# "para intervenções integradas" (plural) é o único aviso de que os usos são
# intervenções; o primeiro par do Canal Caji tem aspas no lugar do minuto.
INTERVENCOES_INTEGRADAS_5557 = portaria(
    'PORTARIA Nº 24.052 DE 13 DE SETEMBRO DE 2021.',
    '2021.001.003971/INEMA/LIC-03971',
    'Autorizar a renovação do direito de uso dos recursos hídricos, válida pelo prazo '
    'de 04 (quatro) anos, à COMPANHIA DE DESENVOLVIMENTO URBANO DO ESTADO DA BAHIA - '
    'CONDER, inscrita no CNPJ nº 13.595.251/0001-08, com sede na Avenida Edgard '
    'Santos, s/n, Narandiba, no município de Salvador, para intervenções integradas '
    'para o manejo de águas pluviais, nas Bacias Hidrográficas dos Rios Joanes e '
    'Ipitanga, no Reservatório de Amortecimento 1, no Rio Ipitanga, no entorno das '
    'coordenadas Lat.12º54’04.5”S e Long.38°22’21”W, para margem esquerda e '
    'Lat.12°54’12.1”S e Long.38°22’16.2”W para margem direita, para fins de '
    'construção de barragem, com volume máximo armazenado de 22.863 m³ e vazão mínima '
    'para jusante de 14,6 m³/s; no Reservatório de Amortecimento 5, no Riacho da '
    'Areia, no entorno das coordenadas Lat.12°53’19.9”S e Long.38°21’26.2”W para '
    'margem esquerda e Lat.12°53’22”S e Long.38°21’32.1”W para margem direita, para '
    'fins de construção de barragem, com volume máximo armazenado de 560.662,6 m³ e '
    'vazão mínima para jusante de 6,7 m³/s; no Canal Caji da Urbis, no afluente sem '
    'nome do Rio Ipitanga, no entorno das coordenadas Lat.12°52"44.9"S e '
    'Long.38°19’49.1"W para início da intervenção e Lat.12°53’28.5"S e '
    'Long.38°19’23.8"W para fim da intervenção, para fins de canalização; no Canal '
    'Jardim dos Pássaros, no afluente sem nome do Rio Ipitanga, no entorno das '
    'coordenadas Lat.12°54’02"S e Long.38°20’21.5"W para início da intervenção e '
    'Lat.12°54’01.4"S e Long.38°19’49.1"W para fim da intervenção, para fins de '
    'canalização; no Ponto 1, no Rio Ipitanga, no entorno das coordenadas '
    'Lat.12°53’21.4"S e Long.38°19’14.8"W para início da intervenção e '
    'Lat.12°51’03.7"S e Long.38°18’44"W para fim da intervenção, para fins de '
    'desassoreamento da calha do rio, datum das coordenadas SIRGAS 2000, localizado '
    'nos municípios de Lauro de Freitas e Salvador,',
)


def test_ampliacao_com_processo_relacionado_e_prazo_de_outra_portaria():
    outorga = unica(AMPLIACAO_15749)
    assert outorga.natureza == 'ampliacao'
    assert outorga.nro_processo == '2014-005032/OUT/AMPL-0012'
    assert outorga.nro_processo_relacionado == '2011-001001/OUT/AUT-0384'
    [uso] = outorga.usos
    assert (uso.nro_portaria_prazo, uso.dt_publicacao_portaria_prazo) == (
        '2201',
        '2012-03-06',
    )
    assert uso.finalidades == ['dessedentacao_animal']
    assert uso.municipios == ['Cotegipe']
    [ponto] = uso.pontos
    assert ponto.corpo_hidrico == 'rio Grande'
    # "datum SIRGAS2000", "vazão de até" e "2 horas/dia".
    assert ponto.sistema_referencia_espacial == 'SIRGAS 2000'
    assert (ponto.vazao_m3_dia, ponto.captacao_horas_dia) == (68, 2)
    assert campos_vazios(extrair_pela_regex(AMPLIACAO_15749)) == []


def test_ampliacao_sem_coordenadas_pede_os_usos_ao_modelo():
    resposta = extrair_pela_regex(AMPLIACAO_SEM_PONTO_1174)
    [outorga] = resposta.outorgas
    assert outorga.natureza == 'ampliacao'
    assert outorga.nro_processo_relacionado == '2011-000859/OUT/RENOV-0113'
    assert outorga.usos == []
    assert campos_vazios(resposta) == ['outorgas.0.usos']


def test_prazo_ate_uma_data():
    [uso] = unica(VALIDA_ATE_22968).usos
    assert uso.dt_validade == '2038-11-10'
    assert uso.prazo_validade_anos is None
    assert uso.pontos[0].identificacao == 'Poço 1'
    assert campos_vazios(extrair_pela_regex(VALIDA_ATE_22968)) == []


def test_prazo_da_portaria_inema():
    [uso] = unica(PRAZO_DA_PORTARIA_INEMA_395).usos
    assert uso.nro_portaria_prazo == '19257'
    assert uso.dt_publicacao_portaria_prazo == '2019-10-01'
    assert uso.metodos_irrigacao == ['aspersao']


def test_canalizacao_com_inicio_e_fim_extensao_e_vazao_de_projeto():
    outorga = unica(CANALIZACAO_19067)
    [uso] = outorga.usos
    assert uso.modo == 'intervencao'
    # O texto cita "bueiro" (travessia), mas a finalidade é a canalização.
    assert uso.tipo_intervencao == 'canalizacao'
    assert uso.extensao_m == 2.86
    assert uso.vazao_projeto_m3_dia == 587_520
    assert uso.vazao_projeto_m3_s == pytest.approx(6.8)
    assert uso.localidade == 'Rua Dantas Bião, Alagoinhas Velha'
    assert uso.municipios == ['Alagoinhas']
    inicio, fim = uso.pontos
    assert inicio.corpo_hidrico == fim.corpo_hidrico == 'afluente do Rio Catu'
    # O datum vem só depois do segundo par e vale para os dois.
    assert inicio.sistema_referencia_espacial == 'SIRGAS 2000'
    assert inicio.ponto == 'POINT(-38.4113333 -12.1401667)'
    # Intervenção não exige vazão nos pontos nem horas por dia.
    assert campos_vazios(extrair_pela_regex(CANALIZACAO_19067)) == []


def test_extensao_em_km_vira_metros():
    [uso] = unica(EXTENSAO_EM_KM_14938).usos
    assert uso.extensao_m == 1500
    assert uso.vazao_projeto_m3_dia == 316_224
    assert uso.pontos[0].corpo_hidrico == 'rio sem denominação'
    # "38º19'39,0"" e o "W" na linha seguinte.
    assert uso.pontos[0].ponto == 'POINT(-38.3275 -12.6466111)'


def test_longitude_antes_da_latitude():
    [uso] = unica(LONGITUDE_ANTES_25445).usos
    assert uso.tipo_intervencao == 'canalizacao'
    assert uso.comprimento_m == 640
    primeiro = uso.pontos[0]
    assert primeiro.coordenada.latitude == '12°57\'39.72"S'
    assert primeiro.coordenada.longitude == '38°23\'34.26"W'
    assert primeiro.ponto == 'POINT(-38.39285 -12.9610333)'
    # Fim do trecho e início do seguinte são o mesmo par, e a vazão vem depois dele.
    assert len(uso.pontos) == 4
    assert uso.pontos[1].vazao_m3_s == 129.5
    assert uso.pontos[1].vazao_m3_dia == 11_188_800


def test_lancamento_de_carga_poluidora():
    [uso] = unica(LANCAMENTO_DE_CARGA_26314).usos
    assert uso.modo == 'lancamento_efluente'
    assert uso.finalidades == ['aquicultura']
    assert uso.pontos[0].corpo_hidrico == 'lago da Barragem de Pedra do Cavalo'
    # Carga em kg/dia não é parâmetro de concentração.
    assert uso.parametros == []


def test_barramento_dispensado_e_local_igual_ao_da_sede_rural():
    outorga = unica(DISPENSADO_22994)
    [uso] = outorga.usos
    [ponto] = uso.pontos
    assert ponto.barramento_dispensado is True
    assert ponto.corpo_hidrico == 'rio Piaçava'
    assert outorga.outorgado.endereco.localidade == 'Fazenda Muqui'
    assert (uso.localidade, uso.municipios) == ('Fazenda Muqui', ['Itabela'])


def test_captacao_em_barramento():
    [uso] = unica(CAPTACAO_EM_BARRAMENTO_22580).usos
    assert uso.modo == 'captacao_superficial'
    [ponto] = uso.pontos
    assert ponto.barramento == 'barramento existente'
    assert ponto.barramento_dispensado is False
    assert ponto.corpo_hidrico == 'Córrego Jequitibá'
    assert ponto.vazao_m3_dia == 4200


def test_datum_sad69_e_local_antes_das_coordenadas():
    [uso] = unica(SAD69_15243).usos
    [ponto] = uso.pontos
    assert ponto.sistema_referencia_espacial == 'SAD 69'
    assert ponto.identificacao == 'poço 01'
    assert ponto.captacao_horas_dia == 12
    assert uso.municipios == ['Igaporã']


def test_coordenadas_sem_lat():
    [ponto] = unica(SEM_LAT_822).usos[0].pontos
    assert ponto.coordenada.latitude == '10°53’48,5”S'
    assert ponto.identificacao == 'poço 4'
    assert ponto.ponto == 'POINT(-40.6854167 -10.8968056)'


def test_aspas_repetidas_no_fim_da_latitude():
    [ponto] = unica(ASPAS_REPETIDAS_517).usos[0].pontos
    assert ponto.coordenada.latitude == '18°01’11,79”S”'
    assert ponto.ponto == 'POINT(-39.8543861 -18.0199417)'


def test_duas_portarias_no_mesmo_ato_viram_duas_outorgas():
    resposta = extrair_pela_regex(DUAS_PORTARIAS_24350)
    assert [o.nro_portaria for o in resposta.outorgas] == ['18324', '18325']
    assert [o.nro_processo for o in resposta.outorgas] == [
        '2018.001.004971/INEMA/LIC-04971',
        '2018.001.005165/INEMA/LIC-05165',
    ]
    # "no poço 2, nas coordenadas ..." e "; e no poço 3": um uso por portaria.
    assert [
        [p.identificacao for uso in o.usos for p in uso.pontos]
        for o in resposta.outorgas
    ] == [['poço 2', 'poço 3'], ['poço 4', 'poço 9']]
    assert resposta.outorgas[1].outorgado.nome == 'ROMEU FRANCIOSI'


def test_varios_municipios_e_finalidades():
    [uso] = unica(VARIOS_MUNICIPIOS_534).usos
    assert uso.municipios == ['Mucuri', 'Nova Viçosa']
    assert uso.finalidades == ['irrigacao', 'pulverizacao_agricola']
    assert uso.area_ha == 45


def test_vazao_malformada_fica_para_o_modelo():
    resposta = extrair_pela_regex(VAZAO_MALFORMADA_15493)
    [outorga] = resposta.outorgas
    [uso] = outorga.usos
    assert uso.nro_portaria_prazo == '6504'
    assert uso.area_ha == 1396.9
    assert uso.pontos[0].vazao_m3_dia is None
    assert campos_vazios(resposta) == [
        'outorgas.0.usos.0.pontos.0.vazao_m3_dia',
        'outorgas.0.usos.0.pontos.0.vazao_m3_s',
    ]
    sede = outorga.outorgado.endereco
    assert (sede.localidade, sede.rodovia, sede.municipio) == (
        'Fazenda Renascer',
        'Rod. BR 349',
        'Correntina',
    )


def test_numero_colado_no_logradouro():
    sede = unica(NUMERO_NO_LOGRADOURO_5492).outorgado.endereco
    assert (sede.logradouro, sede.numero, sede.bairro) == (
        'Rua Torquato Bahia',
        '3',
        'Comércio',
    )


def test_sem_documento_nao_acha_o_outorgado():
    texto = CAPTACAO_SUBTERRANEA_1156.replace(
        ', inscrito no CPF n°\r\n246.713.205-68', ''
    )
    resposta = extrair_pela_regex(texto)
    assert resposta.outorgas[0].outorgado is None
    assert 'outorgas.0.outorgado' in campos_vazios(resposta)


def test_nome_sem_conectivo_em_minusculas_nao_e_nome():
    texto = SEM_CONECTIVO_601.replace('ALEX FAZOLLO SOSSAI', 'Alex Fazollo Sossai')
    assert unica(texto).outorgado is None


def _sem(caminho: str):
    """Esvazia o campo do caminho (``usos.0.bacia_hidrografica``) na outorga 0."""

    def esvaziar(outorga):
        *pais, nome = caminho.split('.')
        objeto = outorga
        for parte in pais:
            objeto = objeto[int(parte)] if parte.isdigit() else getattr(objeto, parte)
        vazio = [] if isinstance(getattr(objeto, nome), list) else None
        setattr(objeto, nome, vazio)

    return esvaziar


def _sem_prazo(outorga):
    for nome in ('prazo_validade_anos', 'dt_validade', 'nro_portaria_prazo'):
        setattr(outorga.usos[0], nome, None)


USO = 'outorgas.0.usos.0'
PONTO = f'{USO}.pontos.0'


@pytest.mark.parametrize(
    'esvaziar, esperado',
    [
        (_sem('nro_processo'), ['outorgas.0.nro_processo']),
        (_sem('nro_processo_relacionado'), ['outorgas.0.nro_processo_relacionado']),
        (_sem('outorgado'), ['outorgas.0.outorgado']),
        (
            _sem('outorgado.nro_documento'),
            [
                'outorgas.0.outorgado.tipo_documento',
                'outorgas.0.outorgado.nro_documento',
            ],
        ),
        (_sem('usos'), ['outorgas.0.usos']),
        (_sem('usos.0.bacia_hidrografica'), [f'{USO}.bacia_hidrografica']),
        (
            _sem('usos.0.finalidade_texto'),
            [
                f'{USO}.finalidade_texto',
                f'{USO}.finalidades',
                f'{USO}.metodos_irrigacao',
            ],
        ),
        (_sem('usos.0.municipios'), [f'{USO}.municipios']),
        (
            _sem_prazo,
            [
                f'{USO}.prazo_validade_anos',
                f'{USO}.dt_validade',
                f'{USO}.nro_portaria_prazo',
                f'{USO}.dt_publicacao_portaria_prazo',
            ],
        ),
        (_sem('usos.0.pontos'), [f'{USO}.pontos']),
        (_sem('usos.0.pontos.0.coordenada'), [f'{PONTO}.coordenada']),
        (
            _sem('usos.0.pontos.0.vazao_m3_dia'),
            [f'{PONTO}.vazao_m3_dia', f'{PONTO}.vazao_m3_s'],
        ),
    ],
)
def test_campos_vazios_de_cada_campo_obrigatorio(esvaziar, esperado):
    # Alteração: o processo relacionado também é obrigatório.
    resposta = extrair_pela_regex(ALTERACAO_26019)
    assert campos_vazios(resposta) == []
    esvaziar(resposta.outorgas[0])
    assert campos_vazios(resposta) == esperado


def test_processo_relacionado_so_e_obrigatorio_na_alteracao_e_na_ampliacao():
    resposta = extrair_pela_regex(CAPTACAO_SUBTERRANEA_1156)
    assert resposta.outorgas[0].nro_processo_relacionado is None
    assert campos_vazios(resposta) == []


def test_horas_por_dia_so_sao_obrigatorias_na_captacao():
    resposta = extrair_pela_regex(LANCAMENTO_24493)
    resposta.outorgas[0].usos[0].pontos[0].captacao_horas_dia = None
    assert campos_vazios(resposta) == []


def test_finalidade_vazia_nao_tem_categoria():
    assert classificar_finalidade(None) == ([], [])
    assert classificar_finalidade('  ') == ([], [])


@pytest.mark.parametrize(
    'texto, tipo',
    [
        ('canalização (e/ou) retificação de canal', 'canalizacao'),
        ('construção de ponte', 'travessia'),
        ('aproveitamento hidrelétrico', 'aproveitamento_hidreletrico'),
        ('extração de areia', 'extracao_mineral_dragagem'),
        ('regularização de barramento existente', 'regularizacao_barramento'),
        ('construção de barragem', 'construcao_barramento'),
        ('captação de água', 'outro'),
    ],
)
def test_classificar_intervencao(texto, tipo):
    assert classificar_intervencao(texto) == tipo


def test_parametro_sem_numero_nao_tem_valor_numerico():
    parametro = ParametroEfluente(nome='DBO', valor='ausente', unidade='mg/L')
    assert parametro.valor_numero is None


def test_modo_e_o_primeiro_campo_de_cada_uso():
    """O modelo gera na ordem do esquema: resposta cortada ainda tem o discriminador."""
    esquema = ExtracaoOutorga.model_json_schema()['$defs']
    for uso in ('UsoCaptacao', 'UsoLancamento', 'UsoIntervencao'):
        assert next(iter(esquema[uso]['properties'])) == 'modo'


def test_finalidades_e_metodos_tem_limite_no_esquema():
    propriedades = ExtracaoOutorga.model_json_schema()['$defs']['UsoCaptacao'][
        'properties'
    ]
    assert propriedades['finalidades']['maxItems'] == len(FINALIDADES)
    assert propriedades['metodos_irrigacao']['maxItems'] == len(METODOS_IRRIGACAO)


def test_finalidades_e_metodos_repetidos_viram_um():
    """Laço do modelo no ato 14706: as repetições não passam do limite do campo."""
    dados = extrair_pela_regex(LANCAMENTO_24493).model_dump()
    uso = dados['outorgas'][0]['usos'][0]
    uso['finalidades'] = ['abastecimento_humano', 'abastecimento_industrial'] * 50
    uso['metodos_irrigacao'] = ['gotejamento'] * 20
    uso = ExtracaoOutorga.model_validate(dados).outorgas[0].usos[0]
    assert uso.finalidades == ['abastecimento_humano', 'abastecimento_industrial']
    assert uso.metodos_irrigacao == ['gotejamento']


def test_intervencoes_no_plural_e_bacias_no_plural():
    outorga = unica(INTERVENCOES_INTEGRADAS_5557)
    usos = outorga.usos
    assert [uso.modo for uso in usos] == ['intervencao'] * 5
    # O tipo vem da finalidade: "Riacho da Areia" não é extração de areia.
    assert [uso.tipo_intervencao for uso in usos] == [
        'construcao_barramento',
        'construcao_barramento',
        'canalizacao',
        'canalizacao',
        'extracao_mineral_dragagem',
    ]
    assert {uso.bacia_hidrografica for uso in usos} == {'Rios Joanes e Ipitanga'}
    # Cada canal fica com o par de início e o de fim, mesmo com o par malformado.
    assert [len(uso.pontos) for uso in usos] == [2] * 5
    caji = usos[2]
    assert caji.pontos[0].coordenada.latitude == '12°52"44.9"S'
    assert caji.pontos[1].coordenada.latitude == '12°53’28.5"S'
    assert usos[1].volume_maximo_acumulacao_m3 == 560_662.6
    assert usos[1].vazao_minima_jusante_m3_s == 6.7
    # Sem vazão nem horas por dia cobradas: o modelo não é chamado.
    assert campos_vazios(extrair_pela_regex(INTERVENCOES_INTEGRADAS_5557)) == []


@pytest.mark.parametrize(
    'trecho, bacia',
    [
        (
            'nas Bacias Hidrográficas dos Rios Itanhém, Jucuruçu, Mucuri e Peruípe, '
            'no Ponto B5',
            'Rios Itanhém, Jucuruçu, Mucuri e Peruípe',
        ),
        (
            'nas Bacias Hidrográficas do Riacho Doce e dos Rios Alcobaça, Mucuri, '
            'Peruípe, no Ponto B2',
            'Riacho Doce e dos Rios Alcobaça, Mucuri, Peruípe',
        ),
        # No singular a vírgula continua fechando a bacia.
        ('na Bacia Hidrográfica do Rio de Contas, no Rio Gongoji', 'Rio de Contas'),
    ],
)
def test_bacia_no_plural_e_uma_lista(trecho, bacia):
    texto = INTERVENCOES_INTEGRADAS_5557.replace(
        'nas Bacias Hidrográficas dos Rios Joanes e Ipitanga,', trecho + ','
    )
    assert unica(texto).usos[0].bacia_hidrografica == bacia
