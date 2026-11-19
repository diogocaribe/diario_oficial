"""Extrai com o LLM local os dados de um tipo de ato, mostra e, se pedido, grava.

O tipo de ato é a sigla de ``dominio.tipo_ato`` (ex.: AIIN) e escolhe a extração em
``diario_oficial.extracao.registro.EXTRACOES``. Pega os atos ligados a esse tipo em
processing.ato_tipo_ato (que só existe para publicações com
auditoria = true), na pasta da extração (dominio.tipo_publicacao), quando ela define
uma. Cada ato é mostrado com o texto completo, os trechos e os registros extraídos; com
``--save-db``, o resultado também é gravado no esquema auto_infracao, trocando a
extração anterior do mesmo ato.

Rodar a partir da raiz do repositório:

    python Scripts/extrair_dados_atos.py AIIN --limite 20
    python Scripts/extrair_dados_atos.py AIIN --data 24-09-2026
    python Scripts/extrair_dados_atos.py AIIN --data 26-06-2026 # multiplos autos
    python Scripts/extrair_dados_atos.py AIIN --ato-id 5604 --ato-id 1469
    python Scripts/extrair_dados_atos.py AIIN --limite 20 --silencioso
    python Scripts/extrair_dados_atos.py AIIN --save-db --pular-extraidos --silencioso
    python Scripts/extrair_dados_atos.py AIMU --limite 20  # qualquer subtipo de auto
"""

from datetime import datetime
from typing import Optional

import typer

from diario_oficial.extracao.registro import EXTRACOES
from diario_oficial.extracao_dados_atos import extrair_dados_atos


def main(
    tipo: str = typer.Argument(
        ..., help=f'Sigla do tipo de ato: {", ".join(sorted(EXTRACOES))}.'
    ),
    data: Optional[str] = typer.Option(None, help='Data da edição, DD-MM-YYYY.'),
    ato_id: Optional[list[int]] = typer.Option(None, help='Id do ato (repetível).'),
    limite: Optional[int] = typer.Option(None, help='Máximo de atos a processar.'),
    modelo: Optional[str] = typer.Option(None, help='Modelo do Ollama.'),
    silencioso: bool = typer.Option(
        False, '--silencioso', help='Mostra só o resumo de cada ato.'
    ),
    save_db: bool = typer.Option(
        False,
        '--save-db/--no-save-db',
        help='Grava no esquema auto_infracao (troca a extração anterior do ato).',
    ),
    pular_extraidos: bool = typer.Option(
        False,
        '--pular-extraidos',
        help='Não extrai de novo os atos que já têm extração gravada.',
    ),
):
    extracao = EXTRACOES.get(tipo.upper())
    if extracao is None:
        raise typer.BadParameter(
            f'sem extração para {tipo!r}; disponíveis: {", ".join(sorted(EXTRACOES))}',
            param_hint='TIPO',
        )
    if save_db and extracao.entidade is None:
        raise typer.BadParameter(
            f'a extração {extracao.sigla_tipo_ato} não tem tabela para gravar',
            param_hint='--save-db',
        )
    extrair_dados_atos(
        extracao,
        data=datetime.strptime(data, '%d-%m-%Y').date() if data else None,
        ato_ids=ato_id,
        limite=limite,
        modelo=modelo,
        silencioso=silencioso,
        save_db=save_db,
        pular_extraidos=pular_extraidos,
    )


if __name__ == '__main__':
    typer.run(main)
