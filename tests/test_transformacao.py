"""Testes de separar_ato, com textos no formato real do DOE.

Caminho real: o texto passa por separar_ato e o resultado passa pela auditoria. Uma
separação certa tem que ser produzida por separar_ato e aprovada pela auditoria.
"""

import pytest

from diario_oficial.transformacao import separar_ato
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


def separar_e_auditar(texto):
    atos = separar_ato(texto)
    assert regras(publicacao(atos, conteudo=texto)) == []
    return atos


@pytest.mark.parametrize('assinatura', SIGNATARIOS)
def test_varias_portarias(assinatura):
    texto = (
        f'\r\n{ato("PORTARIA Nº 35.468 DE 05 DE OUTUBRO DE 2026.", assinatura)}\r\n'
        f'{ato("PORTARIA Nº 35.469 DE 05 DE OUTUBRO DE 2026.", assinatura)}'
    )
    atos = separar_e_auditar(texto)
    assert len(atos) == 2
    assert atos[0].endswith(assinatura)
    assert atos[1].startswith('PORTARIA Nº 35.469')


@pytest.mark.parametrize(
    'titulo',
    [
        'Acordo de Cooperação Técnica n° 001/2020. Processo n° 027.1430.2020.0000154-85.',
        'Acordo de Cooperação n° 002/2020. Processo n° 027.1430.2019.0003118-30.',
        'RECOMENDAÇÃO Nº 06 DE 28 DE NOVEMBRO DE 2019.',
        'RECOMENDAÇÃO CEPRAM Nº 01, DE 06 DE NOVEMBRO DE 2020.',
        'SECRETARIA DO MEIO AMBIENTE - RESULTADO DE JULGAMENTO DO CHAMAMENTO PÚBLICO N°1',
        'Portaria Nº 21299 de 20 de Agosto de 2020',
        'LICENÇA TRATAMENTO DE SAÚDE DEFERIDA PELA JUNTA MÉDICA OFICIAL DO ESTADO',
        'TERMO DE INSTAURAÇÃO DE PROCESSO ADMINISTRATIVO',
        '(*)PORTARIA CONJUNTA SEMA/INEMA N° 04 DE 05 DE AGOSTO DE 2021.',
        '*PORTARIA Nº 20.386 DE 06 DE ABRIL DE 2020.',
        'INSTRUÇÃO NORMATIVA SEMA/INEMA Nº 01 DE 24 DE AGOSTO DE 2021.',
        'INSTRUÇÃO NORMATIVA CONJUNTA SEMA/INEMA Nº 01 DE 16 DE DEZEMBRO DE 2021.',
        'INSTRUÇÃO NORMATIVA SEMA Nº 003 DE 12 DE SETEMBRO DE 2023',
        'Instrução Normativa SEMA/INEMA Nº 15, de 27 de outubro de 2022.',
        'CONSELHO ESTADUAL DO MEIO AMBIENTE - CEPRAM. Errata da RESOLUÇÃO Nº 4.952.',
        'AVISO DE CHAMAMENTO PÚBLICO Nº 01/2022',
        'RESULTADO FINAL DO CHAMAMENTO PÚBLICO Nº 001/2021',
        'PRORROGAÇÃO DO CRONOGRAMA PARA ELEIÇÃO DOS MEMBROS DO COMITÊ',
        '2ª PRORROGAÇÃO DO CRONOGRAMA PARA ELEIÇÃO DOS MEMBROS DO COMITÊ',
        'CRONOGRAMA PROCESSO ELEITORAL APA DO RIO PRETO',
        'DELIBERAÇÃO Nº 002/2022 - RESULTADO DAS AVALIAÇÕES',
        'NOTIFICAÇÃO ADMINISTRATIVA',
        'COMUNICADO',
        'ERRATA referente ao processo nº 2021.001.001753/INEMA/LIC-01753',
        'A SECRETÁRIA DO MEIO AMBIENTE DO ESTADO DA BAHIA - SEMA, informa',
        'A SECRETARIA DO MEIO AMBIENTE DO ESTADO DA BAHIA, torna público',
        'AUTORIZAÇÃO A SECRETARIA DO MEIO AMBIENTE DO ESTADO torna público',
        'O SECRETÁRIO DO MEIO AMBIENTE e a DIRETORA GERAL DO INEMA, RESOLVEM atualizar',
    ],
)
def test_titulo_que_abre_a_publicacao_vira_ato(titulo):
    texto = ato(titulo, MARCIA)
    assert separar_e_auditar(texto) == [texto]


@pytest.mark.parametrize(
    'titulo',
    [
        'COMUNICADO O Instituto do Meio Ambiente',
        'TERMO DE INSTAURAÇÃO DE PROCESSO ADMINISTRATIVO',
        'TERMO DE ADESÃO E COMPROMISSO AO PROTOCOLO DE FISCALIZAÇÃO',
        'RECOMENDAÇÃO CEPRAM Nº 02 DE 01 DE DEZEMBRO DE 2021',
        '3ª PRORROGAÇÃO DO CRONOGRAMA PARA ELEIÇÃO',
        '(*) PORTARIA Nº 26.488 DE 13 DE JULHO DE 2022.',
        'ORTARIA Nº 26.614 DE 01 DE AGOSTO DE 2022.',
    ],
)
def test_titulo_depois_de_assinatura_abre_outro_ato(titulo):
    portaria = ato('PORTARIA Nº 35.468 DE 05 DE OUTUBRO DE 2026.', MARCIA)
    seguinte = ato(titulo, DANILO)
    assert separar_ato(f'{portaria}\r\n{seguinte}') == [portaria, seguinte]


@pytest.mark.parametrize(
    'corpo',
    [
        'Art. 1º - Conceder AUTORIZAÇÃO DE SUPRESSÃO DA VEGETAÇÃO',
        'função de Gestor, no âmbito do Acordo de Cooperação Técnica n° 003/2020',
        'A inscrição seguirá\nAUTORIZAÇÃO A SECRETARIA DO MEIO AMBIENTE',
    ],
)
def test_titulo_de_abertura_no_corpo_nao_inicia_ato(corpo):
    texto = f'PORTARIA Nº 35.468 DE 05 DE OUTUBRO DE 2026. {corpo}. {MARCIA}'
    assert separar_ato(texto) == [texto]


def test_cabecalho_autorizacao_nao_vira_ato_separado():
    aviso = ato('AVISO DE CONSULTA PÚBLICA A SECRETÁRIA torna público', DANILO)
    texto = f'AUTORIZAÇÃO SECRETARÍA DO MEIO AMBIENTE DO ESTADO DA BAHIA {aviso}'
    assert separar_ato(texto) == [aviso]


def test_citacao_de_portaria_nao_inicia_ato():
    texto = (
        'PORTARIA Nº 35.508 DE 09 DE OUTUBRO DE 2026. Todos nomeados pela\r\n'
        f'PORTARIA Nº 34.095/2025. {MARCIA}'
    )
    assert separar_e_auditar(texto) == [texto]


def test_instrucao_normativa_e_ato_proprio():
    edital = ato('EDITAL DE NOTIFICAÇÃO', MARCIA)
    instrucao = ato('INSTRUÇÃO NORMATIVA Nº 35.507 DE 09 DE OUTUBRO DE 2026.', DANILO)
    assert separar_e_auditar(f'{edital} {instrucao}') == [edital, instrucao]


def test_errata_nao_e_cortada_na_instrucao_citada():
    errata = (
        'ERRATA DA INSTRUÇÃO NORMATIVA publicada no D.O.E de 10.10.2026 Onde se Lê: '
        '"...INSTRUÇÃO NORMATIVA Nº 35.507 DE 09 DE OUTUBRO DE 2026." Leia-se: '
        '"...INSTRUÇÃO NORMATIVA Nº 002 DE 09 DE OUTUBRO DE 2026."'
    )
    seguinte = ato('PORTARIA Nº 35.520 DE 13 DE OUTUBRO DE 2026.', DANILO)
    assert separar_e_auditar(f'{errata}\n {seguinte}') == [errata, seguinte]


def test_errata_de_portaria_fica_no_ato():
    texto = (
        'ERRATA\nPORTARIA\r\nNº 33.951/2025, Publicada em DOE de 17 de Outubro de 2025: '
        'ONDE SE LÊ:\r\n(área meio)... LEIA-SE: (área meio das Coordenações) ... '
        'GABINETE DA DIRETORIA GERAL, em 26 de junho de 2026.\r\n'
        'Ass.: EDUARDO FARIAS TOPÁZIO - Diretor Geral'
    )
    assert separar_e_auditar(texto) == [texto]


def test_errata_seguida_de_minuscula_e_ato_proprio():
    edital = ato('EDITAL DE NOTIFICAÇÃO', TOPAZIO)
    errata = ato(
        'ERRATA\r\ndo EDITAL DE NOTIFICAÇÃO, publicado no D.O.E de 10/07/2025.', TOPAZIO
    )
    assert separar_e_auditar(f'{edital}\n\xa0\n{errata}') == [edital, errata]


def test_errata_citada_no_corpo_nao_inicia_ato():
    texto = ato(
        'PORTARIA Nº 1.234 DE 01 DE OUTUBRO DE 2026. Conforme a ERRATA da portaria.',
        DANILO,
    )
    assert separar_e_auditar(texto) == [texto]


def test_secretario_depois_do_titulo_fica_no_ato():
    texto = ato(
        'PORTARIA Nº 01 DE 06 DE JANEIRO DE 2016 - O\r\nSECRETÁRIO\r\nDO MEIO AMBIENTE, '
        'no uso de suas atribuições, RESOLVE:\r\n1. Designar ANA LÚCIA ANTUNES FARIA, '
        'Diretora\r\nAdministrativa, matrícula nº 27.578421-5.',
        DANILO,
    )
    assert separar_e_auditar(texto) == [texto]


def test_retificacao_em_caixa_normal_e_ato_proprio():
    edital = ato('EDITAL DE NOTIFICAÇÃO', TOPAZIO)
    retificacao = (
        'Retificação\r\nda PORTARIA Nº 35.068 publicada no D.O.E de 08/08/2026. '
        'Onde se lê: (...) LUCIANA DE JESUS FERREIRA... Leia-se:\r\n'
        '(...) LUCIANA DE JESUS OLIVEIRA...EDUARDO FARIAS TOPÁZIO - Diretor Geral'
    )
    texto = f'{edital}\n\xa0\n{retificacao}'
    assert separar_e_auditar(texto) == [edital, retificacao]


def test_retificacao_no_corpo_nao_inicia_ato():
    texto = ato(
        'PORTARIA Nº 1.234 DE 01 DE OUTUBRO DE 2026. Conceder\r\n'
        'retificação de curso d’água.',
        DANILO,
    )
    assert separar_e_auditar(texto) == [texto]


def test_preambulo_fica_no_ato():
    texto = (
        'O DIRETOR GERAL DO INSTITUTO DO MEIO AMBIENTE E RECURSOS HÍDRICOS - INEMA, nos '
        'termos da Lei Estadual nº 12.209/2011: DECIDE\r\n'
        f'PORTARIA N° 35.483/2026 Conforme o Relatório. {TOPAZIO}'
    )
    assert separar_e_auditar(texto) == [texto]


PREAMBULO_DECIDE = (
    'A\r\nDIRETORA GERAL DO INSTITUTO DO MEIO AMBIENTE E RECURSOS HÍDRICOS - INEMA, no '
    'uso de suas atribuições e nos termos do artigo 35\r\nda Lei Estadual nº '
    '12.209/2011, de 20 de abril de 2011, DECIDE: \n'
)


@pytest.mark.parametrize('preambulo', [PREAMBULO_RESOLVE, PREAMBULO_DECIDE])
def test_preambulo_da_diretora_fica_fora_dos_atos(preambulo):
    primeira = f'PORTARIA\r\nNº 19.897/2020 - Designar a servidora. Ass.: {MARCIA}'
    segunda = f'PORTARIA\r\nNº 19.898/2020 - Art. 1º - Instaurar. Ass.: {MARCIA}'
    texto = f'{preambulo}{primeira}\n{preambulo}{segunda}'
    assert separar_e_auditar(texto) == [primeira, segunda]


def test_preambulo_entre_as_portarias_19897_e_19898():
    # Caso real: o preâmbulo ficava colado no fim da portaria 19.897
    assinatura = (
        'GABINETE DA DIRETORIA\r\nGERAL, em 06 de janeiro de 2020. Ass.: MARCIA CRISTINA '
        'TELLES DE ARAÚJO\r\nLIMA - Diretora Geral'
    )
    primeira = (
        'PORTARIA\r\nNº 19.897/2020 - Nos termos dos\r\nartigos 204 e 205 da Lei nº '
        '6.677, de 26 de setembro de 1994, DESIGNAR a\r\nservidora AGHATA BARRETO XAVIER '
        '- matrícula n° 46.569.768-8, para compor a Comissão de Sindicância, designada '
        'através da Portaria nº 19.672/2019, a contar da data de publicação deste ato. '
        f'{assinatura}'
    )
    segunda = (
        'PORTARIA\r\nNº 19.898/2020 - Art. 1º - Em atenção\r\nà recomendação esposada no '
        'Parecer Jurídico nº 3511/2019, DECIDO\r\nPELA INSTAURAÇÃO DE SINDICÂNCIA. Art. '
        f'3º Esta\r\nPortaria entra em vigor na data de sua publicação.  {assinatura}'
    )
    texto = f'{primeira}\n{PREAMBULO_DECIDE}{segunda}'
    assert separar_e_auditar(texto) == [primeira, segunda]


def test_diretora_geral_fora_do_preambulo_fica_no_ato():
    texto = (
        'PORTARIA Nº 19.897/2020 - Publicar o que A DIRETORA GERAL DO INSTITUTO DECIDE: '
        f'conceder o prazo de 30 dias. {MARCIA}'
    )
    assert separar_e_auditar(texto) == [texto]


@pytest.mark.parametrize(
    'texto',
    [
        'AVISO DE\r\nCONSULTA PÚBLICA - RPPN',
        'TORNA SEM EFEITO Torna sem efeito a Portaria nº 058.',
    ],
)
def test_termos_de_mais_de_uma_palavra(texto):
    assert separar_e_auditar(texto) == [texto]


def test_portaria_do_rh_com_grau_em_vez_de_ordinal():
    texto = (
        'Portaria N° 00235030\r\nDE 08 de Outubro de 2020\nresolve nomear para o cargo '
        'em comissão Coordenador II, a partir de 08 de Outubro de 2020. '
        'MARCIA CRISTINA TELLES DE ARAUJO LIMA INST DO MEIO AMB E RECURSOS HÍDRICOS'
    )
    assert separar_e_auditar(texto) == [texto]


def test_decisao_so_inicia_ato_como_titulo():
    texto = (
        'DECISÃO\nO SECRETÁRIO DO MEIO AMBIENTE DO ESTADO DA BAHIA, no uso de suas '
        f'atribuições, DECIDE: manter a DECISÃO recorrida. {MARCIA}'
    )
    assert separar_e_auditar(texto) == [texto]


def test_mocao_e_ato_proprio():
    texto = (
        'MOÇÃO\r\nCERBMA-BA N° 01/2020. A Plenária resolve: Art.1° - Aprovar a\r\n'
        'Moção nº 01/2020. Art.2° - Cópia com inteiro teor da Moção estará disponível.'
    )
    assert separar_e_auditar(texto) == [texto]


def test_termo_de_apostilamento_nao_e_cortado_no_corpo():
    texto = (
        'TERMO\r\nDE APOSTILAMENTO DA RESOLUÇÃO FERFA Nº 077/2026\nO PRESIDENTE resolve '
        'lavrar o presente TERMO DE APOSTILAMENTO à\r\nResolução FERFA nº 077.'
    )
    assert separar_e_auditar(texto) == [texto]


def test_termo_de_compromisso_e_ato_proprio():
    # Caso real: publicação sem assinatura de cargo, que antes não gerava nenhum ato
    texto = (
        'TERMO\r\nDE COMPROMISSO PARA COMPENSAÇÃO AMBIENTAL Nº 007/2019\n\n \n\n'
        'PROCESSO DE LICENCIAMENTO AMBIENTAL Nº 2003-005693/TEC/LL-0052 E PROCESSO DE '
        'COMPENSAÇÃO AMBIENTAL Nº 1420130002288 PARTÍCIPES: SECRETARIA DO MEIO AMBIENTE '
        '- SEMA E NOLANDIS EMPREENDIMENTOS E PARTICIPAÇÕES LTDA, COM A INTERVENIÊNCIA DO '
        'INSTITUTO DO MEIO AMBIENTE E RECURSOS HÍDRICOS-INEMA. OBJETO: Termo de '
        'Compromisso, no valor de R$ 1.891.425,10 (um milhão, oitocentos e noventa e um '
        'mil, quatrocentos e vinte e cinco reais e dez centavos), visando o cumprimento, '
        'na modalidade indireta, por parte do EMPREENDEDOR, do art. 1º, VII, previsto na '
        'Licença Prévia concedida por meio da Resolução CEPRAM nº 3293, de 18 de junho '
        'de 2004, referente ao empreendimento denominado “Complexo Hoteleiro Iberostar”, '
        'com vigência de 36 (trinta e seis) meses, a partir da publicação do presente '
        'extrato. Data de Assinatura 23/01/2020 - João Carlos Oliveira da Silva.'
    )
    assert separar_e_auditar(texto) == [texto]


def test_tabela_de_adicional_por_tempo_de_servico_e_ato_proprio():
    # Caso real (publicação 174): tabela do RH, sem assinatura, que não gerava nenhum ato
    ato_tabela = (
        'ADICIONAL\r\n  POR TEMPO DE SERVIÇO - ARTIGO 84 DA LEI N° 6.677/1994\n\n\n\n\n'
        'MATRÍCULA\n\n\nNOME\n\n\nCONCESSÃO\n\n\nACUMULADO\n\n\nVIGÊNCIA\n\n\n\n\n'
        '17233893\n\n\nRosemar\r\n  Brito da Silva\n\n\n+1%\n\n\n38%\n\n\nMarco/2020'
    )
    texto = f'\n\n\n\n\n\n\n\n\n\n\n{ato_tabela}\n\n\n\n\xa0\n\n\n\n'
    assert separar_e_auditar(texto) == [ato_tabela]


def test_adicional_por_tempo_de_servico_no_corpo_nao_inicia_ato():
    texto = ato(
        'PORTARIA Nº 1.234 DE 01 DE OUTUBRO DE 2026. Conceder ADICIONAL POR TEMPO DE '
        'SERVIÇO à servidora.',
        DANILO,
    )
    assert separar_e_auditar(texto) == [texto]


def test_autorizacao_no_corpo_nao_inicia_ato():
    texto = (
        f'PORTARIA Nº 1.234 DE 01 DE OUTUBRO DE 2026. Conceder AUTORIZAÇÃO. {DANILO}'
    )
    assert separar_e_auditar(texto) == [texto]
