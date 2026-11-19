"""Converte a saída de ``extrair`` nas entidades do esquema ``auto_infracao``.

Os campos do esquema Pydantic vão para a coluna de mesmo nome; um campo sem coluna é
erro (``CampoSemColuna``), para o JSON e o banco não divergirem. Os objetos aninhados
viram entidades ligadas por FK, com uma diferença de forma: ``autuado.endereco`` (como
o modelo responde) vai para ``endereco_autuado`` do auto, porque o endereço é um fato do
ato e não da pessoa. ``ponto`` e ``poligono`` são convertidos para o SIRGAS 2000. As
listas de objetos de um subtipo (``bem_apreendido`` da apreensão, ``produto_destruido``
da destruição de produtos) viram linhas da tabela filha da relação de mesmo nome.

Não abre conexão: a pessoa já gravada com o mesmo documento é reaproveitada pelo
repositório (``AutoInfracaoRepository``).
"""

from datetime import date, time
from decimal import Decimal

from geoalchemy2 import WKTElement
from pydantic import BaseModel
from sqlalchemy import inspect

from diario_oficial.database.entity import auto_infracao as entidades
from diario_oficial.extracao import modelo_auto_infracao, modelo_comum
from diario_oficial.extracao.normalizacao import normalizar_documento
from diario_oficial.extracao.utils_geo import wkt_em_sirgas

# Campos que não são colunas do auto: viram entidades à parte ou geometria.
CAMPOS_ANINHADOS = {'autuado', 'local_infracao', 'coordenada', 'ponto', 'poligono'}

CONVERSORES = {
    date: date.fromisoformat,
    time: time.fromisoformat,
    Decimal: lambda valor: Decimal(str(valor)),
}


class CampoSemColuna(ValueError):
    """Campo do esquema Pydantic que não tem coluna na entidade."""


def _valor_da_coluna(coluna, valor):
    if valor is None:
        return None
    try:
        tipo = coluna.type.python_type
    except NotImplementedError:
        return valor
    return CONVERSORES.get(tipo, lambda v: v)(valor)


def _endereco(endereco: modelo_comum.Endereco | None) -> entidades.Endereco | None:
    """Endereço do auto, ou ``None`` se o modelo não preencheu nenhum campo."""
    if endereco is None:
        return None
    dados = endereco.model_dump()
    if all(valor is None for valor in dados.values()):
        return None
    return entidades.Endereco(**dados)


def _geometria(wkt: str | None, sistema: str | None) -> WKTElement | None:
    convertido = wkt_em_sirgas(wkt, sistema)
    return WKTElement(convertido, srid=entidades.SRID) if convertido else None


def _linhas_filhas(entidade: type, itens: list[dict]) -> list:
    """Cada item de uma lista de objetos como linha da tabela filha."""
    colunas = inspect(entidade).columns
    linhas = []
    for item in itens:
        valores = {}
        for campo, valor in item.items():
            if campo not in colunas:
                raise CampoSemColuna(f'{entidade.__name__}.{campo}')
            valores[campo] = _valor_da_coluna(colunas[campo], valor)
        linhas.append(entidade(**valores))
    return linhas


def para_auto(
    registro: modelo_auto_infracao.AutoInfracao,
    entidade: type[entidades.AutoInfracao],
) -> entidades.AutoInfracao:
    """Um auto Pydantic (``AutoInfracao`` ou subclasse) como entidade."""
    mapeamento = inspect(entidade)
    colunas = mapeamento.columns
    relacoes = mapeamento.relationships
    valores = {}
    for campo, valor in registro.model_dump(exclude=CAMPOS_ANINHADOS).items():
        if campo in relacoes:
            # Lista de objetos do subtipo (ex.: bem_apreendido): uma linha por item.
            valores[campo] = _linhas_filhas(relacoes[campo].mapper.class_, valor)
            continue
        if campo not in colunas:
            raise CampoSemColuna(f'{type(registro).__name__}.{campo}')
        valores[campo] = _valor_da_coluna(colunas[campo], valor)

    autuado = registro.autuado
    sistema = registro.sistema_referencia_espacial
    return entidade(
        **valores,
        autuado=entidades.Pessoa(
            nome=autuado.nome,
            tipo_documento=autuado.tipo_documento,
            nro_documento=normalizar_documento(
                autuado.tipo_documento, autuado.nro_documento
            ),
        ),
        autuado_nome=autuado.nome,
        endereco_autuado=_endereco(autuado.endereco),
        local_infracao=_endereco(registro.local_infracao),
        coordenada=[
            entidades.CoordenadaExtraidaTrecho(**par.model_dump())
            for par in registro.coordenada
        ],
        ponto=_geometria(registro.ponto, sistema),
        poligono=_geometria(registro.poligono, sistema),
    )


def para_trechos(
    ato_id: int,
    sigla_tipo_ato: str,
    entidade: type[entidades.AutoInfracao],
    trechos: list[dict],
    modelo_llm: str | None = None,
) -> list[entidades.ExtracaoTrecho]:
    """Os trechos de ``extrair`` (com a chave ``modelos``) como entidades."""
    resultado = []
    for trecho in trechos:
        registros: list[BaseModel] = trecho.get('modelos', [])
        resultado.append(
            entidades.ExtracaoTrecho(
                ato_id=ato_id,
                sigla_tipo_ato=sigla_tipo_ato,
                trecho=trecho['trecho'],
                erro=trecho.get('erro'),
                conferencia=trecho.get('conferencia'),
                preenchido_pela_regex=trecho.get('preenchido_pela_regex', []),
                modelo_llm=modelo_llm,
                autos=[para_auto(registro, entidade) for registro in registros],
            )
        )
    return resultado
