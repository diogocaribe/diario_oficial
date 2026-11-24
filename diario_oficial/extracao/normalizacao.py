"""Normalização dos valores que o texto ou o modelo escrevem de várias formas.

Cada função recebe o valor como veio e devolve o formato do banco, ou ``None`` se não
reconhecer o valor.
"""

import re
import unicodedata
from datetime import date

from diario_oficial.extracao.utils_geo import MUNICIPIOS_BA

# Número de processo de auto: ano, sequencial, /TEC/, tipo do auto e número do auto.
PROCESSO_NO_PADRAO = re.compile(r'(\d{4})[-.]?(\d+)/TEC/(AI[A-Z]{2})-?(\d+)')

# Datas como o modelo ou o texto costumam escrever: AAAA-MM-DD ou DD/MM/AAAA (com / . -)
DATA_ISO = re.compile(r'(\d{4})-(\d{1,2})-(\d{1,2})')
DATA_DIA_MES_ANO = re.compile(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4}|\d{2})')

SISTEMAS_DE_REFERENCIA = (
    (re.compile(r'SIRGAS\s*-?\s*2000?', re.IGNORECASE), 'SIRGAS 2000'),
    (re.compile(r'SAD\s*-?\s*69', re.IGNORECASE), 'SAD 69'),
    (re.compile(r'WGS\s*-?\s*84', re.IGNORECASE), 'WGS 84'),
    (re.compile(r'C[óo]rrego\s+Alegre', re.IGNORECASE), 'Córrego Alegre'),
)

HORA = re.compile(
    r'(?P<hora>\d{1,2})\s*(?::|h)\s*:?\s*(?P<minuto>\d{2})?', re.IGNORECASE
)


def normalizar_texto(texto: str | None) -> str:
    """Tira os espaços de largura zero e junta as quebras de linha num espaço só."""
    sem_invisiveis = re.sub(r'[​‌‍﻿]', '', texto or '')
    return re.sub(r'\s+', ' ', sem_invisiveis).strip()


def normalizar_processo(valor: str | None) -> str | None:
    """Escreve o número do processo como ``AAAA-NNNNNN/TEC/AIXX-NNNN``.

    Tira espaços e troca o ponto do ano por hífen. Devolve ``None`` se o valor, sem os
    espaços, não tem a forma de um processo (ex.: ``20142013-003335/TEC/AIIN-0060``).
    """
    if not valor:
        return None
    sem_espaco = re.sub(r'\s+', '', valor).upper()
    achado = PROCESSO_NO_PADRAO.fullmatch(sem_espaco)
    if achado is None:
        return None
    ano, sequencial, tipo, numero = achado.groups()
    return f'{ano}-{sequencial}/TEC/{tipo}-{numero}'


def normalizar_data(valor: str | None) -> str | None:
    """Data no padrão do banco (``AAAA-MM-DD``), ou ``None`` se não for uma data válida.

    Aceita ``AAAA-MM-DD`` e ``DD/MM/AAAA`` (com ``/``, ``.`` ou ``-``). Ano com dois
    dígitos vira 20AA: os autos da série são todos deste século.
    """
    if not valor:
        return None
    texto = valor.strip()
    if achado := DATA_ISO.fullmatch(texto):
        ano, mes, dia = (int(parte) for parte in achado.groups())
    elif achado := DATA_DIA_MES_ANO.fullmatch(texto):
        dia, mes, ano = (int(parte) for parte in achado.groups())
        if ano < 100:
            ano += 2000
    else:
        return None
    try:
        return date(ano, mes, dia).isoformat()
    except ValueError:
        return None


def normalizar_sistema_referencia(valor: str | None) -> str | None:
    """Nome padronizado do sistema de referência (ex.: ``SIRGAS2000`` -> ``SIRGAS 2000``).

    Valor que não é um sistema conhecido volta ``None``: o modelo às vezes põe aqui um
    trecho do endereço ("Zona Rural").
    """
    if not valor:
        return None
    for padrao, nome in SISTEMAS_DE_REFERENCIA:
        if padrao.search(valor):
            return nome
    return None


def normalizar_hora(valor: str | None) -> str | None:
    """Hora no formato ``HH:MM`` (``11h00min``, ``14:47hs``, ``9h`` -> ``09:00``)."""
    if not valor:
        return None
    achado = HORA.search(valor)
    if achado is None:
        return None
    hora, minuto = int(achado.group('hora')), int(achado.group('minuto') or 0)
    if hora > 23 or minuto > 59:
        return None
    return f'{hora:02d}:{minuto:02d}'


# Número no formato brasileiro (``1.000,00``; ``6,29``) ou com ponto decimal (``6.29``).
NUMERO_BR = re.compile(r'\d+(?:[.,]\d+)*')
MILHAR_COM_PONTO = re.compile(r'\d{1,3}(?:\.\d{3})+')


def normalizar_numero(valor: float | int | str | None) -> float | None:
    """Número de um valor em reais ou de uma quantidade escrita no texto.

    Aceita o formato brasileiro (``R$ 12.000,00`` -> 12000.0; ``6,29 ST`` -> 6.29) e o
    ponto decimal (``6.29`` -> 6.29). Sem vírgula, ponto seguido de três dígitos é
    milhar (``12.000`` -> 12000.0). Devolve ``None`` sem número.
    """
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, int | float):
        return float(valor)
    achado = NUMERO_BR.search(valor)
    if achado is None:
        return None
    numero = achado.group()
    if ',' in numero or MILHAR_COM_PONTO.fullmatch(numero) or numero.count('.') > 1:
        numero = numero.replace('.', '').replace(',', '.')
    return float(numero)


def normalizar_cep(valor: str | None) -> str | None:
    """CEP no formato ``NNNNN-NNN`` (``44.380-000`` -> ``44380-000``).

    Devolve ``None`` se o valor não tiver exatamente oito dígitos.
    """
    digitos = re.sub(r'\D', '', valor or '')
    return f'{digitos[:5]}-{digitos[5:]}' if len(digitos) == 8 else None


def normalizar_documento(tipo: str | None, numero: str | None) -> str | None:
    """Número do documento para identificar a pessoa no banco.

    CPF e CNPJ ficam só com os dígitos (``12.345.678/0001-90`` -> ``12345678000190``);
    os demais, sem os espaços das pontas. ``None`` se não sobrar nada.
    """
    if not numero or not numero.strip():
        return None
    if tipo in ('CPF', 'CNPJ'):
        return re.sub(r'\D', '', numero) or None
    return numero.strip()


def _chave_municipio(texto: str) -> str:
    """Nome sem acento, em minúsculas, com pontuação e espaços repetidos tirados."""
    sem_acento = unicodedata.normalize('NFKD', texto)
    sem_acento = ''.join(c for c in sem_acento if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^\w\s]', ' ', sem_acento.lower()).split())


# Grafias que o DOE usa para o nome oficial do IBGE (lidas nas outorgas).
VARIANTES_MUNICIPIO = {
    'Santa Cruz de Cabrália': 'Santa Cruz Cabrália',
    'Luiz Eduardo Magalhães': 'Luís Eduardo Magalhães',
    'Luis Eduardo Magalhães': 'Luís Eduardo Magalhães',
    'Santa Teresinha': 'Santa Terezinha',
    'Muquém de São Francisco': 'Muquém do São Francisco',
    'Santa Luz': 'Santaluz',
    'Conceição de Feira': 'Conceição da Feira',
    'Morro de Chapéu': 'Morro do Chapéu',
    'Mata do São João': 'Mata de São João',
    'Jequiriçá': 'Jiquiriçá',
    'Gentio de Ouro': 'Gentio do Ouro',
    'Caitité': 'Caetité',
    'América Dourado': 'América Dourada',
    'Carfanaum': 'Cafarnaum',
    'Senhor Bonfim': 'Senhor do Bonfim',
    'Vitória Conquista': 'Vitória da Conquista',
}

MUNICIPIO_POR_CHAVE = {_chave_municipio(nome): nome for nome in MUNICIPIOS_BA} | {
    _chave_municipio(variante): nome for variante, nome in VARIANTES_MUNICIPIO.items()
}

# Prefixos e a UF que o modelo ou o texto juntam ao nome (``Município de X/BA``,
# ``município do Salvador``, ``do Lapão``).
PREFIXO_MUNICIPIO = re.compile(r'^(?:(?:munic[ií]pio|cidade)\s+)?(?:de|do|da)\s+', re.I)
UF_NO_FIM = re.compile(r'\s*(?:[/,(-]|\s)\s*(?:BA|Bahia)\)?\s*$', re.I)


def normalizar_municipio(valor: str | None) -> str | None:
    """Nome oficial do município da Bahia, ou ``None`` se não for um dos 417.

    Ignora acentos, maiúsculas e pontuação, tira "Município de" e a UF no fim
    (``paulo afonso/ba`` -> ``Paulo Afonso``) e aceita as grafias de
    ``VARIANTES_MUNICIPIO`` (``Santa Luz`` -> ``Santaluz``). A UF sozinha ("BA", "Bahia") volta
    ``None``: é o erro mais comum do modelo neste campo.
    """
    if not valor:
        return None
    texto = valor.strip()
    sem_prefixo = PREFIXO_MUNICIPIO.sub('', texto)
    for candidato in (texto, sem_prefixo, UF_NO_FIM.sub('', sem_prefixo)):
        if nome := MUNICIPIO_POR_CHAVE.get(_chave_municipio(candidato)):
            return nome
    return None
