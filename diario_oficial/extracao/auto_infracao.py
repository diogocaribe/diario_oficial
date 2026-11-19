"""Extração estruturada dos autos de infração e dos seus subtipos com um LLM local.

Módulo sem banco e sem efeito no import (além de montar as ``Extracao``). Todos os
subtipos (interdição, multa, advertência, apreensão, embargo, demolição, destruição de
fornos e de produtos) são publicados da mesma forma, então o corte, as instruções e a
conferência são os mesmos; o que muda fica num ``SubtipoAuto``: a sigla do processo, o
nome da penalidade, o esquema, a tabela e os campos próprios que a regex lê.

O texto de um ato pode trazer vários autos (os editais de notificação juntam autuados
de tipos diferentes), então a extração tem duas partes:

1. ``separar_trechos`` corta o texto em trechos, um por autuado, e fica só com os que
   são do subtipo (processo ``/TEC/<SIGLA>-`` ou, sem número, a penalidade escrita
   logo depois). É código, porque a extração usa contexto de 8 mil tokens e um edital
   inteiro com o JSON de todos os autos não cabe.
2. o modelo recebe cada trecho com o esquema do subtipo (``Extracao<Subtipo>`` em
   ``modelo_auto_infracao``) e as instruções de ``instrucoes(subtipo)``.

``criar_extracao`` junta essas peças no contrato de ``extracao.base``; quem roda é
``extracao.base.extrair``, que também confere o resultado (``conferir``) contra os
números de processo achados por regex no trecho. Número de processo escrito fora do
padrão (com espaços, sem "nº" ou sem número) não tira o autuado da extração: o trecho
vai para o modelo, que devolve o número corrigido, e a conferência marca esse caso em
``processo_pelo_modelo``.

Subtipo novo: declarar o ``SubtipoAuto`` no fim deste módulo e incluí-lo em
``SUBTIPOS``; o esquema vai em ``modelo_auto_infracao`` e a tabela em
``database/entity/auto_infracao.py`` (com a migração).
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from pydantic import BaseModel

from diario_oficial.database.entity import auto_infracao as entidades
from diario_oficial.extracao import modelo_auto_infracao as modelos
from diario_oficial.extracao.base import Extracao
from diario_oficial.extracao.normalizacao import (
    normalizar_data,
    normalizar_numero,
    normalizar_processo,
    normalizar_sistema_referencia,
    normalizar_texto,
)


# Número de processo de auto como aparece nos textos, inclusive com erro de digitação:
# espaços em volta das barras e do hífen, ponto no lugar do hífen, ano com dígitos a mais
# ("2012 004565/TEC/AIIN-0022", "20142013- 003335/ TEC/AIIN-0060"). ``tipo`` é o que
# vem depois de "AI" na sigla (IN em AIIN, MU em AIMU).
def _processo_solto(tipo: str) -> str:
    return r'\d{4,8}[\s.-]*\d+\s*/\s*TEC\s*/\s*AI\s*' + tipo + r'\s*-?\s*\d+'


# Número de processo de qualquer auto de infração (AIIN, AIMU, AIAD, AIAP...)
PROCESSO_AUTO = re.compile(_processo_solto('[A-Z]{2}'))

# Cada autuado de um edital termina em "nos autos do processo administrativo nº <nº>".
# O "nº" e o próprio número podem faltar ("processo administrativo 2022-...",
# "processo administrativo nº , em ...").
INICIO_DO_PROCESSO = re.compile(
    r'nos\s+autos\s+do\s+processo[\s/]*administrativo\s+(?:de\s+)?'
    r'(?:n[ºo°]\.?\s*:?\s*)?(?P<processo>' + PROCESSO_AUTO.pattern + r')?',
    re.IGNORECASE,
)
# Sem número de processo, o tipo do auto sai da penalidade logo depois ("Auto de
# Infração de Interdição", "Penalidade de Multa").
ABERTURA_DA_PENALIDADE = r'(?:Auto\s+de\s+Infra[çc][ãa]o\s+de|Penalidade\s+de)\s+'
JANELA_DA_PENALIDADE = 150
# Fim do autuado anterior: aspas que fecham a descrição (com ";", "." ou " e "
# depois) ou o "Autuado(s):" que abre a lista.
FIM_DO_AUTUADO_ANTERIOR = re.compile(
    r'(?:["”]\s*[;.]?\s*(?:e\s+)?|;\s*|Autuad[oa]s?\s*:\s*)', re.IGNORECASE
)
JANELA_DO_AUTUADO = 400

# Campos que o texto escreve de forma mecânica em qualquer auto.
DOCUMENTO = re.compile(
    r'\b(?P<tipo>CPF|CNPJ|RG)\b\s*(?:n[ºo°]\.?)?\s*:?\s*(?P<numero>\d[\d./-]{5,}\d)',
    re.IGNORECASE,
)
DATA_HOMOLOGACAO = re.compile(
    r'em\s+(?P<data>\d{1,2}/\d{1,2}/\d{4}),?\s*foi\s+homologad', re.IGNORECASE
)
RESULTADO_RECURSO = re.compile(
    r'\b(?P<resultado>Indeferir|Deferir)\s+(?:o\s+)?recurso', re.IGNORECASE
)
ATO_DECISORIO = re.compile(
    r'RESOLU[ÇC][ÃA]O\s+N[º°o]\.?\s*(?P<nro>\d[\d.]*\d|\d)', re.IGNORECASE
)
SISTEMA_REFERENCIA = re.compile(
    r'SIRGAS\s*-?\s*2000?|SAD\s*-?\s*69|WGS\s*-?\s*84|C[óo]rrego\s+Alegre',
    re.IGNORECASE,
)
# Data com erro de digitação no texto: ano de três dígitos ou "º" colado ao ano.
DATA_COM_ERRO = re.compile(r'\b\d{1,2}/\d{1,2}/(?:\d{3}\b|\d{4}[º°])')
LACRE = re.compile(
    r'lacres?\s+(?:de\s+)?(?:n[º°o]\.?\s*)?(?P<nros>\d{4,}(?:\s*(?:,|e)\s*\d{4,})*)',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SubtipoAuto:
    """O que muda de um subtipo de auto de infração para outro.

    - ``sigla``: sigla em ``dominio.tipo_ato`` e no número do processo (ex.: AIIN).
    - ``nome``: a penalidade como o prompt a cita, "autos de infração de <nome>"
      (ex.: interdição).
    - ``penalidade``: regex do nome da penalidade depois de "Auto de Infração de" ou
      "Penalidade de", para reconhecer o autuado cujo processo veio sem número.
    - ``esquema``: ``Extracao<Subtipo>`` de ``modelo_auto_infracao``.
    - ``entidade``: tabela do esquema ``auto_infracao`` onde o auto é gravado.
    - ``campos_do_subtipo_por_regex``: lê do trecho os campos próprios do subtipo
      (ex.: a modalidade da interdição) e devolve ``{campo: valor ou None}``; esses
      campos entram na conferência junto com os comuns.
    - ``campos_preenchidos_pela_regex``: dos campos lidos pela regex, os que ela grava
      quando o modelo os deixa vazios (ver ``preencher_vazios_pela_regex``).
    - ``regras_do_subtipo``: linhas a mais nas instruções do modelo.
    """

    sigla: str
    nome: str
    penalidade: str
    esquema: type[BaseModel]
    entidade: type[entidades.AutoInfracao]
    campos_do_subtipo_por_regex: Callable[[str], dict] | None = None
    campos_preenchidos_pela_regex: tuple[str, ...] = ()
    regras_do_subtipo: tuple[str, ...] = ()

    @property
    def processo(self) -> re.Pattern:
        """Número de processo deste subtipo (ex.: .../TEC/AIIN-0222)."""
        return re.compile(_processo_solto(self.sigla[2:]))

    @property
    def penalidade_sem_processo(self) -> re.Pattern:
        return re.compile(ABERTURA_DA_PENALIDADE + self.penalidade, re.IGNORECASE)


def _inicio_do_autuado(texto: str, inicio_do_processo: int, limite: int) -> int:
    """Posição onde começa o nome do autuado que antecede ``inicio_do_processo``."""
    janela_inicio = max(limite, inicio_do_processo - JANELA_DO_AUTUADO)
    inicio = janela_inicio
    for achado in FIM_DO_AUTUADO_ANTERIOR.finditer(
        texto, janela_inicio, inicio_do_processo
    ):
        inicio = achado.end()
    return inicio


def _e_do_subtipo(subtipo: SubtipoAuto, texto: str, achado: re.Match) -> bool:
    """Se o autuado de ``achado`` é do subtipo, pelo número ou pela penalidade."""
    processo = achado.group('processo')
    if processo:
        return subtipo.processo.fullmatch(processo) is not None
    depois = texto[achado.end() : achado.end() + JANELA_DA_PENALIDADE]
    return subtipo.penalidade_sem_processo.search(depois) is not None


def separar_trechos(subtipo: SubtipoAuto, texto: str | None) -> list[str]:
    """Divide o texto em trechos de um autuado cada e devolve os do subtipo.

    Sem a estrutura de edital (resolução do CEPRAM, termo de compromisso, portaria de
    sustação), o texto inteiro volta como um trecho só, se citar algum processo do
    subtipo.
    """
    normalizado = normalizar_texto(texto)
    processos = list(INICIO_DO_PROCESSO.finditer(normalizado))
    if not processos:
        return [normalizado] if subtipo.processo.search(normalizado) else []

    inicios = []
    limite = 0
    for achado in processos:
        inicio = _inicio_do_autuado(normalizado, achado.start(), limite)
        inicios.append(inicio)
        limite = achado.end()

    trechos = []
    for indice, achado in enumerate(processos):
        if not _e_do_subtipo(subtipo, normalizado, achado):
            continue
        fim = inicios[indice + 1] if indice + 1 < len(inicios) else len(normalizado)
        trechos.append(normalizado[inicios[indice] : fim].strip())
    return trechos


def instrucoes(subtipo: SubtipoAuto) -> str:
    """Mensagem de sistema do modelo para o subtipo."""
    outras = ', '.join(s.sigla for s in SUBTIPOS if s.sigla != subtipo.sigla)
    regras = [
        f'Inclua só os autos cujo número de processo contém /{subtipo.sigla}-. '
        f'Ignore os autos de outros tipos ({outras}).',
        'Ignore números de processo apenas citados dentro da descrição de outro auto.',
        'Use somente o que está escrito no trecho. Se uma informação não aparece, use '
        'null (ou lista vazia nos campos de lista). Não invente valores.',
        'Copie nomes, documentos e números exatamente como estão no texto. A exceção é '
        'o número do processo: escreva sempre no padrão '
        f'AAAA-NNNNNN/TEC/{subtipo.sigla}-NNNN, corrigindo espaços e erros de '
        'digitação.',
        'Datas sempre no formato AAAA-MM-DD, qualquer que seja a forma no texto: por '
        'extenso ("aos cinco dias do mês de agosto de 2010" -> 2010-08-05), com ano de '
        'dois dígitos (06.12.18 -> 2018-12-06) ou com erro de digitação (27/05/215 -> '
        '2015-05-27; 21/08/2014º -> 2014-08-21). Se não der para saber o dia, o mês ou '
        'o ano, use null.',
        'Em coordenada, copie todos os pares de coordenadas do trecho, na ordem: cada '
        'vértice da área (tipo vertice) e o ponto de constatação (tipo ponto). Pares '
        'em UTM também entram, com o fuso em fuso_utm quando o texto o informa.',
        *subtipo.regras_do_subtipo,
        'Responda somente com o JSON.',
    ]
    return (
        f'Você extrai dados de autos de infração de {subtipo.nome} publicados no '
        'Diário Oficial do Estado da Bahia pelo INEMA.\n\nRegras:\n'
        + '\n'.join(f'- {regra}' for regra in regras)
    )


def campos_por_regex(subtipo: SubtipoAuto, trecho: str) -> dict:
    """Campos que o texto escreve de forma mecânica, para conferir o modelo.

    Os comuns a todo auto mais os do subtipo. Só vale para trecho de um auto (o caso
    dos editais): pega a primeira ocorrência.
    """
    documento = DOCUMENTO.search(trecho)
    data = DATA_HOMOLOGACAO.search(trecho)
    resultado = RESULTADO_RECURSO.search(trecho)
    ato_decisorio = ATO_DECISORIO.search(trecho)
    sistema = SISTEMA_REFERENCIA.search(trecho)
    lacres = [
        numero
        for achado in LACRE.finditer(trecho)
        for numero in re.findall(r'\d{4,}', achado.group('nros'))
    ]
    do_subtipo = (
        subtipo.campos_do_subtipo_por_regex(trecho)
        if subtipo.campos_do_subtipo_por_regex
        else {}
    )
    return {
        **do_subtipo,
        'tipo_documento': documento and documento.group('tipo').upper(),
        'nro_documento': documento and documento.group('numero'),
        'dt_homologacao': data and normalizar_data(data.group('data')),
        'resultado_recurso': resultado
        and (
            'indeferido'
            if resultado.group('resultado').lower() == 'indeferir'
            else 'deferido'
        ),
        'nro_ato_decisorio': ato_decisorio and ato_decisorio.group('nro'),
        'sistema_referencia_espacial': sistema
        and normalizar_sistema_referencia(sistema.group()),
        'nro_lacre': sorted(set(lacres)) or None,
    }


def _um_auto_so(subtipo: SubtipoAuto, trecho: str, extracao: BaseModel) -> bool:
    """Se o trecho e a resposta têm um auto só (o caso dos editais).

    Com vários autos no trecho, a primeira ocorrência de um campo achada pela regex
    pode ser de qualquer um deles.
    """
    brutos = subtipo.processo.findall(trecho)
    esperados = {normalizar_processo(bruto) for bruto in brutos} - {None}
    return len(esperados) <= 1 and len(brutos) <= 1 and len(extracao.auto) == 1


def _valor_do_modelo(auto: modelos.AutoInfracao, campo: str):
    """Valor do campo na resposta do modelo, na forma de ``campos_por_regex``."""
    if campo in ('tipo_documento', 'nro_documento'):
        return getattr(auto.autuado, campo)
    if campo == 'nro_lacre':
        return sorted(set(auto.nro_lacre)) or None
    return getattr(auto, campo)


def preencher_vazios_pela_regex(
    subtipo: SubtipoAuto, trecho: str, extracao: BaseModel
) -> list[str]:
    """Grava no auto o valor da regex nos campos que o modelo deixou vazios.

    Só os campos de ``subtipo.campos_preenchidos_pela_regex`` e só para trecho de um
    auto. Não troca o que o modelo preencheu: se ele discorda da regex, a divergência
    aparece na conferência. Devolve os campos preenchidos.
    """
    if not subtipo.campos_preenchidos_pela_regex:
        return []
    if not _um_auto_so(subtipo, trecho, extracao):
        return []
    auto = extracao.auto[0]
    pela_regex = campos_por_regex(subtipo, trecho)
    preenchidos = []
    for campo in subtipo.campos_preenchidos_pela_regex:
        if getattr(auto, campo) is None and pela_regex[campo] is not None:
            setattr(auto, campo, pela_regex[campo])
            preenchidos.append(campo)
    return preenchidos


def conferir(subtipo: SubtipoAuto, trecho: str, extracao: BaseModel) -> dict:
    """Compara a saída do modelo com o que a regex acha no trecho.

    ``faltantes`` são processos do subtipo no trecho que o modelo não devolveu;
    ``inesperados`` são processos que o modelo devolveu e não estão no trecho
    (alucinação ou erro de cópia). Quando a regex não consegue ler algum número do
    trecho (ano com dígitos a mais, número ausente), os processos devolvidos pelo modelo
    vão para ``processo_pelo_modelo``: foram corrigidos por ele e precisam de revisão.
    ``data_corrigida_pelo_modelo`` lista as datas com erro de digitação no trecho, cuja
    correção ficou com o modelo.
    ``divergencias`` lista, para trecho de um auto só, os campos em que o modelo e a
    regex discordam: ``{campo: [modelo, regex]}``.
    """
    brutos = subtipo.processo.findall(trecho)
    normalizados = [normalizar_processo(bruto) for bruto in brutos]
    esperados = {processo for processo in normalizados if processo}
    regex_incompleta = not brutos or None in normalizados
    extraidos = {auto.nro_processo for auto in extracao.auto if auto.nro_processo}
    inesperados = sorted(extraidos - esperados)
    processo_pelo_modelo = []
    if regex_incompleta:
        processo_pelo_modelo, inesperados = inesperados, []
    divergencias = {}
    if _um_auto_so(subtipo, trecho, extracao):
        auto = extracao.auto[0]
        for campo, valor_regex in campos_por_regex(subtipo, trecho).items():
            valor_modelo = _valor_do_modelo(auto, campo)
            # Lacre que o texto não cita é invenção do modelo: compara mesmo sem regex.
            comparar = valor_regex is not None or (
                campo == 'nro_lacre' and valor_modelo is not None
            )
            if comparar and valor_modelo != valor_regex:
                divergencias[campo] = [valor_modelo, valor_regex]
    return {
        'faltantes': sorted(esperados - extraidos),
        'inesperados': inesperados,
        'processo_pelo_modelo': processo_pelo_modelo,
        'data_corrigida_pelo_modelo': DATA_COM_ERRO.findall(trecho),
        'divergencias': divergencias,
    }


def criar_extracao(subtipo: SubtipoAuto) -> Extracao:
    """A ``Extracao`` do subtipo, com as funções deste módulo presas a ele."""
    return Extracao(
        sigla_tipo_ato=subtipo.sigla,
        pasta='Portarias',
        esquema=subtipo.esquema,
        instrucoes=instrucoes(subtipo),
        campo_registros='auto',
        separar_trechos=partial(separar_trechos, subtipo),
        preencher_vazios_pela_regex=partial(preencher_vazios_pela_regex, subtipo),
        conferir=partial(conferir, subtipo),
        entidade=subtipo.entidade,
    )


# Campos próprios de cada subtipo que a regex lê.

MODALIDADE_INTERDICAO = re.compile(
    r'interdi[çc][ãa]o\s+(?P<modalidade>temp|termp|defin)', re.IGNORECASE
)
MODALIDADE_EMBARGO = re.compile(r'embargo\s+(?P<modalidade>temp|defin)', re.IGNORECASE)
# "multa no valor original de R$ 50.000,00", "Multa Simples no valor de R$ 1.000,00"
VALOR_MULTA = re.compile(
    r'multa\s+(?:simples\s+|di[áa]ria\s+)?no\s+valor\s+(?:original\s+)?de\s+'
    r'R\$\s*(?P<valor>\d[\d.]*(?:,\d{1,2})?)',
    re.IGNORECASE,
)


def _modalidade(
    padrao: re.Pattern, definitiva: str, temporaria: str, trecho: str
) -> dict:
    achado = padrao.search(trecho)
    if achado is None:
        return {'modalidade': None}
    if achado.group('modalidade').lower() == 'defin':
        return {'modalidade': definitiva}
    return {'modalidade': temporaria}


def _valor_multa(trecho: str) -> dict:
    achado = VALOR_MULTA.search(trecho)
    return {'valor_multa': achado and normalizar_numero(achado.group('valor'))}


INTERDICAO = SubtipoAuto(
    sigla='AIIN',
    nome='interdição',
    # Interdição seguida de embargo, demolição ou apreensão não é penalidade de AIIN.
    penalidade=r'interdi[çc][ãa]o(?!\s+(?:embargo|demoli|apreens))',
    esquema=modelos.ExtracaoInterdicao,
    entidade=entidades.AutoInterdicao,
    campos_do_subtipo_por_regex=partial(
        _modalidade, MODALIDADE_INTERDICAO, 'definitiva', 'temporaria'
    ),
    # A modalidade vem no nome da penalidade ("Auto de Infração de Interdição
    # Temporária"), e o modelo a deixou null em 72 de 84 autos.
    campos_preenchidos_pela_regex=('modalidade',),
)
MULTA = SubtipoAuto(
    sigla='AIMU',
    nome='multa',
    penalidade=r'multa',
    esquema=modelos.ExtracaoMulta,
    entidade=entidades.AutoMulta,
    campos_do_subtipo_por_regex=_valor_multa,
)
ADVERTENCIA = SubtipoAuto(
    sigla='AIAD',
    nome='advertência',
    penalidade=r'advert[êe]ncia',
    esquema=modelos.ExtracaoAdvertencia,
    entidade=entidades.AutoAdvertencia,
)
APREENSAO = SubtipoAuto(
    sigla='AIAP',
    nome='apreensão',
    penalidade=r'apreens[ãa]o',
    esquema=modelos.ExtracaoApreensao,
    entidade=entidades.AutoApreensao,
)
EMBARGO = SubtipoAuto(
    sigla='AIEM',
    nome='embargo',
    penalidade=r'embargo',
    esquema=modelos.ExtracaoEmbargo,
    entidade=entidades.AutoEmbargo,
    campos_do_subtipo_por_regex=partial(
        _modalidade, MODALIDADE_EMBARGO, 'definitivo', 'temporario'
    ),
    campos_preenchidos_pela_regex=('modalidade',),
)
DEMOLICAO = SubtipoAuto(
    sigla='AIDM',
    nome='demolição',
    penalidade=r'demoli[çc][ãa]o',
    esquema=modelos.ExtracaoDemolicao,
    entidade=entidades.AutoDemolicao,
)
DESTRUICAO_FORNOS = SubtipoAuto(
    sigla='AIDF',
    nome='destruição de fornos para produção de carvão vegetal',
    penalidade=r'destrui[çc][ãa]o\s+de\s+fornos',
    esquema=modelos.ExtracaoDestruicaoFornos,
    entidade=entidades.AutoDestruicaoFornos,
)
DESTRUICAO_PRODUTOS = SubtipoAuto(
    sigla='AIDP',
    nome='destruição ou inutilização de produtos',
    penalidade=r'destrui[çc][ãa]o\s+ou\s+inutiliza[çc][ãa]o',
    esquema=modelos.ExtracaoDestruicaoProdutos,
    entidade=entidades.AutoDestruicaoProdutos,
)

SUBTIPOS: tuple[SubtipoAuto, ...] = (
    INTERDICAO,
    MULTA,
    ADVERTENCIA,
    APREENSAO,
    EMBARGO,
    DEMOLICAO,
    DESTRUICAO_FORNOS,
    DESTRUICAO_PRODUTOS,
)

EXTRACOES: dict[str, Extracao] = {
    subtipo.sigla: criar_extracao(subtipo) for subtipo in SUBTIPOS
}
