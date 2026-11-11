import importlib.util
from pathlib import Path

import pytest

from diario_oficial.tipo_ato import TipoAto, compilar_catalogo, extrair_tipos_ato

LO = TipoAto(1, 'Licença de Operação', 'LO')
RLO = TipoAto(2, 'Renovação de Licença de Operação', 'RLO')
LP = TipoAto(3, 'Licença Prévia', 'LP')
LI = TipoAto(4, 'Licença de Instalação', 'LI')
PPV_LI = TipoAto(
    5, 'Prorrogação de Prazo de Validade de Licença de Instalação', 'PPV/LI'
)
ASV = TipoAto(6, 'Autorização de Supressão de Vegetação', 'ASV')
OUT = TipoAto(7, 'Outorga de uso de recurso hídrico', 'OUT')
LS_SEM_SIGLA = TipoAto(
    8, 'Prorrogação do Prazo de Validade de Licença Simplificada', None
)
LS_COM_SIGLA = TipoAto(
    9, 'Prorrogação do Prazo de Validade da Licença Simplificada', 'PPV/LS'
)
CANCELAMENTO = TipoAto(10, 'Cancelamento, Revogação ou Suspensão de Portarias', None)
RENOVACAO_LIC = TipoAto(11, 'RENOVAÇÃO DE LICENCIAMENTOS', None)

CATALOGO = compilar_catalogo(
    [
        LO,
        RLO,
        LP,
        LI,
        PPV_LI,
        ASV,
        OUT,
        LS_SEM_SIGLA,
        LS_COM_SIGLA,
        CANCELAMENTO,
        RENOVACAO_LIC,
    ]
)


@pytest.mark.parametrize(
    'texto, esperado',
    [
        ('Art. 1º - Conceder Licença de Operação à empresa', [LO.id]),
        ('Art. 1º - Conceder AUTORIZAÇÃO DE SUPRESSÃO DA VEGETAÇÃO', [ASV.id]),
        ('Conceder\r\n  Licença\n\nPrévia à empresa', [LP.id]),
        ('Conceder OUTORGA DE DIREITO DE USO DE RECURSOS HÍDRICOS', [OUT.id]),
        ('CANCELAMENTO, REVOGAÇÃO OU SUSPENSÃO DE PORTARIAS', [CANCELAMENTO.id]),
        ('Renovação de Licenciamento', [RENOVACAO_LIC.id]),
    ],
)
def test_reconhece_variacoes_do_nome(texto, esperado):
    assert extrair_tipos_ato(texto, CATALOGO) == esperado


def test_ato_com_mais_de_um_tipo():
    texto = 'Conceder Licença Prévia e Licença de Instalação. Conceder Licença Prévia.'
    assert extrair_tipos_ato(texto, CATALOGO) == [LP.id, LI.id]


def test_nome_mais_longo_nao_conta_tambem_o_contido():
    assert extrair_tipos_ato('Renovação de Licença de Operação', CATALOGO) == [RLO.id]


def test_nomes_iguais_depois_de_normalizados_contam_uma_vez_com_a_sigla():
    texto = 'Prorrogação do Prazo de Validade de Licença Simplificada'
    assert extrair_tipos_ato(texto, CATALOGO) == [LS_COM_SIGLA.id]


def test_citacao_de_ato_anterior_nao_conta():
    texto = 'previsto na Licença Prévia concedida por meio da Resolução CEPRAM nº 3293'
    assert extrair_tipos_ato(texto, CATALOGO) == []


def test_tipo_derivado_seguido_de_participio_conta():
    texto = 'Prorrogação de Prazo de Validade de Licença de Instalação concedida pela Portaria'
    assert extrair_tipos_ato(texto, CATALOGO) == [PPV_LI.id]


def test_sigla_em_numero_de_processo_nao_conta():
    assert extrair_tipos_ato('Processo 2003-005693/TEC/LO-0052 (LO)', CATALOGO) == []


@pytest.mark.parametrize('texto', [None, '', 'PORTARIA Nº 35.468 sem tipo nenhum'])
def test_texto_sem_tipo(texto):
    assert extrair_tipos_ato(texto, CATALOGO) == []


# Catálogo com a lista real da migração, para os tipos novos (autos de infração,
# notificações, denúncia, emergência e termos) concorrerem com todos os nomes do domínio.
# Os ids seguem a ordem de inserção, como o serial do banco faria.
def _carregar_tipos_da_migracao():
    caminho = (
        Path(__file__).parents[1]
        / 'migrations/versions/4e8a2f6b1c37_criando_tipo_ato_e_ato_tipo_ato.py'
    )
    spec = importlib.util.spec_from_file_location('migracao_tipo_ato', caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return [
        TipoAto(indice, nome, sigla)
        for indice, (nome, sigla) in enumerate(modulo.TIPOS_ATO, start=1)
    ]


TIPOS_DOMINIO = _carregar_tipos_da_migracao()
ID_POR_NOME = {tipo.nome: tipo.id for tipo in TIPOS_DOMINIO}
CATALOGO_DOMINIO = compilar_catalogo(TIPOS_DOMINIO)


def _nomes(texto):
    nome_por_id = {tipo.id: tipo.nome for tipo in TIPOS_DOMINIO}
    return [nome_por_id[i] for i in extrair_tipos_ato(texto, CATALOGO_DOMINIO)]


@pytest.mark.parametrize(
    'texto, esperado',
    [
        ('Lavrar AUTO DE INFRAÇÃO DE MULTA no valor', 'Auto de Infração de Multa'),
        ('Auto de Infração de Advertência', 'Auto de Infração de Advertência'),
        ('AUTOS DE INFRAÇÃO DE INTERDIÇÃO', 'Auto de Infração de Interdição'),
        ('Auto de Infração de Apreensão', 'Auto de Infração de Apreensão'),
        ('auto de infração de embargo', 'Auto de Infração de Embargo'),
        ('Auto de Infração de Demolição', 'Auto de Infração de Demolição'),
        (
            'AUTO DE INFRAÇÃO DE DESTRUIÇÃO DE FORNOS PARA PRODUÇÃO DE CARVÃO VEGETAL',
            'Auto de Infração de Destruição de Fornos para Produção de Carvão Vegetal',
        ),
        (
            'Auto de Infração de Destruição ou Inutilização de Produtos',
            'Auto de Infração de Destruição ou Inutilização de Produtos',
        ),
        ('NOTIFICAÇÃO nº 123/2023', 'Notificação'),
        ('NOTIFICAÇÃO DE COMUNICAÇÃO', 'Notificação de Comunicação'),
        ('Notificação de Homologação', 'Notificação de Homologação'),
        ('Denúncias', 'Denúncia'),
        ('EMERGÊNCIA AMBIENTAL', 'Emergência Ambiental'),
        ('AUTORIZAÇÃO PARA MANEJO DE FAUNA', 'Autorização de Manejo de Fauna'),
        ('Autorização de Manejo de Fauna', 'Autorização de Manejo de Fauna'),
        ('Termo de Compromisso', 'Termo de Compromisso'),
        (
            'TERMO DE COMPROMISSO DE RESPONSABILIDADE AMBIENTAL',
            'Termo de Compromisso de Responsabilidade Ambiental',
        ),
    ],
)
def test_reconhece_tipos_novos(texto, esperado):
    assert _nomes(texto) == [esperado]


OUTORGA = 'Outorga de Direito de Uso de Recurso Hídrico'
ALTERACAO_DE_OUTORGA = 'Alteração de Outorga de Direito de Uso de Recurso Hídrico'
RENOVACAO_DE_OUTORGA = 'Renovação de Outorga de Direito de Uso de Recurso Hídrico'
PRORROGACAO_DE_OUTORGA = 'Prorrogação do Prazo de Validade de Outorga'


@pytest.mark.parametrize(
    'texto, esperado',
    [
        (
            'Art. 1º - Autorizar o direito de uso dos recursos hídricos, em favor de',
            OUTORGA,
        ),
        ('AUTORIZAR O DIREITO DE USO DE RECURSO HÍDRICO', OUTORGA),
        ('Conceder OUTORGA DE DIREITO DE USO DE RECURSOS HÍDRICOS', OUTORGA),
        (
            'Art. 1º - Autorizar a alteração do direito de uso dos recursos '
            'hídricos, em favor de',
            ALTERACAO_DE_OUTORGA,
        ),
        (
            'AUTORIZAR A ALTERAÇÃO DO DIREITO DE USO DE RECURSO HÍDRICO',
            ALTERACAO_DE_OUTORGA,
        ),
        (
            'Conceder ALTERAÇÃO DE OUTORGA DE DIREITO DE USO DE RECURSOS HÍDRICOS',
            ALTERACAO_DE_OUTORGA,
        ),
        (
            'Art. 1º - Autorizar a renovação do direito de uso dos recursos '
            'hídricos, em favor de',
            RENOVACAO_DE_OUTORGA,
        ),
        (
            'AUTORIZAR A RENOVAÇÃO DO DIREITO DE USO DE RECURSO HÍDRICO',
            RENOVACAO_DE_OUTORGA,
        ),
        (
            'Conceder RENOVAÇÃO DE OUTORGA DE DIREITO DE USO DE RECURSOS HÍDRICOS',
            RENOVACAO_DE_OUTORGA,
        ),
        (
            'Conceder PRORROGAÇÃO DO PRAZO DE VALIDADE, por 02 (dois) anos a partir '
            'da data do vencimento, da Outorga de direito de uso da água, concedida '
            'mediante Portaria INEMA nº 6323',
            PRORROGACAO_DE_OUTORGA,
        ),
        (
            'Conceder PRORROGAÇÃO DO PRAZO DE VALIDADE por 1 (um) ano, a partir da '
            'data do vencimento da Outorga de direito de uso da água',
            PRORROGACAO_DE_OUTORGA,
        ),
        (
            'Conceder PRORROGAÇÃO DO PRAZO DE VALIDADE, por 10 anos a partir da data '
            'do vencimento, da Outorga de direito de uso da água',
            PRORROGACAO_DE_OUTORGA,
        ),
        (
            'Conceder Prorrogação do Prazo de Validade de Outorga',
            PRORROGACAO_DE_OUTORGA,
        ),
    ],
)
def test_outorga_e_alteracao_de_outorga_pelo_nome_ou_pelo_sinonimo(texto, esperado):
    assert _nomes(texto) == [esperado]


@pytest.mark.parametrize(
    'texto, curto',
    [
        ('Notificação de Comunicação', 'Notificação'),
        ('Notificação de Homologação', 'Notificação'),
        (
            'Termo de Compromisso de Responsabilidade Ambiental',
            'Termo de Compromisso',
        ),
    ],
)
def test_tipo_novo_mais_longo_nao_conta_o_contido(texto, curto):
    assert ID_POR_NOME[curto] not in extrair_tipos_ato(texto, CATALOGO_DOMINIO)


def test_auto_de_infracao_sem_modalidade_nao_conta():
    # Nenhum tipo do domínio é só "Auto de Infração" ou só "Destruição"
    assert _nomes('Auto de Infração de Destruição nº 123') == []


@pytest.mark.parametrize(
    'texto',
    [
        'Processo 2023-001073/TEC/AIMU-0081',
        'Processo 2022-004321/TEC/NOTC-0012 (NOT)',
        'Processo 2021-000111/TEC/TCRA-0003',
    ],
)
def test_sigla_dos_tipos_novos_em_numero_de_processo_nao_conta(texto):
    assert _nomes(texto) == []


def test_notificacao_citada_como_ato_anterior_nao_conta():
    assert _nomes('em atendimento à Notificação emitida em 10/01/2023') == []


def test_auto_de_infracao_junto_com_outro_tipo():
    texto = (
        'Lavrar Auto de Infração de Multa e Auto de Infração de Embargo, '
        'e firmar Termo de Compromisso.'
    )
    assert _nomes(texto) == [
        'Auto de Infração de Multa',
        'Auto de Infração de Embargo',
        'Termo de Compromisso',
    ]


def test_renovacao_de_outorga_nao_requerida_nao_conta_outorga():
    texto = (
        'Auto de Infração de Multa, por ter sido constatado que o interessado não '
        'requereu renovação da outorga do direito do uso da água dentro do prazo '
        'legal, conforme estabelecido na Portaria INEMA nº 11.292 de 13/02/2016, '
        'Art. 28 (O pedido de renovação de outorga de direito de uso de recursos '
        'hídricos deverá ser protocolizado junto ao INEMA). Art. 18 - Ficam sujeitos '
        'a outorga de direito de uso de recursos hídricos'
    )
    assert _nomes(texto) == ['Auto de Infração de Multa']


def test_outorga_sem_a_citacao_de_renovacao_continua_contando():
    texto = 'O pedido de renovação de outorga de direito de uso de recursos hídricos'
    assert _nomes(texto) == [
        'Renovação de Outorga de Direito de Uso de Recurso Hídrico'
    ]


@pytest.mark.parametrize(
    'texto',
    [
        'poço tubular sem a devida outorga de direito de uso do recurso hídrico',
        'captação de água sem a respectiva Outorga de Direito de Uso de Recursos Hídricos',
        'rio São Francisco sem dispensa ou outorga de direito de uso de recurso hídrico',
        'supressão de vegetação nativa sem Autorização Ambiental',
        'manter pássaros sem a devida Autorização de Manejo de Fauna',
    ],
)
def test_tipo_precedido_de_sem_nao_conta(texto):
    assert _nomes(texto) == []


def test_tipo_precedido_de_sem_nao_esconde_o_ato_publicado():
    texto = (
        'Conceder Autorização Ambiental à empresa, que operava sem a devida '
        'outorga de direito de uso do recurso hídrico'
    )
    assert _nomes(texto) == ['Autorização Ambiental']
