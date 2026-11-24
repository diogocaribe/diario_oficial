"""Extração das outorgas de direito de uso de recursos hídricos (OUT, ROUT, AOUT, AMOUT).

O texto das outorgas segue um modelo fixo, então a extração principal é por regex
(``extrair_pela_regex``). O modelo de linguagem só entra para os campos obrigatórios
que a regex deixou vazios (``campos_vazios``).

Como a regex lê o Art. 1º:

1. Cada "Autorizar o direito / a renovação / a alteração / a ampliação ... de uso dos
   recursos hídricos" abre uma ``Outorga``. O cabeçalho (número e data da portaria) e o
   processo são os últimos antes dela.
2. A abertura (até o primeiro modo de uso ou §) traz o prazo, o processo relacionado e
   o outorgado (nome, documento e sede).
3. O resto é cortado nos parágrafos (``§ 1º -``); sem parágrafos, é um bloco só.
4. Os pares de coordenadas ancoram os pontos. O que fica antes de um par (corpo
   hídrico, barramento, "no poço 2") é do ponto seguinte; o que fica depois (datum,
   "do poço 1", vazão, h/d, finalidade) é do ponto anterior.
5. Um uso termina no ponto seguido de "para fins de", no fim do bloco ou quando o
   próximo ponto muda de modo. Os atributos do uso (finalidade, área, local,
   parâmetros do efluente, medidas da obra) são lidos no trecho do uso.

Os padrões procuram numa cópia do texto sem acento e em maiúsculas, com o mesmo
comprimento (``_chave``), e os valores são copiados do texto original.
"""

import re
import unicodedata
from dataclasses import dataclass, field

from diario_oficial.database.entity import recurso_hidrico as entidades
from diario_oficial.extracao.base import Extracao
from diario_oficial.extracao.modelo_comum import (
    CoordenadaGeografica,
    Endereco,
    Pessoa,
)
from diario_oficial.extracao.modelo_outorga import (
    ExtracaoOutorga,
    Outorga,
    ParametroEfluente,
    PontoUso,
    UsoCaptacao,
    UsoIntervencao,
    UsoLancamento,
)
from diario_oficial.extracao.normalizacao import (
    normalizar_numero,
    normalizar_texto,
)

MESES = {
    'JANEIRO': 1,
    'FEVEREIRO': 2,
    'MARCO': 3,
    'ABRIL': 4,
    'MAIO': 5,
    'JUNHO': 6,
    'JULHO': 7,
    'AGOSTO': 8,
    'SETEMBRO': 9,
    'OUTUBRO': 10,
    'NOVEMBRO': 11,
    'DEZEMBRO': 12,
}

NUMERO = r'\d[\d.,]*\d|\d'
DATA = r'\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{2,4}'
UNIDADE_VAZAO = r'M\s*[³3]\s*/\s*(?:DIA|D|S|SEG|H)\b'

AUTORIZAR = re.compile(
    r'AUTORIZAR\s+(?:O|A)\s+(?P<natureza>DIREITO|RENOVACAO|ALTERACAO|AMPLIACAO)\b'
    r'(?=.{0,80}?RECURSOS?\s+HIDRICOS?)'
)
NATUREZA = {
    'DIREITO': 'outorga',
    'RENOVACAO': 'renovacao',
    'ALTERACAO': 'alteracao',
    'AMPLIACAO': 'ampliacao',
}
FIM_DO_ART_1 = re.compile(
    r'\bART\.?\s*2\s*[º°O.]|OS\s+ATOS\s+AUTORIZADOS\s+NO\s+ART|'
    r'AUTORIZAR\s+(?:O|A)\s+(?:DIREITO|RENOVACAO|ALTERACAO|AMPLIACAO)\b'
)
CABECALHO = re.compile(
    r'PORTARIA\s*(?:INEMA\s*)?N\s*[º°O.]*\s*(?P<nro>\d[\d.]*\d|\d)\s*,?\s*DE\s*'
    r'(?P<dia>\d{1,2})\s*[º°]?\s*DE\s*(?P<mes>[A-Z]+)\s*DE\s*(?P<ano>\d{4})'
)
# O número às vezes vem com espaços ("2013. 001.001144/ INEMA/LIC- 01144"): vai até a
# vírgula ou o RESOLVE e os espaços saem em ``_processo``.
PROCESSO = re.compile(
    r'PROCESSO\s*(?:SOB\s*)?(?:N\s*[º°O.]*\s*)?:?\s*(?P<nro>\d[\w./\s-]*?\w)'
    r'(?=\s*(?:,|;|\bRESOLVE\b|$))'
)
PROCESSO_RELACIONADO = re.compile(
    r'RELACIONAD[OA]S?\s+(?:A|AO)\s+PROCESSO\s*(?:N\s*[º°O.]*\s*)?:?\s*'
    r'(?P<nro>\d[\w./\s-]*?\w)(?=\s*(?:,|;|\bVALID|$))'
)
PRAZO_EM_ANOS = re.compile(
    r'VALID[OA]S?\s*(?:PELO\s*)?(?:PRAZO\s*)?(?:DE\s*)?(?P<anos>\d{1,2})\s*'
    r'(?:\([A-Z\s]+\)\s*)?ANOS?\b'
)
PRAZO_ATE_DATA = re.compile(rf'VALID[OA]S?\s*ATE\s*(?P<data>{DATA})')
PRAZO_DA_PORTARIA = re.compile(
    r'VALID[OA]S?\s*PELO\s*(?:MESMO\s*)?PRAZO\s*(?:DE\s*VIGENCIA\s*|VIGENTE\s*)?'
    r'DA\s*PORTARIA\s*(?:INEMA\s*)?(?:N\s*[º°O.]*\s*)?(?P<nro>\d[\d./]*\d|\d)'
    rf'(?:,?[^,;]{{0,40}}?PUBLICADA\s*NO\s*D\.?\s*O\.?\s*E\.?\s*(?:DE|EM)\s*'
    rf'(?P<data>{DATA}))?'
)
DOCUMENTO = re.compile(
    r'\b(?P<tipo>CPF|CNPJ)\s*(?:/\s*MF)?\s*(?:SOB\s*)?(?:O\s*)?(?:N\s*[º°O.]*\s*)?'
    r':?\s*(?P<nro>\d[\d.\s/-]{9,22}\d)'
)
FIM_DO_NOME = re.compile(r',?\s*(?:INSCRIT[OA]S?|PORTADOR|CPF|CNPJ)\b')
CONECTIVO_DO_NOME = re.compile(r'(?:^|[\s,])(?:à|ao|aos|às|a)\s+(?=[A-ZÀ-Ý0-9"“])')
SEDE = re.compile(
    r'COM\s+SEDE\s*(?:NA|NO|EM|A)?\s+(?P<endereco>.*?),?\s*(?:N[OA]\s+)?'
    r'MUNICIPIO\s*(?:DE\s+)?(?P<municipio>[^,§:;]*?)\s*(?=,|§|;|:|\bPARA\b|$)'
)
PARAGRAFO = re.compile(r'§\s*\d+\s*[º°O]?\s*[-–:]')
MODO = re.compile(
    r'(?P<sub>CAPTACAO\s+(?:DE\s+AGUAS?\s+)?SUBTERRANEA)|'
    r'(?P<sup>CAPTACAO\s+(?:DE\s+AGUAS?\s+)?SUPERFICIAL|CAPTACAO\s+EM\s+BARRA|'
    r'DERIVACAO)|'
    r'(?P<lanc>LANCAMENTO\s+DE\s+(?:EFLUENTES?|CARGA))|'
    r'(?P<interv>INTERVENCAO)'
)

# Grau-minuto-segundo como o DOE escreve, com os erros de digitação comuns: espaço no
# lugar do grau ("37 57’00”W"), aspas no lugar do minuto ("45°42”57,7”W") e aspas
# repetidas no fim ("11,79”S”").
GMS = (
    r'-?\s*\d{1,3}\s*(?:[°º]|\s)\s*\d{1,2}\s*(?:[\'’′`´”"]{1,2}|\s)\s*'
    r'(?:\d{1,2}(?:[.,]\d+)?\s*(?:["”“″]|[\'’′]{2})?)?\s*[SNWO]?\b(?:\s*[”"])?'
)
# A latitude às vezes vem sem "Lat." ("nas coordenadas 10°53’48,5”S e Long.").
# "LAT[A-Z]*" e não "LAT\w*": sem o ponto ("Lat12°42’56.93”S"), \w comeria o
# primeiro dígito do grau.
PAR = re.compile(
    rf'(?:LAT[A-Z]*\.?|COORDENADAS?)\s*:?\s*(?P<lat>{GMS})\s*(?:,|;|\bE\b)?\s*'
    rf'LONG[A-Z]*\.?\s*:?\s*(?P<lon>{GMS})|'
    rf'LONG[A-Z]*\.?\s*:?\s*(?P<lon2>{GMS})\s*(?:,|;|\bE\b)?\s*'
    rf'LAT[A-Z]*\.?\s*:?\s*(?P<lat2>{GMS})'
)
DATUM = re.compile(
    r'DATUM\s*:?\s*(?P<datum>SIRGAS\s*-?\s*2000?|SAD\s*-?\s*69|WGS\s*-?\s*84)'
)

IDENTIFICACAO_ANTES = re.compile(
    r'\bN[OA]S?\s+(?P<id>PONTO\s*(?:P\s*)?\d+\w*|POCO\s*(?:TUBULAR\s*)?'
    r'(?:N\s*[º°O.]*\s*)?[\w-]*\d\w*|P\s?\d+\w*)'
)
IDENTIFICACAO_DEPOIS = re.compile(
    r'^\W{0,3}(?:DATUM\s*\S+\s*\S*\s*,?\s*)?D[OA]S?\s+(?P<id>POCO\s*(?:TUBULAR\s*)?'
    r'(?:N\s*[º°O.]*\s*)?[\w-]*\d\w*|PONTO\s*(?:P\s*)?\d+\w*)'
)
CORPO_HIDRICO = re.compile(
    r'\b(?:N[OA]S?|EM|D[OA])\s+(?P<corpo>(?:AFLUENTE|RIO|CORREGO|RIACHO|RIBEIRAO|'
    r'RIACHAO|LAGOA|LAGO|ACUDE|REPRESA|CANAL|VEREDA|BREJO|MANANCIAL)\b'
    r'[^,;]*?)(?=,|;|\s+NAS?\s+COORDENADAS?|\s+EM\s+BARRA|\s+NA\s+BARRAGEM|$)'
)
BARRAMENTO = re.compile(
    r'\b(?:EM|N[OA])\s+(?P<barramento>(?:BARRAMENTO|BARRAGEM|RESERVATORIO)\b[^,;]*?)'
    r'(?=,|;|\s+NAS?\s+COORDENADAS?|$)'
)
DISPENSADO = re.compile(r'DISPENSAD[OA]S?\s+(?:DE|DA)\s+OUTORGA')
BACIA = re.compile(
    r'BACIA\s+HIDROGRAFICA\s+(?:D[OAE]S?\s+)?(?P<bacia>.+?)'
    r'(?=,|;|\s+N[OA]S?\s|\s+EM\s|\s+LOCALIZAD|$)'
)
VAZAO = re.compile(
    r'VAZAO(?!\s+(?:DE\s+)?(?:DILUICAO|MINIMA|DE\s+PROJETO|PROJETO|REMANESCENTE))'
    rf'[^;\d]{{0,40}}?(?P<valor>{NUMERO})\s*(?P<unidade>{UNIDADE_VAZAO})'
    rf'(?:\s*(?:OU|\()\s*(?P<valor2>{NUMERO})\s*(?P<unidade2>{UNIDADE_VAZAO}))?'
)
HORAS = re.compile(
    r'(?P<horas>\d{1,2}(?:[.,]\d+)?)\s*(?:H|HS|HORAS?)\s*(?:/|POR)\s*D(?:IA)?\b'
)
FINALIDADE = re.compile(
    r'PARA\s+(?:OS\s+)?FINS?\s+(?:DE\s+)?(?P<finalidade>.+?)'
    r'(?=,|;|\.\s|\s+COM\s|\s+LOCALIZAD|\s+MEDIANTE|\s+AREA\b|\s+NA\s+LOCALIDADE|'
    r'\s+DURANTE|\s+VALID|\s+NAS?\s+COORDENADAS|$)'
)
AREA = re.compile(
    rf'AREA\s*(?:IRRIGADA\s*)?(?:TOTAL\s*)?(?:DE\s*)?(?:ATE\s*)?:?\s*(?P<area>{NUMERO})'
    r'\s*(?:HA|HECTARES?)\b'
)
LOCAL = re.compile(
    r'LOCALIZAD[OA]S?\s+(?:(?:N[OA]S?|EM)\s+)?(?P<local>.*?),?\s*(?:N[OA]S?\s+)?'
    r'MUNICIPIOS?\s*(?:D[EOA]\s+)?(?P<municipios>[^,;§.]+?)\s*'
    r'(?=,|;|§|\.|\bMEDIANTE\b|\s+NAS?\s+COORDENADAS|\s+PARA\s+FINS|\s+NO\s+PONTO|$)'
)
MESMO_LOCAL = re.compile(
    r'LOCALIZAD[OA]S?\s+(?:N[OA]|NESSE|NESTE|NESSA|NESTA)\s+MESM[OA]\s+LOCAL'
)
VAZAO_DILUICAO = re.compile(
    rf'VAZAO\s+DE\s+DILUICAO\s*(?:DE\s*)?:?\s*(?P<valor>{NUMERO})\s*'
    rf'(?P<unidade>{UNIDADE_VAZAO})'
)
PARAMETRO = re.compile(
    r'(?P<valor>\d+(?:[.,]\d+)?(?:\s*X\s*10\s*\^?\s*[⁰¹²³⁴⁵⁶⁷⁸⁹\d]+)?)\s*'
    r'(?P<unidade>MG\s*/\s*L|(?:NMP|UFC|CT)\s*/\s*100\s*ML|/\s*100\s*ML)\s*'
    r'(?:PARA|DE)\s+(?P<nome>[A-Z][A-Z\s]*?)(?=,|;|\.|\s+E\s|\s+DURANTE|$)'
)
VOLUME = re.compile(
    r'VOLUME\s+(?:MAXIMO\s+)?(?:DE\s+ACUMULACAO|ARMAZENADO|ACUMULADO|UTIL)?\s*'
    rf'(?:MAXIMO\s*)?(?:DE\s*)?:?\s*(?P<valor>{NUMERO})\s*M\s*[³3](?!\s*/)'
)
ALTURA = re.compile(
    r'ALTURA\s+(?:MAXIMA\s+)?(?:DO\s+(?:BARRAMENTO|MACICO)\s+)?(?:DE\s*)?:?\s*'
    rf'(?P<valor>{NUMERO})\s*M\b'
)
VAZAO_JUSANTE = re.compile(
    r'VAZAO\s+(?:MINIMA\s+)?(?:PARA\s+)?(?:A\s+)?(?:JUSANTE|REMANESCENTE)'
    rf'[^;\d]{{0,30}}?(?P<valor>{NUMERO})\s*(?P<unidade>{UNIDADE_VAZAO})'
    rf'(?:\s*(?:OU|\()\s*(?P<valor2>{NUMERO})\s*(?P<unidade2>{UNIDADE_VAZAO}))?'
)
VAZAO_PROJETO = re.compile(
    r'VAZAO\s+(?:MAXIMA\s+)?(?:DE\s+)?PROJETO\s*(?:DE\s*)?:?\s*'
    rf'(?P<valor>{NUMERO})\s*(?P<unidade>{UNIDADE_VAZAO})'
)
DESCARGA_DE_FUNDO = re.compile(r'DESCARGA\s+DE\s+FUNDO')
MEDIDA = {
    'extensao_m': re.compile(
        rf'EXTENSAO\s*(?:TOTAL\s*)?(?:DE\s*)?:?\s*(?P<valor>{NUMERO})\s*'
        r'(?P<unidade>KM|M)\b'
    ),
    'largura_m': re.compile(
        rf'LARGURA\s*(?:DE\s*)?:?\s*(?P<valor>{NUMERO})\s*(?P<unidade>KM|M)\b'
    ),
    'comprimento_m': re.compile(
        rf'COMPRIMENTO\s*(?:TOTAL\s*)?(?:DE\s*)?:?\s*(?P<valor>{NUMERO})\s*'
        r'(?P<unidade>KM|M)\b'
    ),
}

# Categoria da finalidade: a primeira regra de cada categoria que casar.
REGRAS_FINALIDADE = (
    ('irrigacao', r'IRRIGA|IRIGA'),
    ('abastecimento_humano', r'(?:ABASTECIMENTO|CONSUMO|USO)\s+HUMANO|POTAVEL'),
    ('abastecimento_industrial', r'INDUSTRIA'),
    ('dessedentacao_animal', r'DESSEDENTA|ABASTECIMENTO\s+ANIMAL|ANIMAL|CRIACAO'),
    ('comercio_servicos', r'COMERCI|SERVICO'),
    ('aquicultura', r'AQUICULTURA|PISCICULTURA|CARCINICULTURA|AQUICOLA'),
    ('mineracao', r'MINERA|EXTRACAO'),
    ('aproveitamento_hidreletrico', r'HIDRELETRIC|ENERGIA|\bPCH\b|\bCGH\b'),
    ('obra_infraestrutura', r'INFRAESTRUTURA|OBRA|CONCRETO|CONSTRUCAO\s+CIVIL'),
    ('pulverizacao_agricola', r'PULVERIZA'),
    ('combate_incendio', r'INCENDIO'),
    ('diluicao_efluente', r'DILUICAO|DISPOSICAO\s+FINAL|DESTINACAO\s+FINAL'),
    ('barramento', r'BARRAMENTO|BARRAGEM'),
    ('canalizacao', r'CANALIZA'),
    ('dragagem', r'DRAGAGEM|DESASSOREAMENTO'),
    ('lazer', r'LAZER|TURISMO|PAISAGIS|RECREA'),
)
REGRAS_IRRIGACAO = (
    ('gotejamento', r'GOTEJ'),
    ('microaspersao', r'MICRO\s*-?\s*ASPERS|MICRO\s*-?\s*JET'),
    ('pivo_central', r'PIVO'),
    ('aspersao_convencional', r'ASPERSAO\s+CONVENCIONAL'),
    ('autopropelido', r'AUTOPROPELIDO|CARRETEL'),
    ('caminhao_pipa', r'CAMINHAO\s*-?\s*PIPA|CARRO\s*-?\s*PIPA'),
    ('mangueira', r'MANGUEIRA'),
    ('superficie', r'SULCO|INUNDA'),
)
# "aspersão" sozinha: sem micro, sem convencional e sem ser o pivô ("aspersão com pivô").
ASPERSAO_SOZINHA = re.compile(
    r'(?<!MICRO)(?<!MICRO\s)(?<!MICRO-)ASPERSAO(?!\s+CONVENCIONAL)'
    r'(?!\s+(?:COM|POR|VIA|TIPO)\s+PIVO)'
)
REGRAS_INTERVENCAO = (
    ('canalizacao', r'CANALIZA'),
    ('travessia', r'\bPONTE|TRAVESSIA|BUEIRO|GALERIA|PASSAGEM\s+MOLHADA'),
    ('aproveitamento_hidreletrico', r'HIDRELETRIC|\bPCH\b|\bCGH\b|\bUHE\b'),
    ('extracao_mineral_dragagem', r'EXTRACAO|DRAGAGEM|DESASSOREAMENTO|AREIA'),
    ('regularizacao_barramento', r'REGULARIZA\w*\s+(?:DE\s+)?(?:BARRA|BARRAGEM)'),
    ('construcao_barramento', r'BARRAMENTO|BARRAGEM|BARRAGENS|RESERVATORIO'),
)


def _chave(texto: str) -> str:
    """Cópia sem acento e em maiúsculas, com o mesmo comprimento do texto.

    Cada caractere vira a sua letra base (``ç`` -> ``C``), para as posições achadas na
    chave valerem no texto original.
    """
    return ''.join(
        unicodedata.normalize('NFD', caractere)[0].upper()
        if len(unicodedata.normalize('NFD', caractere)[0].upper()) == 1
        else caractere
        for caractere in texto
    )


def _numero(valor: str | None) -> float | None:
    """``normalizar_numero`` sem erro: número malformado (``81,347,0``) volta ``None``."""
    try:
        return normalizar_numero(valor)
    except ValueError:
        return None


def _vazao(valor: str, unidade: str) -> tuple[float | None, float | None]:
    """(m³/dia, m³/s) do valor na unidade do texto; a outra unidade fica ``None``."""
    numero = _numero(valor)
    unidade = re.sub(r'\s', '', unidade)
    if numero is None:
        return None, None
    if unidade.endswith('/S') or unidade.endswith('/SEG'):
        return None, numero
    if unidade.endswith('/H'):
        return round(numero * 24, 3), None
    return numero, None


def _vazao_do_achado(achado: re.Match) -> tuple[float | None, float | None]:
    """Junta as duas unidades quando o texto traz "0,69 m³/s ou 59.726,0 m³/dia"."""
    por_dia, por_segundo = _vazao(achado['valor'], achado['unidade'])
    if achado.groupdict().get('valor2'):
        outro_dia, outro_segundo = _vazao(achado['valor2'], achado['unidade2'])
        por_dia = por_dia if por_dia is not None else outro_dia
        por_segundo = por_segundo if por_segundo is not None else outro_segundo
    return por_dia, por_segundo


def _metros(achado: re.Match | None) -> float | None:
    if achado is None or (numero := _numero(achado['valor'])) is None:
        return None
    return numero * 1000 if achado['unidade'] == 'KM' else numero


def _limpo(valor: str | None) -> str | None:
    valor = (valor or '').strip(' ,;:-–.')
    return valor or None


def classificar_finalidade(texto: str | None) -> tuple[list[str], list[str]]:
    """Categorias da finalidade e métodos de irrigação citados no texto."""
    chave = _chave(texto or '')
    if not chave.strip():
        return [], []
    finalidades = [
        nome for nome, padrao in REGRAS_FINALIDADE if re.search(padrao, chave)
    ]
    metodos = [nome for nome, padrao in REGRAS_IRRIGACAO if re.search(padrao, chave)]
    if ASPERSAO_SOZINHA.search(chave) and 'aspersao_convencional' not in metodos:
        metodos.append('aspersao')
    return finalidades or ['outro'], metodos


def classificar_intervencao(texto: str) -> str:
    chave = _chave(texto)
    for nome, padrao in REGRAS_INTERVENCAO:
        if re.search(padrao, chave):
            return nome
    return 'outro'


def _processo(texto: str, achado: re.Match | None) -> str | None:
    """Número do processo sem espaços, ou ``None`` se não tiver o formato de processo.

    Fica só o que tem barra (``2019.001.007825/INEMA/LIC-07825``,
    ``2010-000572/OUT/AMPL-0026``, ``1880/99``): sem ela, a regex pegou outra coisa.
    """
    if achado is None:
        return None
    numero = re.sub(r'\s', '', texto[achado.start('nro') : achado.end('nro')])
    return numero if '/' in numero else None


def _data_por_extenso(achado: re.Match) -> str | None:
    mes = MESES.get(achado['mes'])
    if mes is None:
        return None
    return f'{achado["ano"]}-{mes:02d}-{int(achado["dia"]):02d}'


def _endereco_da_sede(endereco: str, municipio: str) -> Endereco:
    """Corta o endereço da sede nas vírgulas: logradouro, número, complemento, bairro."""
    partes = [parte.strip() for parte in endereco.split(',') if parte.strip()]
    numero = None
    localidade = None
    rodovia = None
    resto = []
    for parte in partes:
        chave = _chave(parte)
        if numero is None and re.fullmatch(
            r'(?:N\s*[º°O.]*\s*)?(?:\d+[\w-]*|S\s*/\s*N)', chave
        ):
            numero = re.sub(r'^(?:n\s*[º°o.]*\s*)', '', parte, flags=re.I)
        elif localidade is None and re.match(
            r'(?:FAZENDA|ZONA\s+RURAL|POVOADO|SITIO|CHACARA|ASSENTAMENTO|DISTRITO)',
            chave,
        ):
            localidade = parte
        elif rodovia is None and re.match(r'(?:RODOVIA|BR|BA)\s*-?\s*\d|ROD\.', chave):
            rodovia = parte
        else:
            resto.append(parte)
    logradouro = resto.pop(0) if resto else None
    if logradouro and numero is None:
        if embutido := re.search(r',?\s*n\s*[º°o.]+\s*(\d+\w*)$', logradouro, re.I):
            numero = embutido.group(1)
            logradouro = logradouro[: embutido.start()]
    bairro = resto.pop() if resto else None
    return Endereco(
        localidade=localidade,
        logradouro=_limpo(logradouro),
        numero=_limpo(numero),
        complemento=_limpo(', '.join(resto)),
        bairro=_limpo(bairro),
        rodovia=_limpo(rodovia),
        cep=None,
        municipio=_limpo(municipio),
    )


def _outorgado(texto: str, chave: str) -> Pessoa | None:
    """Nome, documento e sede de quem recebe a outorga, na abertura do Art. 1º."""
    fim_do_nome = FIM_DO_NOME.search(chave)
    if fim_do_nome is None:
        return None
    antes = texto[: fim_do_nome.start()]
    conectivos = list(CONECTIVO_DO_NOME.finditer(antes))
    if conectivos:
        nome = _limpo(antes[conectivos[-1].end() :])
    else:
        # Sem "a/à/ao" antes do nome ("válido pelo prazo de 04 anos, ALEX ..."): o
        # nome é o que vem depois da última vírgula, se estiver em maiúsculas.
        nome = _limpo(antes.rsplit(',', 1)[-1])
        if not nome or nome != nome.upper():
            return None
    if not nome:
        return None
    documento = DOCUMENTO.search(chave, fim_do_nome.start())
    sede = SEDE.search(chave, fim_do_nome.start())
    endereco = None
    if sede:
        endereco = _endereco_da_sede(
            texto[sede.start('endereco') : sede.end('endereco')],
            texto[sede.start('municipio') : sede.end('municipio')],
        )
    return Pessoa(
        nome=nome,
        tipo_documento=documento['tipo'] if documento else None,
        nro_documento=(
            re.sub(r'\s', '', texto[documento.start('nro') : documento.end('nro')])
            if documento
            else None
        ),
        endereco=endereco,
    )


@dataclass
class _Prazo:
    anos: int | None = None
    data: str | None = None
    portaria: str | None = None
    publicacao: str | None = None

    def vazio(self) -> bool:
        return self.anos is None and self.data is None and self.portaria is None


def _prazo(chave: str) -> _Prazo:
    """O primeiro prazo do trecho, em anos, até uma data ou pelo de outra portaria."""
    achados = [
        (achado.start(), tipo, achado)
        for tipo, padrao in (
            ('portaria', PRAZO_DA_PORTARIA),
            ('data', PRAZO_ATE_DATA),
            ('anos', PRAZO_EM_ANOS),
        )
        if (achado := padrao.search(chave))
    ]
    if not achados:
        return _Prazo()
    _, tipo, achado = min(achados, key=lambda item: item[0])
    if tipo == 'anos':
        return _Prazo(anos=int(achado['anos']))
    if tipo == 'data':
        return _Prazo(data=re.sub(r'\s', '', achado['data']))
    data = achado['data']
    return _Prazo(
        portaria=achado['nro'].replace('.', ''),
        publicacao=re.sub(r'\s', '', data) if data else None,
    )


@dataclass
class _Ponto:
    """Um par de coordenadas e o que a regex leu em volta dele."""

    inicio: int
    fim: int
    modo: str | None
    latitude: str
    longitude: str
    atributos: dict = field(default_factory=dict)
    tem_finalidade: bool = False


def _modo(achado: re.Match) -> str:
    return {
        'sub': 'captacao_subterranea',
        'sup': 'captacao_superficial',
        'lanc': 'lancamento_efluente',
        'interv': 'intervencao',
    }[achado.lastgroup]


def _primeiro(padrao: re.Pattern, chave: str, inicio: int, fim: int) -> re.Match | None:
    return padrao.search(chave, inicio, fim)


def _ultimo(padrao: re.Pattern, chave: str, inicio: int, fim: int) -> re.Match | None:
    achado = None
    for achado in padrao.finditer(chave, inicio, fim):
        pass
    return achado


def _pontos_do_bloco(texto: str, chave: str, inicio: int, fim: int) -> list[_Ponto]:
    """Os pares de coordenadas do bloco, com os atributos de antes e de depois."""
    pares = list(PAR.finditer(chave, inicio, fim))
    pontos = []
    for numero, par in enumerate(pares):
        anterior = pares[numero - 1].end() if numero else inicio
        seguinte = pares[numero + 1].start() if numero + 1 < len(pares) else fim
        modo = _ultimo(MODO, chave, inicio, par.start())
        lat = 'lat' if par.group('lat') else 'lat2'
        lon = 'lon' if par.group('lon') else 'lon2'
        ponto = _Ponto(
            inicio=par.start(),
            fim=par.end(),
            modo=_modo(modo) if modo else None,
            latitude=texto[par.start(lat) : par.end(lat)].strip(),
            longitude=texto[par.start(lon) : par.end(lon)].strip(),
        )
        # Antes do par: o que é do ponto que ele abre.
        if achado := _ultimo(IDENTIFICACAO_ANTES, chave, anterior, par.start()):
            ponto.atributos['identificacao'] = texto[
                achado.start('id') : achado.end('id')
            ]
        if achado := _ultimo(CORPO_HIDRICO, chave, anterior, par.start()):
            if (
                'HIDROGRAFICA'
                not in chave[max(0, achado.start() - 25) : achado.start()]
            ):
                ponto.atributos['corpo_hidrico'] = texto[
                    achado.start('corpo') : achado.end('corpo')
                ]
        if achado := _ultimo(BARRAMENTO, chave, anterior, par.start()):
            ponto.atributos['barramento'] = texto[
                achado.start('barramento') : achado.end('barramento')
            ]
        ponto.atributos['barramento_dispensado'] = bool(
            DISPENSADO.search(chave, anterior, par.start())
        )
        # Depois do par: o que é dele.
        if achado := IDENTIFICACAO_DEPOIS.search(chave[par.end() : seguinte]):
            ponto.atributos.setdefault(
                'identificacao',
                texto[par.end() + achado.start('id') : par.end() + achado.end('id')],
            )
        if achado := _primeiro(DATUM, chave, par.end(), seguinte):
            ponto.atributos['sistema_referencia_espacial'] = achado['datum']
        if achado := _primeiro(VAZAO, chave, par.end(), seguinte):
            ponto.atributos['vazao'] = _vazao_do_achado(achado)
        if achado := _primeiro(HORAS, chave, par.end(), seguinte):
            ponto.atributos['captacao_horas_dia'] = _numero(achado['horas'])
        ponto.tem_finalidade = bool(FINALIDADE.search(chave, par.end(), seguinte))
        pontos.append(ponto)
    return pontos


def _agrupar_em_usos(pontos: list[_Ponto]) -> list[list[_Ponto]]:
    """Um uso fecha no ponto com finalidade ou quando o modo muda."""
    usos, atual = [], []
    for numero, ponto in enumerate(pontos):
        atual.append(ponto)
        seguinte = pontos[numero + 1] if numero + 1 < len(pontos) else None
        if seguinte is None or ponto.tem_finalidade or seguinte.modo != ponto.modo:
            usos.append(atual)
            atual = []
    return usos


def _herdar_atributos(pontos: list[_Ponto]) -> None:
    """Datum e horas faltando vêm do próximo ponto do uso (ou do anterior)."""
    for nome in ('sistema_referencia_espacial', 'captacao_horas_dia'):
        valores = [p.atributos.get(nome) for p in pontos]
        for numero, ponto in enumerate(pontos):
            if valores[numero] is None:
                vizinhos = valores[numero + 1 :] + valores[:numero][::-1]
                if herdado := next((v for v in vizinhos if v is not None), None):
                    ponto.atributos[nome] = herdado


def _ponto_uso(ponto: _Ponto) -> PontoUso:
    por_dia, por_segundo = ponto.atributos.get('vazao', (None, None))
    return PontoUso(
        identificacao=_limpo(ponto.atributos.get('identificacao')),
        corpo_hidrico=_limpo(ponto.atributos.get('corpo_hidrico')),
        barramento=_limpo(ponto.atributos.get('barramento')),
        barramento_dispensado=ponto.atributos.get('barramento_dispensado', False),
        coordenada=CoordenadaGeografica(
            latitude=ponto.latitude,
            longitude=ponto.longitude,
            fuso_utm=None,
            tipo='ponto',
        ),
        sistema_referencia_espacial=ponto.atributos.get('sistema_referencia_espacial'),
        vazao_m3_dia=por_dia,
        vazao_m3_s=por_segundo,
        captacao_horas_dia=ponto.atributos.get('captacao_horas_dia'),
    )


def _municipios(texto: str) -> list[str]:
    return [
        parte for parte in re.split(r',|\s+e\s+', texto, flags=re.I) if parte.strip()
    ]


def _uso(
    texto: str,
    chave: str,
    pontos: list[_Ponto],
    trecho: tuple[int, int],
    prazo: _Prazo,
    bacia: str | None,
    sede: Endereco | None,
):
    """Monta o uso com os atributos lidos no trecho dele (do início ao próximo uso)."""
    inicio, fim = trecho
    modo = pontos[0].modo or 'captacao_superficial'
    finalidade = _primeiro(FINALIDADE, chave, inicio, fim)
    finalidade_texto = (
        texto[finalidade.start('finalidade') : finalidade.end('finalidade')]
        if finalidade
        else None
    )
    finalidades, metodos = classificar_finalidade(finalidade_texto)
    area = _primeiro(AREA, chave, inicio, fim)
    localidade, municipios = None, []
    # "localizado no mesmo local e município" é o lugar da sede do outorgado; vem antes
    # de LOCAL, que casaria com "mesmo local e" como localidade e nenhum município.
    if MESMO_LOCAL.search(chave, inicio, fim):
        if sede is not None:
            localidade = sede.localidade
            municipios = [sede.municipio] if sede.municipio else []
    elif local := _primeiro(LOCAL, chave, inicio, fim):
        localidade = texto[local.start('local') : local.end('local')]
        municipios = _municipios(
            texto[local.start('municipios') : local.end('municipios')]
        )
    comuns = dict(
        prazo_validade_anos=prazo.anos,
        dt_validade=prazo.data,
        nro_portaria_prazo=prazo.portaria,
        dt_publicacao_portaria_prazo=prazo.publicacao,
        bacia_hidrografica=bacia,
        finalidade_texto=_limpo(finalidade_texto),
        finalidades=finalidades,
        metodos_irrigacao=metodos,
        area_ha=_numero(area['area']) if area else None,
        localidade=_limpo(localidade),
        municipios=municipios,
        pontos=[_ponto_uso(ponto) for ponto in pontos],
    )
    if modo == 'lancamento_efluente':
        diluicao = _primeiro(VAZAO_DILUICAO, chave, inicio, fim)
        por_dia, por_segundo = _vazao_do_achado(diluicao) if diluicao else (None, None)
        return UsoLancamento(
            modo=modo,
            vazao_diluicao_m3_dia=por_dia,
            vazao_diluicao_m3_s=por_segundo,
            parametros=[
                ParametroEfluente(
                    nome=texto[achado.start('nome') : achado.end('nome')].strip(),
                    valor=texto[achado.start('valor') : achado.end('valor')].strip(),
                    unidade=texto[achado.start('unidade') : achado.end('unidade')],
                )
                for achado in PARAMETRO.finditer(chave, inicio, fim)
            ],
            **comuns,
        )
    if modo == 'intervencao':
        jusante = _primeiro(VAZAO_JUSANTE, chave, inicio, fim)
        projeto = _primeiro(VAZAO_PROJETO, chave, inicio, fim)
        volume = _primeiro(VOLUME, chave, inicio, fim)
        altura = _primeiro(ALTURA, chave, inicio, fim)
        jusante_dia, jusante_segundo = (
            _vazao_do_achado(jusante) if jusante else (None, None)
        )
        projeto_dia, projeto_segundo = (
            _vazao_do_achado(projeto) if projeto else (None, None)
        )
        return UsoIntervencao(
            modo=modo,
            tipo_intervencao=classificar_intervencao(texto[inicio:fim]),
            volume_maximo_acumulacao_m3=_numero(volume['valor']) if volume else None,
            altura_maxima_m=_numero(altura['valor']) if altura else None,
            vazao_minima_jusante_m3_dia=jusante_dia,
            vazao_minima_jusante_m3_s=jusante_segundo,
            descarga_de_fundo=bool(DESCARGA_DE_FUNDO.search(chave, inicio, fim)),
            vazao_projeto_m3_dia=projeto_dia,
            vazao_projeto_m3_s=projeto_segundo,
            **{
                nome: _metros(padrao.search(chave, inicio, fim))
                for nome, padrao in MEDIDA.items()
            },
            **comuns,
        )
    return UsoCaptacao(modo=modo, **comuns)


def _usos(
    texto: str, chave: str, inicio: int, fim: int, prazo_geral: _Prazo, sede
) -> list:
    """Os usos do Art. 1º, de ``inicio`` (fim da abertura) a ``fim``."""
    paragrafos = [achado.start() for achado in PARAGRAFO.finditer(chave, inicio, fim)]
    limites = [inicio, *paragrafos, fim] if paragrafos else [inicio, fim]
    usos = []
    for bloco_inicio, bloco_fim in zip(limites, limites[1:]):
        pontos = _pontos_do_bloco(texto, chave, bloco_inicio, bloco_fim)
        if not pontos:
            continue
        # O prazo do parágrafo vale para ele; sem prazo na abertura, vale o do bloco.
        prazo = _prazo(chave[bloco_inicio:bloco_fim]) if paragrafos else _Prazo()
        if prazo.vazio():
            prazo = prazo_geral
        if prazo.vazio():
            prazo = _prazo(chave[bloco_inicio:bloco_fim])
        grupos = _agrupar_em_usos(pontos)
        anterior_corpo = None
        for numero, grupo in enumerate(grupos):
            _herdar_atributos(grupo)
            for ponto in grupo:
                if ponto.modo != 'captacao_subterranea':
                    if 'corpo_hidrico' in ponto.atributos:
                        anterior_corpo = ponto.atributos['corpo_hidrico']
                    elif anterior_corpo:
                        ponto.atributos['corpo_hidrico'] = anterior_corpo
            trecho_inicio = bloco_inicio if numero == 0 else grupo[0].fim
            trecho_fim = (
                grupos[numero + 1][0].inicio if numero + 1 < len(grupos) else bloco_fim
            )
            bacia = _ultimo(BACIA, chave, 0, grupo[0].inicio)
            usos.append(
                _uso(
                    texto,
                    chave,
                    grupo,
                    (trecho_inicio, trecho_fim),
                    prazo,
                    _limpo(texto[bacia.start('bacia') : bacia.end('bacia')])
                    if bacia
                    else None,
                    sede,
                )
            )
    _local_dos_vizinhos(usos)
    return usos


def _local_dos_vizinhos(usos: list) -> None:
    """Uso sem local fica com o do próximo uso (ou do anterior) que tiver."""
    for numero, uso in enumerate(usos):
        if uso.municipios or uso.localidade:
            continue
        vizinhos = usos[numero + 1 :] + usos[:numero][::-1]
        if doador := next((v for v in vizinhos if v.municipios or v.localidade), None):
            uso.localidade = doador.localidade
            uso.municipios = list(doador.municipios)


def extrair_pela_regex(trecho: str | None) -> ExtracaoOutorga:
    """As outorgas do trecho lidas pela regex (lista vazia se não houver nenhuma)."""
    texto = normalizar_texto(trecho)
    chave = _chave(texto)
    outorgas = []
    for autorizar in AUTORIZAR.finditer(chave):
        fim = FIM_DO_ART_1.search(chave, autorizar.end())
        fim = fim.start() if fim else len(chave)
        cabecalho = _ultimo(CABECALHO, chave, 0, autorizar.start())
        processo = _ultimo(
            PROCESSO, chave, cabecalho.end() if cabecalho else 0, autorizar.start()
        )
        primeiro_uso = min(
            (
                achado.start()
                for padrao in (MODO, PARAGRAFO, PAR)
                if (achado := padrao.search(chave, autorizar.end(), fim))
            ),
            default=fim,
        )
        abertura = slice(autorizar.end(), primeiro_uso)
        relacionado = PROCESSO_RELACIONADO.search(chave, abertura.start, abertura.stop)
        outorgado = _outorgado(texto[abertura], chave[abertura])
        outorgas.append(
            Outorga(
                natureza=NATUREZA[autorizar['natureza']],
                nro_portaria=cabecalho['nro'].replace('.', '') if cabecalho else None,
                dt_portaria=_data_por_extenso(cabecalho) if cabecalho else None,
                nro_processo=_processo(texto, processo),
                nro_processo_relacionado=_processo(texto, relacionado),
                outorgado=outorgado,
                usos=_usos(
                    texto,
                    chave,
                    primeiro_uso,
                    fim,
                    _prazo(chave[abertura]),
                    outorgado.endereco if outorgado else None,
                ),
            )
        )
    return ExtracaoOutorga(outorgas=outorgas)


def campos_vazios(resposta: ExtracaoOutorga) -> list[str]:
    """Caminhos dos campos obrigatórios que a regex deixou vazios.

    São os que todo ato de outorga traz: processo, outorgado e documento, processo da
    outorga original (alteração e ampliação), usos, e em cada uso a bacia, a finalidade,
    o município, o prazo e os pontos; em cada ponto, a coordenada, a vazão (fora da
    intervenção) e as horas por dia (captação). Ficam de fora os que o texto muitas
    vezes não tem: datum, corpo hídrico, área, identificação do ponto. A
    coordenada só conta se a regex não achou o par: par achado e inválido não melhora
    com o modelo.
    """
    vazios = []
    for o, outorga in enumerate(resposta.outorgas):
        raiz = f'outorgas.{o}'
        if outorga.nro_processo is None:
            vazios.append(f'{raiz}.nro_processo')
        if outorga.natureza in ('alteracao', 'ampliacao') and (
            outorga.nro_processo_relacionado is None
        ):
            vazios.append(f'{raiz}.nro_processo_relacionado')
        if outorga.outorgado is None:
            vazios.append(f'{raiz}.outorgado')
        elif outorga.outorgado.nro_documento is None:
            vazios += [
                f'{raiz}.outorgado.tipo_documento',
                f'{raiz}.outorgado.nro_documento',
            ]
        if not outorga.usos:
            vazios.append(f'{raiz}.usos')
        for u, uso in enumerate(outorga.usos):
            caminho_uso = f'{raiz}.usos.{u}'
            if uso.bacia_hidrografica is None:
                vazios.append(f'{caminho_uso}.bacia_hidrografica')
            if uso.finalidade_texto is None:
                vazios += [
                    f'{caminho_uso}.finalidade_texto',
                    f'{caminho_uso}.finalidades',
                    f'{caminho_uso}.metodos_irrigacao',
                ]
            if not uso.municipios:
                vazios.append(f'{caminho_uso}.municipios')
            if (
                uso.prazo_validade_anos is None
                and uso.dt_validade is None
                and uso.nro_portaria_prazo is None
            ):
                vazios += [
                    f'{caminho_uso}.{nome}'
                    for nome in (
                        'prazo_validade_anos',
                        'dt_validade',
                        'nro_portaria_prazo',
                        'dt_publicacao_portaria_prazo',
                    )
                ]
            if not uso.pontos:
                vazios.append(f'{caminho_uso}.pontos')
            for p, ponto in enumerate(uso.pontos):
                caminho_ponto = f'{caminho_uso}.pontos.{p}'
                # Par lido no texto mas fora da Bahia é erro de digitação do DOE
                # ("Lat.44°34’39.34”S"): o modelo copiaria o mesmo valor.
                if ponto.coordenada is None:
                    vazios.append(f'{caminho_ponto}.coordenada')
                if uso.modo != 'intervencao' and ponto.vazao_m3_dia is None:
                    vazios += [
                        f'{caminho_ponto}.vazao_m3_dia',
                        f'{caminho_ponto}.vazao_m3_s',
                    ]
                if uso.modo.startswith('captacao') and ponto.captacao_horas_dia is None:
                    vazios.append(f'{caminho_ponto}.captacao_horas_dia')
    return vazios


INSTRUCOES = """\
Você extrai dados de portarias de outorga de direito de uso de recursos hídricos do
INEMA (Bahia) publicadas no Diário Oficial. Responda só com o JSON do esquema.

- Uma outorga por "Autorizar o direito de uso / a renovação / a alteração / a ampliação
  ... dos recursos hídricos" do trecho.
- Um uso por parágrafo (§) do Art. 1º ou por conjunto de pontos com a mesma
  finalidade ("para fins de ..."). Cada uso tem o modo: captacao_subterranea (poço),
  captacao_superficial (rio, córrego, barramento), lancamento_efluente ou intervencao
  (barramento, canalização, ponte, hidrelétrica, dragagem).
- Um ponto por par de coordenadas, na ordem do texto. Copie latitude e longitude como
  estão no texto.
- Vazão: copie em vazao_m3_dia se o texto der m³/dia e em vazao_m3_s se der m³/s; não
  converta.
- Copie nomes, números e documentos exatamente como estão no texto. Campo que o texto
  não traz fica null (ou lista vazia).
"""


def _extracao(sigla: str) -> Extracao:
    return Extracao(
        sigla_tipo_ato=sigla,
        pasta='Portarias',
        esquema=ExtracaoOutorga,
        instrucoes=INSTRUCOES,
        campo_registros='outorgas',
        extrair_pela_regex=extrair_pela_regex,
        campos_vazios=campos_vazios,
        entidade=entidades.Outorga,
    )


# A PPV/OUT (prorrogação de prazo) tem outro texto e um ato só na série: fica de fora.
SIGLAS = ('OUT', 'ROUT', 'AOUT', 'AMOUT')
EXTRACOES: dict[str, Extracao] = {sigla: _extracao(sigla) for sigla in SIGLAS}
