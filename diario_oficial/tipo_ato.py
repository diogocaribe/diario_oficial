"""Identifica quais tipos de ato (dominio.tipo_ato) aparecem no texto de um ato.

Módulo sem banco e sem efeito no import. Procura só pelo nome do tipo: as siglas não
servem, porque também aparecem nos números de processo (ex.: 2003-005693/TEC/LL-0052).
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, NamedTuple

# Palavras que variam entre o nome do domínio e o texto do DOE ("Supressão de Vegetação" e
# "SUPRESSÃO DA VEGETAÇÃO"; "Outorga de uso" e "Outorga de direito de uso").
CONECTIVOS = ('DE', 'DA', 'DO', 'DAS', 'DOS', 'A', 'AS', 'O', 'OS', 'DIREITO')
SEPARADOR = rf'(?: (?:{"|".join(CONECTIVOS)}))* '

# Tipo seguido de um destes particípios cita um ato anterior, não publica um novo:
# "Licença Prévia concedida por meio da Resolução CEPRAM nº 3293".
CITACAO_DE_ATO_ANTERIOR = re.compile(
    r' (?:JA )?(?:CONCEDID|OUTORGAD|EMITID|EXPEDID|APROVAD|AUTORIZAD|PUBLICAD|OBTID|DEFERID)'
    r'AS?\b'
)

# Estes tipos atuam sobre um ato anterior, então o particípio se refere àquele ato:
# "Prorrogação do Prazo de Validade da Licença de Instalação concedida pela Portaria".
PRIMEIRA_PALAVRA_DE_TIPO_DERIVADO = frozenset(
    {
        'ALTERACAO',
        'AMPLIACAO',
        'CANCELAMENTO',
        'EXCLUSAO',
        'PRORROGACAO',
        'RENOVACAO',
        'REVISAO',
        'SUSPENSAO',
        'TRANSFERENCIA',
    }
)
# Tipo precedido de "sem" descreve a falta do ato numa infração, não publica um novo:
# "captação de água subterrânea sem a devida outorga de direito de uso do recurso hídrico".
FALTA_DO_ATO = re.compile(
    r'\bSEM(?: A| O)?(?: DEVID[AO]| RESPECTIV[AO])?(?: DISPENSA OU)? $'
)

# Auto de infração por perda do prazo de renovação: "o interessado não requereu renovação da
# outorga do direito do uso da água dentro do prazo legal" vem seguido da transcrição do
# Art. 28 da Portaria INEMA nº 11.292 ("O pedido de renovação de outorga de direito de uso
# de recursos hídricos deverá ser protocolizado..."). Nenhuma outorga é publicada no ato,
# então os tipos de outorga não contam em todo o texto.
CITACAO_DE_RENOVACAO_DE_OUTORGA = re.compile(
    r'\bREQUEREU RENOVACAO(?: (?:DA|DE))? OUTORGA\b'
)


# Marcador de número nos sinônimos. O texto normalizado de "por 02 (dois) anos" é
# "POR 02 DOIS ANOS": o marcador casa com os algarismos e com o número por extenso
# opcional que vem depois, então "por XX anos" vale para qualquer prazo.
MARCADOR_DE_NUMERO = 'XX'
NUMERO = r'\d+(?: [A-Z]+)?'

# Outras formas de escrever um tipo no DOE, pela chave do nome normalizado do domínio.
# Concorrem no regex como nomes à parte, cada uma pelo seu número de palavras.
SINONIMOS = {
    'OUTORGA DE DIREITO DE USO DE RECURSO HIDRICO': (
        'Autorizar o direito de uso dos recursos hídricos',
    ),
    'ALTERACAO DE OUTORGA DE DIREITO DE USO DE RECURSO HIDRICO': (
        'Autorizar a alteração do direito de uso dos recursos hídricos',
    ),
    'RENOVACAO DE OUTORGA DE DIREITO DE USO DE RECURSO HIDRICO': (
        'Autorizar a renovação do direito de uso dos recursos hídricos',
    ),
    'PRORROGACAO DO PRAZO DE VALIDADE DE OUTORGA': (
        'Prorrogação do Prazo de Validade, por XX anos a partir da data do '
        'vencimento, da Outorga de direito de uso da água',
    ),
    'AUTORIZACAO DE MANEJO DE FAUNA': ('Autorização para Manejo de Fauna',),
}


class TipoAto(NamedTuple):
    id: int
    nome: str
    sigla: str | None


@dataclass(frozen=True)
class Catalogo:
    padrao: re.Pattern
    derivados: frozenset[int]
    outorgas: frozenset[int] = frozenset()


def normalizar(texto: str | None) -> str:
    """Maiúsculas sem acento, com pontuação e quebras de linha trocadas por um espaço."""
    decomposto = unicodedata.normalize('NFKD', texto or '')
    sem_acento = decomposto.encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Z0-9]+', ' ', sem_acento.upper()).strip()


def _palavras_do_nome(nome: str) -> list[str]:
    return [
        palavra for palavra in normalizar(nome).split() if palavra not in CONECTIVOS
    ]


def _regex_da_palavra(palavra: str) -> str:
    if palavra == MARCADOR_DE_NUMERO:
        return NUMERO
    # O plural aparece no DOE ("recursos hídricos") e no domínio ("Licenciamentos")
    return f'{palavra.removesuffix("S")}S?'


def compilar_catalogo(tipos: Iterable[TipoAto]) -> Catalogo:
    """Monta o regex único de todos os tipos, com os nomes mais longos primeiro.

    Assim "Renovação de Licença de Operação" não conta também como "Licença de Operação".
    Nomes que ficam iguais depois de normalizados são um tipo só: vence o que tem sigla e,
    entre esses, o de menor id.
    """
    tipos_com_palavras = []
    derivados = set()
    outorgas = set()
    for tipo in tipos:
        palavras_do_nome = _palavras_do_nome(tipo.nome)
        if palavras_do_nome[0] in PRIMEIRA_PALAVRA_DE_TIPO_DERIVADO:
            derivados.add(tipo.id)
        if 'OUTORGA' in palavras_do_nome:
            outorgas.add(tipo.id)
        formas = (tipo.nome, *SINONIMOS.get(normalizar(tipo.nome), ()))
        for indice, forma in enumerate(formas):
            tipos_com_palavras.append((tipo, indice, _palavras_do_nome(forma)))
    tipos_com_palavras.sort(
        key=lambda item: (-len(item[2]), item[0].sigla is None, item[0].id, item[1])
    )

    alternativas = []
    for tipo, indice, palavras in tipos_com_palavras:
        corpo = SEPARADOR.join(_regex_da_palavra(palavra) for palavra in palavras)
        alternativas.append(f'(?P<t{tipo.id}_{indice}>{corpo})')

    return Catalogo(
        padrao=re.compile(rf'\b(?:{"|".join(alternativas)})\b'),
        derivados=frozenset(derivados),
        outorgas=frozenset(outorgas),
    )


def extrair_tipos_ato(texto: str | None, catalogo: Catalogo) -> list[int]:
    """Devolve os ids dos tipos encontrados no texto, sem repetição, na ordem em que surgem."""
    normalizado = normalizar(texto)
    ignorados = (
        catalogo.outorgas
        if CITACAO_DE_RENOVACAO_DE_OUTORGA.search(normalizado)
        else frozenset()
    )
    encontrados = {}
    for achado in catalogo.padrao.finditer(normalizado):
        id_tipo = int(achado.lastgroup[1:].split('_')[0])
        if id_tipo in ignorados or FALTA_DO_ATO.search(
            normalizado, max(0, achado.start() - 40), achado.start()
        ):
            continue
        if id_tipo not in catalogo.derivados and CITACAO_DE_ATO_ANTERIOR.match(
            normalizado, achado.end()
        ):
            continue
        encontrados[id_tipo] = True
    return list(encontrados)
