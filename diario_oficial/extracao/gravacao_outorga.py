"""Converte a saída de ``extrair`` das outorgas nas entidades do esquema ``recurso_hidrico``.

As regras comuns a todas as gravações (campo na coluna de mesmo nome, endereço, pessoa,
geometria) ficam em ``gravacao_comum``. As diferenças de forma:

- ``outorgado`` vira ``public.pessoa`` (``outorgado``), o nome como está na portaria
  (``outorgado_nome``) e o endereço da sede (``endereco_outorgado``), que é da outorga;
- cada uso vira a entidade do seu ``modo`` (``UsoCaptacao``, ``UsoLancamento``,
  ``UsoIntervencao``), que grava o ``tipo_uso``;
- ``coordenada`` do ponto vira as colunas ``latitude`` e ``longitude`` (como no texto)
  e ``ponto`` é convertido do datum do texto para o SIRGAS 2000.

Não abre conexão: a pessoa já gravada com o mesmo documento é reaproveitada pelo
repositório (``RecursoHidricoRepository``).
"""

from diario_oficial.database.entity import recurso_hidrico as entidades
from diario_oficial.extracao import modelo_outorga
from diario_oficial.extracao.gravacao_comum import (
    para_endereco,
    para_geometria,
    para_pessoa,
    valores_das_colunas,
)

# Entidade de cada modo do uso.
ENTIDADE_DO_MODO = {
    'captacao_subterranea': entidades.UsoCaptacao,
    'captacao_superficial': entidades.UsoCaptacao,
    'lancamento_efluente': entidades.UsoLancamento,
    'intervencao': entidades.UsoIntervencao,
}


def _ponto(registro: modelo_outorga.PontoUso) -> entidades.PontoUso:
    valores = valores_das_colunas(entidades.PontoUso, registro, {'coordenada', 'ponto'})
    coordenada = registro.coordenada
    return entidades.PontoUso(
        **valores,
        latitude=coordenada.latitude if coordenada else None,
        longitude=coordenada.longitude if coordenada else None,
        ponto=para_geometria(registro.ponto, registro.sistema_referencia_espacial),
    )


def _parametro(
    registro: modelo_outorga.ParametroEfluente,
) -> entidades.ParametroEfluente:
    return entidades.ParametroEfluente(
        **valores_das_colunas(entidades.ParametroEfluente, registro, set())
    )


def para_uso(registro: modelo_outorga.Uso) -> entidades.UsoRecursoHidrico:
    """Um uso Pydantic como a entidade do seu modo, com pontos e parâmetros."""
    entidade = ENTIDADE_DO_MODO[registro.modo]
    valores = valores_das_colunas(entidade, registro, {'pontos', 'parametros'})
    if isinstance(registro, modelo_outorga.UsoLancamento):
        valores['parametros'] = [_parametro(item) for item in registro.parametros]
    return entidade(**valores, pontos=[_ponto(ponto) for ponto in registro.pontos])


def para_outorga(registro: modelo_outorga.Outorga) -> entidades.Outorga:
    """Uma outorga Pydantic como entidade, com outorgado, endereço e usos."""
    valores = valores_das_colunas(entidades.Outorga, registro, {'outorgado', 'usos'})
    outorgado = registro.outorgado
    if outorgado is not None:
        valores.update(
            outorgado=para_pessoa(outorgado),
            outorgado_nome=outorgado.nome,
            endereco_outorgado=para_endereco(outorgado.endereco, entidades.Endereco),
        )
    return entidades.Outorga(**valores, usos=[para_uso(uso) for uso in registro.usos])


def para_trechos(
    ato_id: int,
    sigla_tipo_ato: str,
    trechos: list[dict],
    modelo_llm: str | None = None,
) -> list[entidades.ExtracaoTrecho]:
    """Os trechos de ``extrair`` (com a chave ``modelos``) como entidades."""
    return [
        entidades.ExtracaoTrecho(
            ato_id=ato_id,
            sigla_tipo_ato=sigla_tipo_ato,
            trecho=trecho['trecho'],
            erro=trecho.get('erro'),
            preenchido_pelo_modelo=trecho.get('preenchido_pelo_modelo', []),
            erro_modelo=trecho.get('erro_modelo'),
            modelo_llm=modelo_llm,
            outorgas=[para_outorga(registro) for registro in trecho.get('modelos', [])],
        )
        for trecho in trechos
    ]
