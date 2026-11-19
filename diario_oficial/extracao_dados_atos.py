"""Lê do banco os atos de um tipo, extrai os dados com o LLM local, mostra e grava.

Usado por ``Scripts/extrair_dados_atos.py`` (um tipo de ato) e pelo comando
``extrair-autos-infracao`` da CLI (todos os subtipos de auto). O pacote
``diario_oficial.extracao`` fica sem banco: a leitura dos atos e a gravação ficam aqui.
"""

import json
import time
from datetime import date

from rich.console import Console
from rich.markup import escape
from sqlalchemy import bindparam, text

from diario_oficial.database.configs.connection import DBConnectionHandler
from diario_oficial.database.repository.auto_infracao_repository import (
    AutoInfracaoRepository,
)
from diario_oficial.extracao.base import Extracao, achados, extrair
from diario_oficial.extracao.gravacao import para_trechos
from diario_oficial.settings import Settings

console = Console()

CONSULTA = """
    SELECT a.id, d.dt_edicao, a.conteudo_ato
    FROM processing.ato a
    JOIN processing.ato_tipo_ato ata ON ata.ato_id = a.id
    JOIN dominio.tipo_ato t ON t.id = ata.tipo_ato_id
    JOIN processing.publicacao p ON p.id = a.publicacao_id
    JOIN processing.doe_bruto d ON d.id = p.doe_bruto_id
    LEFT JOIN dominio.tipo_publicacao tp ON tp.id = p.tipo_publicacao_id
    WHERE t.sigla = :sigla
      AND (CAST(:pasta AS text) IS NULL OR tp.nome = :pasta)
      AND (CAST(:data AS date) IS NULL OR d.dt_edicao = :data)
      AND (:sem_filtro_id OR a.id IN :ids)
    ORDER BY d.dt_edicao, a.id
"""


def buscar_atos(extracao: Extracao, data: date | None, ids: list[int]) -> list:
    consulta = text(CONSULTA).bindparams(bindparam('ids', expanding=True))
    with DBConnectionHandler() as db:
        return db.session.execute(
            consulta,
            {
                'sigla': extracao.sigla_tipo_ato,
                'pasta': extracao.pasta,
                'data': data,
                'sem_filtro_id': not ids,
                'ids': ids or [0],
            },
        ).all()


def extrair_dados_atos(
    extracao: Extracao,
    data: date | None = None,
    ato_ids: list[int] | None = None,
    limite: int | None = None,
    modelo: str | None = None,
    silencioso: bool = False,
    save_db: bool = False,
    pular_extraidos: bool = False,
) -> int:
    """Extrai os dados dos atos do tipo de ``extracao``, mostra e, se pedido, grava.

    Com ``save_db``, troca a extração anterior de cada ato no esquema auto_infracao.

    Returns:
        Quantidade de atos processados.
    """
    if save_db and extracao.entidade is None:
        raise ValueError(
            f'a extração {extracao.sigla_tipo_ato} não tem tabela para gravar'
        )
    settings = Settings()
    repositorio = AutoInfracaoRepository()
    atos = buscar_atos(extracao, data, ato_ids or [])
    if pular_extraidos:
        extraidos = repositorio.get_atos_extraidos(
            extracao.sigla_tipo_ato, [ato.id for ato in atos]
        )
        atos = [ato for ato in atos if ato.id not in extraidos]
    if limite is not None:
        atos = atos[:limite]
    console.print(f'{len(atos)} atos {extracao.sigla_tipo_ato} para extrair.')
    if not atos:
        return 0

    nome_modelo = modelo or settings.OLLAMA_MODELO
    extrator = extracao.criar_extrator(
        modelo=nome_modelo, base_url=settings.OLLAMA_BASE_URL
    )
    for numero, ato in enumerate(atos, start=1):
        if not silencioso:
            console.rule(f'[{numero}/{len(atos)}] ato {ato.id}: texto completo')
            console.print(escape(ato.conteudo_ato), '\n')
        inicio = time.monotonic()
        trechos = extrair(ato.conteudo_ato, extracao, extrator)
        registros = sum(len(trecho['registros']) for trecho in trechos)
        erros = sum('erro' in trecho for trecho in trechos)
        com_achados = sum(
            bool(achados(trecho.get('conferencia'))) for trecho in trechos
        )
        preenchidos = sum(len(trecho['preenchido_pela_regex']) for trecho in trechos)
        console.rule(
            f'[{numero}/{len(atos)}] ato {ato.id} ({ato.dt_edicao.isoformat()}): '
            f'{len(trechos)} trechos, {registros} registros, {erros} erros, '
            f'{com_achados} com achados na conferência, '
            f'{preenchidos} campos preenchidos pela regex, '
            f'{time.monotonic() - inicio:.0f}s'
        )
        if silencioso:
            imprimir_conferencia(trechos)
        else:
            imprimir_trechos(trechos)
        if save_db:
            repositorio.gravar_extracao(
                ato.id,
                extracao.sigla_tipo_ato,
                para_trechos(
                    ato.id,
                    extracao.sigla_tipo_ato,
                    extracao.entidade,
                    trechos,
                    nome_modelo,
                ),
            )
    return len(atos)


def imprimir_trechos(trechos: list[dict]) -> None:
    """Mostra cada trecho com os registros extraídos."""
    for indice, trecho in enumerate(trechos, start=1):
        console.print(f'\n[bold]Trecho {indice}:[/bold]', escape(trecho['trecho']))
        if 'erro' in trecho:
            console.print(f'[bold red]Erro:[/bold red] {escape(trecho["erro"])}')
            continue
        for registro in trecho['registros']:
            console.print_json(json.dumps(registro, ensure_ascii=False))
        imprimir_conferencia([trecho], indices=[indice])
    console.print()


def imprimir_conferencia(trechos: list[dict], indices: list[int] | None = None) -> None:
    """Mostra, por trecho, os achados da conferência e os campos preenchidos pela regex.

    Trecho sem achado e sem campo preenchido não aparece.
    """
    for indice, trecho in zip(indices or range(1, len(trechos) + 1), trechos):
        encontrados = achados(trecho.get('conferencia'))
        if trecho['preenchido_pela_regex']:
            console.print(
                f'[yellow]Trecho {indice}, preenchido pela regex:[/yellow]',
                ', '.join(trecho['preenchido_pela_regex']),
            )
        if encontrados:
            console.print(f'[bold yellow]Trecho {indice}, conferência:[/bold yellow]')
            console.print_json(json.dumps(encontrados, ensure_ascii=False))
