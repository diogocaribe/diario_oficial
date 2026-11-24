from langchain_core.runnables import RunnableLambda

from functools import partial

from diario_oficial.extracao import auto_infracao
from diario_oficial.extracao.auto_infracao import INTERDICAO
from diario_oficial.extracao.base import achados, extrair
from diario_oficial.extracao.registro import EXTRACOES
from diario_oficial.extracao.utils_geo import (
    grau_decimal,
    metro_utm,
    utm_para_lon_lat,
)
from diario_oficial.extracao.modelo_auto_infracao import (
    AutoInterdicao,
    ExtracaoInterdicao,
)
from diario_oficial.extracao.modelo_comum import (
    CoordenadaGeografica,
    Endereco,
    Pessoa,
)
from diario_oficial.extracao.normalizacao import (
    normalizar_texto,
    normalizar_cep,
    normalizar_data,
    normalizar_hora,
    normalizar_municipio,
    normalizar_processo,
    normalizar_sistema_referencia,
)

# As funções de auto_infracao presas ao subtipo de interdição.
separar_trechos = partial(auto_infracao.separar_trechos, INTERDICAO)
campos_por_regex = partial(auto_infracao.campos_por_regex, INTERDICAO)
conferir = partial(auto_infracao.conferir, INTERDICAO)
preencher_vazios_pela_regex = partial(
    auto_infracao.preencher_vazios_pela_regex, INTERDICAO
)
EXTRACAO = auto_infracao.EXTRACOES['AIIN']

# Edital real (2019-08-08) reduzido: um AIIN entre um AIAD e um AIIN.
EDITAL = """EDITAL
DE NOTIFICAÇÃO

O INSTITUTO DO MEIO AMBIENTE E RECURSOS HÍDRICOS - INEMA, através da sua Diretora Geral,
FAZ SABER a todos ... aos
Autuados: ASSOCIAÇÃO DO ABATEDOURO MUNICIPAL SÃO FRANCISCO DE ASSIS, CNPJ
nº 04.710.537/0001-04 nos autos do processo administrativo nº.
2017-009301/TEC/AIIN-0222, em 01/04/2019, foi
homologado o Auto de Infração de Interdição Temporária, "por
promover funcionamento de matadouro sem a necessária licença ambiental. A infração foi
constatada no município de Paulo Afonso, em 02/08/2017."; MACHADO E SOUZA LTDA,
CNPJ nº. 13.826.474/0001-39 nos autos do processo administrativo nº.
2011-013177/TEC/AIAD-0174, em 09/05/2019, foi homologado o Auto
de Infração de Advertência, "por realizar suas atividades sem a devida licença
ambiental."; HERMANDO JOSE DOS SANTOS, CPF nº 440.804.685-04 nos autos do processo
administrativo nº 2013-002246/TEC/AIIN-0029, em 08/03/2016, foi homologado o Auto de
Infração de Interdição Definitiva​, "por operar na extração de minério sem a devida
licença ambiental."
"""

RESOLUCAO = (
    'RESOLUÇÃO Nº 4436 DE 27 DE NOVEMBRO DE 2015 - O CEPRAM, tendo em vista o que '
    'consta do Processo Administrativo nº 2008-017747/TEC/AIIN-0132, RESOLVE: Art. 1º '
    '- Indeferir recurso interposto contra Auto de Infração de Interdição Temporária '
    'imposto pelo INEMA, a JOSE CARLOS DE LACERDA, CPF nº. 009.704.925-53.'
)


def _endereco(**campos) -> Endereco:
    padrao = dict.fromkeys(Endereco.model_fields)
    return Endereco(**{**padrao, **campos})


def _auto(**campos) -> AutoInterdicao:
    padrao = dict(
        nro_processo='2017-009301/TEC/AIIN-0222',
        natureza='homologacao',
        resultado_recurso=None,
        nro_ato_decisorio=None,
        autuado=Pessoa(
            nome='ASSOCIAÇÃO DO ABATEDOURO MUNICIPAL SÃO FRANCISCO DE ASSIS',
            tipo_documento='CNPJ',
            nro_documento='04.710.537/0001-04',
            endereco=None,
        ),
        dt_homologacao='2019-04-01',
        modalidade='temporaria',
        conduta='funcionamento de matadouro sem licença',
        atividade_interditada='matadouro',
        instrumento_ausente='licença ambiental',
        local_infracao=_endereco(municipio='Paulo Afonso'),
        dt_constatacao='2017-08-02',
        hr_constatacao=None,
        coordenada=[],
        sistema_referencia_espacial=None,
        area_hectare=None,
        excecao_interdicao=None,
        condicao=None,
        gravidade=None,
        nro_lacre=[],
        especie_citada=[],
    )
    return AutoInterdicao(**{**padrao, **campos})


def test_normalizar_tira_espaco_de_largura_zero_e_quebras():
    assert normalizar_texto('Definitiva​,\n "por') == 'Definitiva, "por'


def test_edital_vira_um_trecho_por_aiin_sem_os_outros_autos():
    trechos = separar_trechos(EDITAL)

    assert len(trechos) == 2
    assert trechos[0].startswith('ASSOCIAÇÃO DO ABATEDOURO')
    assert 'AIIN-0222' in trechos[0] and 'AIAD' not in trechos[0]
    assert trechos[1].startswith('HERMANDO JOSE DOS SANTOS')
    assert 'AIIN-0029' in trechos[1]


def test_texto_sem_estrutura_de_edital_vai_inteiro():
    assert separar_trechos(RESOLUCAO) == [normalizar_texto(RESOLUCAO)]


def test_texto_sem_aiin_nao_gera_trecho():
    assert separar_trechos('PORTARIA Nº 1 - Conceder Licença de Operação.') == []


def test_aiin_so_citado_em_auto_de_multa_nao_gera_trecho():
    texto = (
        'Autuado: FULANO, CPF nº 012.219.575-20 nos autos do processo administrativo '
        'nº 2012-016854/TEC/AIMU-0587, com a Penalidade de Multa "pelo descumprimento '
        'do Auto de Infração de Interdição nº 2012-004541/TEC/AIIN-0020".'
    )
    assert separar_trechos(texto) == []


def test_campos_por_regex_do_trecho():
    trechos = separar_trechos(EDITAL)

    assert campos_por_regex(trechos[0]) == {
        'modalidade': 'temporaria',
        'tipo_documento': 'CNPJ',
        'nro_documento': '04.710.537/0001-04',
        'dt_homologacao': '2019-04-01',
        'resultado_recurso': None,
        'nro_ato_decisorio': None,
        'sistema_referencia_espacial': None,
        'nro_lacre': None,
    }
    assert campos_por_regex(trechos[1])['modalidade'] == 'definitiva'


def test_conferir_aponta_divergencia_faltante_e_inesperado():
    trecho = separar_trechos(EDITAL)[0]

    certo = conferir(trecho, ExtracaoInterdicao(auto=[_auto()]))
    assert certo == {
        'faltantes': [],
        'inesperados': [],
        'processo_pelo_modelo': [],
        'data_corrigida_pelo_modelo': [],
        'divergencias': {},
    }

    modalidade_errada = conferir(
        trecho, ExtracaoInterdicao(auto=[_auto(modalidade='definitiva')])
    )
    assert modalidade_errada['divergencias'] == {
        'modalidade': ['definitiva', 'temporaria']
    }

    processo_errado = conferir(
        trecho,
        ExtracaoInterdicao(auto=[_auto(nro_processo='2017-009301/TEC/AIIN-0223')]),
    )
    assert processo_errado['faltantes'] == ['2017-009301/TEC/AIIN-0222']
    assert processo_errado['inesperados'] == ['2017-009301/TEC/AIIN-0223']


def test_heranca_e_esquema_do_modelo():
    esquema = ExtracaoInterdicao.model_json_schema()['$defs']
    assert {'AutoInterdicao', 'Pessoa', 'Endereco', 'CoordenadaGeografica'} <= set(
        esquema
    )
    assert 'modalidade' not in esquema['Pessoa']['properties']
    propriedades = esquema['AutoInterdicao']['properties']
    assert 'qtd_dia_prazo' not in propriedades
    for campo in (
        'resultado_recurso',
        'nro_ato_decisorio',
        'excecao_interdicao',
        'sistema_referencia_espacial',
        'nro_lacre',
        'especie_citada',
    ):
        assert campo in propriedades
    # Calculados pelo código: o modelo não recebe nem preenche.
    assert 'ponto' not in propriedades and 'poligono' not in propriedades
    assert 'conduta' not in esquema['AutoInterdicao']['required'] or (
        propriedades['conduta']['anyOf'][1]['type'] == 'null'
    )


def test_ponto_e_poligono_a_partir_das_coordenadas():
    auto = _auto(
        coordenada=[
            _par('S -12,20388º', 'W - 41,75649º', 'ponto'),
            _par('-13.07824', '-41.82780', 'vertice'),
            _par('-13.07848', '-41.82843', 'vertice'),
            # x e y invertidos no texto, como no ato 11799
            _par('x -41,82833', 'y -13,07867', 'vertice'),
        ]
    )

    dados = auto.model_dump()
    assert dados['ponto'] == 'POINT(-41.75649 -12.20388)'
    assert dados['poligono'] == (
        'POLYGON((-41.8278 -13.07824, -41.82843 -13.07848, '
        '-41.82833 -13.07867, -41.8278 -13.07824))'
    )


def test_menos_de_tres_vertices_nao_gera_poligono():
    utm = _par('0494359', '8405671', 'ponto')
    dois_vertices = [
        _par('-13.07', '-41.82', 'vertice'),
        _par('-13.08', '-41.83', 'vertice'),
    ]

    auto = _auto(coordenada=[utm, *dois_vertices])

    assert auto.poligono is None
    # O UTM sem fuso usa os pares em graus do auto como referência (fuso 24).
    assert auto.ponto.startswith('POINT(-39.05')


def test_grau_decimal_le_os_formatos_dos_textos():
    assert grau_decimal('-10°11’58,7”') == 10 + 11 / 60 + 58.7 / 3600
    assert grau_decimal('Lat.: S 12.40082°') == 12.40082
    assert grau_decimal('-44. 56615') == 44.56615
    assert grau_decimal('W -39.,47628º') == 39.47628
    assert grau_decimal('8405671') is None
    assert grau_decimal('') is None


def test_datas_no_padrao_do_banco():
    assert normalizar_data('2019-04-01') == '2019-04-01'
    assert normalizar_data('01/04/2019') == '2019-04-01'
    assert normalizar_data('06.12.18') == '2018-12-06'
    assert normalizar_data('3/6/14') == '2014-06-03'
    assert normalizar_data('27/05/215') is None
    assert normalizar_data('31/02/2020') is None
    assert normalizar_data(None) is None


def test_validadores_corrigem_a_saida_do_modelo():
    auto = _auto(
        nro_processo='2012 004565 / TEC/AIIN-0022',
        dt_homologacao='25/08/2022',
        dt_constatacao='aos cinco dias',
        sistema_referencia_espacial='Sirgas2000',
    )

    assert auto.nro_processo == '2012-004565/TEC/AIIN-0022'
    assert auto.dt_homologacao == '2022-08-25'
    assert auto.dt_constatacao is None
    assert auto.sistema_referencia_espacial == 'SIRGAS 2000'
    assert normalizar_sistema_referencia('DATUM SAD 69') == 'SAD 69'
    assert normalizar_sistema_referencia('WGS-84') == 'WGS 84'
    assert (
        normalizar_sistema_referencia('datum SIRGAS 200') == 'SIRGAS 2000'
    )  # ato 10519


def test_normalizar_processo():
    assert (
        normalizar_processo('2023-007869 /TEC/AIIN-0184') == '2023-007869/TEC/AIIN-0184'
    )
    assert (
        normalizar_processo('2014.009708/TEC/AIIN-0170') == '2014-009708/TEC/AIIN-0170'
    )
    assert normalizar_processo('20142013- 003335/ TEC/AIIN-0060') is None
    assert normalizar_processo(None) is None


def _edital(*autuados: str) -> str:
    return 'EDITAL DE NOTIFICAÇÃO ... aos Autuados: ' + ' '.join(autuados)


MULTA = (
    'FULANO, CPF nº 012.219.575-20, nos autos do processo administrativo nº '
    '2012-016854/TEC/AIMU-0587, com a Penalidade de Multa "pela infração.";'
)


def test_processo_fora_do_padrao_nao_tira_o_aiin_da_extracao():
    casos = {
        # ato 10089: espaço no lugar do hífen
        'espaco': 'nos autos do processo administrativo nº 2012 004565/TEC/AIIN-0022 em',
        # ato 30276: espaço antes da barra
        'barra': 'nos autos do processo administrativo nº 2023-007869 /TEC/AIIN-0184, em',
        # ato 25675: ano com dígitos a mais
        'ano': 'nos autos do processo administrativo nº. 20142013- 003335/ TEC/AIIN-0060,',
        # ato 10297: sem "nº"
        'sem_no': 'nos autos do processo administrativo 2022-009694/TEC/AIIN-0213, com a',
    }
    for nome, trecho in casos.items():
        texto = _edital(MULTA, f'BELTRANO, CPF nº 1, {trecho} Interdição "por x".')
        trechos = separar_trechos(texto)
        assert len(trechos) == 1, nome
        assert trechos[0].startswith('BELTRANO'), nome


def test_processo_sem_numero_entra_pela_penalidade():
    # ato 14361: o texto não traz o número
    interdicao = (
        'BELTRANO, CPF nº 1, nos autos do processo administrativo nº , em 02/09/2022, '
        'foi homologado o Auto de Infração de INTERDIÇÃO TEMPORÁRIA, "por corte".'
    )
    embargo = (
        'CICRANO, CPF nº 2, nos autos do processo administrativo nº , em 02/09/2022, '
        'foi homologado o Auto de Infração de Interdição EMBARGO TEMPORÁRIO, "obra".'
    )

    trechos = separar_trechos(_edital(MULTA, interdicao, embargo))

    assert len(trechos) == 1
    assert trechos[0].startswith('BELTRANO')


def test_conferir_aceita_processo_corrigido_pelo_modelo():
    trecho = (
        'BELTRANO, nos autos do processo administrativo nº. 20142013- 003335/ '
        'TEC/AIIN-0060, em 28/03/2019, foi homologado o Auto de Infração de Interdição'
    )

    resultado = conferir(
        trecho,
        ExtracaoInterdicao(auto=[_auto(nro_processo='2014-003335/TEC/AIIN-0060')]),
    )

    assert resultado['inesperados'] == []
    assert resultado['processo_pelo_modelo'] == ['2014-003335/TEC/AIIN-0060']


def test_campos_por_regex_da_resolucao_e_do_lacre():
    campos = campos_por_regex(normalizar_texto(RESOLUCAO))
    assert campos['resultado_recurso'] == 'indeferido'
    assert campos['nro_ato_decisorio'] == '4436'

    deferida = campos_por_regex(
        'RESOLUÇÃO Nº 5.192, DE 26 DE ABRIL DE 2024 ... Art. 1º - Deferir o recurso'
    )
    assert deferida['resultado_recurso'] == 'deferido'
    assert deferida['nro_ato_decisorio'] == '5.192'

    lacrado = campos_por_regex(
        'a bomba foi lacrada com os lacres de N° 0029256. Lacre N° 0029770. '
        'Coordenadas Datum Sirgas 2000.'
    )
    assert lacrado['nro_lacre'] == ['0029256', '0029770']
    assert lacrado['sistema_referencia_espacial'] == 'SIRGAS 2000'


def test_conferir_le_o_documento_do_autuado():
    trecho = separar_trechos(EDITAL)[0]
    autuado = Pessoa(nome='X', tipo_documento='CPF', nro_documento='1', endereco=None)

    resultado = conferir(trecho, ExtracaoInterdicao(auto=[_auto(autuado=autuado)]))

    assert resultado['divergencias'] == {
        'tipo_documento': ['CPF', 'CNPJ'],
        'nro_documento': ['1', '04.710.537/0001-04'],
    }


def test_extrair_chama_o_modelo_por_trecho_e_guarda_erro():
    chamadas = []

    def modelo_falso(entrada):
        chamadas.append(entrada['trecho'])
        if 'HERMANDO' in entrada['trecho']:
            raise ValueError('JSON fora do esquema')
        return ExtracaoInterdicao(auto=[_auto()])

    resultados = extrair(EDITAL, EXTRACAO, RunnableLambda(modelo_falso))

    assert len(chamadas) == 2
    registro = resultados[0]['registros'][0]
    assert registro['nro_processo'] == '2017-009301/TEC/AIIN-0222'
    assert resultados[0]['conferencia']['faltantes'] == []
    assert resultados[1]['registros'] == []
    assert 'JSON fora do esquema' in resultados[1]['erro']


def test_validadores_limpam_o_lixo_do_modelo():
    vazio = _par('', '', 'vertice')
    auto = _auto(
        sistema_referencia_espacial='Zona Rural',
        hr_constatacao='11h00min',
        nro_lacre=['95 lascas', '2015-08-19', 'Lacre N° 0029770', '0029770'],
        coordenada=[vazio],
    )

    assert auto.sistema_referencia_espacial is None
    assert auto.hr_constatacao == '11:00'
    assert auto.nro_lacre == ['0029770']
    assert auto.coordenada == []
    assert normalizar_hora('14: 47hs') == '14:47'
    assert normalizar_hora('9h') == '09:00'
    assert normalizar_hora('por volta das quinze horas') is None


def _par(latitude, longitude, tipo='ponto', fuso_utm=None):
    return CoordenadaGeografica(
        latitude=latitude, longitude=longitude, tipo=tipo, fuso_utm=fuso_utm
    )


def test_utm_com_fuso_informado_vira_ponto_e_poligono():
    # ato 32059: UTM (24L), Serra Grande, Uruçuca
    auto = _auto(
        coordenada=[
            _par('8405671', '0494359', 'vertice'),
            _par('8405884', '0494349', 'vertice'),
            _par('8405881', '0494269', 'vertice'),
            _par('latitude 0494359', 'longitude 8405671', 'ponto', '24L'),
        ]
    )

    lon, lat = (float(v) for v in auto.ponto[6:-1].split())
    assert -39.06 < lon < -39.04 and -14.43 < lat < -14.41
    assert auto.poligono.startswith('POLYGON((-39.05')


def test_utm_sem_fuso_usa_o_unico_fuso_dentro_da_bahia():
    # ato 12979: X 249723 cai fora da Bahia no fuso 23, então é fuso 24
    auto = _auto(
        sistema_referencia_espacial='SIRGAS 2000',
        coordenada=[
            _par('Y8599194.221', 'X - 249723.819', 'vertice'),
            _par('Y - 8599246.885', 'X - 249659.127', 'vertice'),
            _par('Y - 8599069.663', 'X - 249617.764', 'vertice'),
        ],
    )

    assert auto.poligono is not None
    assert auto.poligono.startswith('POLYGON((-41.3')


def test_utm_sem_fuso_ambiguo_usa_o_par_em_graus_ou_desiste():
    # ato 10519 (São Desidério): os dois fusos caem na Bahia
    vertices = [
        _par('8608374', '438129', 'vertice'),
        _par('8608380', '438226', 'vertice'),
        _par('8608330', '438229', 'vertice'),
    ]
    assert _auto(coordenada=vertices).poligono is None

    com_referencia = _auto(coordenada=[*vertices, _par('-12.62', '-45.58')])
    assert com_referencia.poligono.startswith('POLYGON((-45.5')


def test_conversao_utm_e_leitura_dos_metros():
    assert metro_utm('Y8599194.221') == 8599194.221
    assert metro_utm('0494359') == 494359.0
    assert metro_utm('-12.60074') is None
    assert utm_para_lon_lat(494359, 8405671, 23, None) is not None
    assert utm_para_lon_lat(249723, 8599194, 23, 'SAD 69') is None  # fora da Bahia
    assert utm_para_lon_lat(494359, 8405671, 22, None) is None  # fuso fora da Bahia
    sad = utm_para_lon_lat(494359, 8405671, 24, 'SAD 69')
    sirgas = utm_para_lon_lat(494359, 8405671, 24, 'SIRGAS 2000')
    assert sad != sirgas


def test_conferir_marca_data_com_erro_de_digitacao():
    trecho = (
        'FULANO, nos autos do processo administrativo nº 2015-013428/TEC/AIIN-0308, '
        'em 02/09/2020, foi homologado o Auto de Infração de INTERDIÇÃO TEMPORÁRIA, '
        '"constatada às 09h:15min do dia 27/05/215, no dia 21/08/2014º."'
    )

    resultado = conferir(
        trecho,
        ExtracaoInterdicao(
            auto=[
                _auto(
                    nro_processo='2015-013428/TEC/AIIN-0308',
                    dt_homologacao='2020-09-02',
                )
            ]
        ),
    )

    assert resultado['data_corrigida_pelo_modelo'] == ['27/05/215', '21/08/2014º']


def test_criar_extrator_usa_parametros_contra_alucinacao():
    # Monta a cadeia sem chamar o Ollama.
    chat = EXTRACAO.criar_extrator(top_k=5).steps[1].bound

    assert chat.temperature == 0.0
    assert chat.repeat_penalty == 1.0
    assert chat.top_k == 5
    assert chat.top_p == 0.5
    assert chat.seed == 42
    assert chat.num_predict == 6144
    assert chat.model == 'qwen3:14b'
    assert chat.reasoning is False


def test_lacre_e_datum_fora_do_lugar():
    auto = _auto(
        nro_lacre=['2014-010923/TEC/AIIN-0215', 'lacres nº 0029734 e 0029735'],
        coordenada=[_par('249723.819', '8599194.221', 'vertice', 'DATUM SIRGAS 2000')],
    )

    assert auto.nro_lacre == ['0029734', '0029735']
    assert auto.sistema_referencia_espacial == 'SIRGAS 2000'
    assert auto.coordenada[0].fuso() is None
    assert _par('1', '1', fuso_utm='24L').fuso() == 24
    assert _par('1', '1', fuso_utm='Zona 23').fuso() == 23


def test_conferir_marca_lacre_que_o_texto_nao_cita():
    trecho = separar_trechos(EDITAL)[0]

    resultado = conferir(
        trecho, ExtracaoInterdicao(auto=[_auto(nro_lacre=['0029770'])])
    )

    assert resultado['divergencias'] == {'nro_lacre': [['0029770'], None]}


def test_normalizar_cep():
    assert normalizar_cep('44.380-000') == '44380-000'
    assert normalizar_cep('44380000') == '44380-000'
    assert normalizar_cep('4438-000') is None
    assert normalizar_cep(None) is None


def test_endereco_obriga_todos_os_campos_no_esquema():
    esquema = Endereco.model_json_schema()
    assert set(esquema['required']) == set(Endereco.model_fields)
    assert 'local' not in esquema['properties']
    endereco = _endereco(localidade='Fazenda Boa Vista', cep='44.380-000')
    assert endereco.cep == '44380-000'
    assert endereco.municipio is None


def test_normalizar_municipio_so_aceita_municipio_da_bahia():
    assert normalizar_municipio('Paulo Afonso') == 'Paulo Afonso'
    assert normalizar_municipio('PAULO AFONSO/BA') == 'Paulo Afonso'
    assert normalizar_municipio('Pilão Arcado - BA') == 'Pilão Arcado'
    assert normalizar_municipio('Município de Feira de Santana, Bahia') == (
        'Feira de Santana'
    )
    assert normalizar_municipio('sao felix do coribe') == 'São Félix do Coribe'
    assert normalizar_municipio('Dias D’Ávila') == "Dias d'Ávila"
    assert normalizar_municipio('BA') is None
    assert normalizar_municipio('Bahia') is None
    assert normalizar_municipio('Zona Rural') is None
    assert normalizar_municipio(None) is None


def test_endereco_troca_uf_por_null_no_municipio():
    assert _endereco(municipio='BA').municipio is None
    assert _endereco(municipio='barreiras/ba').municipio == 'Barreiras'


def test_localidade_igual_ao_municipio_e_descartada():
    endereco = _endereco(localidade='BARREIRAS/BA', municipio='Barreiras')
    assert endereco.localidade is None
    assert endereco.municipio == 'Barreiras'


def test_localidade_com_nome_de_municipio_vai_para_municipio():
    endereco = _endereco(localidade='Município de Barreiras')
    assert endereco.localidade is None
    assert endereco.municipio == 'Barreiras'


def test_localidade_que_nao_e_so_o_municipio_fica():
    endereco = _endereco(localidade='Zona rural de Barreiras', municipio='Barreiras')
    assert endereco.localidade == 'Zona rural de Barreiras'
    homonimo = _endereco(localidade='Bonito', municipio='Utinga')
    assert homonimo.localidade == 'Bonito'
    assert homonimo.municipio == 'Utinga'


def test_aiin_registrado_pela_sigla_com_a_pasta_portarias():
    assert EXTRACOES['AIIN'] is EXTRACAO
    assert EXTRACAO.pasta == 'Portarias'


def test_extracao_sem_corte_nem_conferencia_manda_o_texto_inteiro():
    from diario_oficial.extracao.base import Extracao

    extracao = Extracao(
        sigla_tipo_ato='XX',
        pasta=None,
        esquema=ExtracaoInterdicao,
        instrucoes='',
        campo_registros='auto',
    )
    chamadas = []

    def modelo_falso(entrada):
        chamadas.append(entrada['trecho'])
        return ExtracaoInterdicao(auto=[])

    resultados = extrair(' texto\n do  ato ', extracao, RunnableLambda(modelo_falso))

    assert chamadas == ['texto do ato']
    assert resultados == [
        {
            'trecho': 'texto do ato',
            'registros': [],
            'modelos': [],
            'preenchido_pela_regex': [],
            'preenchido_pelo_modelo': [],
        }
    ]
    assert extrair(None, extracao, RunnableLambda(modelo_falso)) == []


def test_regex_preenche_a_modalidade_que_o_modelo_deixou_vazia():
    trecho = separar_trechos(EDITAL)[0]
    resposta = ExtracaoInterdicao(auto=[_auto(modalidade=None)])

    assert preencher_vazios_pela_regex(trecho, resposta) == ['modalidade']
    assert resposta.auto[0].modalidade == 'temporaria'


def test_regex_nao_troca_a_modalidade_que_o_modelo_preencheu():
    trecho = separar_trechos(EDITAL)[0]
    resposta = ExtracaoInterdicao(auto=[_auto(modalidade='definitiva')])

    assert preencher_vazios_pela_regex(trecho, resposta) == []
    assert resposta.auto[0].modalidade == 'definitiva'
    assert conferir(trecho, resposta)['divergencias'] == {
        'modalidade': ['definitiva', 'temporaria']
    }


def test_regex_nao_preenche_trecho_com_varios_autos():
    resposta = ExtracaoInterdicao(auto=[_auto(modalidade=None), _auto(modalidade=None)])

    assert preencher_vazios_pela_regex(EDITAL, resposta) == []
    assert [auto.modalidade for auto in resposta.auto] == [None, None]


def test_extrair_preenche_pela_regex_antes_de_conferir():
    resultados = extrair(
        EDITAL,
        EXTRACAO,
        RunnableLambda(lambda _: ExtracaoInterdicao(auto=[_auto(modalidade=None)])),
    )

    assert resultados[0]['preenchido_pela_regex'] == ['modalidade']
    assert resultados[0]['registros'][0]['modalidade'] == 'temporaria'
    assert 'modalidade' not in resultados[0]['conferencia']['divergencias']


def test_achados_deixa_so_o_que_aponta_problema():
    conferencia = {
        'faltantes': [],
        'inesperados': ['2017-009301/TEC/AIIN-0223'],
        'divergencias': {},
    }
    assert achados(conferencia) == {'inesperados': ['2017-009301/TEC/AIIN-0223']}
    assert achados(None) == {}
