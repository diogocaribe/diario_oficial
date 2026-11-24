"""Regras comuns às gravações: campo na coluna de mesmo nome, endereço e pessoa.

Cada tipo de ato tem o seu módulo de gravação (``gravacao_auto_infracao``,
``gravacao_outorga``), que converte os objetos Pydantic da extração nas entidades do
seu esquema. O que vale para todos fica aqui, como ``modelo_comum`` para os esquemas:

- cada campo vai para a coluna de mesmo nome, com o tipo do banco
  (``valor_da_coluna``); um campo sem coluna é erro (``CampoSemColuna``), para o JSON e
  o banco não divergirem;
- o endereço vira uma linha da tabela ``endereco`` do esquema, ou nada se vier vazio;
- a pessoa vai para ``public.pessoa``, com o CPF/CNPJ só em dígitos;
- a geometria (WKT no datum do texto) é convertida para o SIRGAS 2000.

Não abre conexão: a pessoa já gravada com o mesmo documento é reaproveitada pelo
repositório de cada esquema.
"""

from datetime import date, time
from decimal import Decimal

from geoalchemy2 import WKTElement
from pydantic import BaseModel
from sqlalchemy import inspect

from diario_oficial.database.entity.pessoa import Pessoa
from diario_oficial.extracao import modelo_comum
from diario_oficial.extracao.normalizacao import normalizar_documento
from diario_oficial.extracao.utils_geo import wkt_em_sirgas

# SIRGAS 2000, o sistema oficial do Brasil: as geometrias são gravadas nele.
SRID = 4674

CONVERSORES = {
    date: date.fromisoformat,
    time: time.fromisoformat,
    Decimal: lambda valor: Decimal(str(valor)),
}


class CampoSemColuna(ValueError):
    """Campo do esquema Pydantic que não tem coluna na entidade."""


def valor_da_coluna(coluna, valor):
    """``valor`` convertido para o tipo Python da ``coluna`` (data, hora, Decimal)."""
    if valor is None:
        return None
    try:
        tipo = coluna.type.python_type
    except NotImplementedError:
        return valor
    return CONVERSORES.get(tipo, lambda v: v)(valor)


def valores_das_colunas(entidade: type, registro: BaseModel, fora: set[str]) -> dict:
    """Os campos de ``registro`` (menos ``fora``) nas colunas de mesmo nome."""
    colunas = inspect(entidade).columns
    valores = {}
    for campo, valor in registro.model_dump(exclude=fora).items():
        if campo not in colunas:
            raise CampoSemColuna(f'{type(registro).__name__}.{campo}')
        valores[campo] = valor_da_coluna(colunas[campo], valor)
    return valores


def para_endereco(endereco: modelo_comum.Endereco | None, entidade: type):
    """O endereço como ``entidade`` do esquema, ou ``None`` se nenhum campo veio."""
    if endereco is None:
        return None
    dados = endereco.model_dump()
    if all(valor is None for valor in dados.values()):
        return None
    return entidade(**dados)


def para_pessoa(pessoa: modelo_comum.Pessoa) -> Pessoa:
    """A pessoa de ``public.pessoa``, sem o endereço (que é do ato)."""
    return Pessoa(
        nome=pessoa.nome,
        tipo_documento=pessoa.tipo_documento,
        nro_documento=normalizar_documento(pessoa.tipo_documento, pessoa.nro_documento),
    )


def para_geometria(wkt: str | None, sistema: str | None) -> WKTElement | None:
    """O WKT no datum ``sistema`` convertido para o SIRGAS 2000, ou ``None``."""
    convertido = wkt_em_sirgas(wkt, sistema)
    return WKTElement(convertido, srid=SRID) if convertido else None
