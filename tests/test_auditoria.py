"""Testes das regras da auditoria, com textos no formato real do DOE.

Uma regra só deve reprovar diante de evidência de separação errada.
"""

from datetime import date

import pytest

from diario_oficial.auditoria import (
    Achado,
    Edicao,
    Publicacao,
    RelatorioDia,
    auditar_edicao,
    linhas_de_log,
)
from tests.apoio import (
    DANILO,
    MARCIA,
    PREAMBULO_RESOLVE,
    SIGNATARIOS,
    TOPAZIO,
    ato,
    publicacao,
    regras,
)


def portaria(numero='35.468', assinatura=TOPAZIO):
    return ato(f'PORTARIA\xa0Nº\xa0{numero} DE 05 DE OUTUBRO DE 2026.\r\n', assinatura)


def test_ato_bem_separado_nao_gera_achado():
    assert regras(publicacao([portaria()])) == []


@pytest.mark.parametrize(
    'fim',
    [
        *SIGNATARIOS,
        'EDUARDO FARIAS TOPÁZIO. Diretor Geral',
        'EDUARDO FARIAS TOPÁZIO - Diretor Geral]',
        'ASS.: EDUARDO FARIAS TOPÁZIO - DIRETOR GERAL.',
        'EDUARDO SODRÉ MARTINS\nSecretário\r\ndo Meio Ambiente',
        'EDUARDO SODRÉ MARTINS SECRETÁRIO DO MEIO AMBIENTE DO ESTADO DA BAHIA - SEMA',
        'Eduardo Topázio. Diretor Geral do Instituto do Meio Ambiente - INEMA.',
        'EDUARDO SODRÉ MARTINS Secretário do Meio Ambiente EDUARDO TOPÁZIO Diretor Geral',
        'Eduardo Martins (Compromitente) Tainá de Andrade (Compromissária)',
        'Renato Pêgas Paes da Cunha Vice-Coordenação CERBMA-BA',
        f'{MARCIA}. PROCESSO SEI: 046.13122.2026.0024261-83.',
        f'{TOPAZIO} ANEXO I 046.2782.2026.0029195-48 Floriano Soto SEMA 2021/2026',
        f'{DANILO} ANEXO I Abaixo de 06 pontos Sem direito à GAC no período',
    ],
)
def test_qualquer_forma_de_assinatura_e_aprovada(fim):
    assert (
        regras(publicacao([ato('PORTARIA Nº 058 DE 06 DE OUTUBRO DE 2026', fim)])) == []
    )


@pytest.mark.parametrize(
    'titulo',
    [
        'PORTARIA N° 058 DE 06 DE OUTUBRO DE 2026',
        'PORTARIA N.º 050 DE 28 DE AGOSTO DE 2026.',
        'PORTARIA SEMA/FERHBA N° N° 058 DE 14 DE OUTUBRO DE 2026',
        'PORTARIA N° 35.483/2026',
        'Portaria Nº 01128013 de 09 de Outubro de 2026',
        'RESOLUÇÃO Nº 5.436, DE 01 DE SETEMBRO DE 2026',
        'EDITAL DE NOTIFICAÇÃO',
        'EDITAL INTERESSE',
        'EDITAL SEMA/FERFA Nº 001/2026',
        'CONVOCAÇÃO PARA AUDIÊNCIA PÚBLICA',
        'EXTRATO DE TERMO DE COMPROMISSO SOCIOAMBIENTAL',
        'O DIRETOR GERAL DO INEMA, nos termos da Lei: DECIDE PORTARIA N° 35.483/2026',
        'ADICIONAL POR TEMPO DE SERVIÇO - ARTIGO 84 DA LEI N° 6.677/1994',
    ],
)
def test_formas_reais_de_titulo(titulo):
    assert regras(publicacao([ato(titulo, MARCIA)])) == []


@pytest.mark.parametrize(
    'fim', ['Todos nomeados pela', 'Art. 6º - Esta Portaria entrará']
)
def test_ato_cortado_no_meio_da_frase(fim):
    texto = ato('PORTARIA Nº 35.508 DE 09 DE OUTUBRO DE 2026.', fim)
    assert regras(publicacao([texto])) == ['ATO_CORTADO']


def test_inicio_sem_numero_e_sinal_de_citacao():
    assert 'INICIO_SEM_TITULO' in regras(
        publicacao([ato('PORTARIA conjunta.', DANILO)])
    )


@pytest.mark.parametrize('assinatura', SIGNATARIOS)
@pytest.mark.parametrize(
    'seguinte',
    [
        'INSTRUÇÃO NORMATIVA Nº 35.507 DE 09 DE OUTUBRO DE 2026.',
        'ORTARIA Nº 35.375 DE 22 DE SETEMBRO DE 2026.',
        'Retificação da PORTARIA Nº 35.068 publicada no D.O.E de 08/08/2026.',
        'ERRATA do EDITAL DE NOTIFICAÇÃO, publicado no D.O.E de 10/07/2025',
        'O DIRETOR GERAL DO INSTITUTO DO MEIO AMBIENTE, no uso de suas atribuições',
        'A DIRETORA GERAL DO INSTITUTO DO MEIO AMBIENTE, no uso de suas atribuições',
        'RETIFICAÇÃO da Resolução Nº 2',
        'ADICIONAL POR TEMPO DE SERVIÇO - ARTIGO 84 DA LEI N° 6.677/1994',
    ],
)
def test_outro_ato_depois_da_assinatura(seguinte, assinatura):
    texto = f'{ato("EDITAL DE NOTIFICAÇÃO", assinatura)} {ato(seguinte, assinatura)}'
    assert regras(publicacao([texto])) == ['ATOS_JUNTOS']


def test_cargo_citado_no_corpo_nao_e_assinatura():
    titulo = (
        'EDITAL DE NOTIFICAÇÃO O INEMA, através do seu Diretor Geral, nos termos do '
        'art. 261.'
    )
    assert regras(publicacao([ato(titulo, MARCIA)])) == []


@pytest.mark.parametrize(
    'texto',
    [
        'ERRATA DA INSTRUÇÃO NORMATIVA publicada no D.O.E de 10.10.2026',
        'TORNA SEM EFEITO Torna sem efeito a Portaria nº 058, de 6 de outubro de 2026.',
        'PORTARIA Nº 34.095/2025. EDUARDO FARIAS TOPÁZIO -\r\nDiretor Geral',
    ],
)
def test_tamanho_do_ato_nao_e_criterio(texto):
    assert regras(publicacao([texto])) == []


def test_texto_antes_do_primeiro_ato():
    texto = portaria()
    conteudo = f'COMUNICADO O INEMA informa o cronograma. {texto}'
    assert regras(publicacao([texto], conteudo=conteudo)) == ['TEXTO_FORA_DOS_ATOS']


def test_espaco_em_branco_entre_atos_nao_e_texto_perdido():
    textos = [portaria('1'), portaria('2')]
    conteudo = f'\r\n \xa0{textos[0]}\n\n\xa0{textos[1]}\r\n'
    assert regras(publicacao(textos, conteudo=conteudo)) == []


def test_ato_que_nao_esta_no_texto():
    assert 'ATO_FORA_DO_TEXTO' in regras(
        publicacao([portaria()], conteudo='Outro texto')
    )


def test_ato_repetido_no_proprio_doe_e_aprovado():
    # Caso real: a Resolução 5.436 foi publicada duas vezes no mesmo texto
    assert regras(publicacao([portaria(), portaria()])) == []


def test_linha_gravada_a_mais_e_detectada():
    pub = publicacao([portaria(), portaria()], conteudo=portaria())
    assert regras(pub) == ['ATO_FORA_DO_TEXTO']


def test_nome_da_publicacao_nao_e_criterio():
    # Casos reais: o nome é texto livre e pode ter erro de digitação
    for nome in ['#1 - PORTARIAS 35.217 a 35.329', '#1 - 08 EDITAIS E PORTARIA 1.000']:
        assert regras(publicacao([portaria()], nome)) == []


@pytest.mark.parametrize('conteudo', [None, '', ' \r\n '])
def test_conteudo_nao_coletado(conteudo):
    pub = Publicacao(1, 'nome', conteudo, None)
    assert regras(pub) == ['CONTEUDO_NAO_COLETADO']


def test_texto_sem_nenhum_ato():
    pub = Publicacao(1, 'nome', 'TERMO DE APOSTILAMENTO DA RESOLUÇÃO FERFA.', True)
    assert regras(pub) == ['SEM_ATOS']


def test_atos_gravados_em_publicacao_nao_marcada():
    assert regras(publicacao([portaria()], processada=None)) == [
        'PROCESSAMENTO_PARCIAL'
    ]


def test_resultado_por_publicacao():
    aprovada = publicacao([portaria()])
    reprovada = Publicacao(2, 'nome', 'Texto sem ato', None)
    edicao = Edicao(date(2026, 10, 6), True, True, [aprovada, reprovada])
    assert auditar_edicao(edicao).resultado_publicacoes == {1: True, 2: False}


def test_achados_separados_por_publicacao_e_edicao():
    aprovada = publicacao([portaria()])
    reprovada = Publicacao(2, 'nome', 'Texto sem ato', None)
    edicao = Edicao(date(2026, 10, 6), True, None, [aprovada, reprovada])
    relatorio = auditar_edicao(edicao)

    assert relatorio.achados_da_publicacao(1) == []
    assert [a.regra for a in relatorio.achados_da_publicacao(2)] == ['SEM_ATOS']
    assert [a.regra for a in relatorio.achados_da_publicacao(None)] == [
        'EDICAO_NAO_TRANSFORMADA'
    ]


def test_linhas_de_log_de_ato_e_de_publicacao():
    edicao = Edicao(date(2026, 10, 6), True, True, id=7)
    achados = [
        Achado('ATO_CORTADO', 'descrição do ato', 2, 30, 'fim do ato'),
        Achado('SEM_ATOS', 'descrição da publicação', 3),
    ]
    assert linhas_de_log(RelatorioDia(edicao, achados)) == [
        {
            'etapa': 'auditoria',
            'tipo': 'ATO_CORTADO',
            'descricao': 'descrição do ato',
            'trecho': 'fim do ato',
            'doe_bruto_id': 7,
            'publicacao_id': 2,
            'ato_id': 30,
        },
        {
            'etapa': 'auditoria',
            'tipo': 'SEM_ATOS',
            'descricao': 'descrição da publicação',
            'trecho': None,
            'doe_bruto_id': 7,
            'publicacao_id': 3,
            'ato_id': None,
        },
    ]


def test_linhas_de_log_de_achado_da_edicao():
    edicao = Edicao(date(2026, 10, 11), True, None, id=7)
    [linha] = linhas_de_log(auditar_edicao(edicao))
    assert linha['tipo'] == 'EDICAO_NAO_TRANSFORMADA'
    assert linha['doe_bruto_id'] == 7
    assert linha['publicacao_id'] is None


def test_edicao_nao_transformada():
    assert regras(transformada=None) == ['EDICAO_NAO_TRANSFORMADA']


@pytest.mark.parametrize('existe', [False, True])
def test_edicao_sem_conteudo_e_aprovada(existe):
    edicao = Edicao(date(2026, 10, 11), existe, True)
    assert auditar_edicao(edicao).aprovada


def test_edicao_com_achado_e_reprovada():
    edicao = Edicao(date(2026, 10, 11), True, None)
    assert not auditar_edicao(edicao).aprovada


def test_texto_fora_dos_atos_alem_do_preambulo_e_detectado():
    texto = portaria()
    conteudo = f'{PREAMBULO_RESOLVE} COMUNICADO O INEMA informa. {texto}'
    assert regras(publicacao([texto], conteudo=conteudo)) == ['TEXTO_FORA_DOS_ATOS']


def test_edital_que_termina_em_site_nao_esta_cortado():
    texto = 'EDITAL DE INTIMAÇÃO COM PRAZO DE 05 DIAS. Site: www.inema.ba.gov.br'
    assert regras(publicacao([texto])) == []


def test_portaria_conjunta_com_muitos_orgaos_tem_titulo():
    orgaos = 'SEMA/INEMA/CMG/SSP/CBMBA/PCBA/PMBA/SUDEC/SESAB/BAHIATER/IBAMA'
    assert regras(publicacao([ato(f'PORTARIA CONJUNTA {orgaos} N° 01 DE 2024', MARCIA)])) == []


@pytest.mark.parametrize(
    'titulo',
    ['EDITAL DE NOTIFICAÇÃO', 'RESOLUÇÃO Nº 056/2024', 'EDITAL 001/2024', 'RESUMO'],
)
def test_ato_so_com_o_titulo_e_reprovado(titulo):
    assert 'ATO_SO_TITULO' in regras(publicacao([titulo]))


@pytest.mark.parametrize(
    'titulo',
    [
        'LICENÇA MÉDICA DEFERIDA PELA JUNTA MÉDICA',
        'APOSTILA Nº 01/2020',
        'RECOMENDAÇÃO CEPRAM Nº 02 DE 2021',
        'PRORROGAÇÃO DO CRONOGRAMA PARA ELEIÇÃO',
    ],
)
def test_titulo_novo_depois_de_assinatura_indica_atos_juntos(titulo):
    texto = f'{ato("PORTARIA Nº 35.468 DE 05 DE OUTUBRO DE 2026.", MARCIA)} {titulo} corpo'
    assert 'ATOS_JUNTOS' in regras(publicacao([texto]))


@pytest.mark.parametrize(
    'sobra',
    [
        'GOVERNO DO ESTADO DA BAHIA SECRETARIA DO MEIO AMBIENTE',
        'A DIRETORA GERAL, EM EXERCÍCIO, DO INSTITUTO, RESOLVE:',
        'O SECRETÁRIO DO MEIO AMBIENTE - SEMA, no uso de suas atribuições, RESOLVE:',
    ],
)
def test_sobra_esperada_nao_e_texto_fora_dos_atos(sobra):
    portaria = ato('PORTARIA Nº 35.468 DE 05 DE OUTUBRO DE 2026.', MARCIA)
    assert regras(publicacao([portaria], conteudo=f'{sobra}\n{portaria}')) == []
