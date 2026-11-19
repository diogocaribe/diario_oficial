"""Contrato comum das extrações e a função que roda qualquer uma delas.

Cada extração (um subtipo de auto em ``auto_infracao``, ou o módulo de outro tipo de
ato) descreve o que é dela numa ``Extracao``: o tipo de ato (sigla de
``dominio.tipo_ato``) e a pasta do DOE (``dominio.tipo_publicacao``) de onde vêm os
atos, o esquema e as instruções do modelo, como cortar o texto em trechos e como
conferir a resposta. ``extrair`` é igual para
todas: corta o texto, chama o modelo por trecho e guarda o erro do trecho que falhar.
"""

from collections.abc import Callable
from dataclasses import dataclass

from langchain_core.runnables import Runnable
from pydantic import BaseModel

from diario_oficial.extracao import llm
from diario_oficial.extracao.normalizacao import normalizar_texto


def texto_inteiro(texto: str | None) -> list[str]:
    """Corte padrão: o texto normalizado inteiro, num trecho só (nenhum se vazio)."""
    normalizado = normalizar_texto(texto)
    return [normalizado] if normalizado else []


@dataclass(frozen=True)
class Extracao:
    """O que muda de uma extração para outra.

    - ``sigla_tipo_ato``: sigla em ``dominio.tipo_ato`` dos atos a extrair.
    - ``pasta``: nome em ``dominio.tipo_publicacao`` onde esses atos são publicados;
      ``None`` aceita qualquer pasta.
    - ``esquema``: modelo Pydantic da resposta do LLM, com uma lista de registros no
      campo ``campo_registros`` (um registro por ato/auto encontrado no trecho).
    - ``instrucoes``: mensagem de sistema do modelo.
    - ``separar_trechos``: corta o texto do ato nos trechos que vão para o modelo.
    - ``preencher_vazios_pela_regex``: corrige a resposta do modelo onde ele deixou
      um campo vazio (``null``) que a regex consegue ler no trecho. Exemplo: o texto
      diz "Interdição Temporária" e o modelo devolveu ``modalidade = null``; a função
      grava ``temporaria``. Nunca troca um valor que o modelo preencheu. Devolve os
      nomes dos campos preenchidos (ex.: ``['modalidade']``); ``None`` se a extração
      usa só o que o modelo respondeu.
    - ``conferir``: compara a resposta (já com os vazios preenchidos) com o trecho
      (regex) e devolve um dict; ``None`` se a extração não tem conferência.
    - ``entidade``: classe de ``database/entity/auto_infracao.py`` onde cada
      registro é gravado (ex.: ``AutoInterdicao``); ``None`` se a extração não grava.
    """

    sigla_tipo_ato: str
    pasta: str | None
    esquema: type[BaseModel]
    instrucoes: str
    campo_registros: str
    separar_trechos: Callable[[str | None], list[str]] = texto_inteiro
    preencher_vazios_pela_regex: Callable[[str, BaseModel], list[str]] | None = None
    conferir: Callable[[str, BaseModel], dict] | None = None
    entidade: type | None = None

    def criar_extrator(self, **parametros) -> Runnable:
        """``extracao.llm.criar_extrator`` com o esquema e as instruções desta extração.

        ``parametros`` vão para o ``ChatOllama`` (modelo, base_url, num_ctx...).
        """
        return llm.criar_extrator(self.esquema, self.instrucoes, **parametros)


def extrair(texto: str | None, extracao: Extracao, extrator: Runnable) -> list[dict]:
    """Extrai os registros de cada trecho do texto.

    Devolve um dict por trecho, com ``trecho``, ``registros`` (dicts do esquema) e
    ``modelos`` (os mesmos registros como objetos Pydantic, para a gravação), mais
    ``preenchido_pela_regex`` (campos que o modelo deixou vazios e a regex preencheu),
    ``conferencia`` quando a extração tem conferência, ou ``erro`` quando o modelo
    falhou nesse trecho (saída fora do esquema, Ollama fora do ar...).
    """
    resultados = []
    for trecho in extracao.separar_trechos(texto):
        try:
            resposta = extrator.invoke({'trecho': trecho})
        except Exception as erro:
            resultados.append(
                {
                    'trecho': trecho,
                    'registros': [],
                    'modelos': [],
                    'preenchido_pela_regex': [],
                    'erro': repr(erro),
                }
            )
            continue
        preenchidos = []
        if extracao.preencher_vazios_pela_regex is not None:
            preenchidos = extracao.preencher_vazios_pela_regex(trecho, resposta)
        objetos = list(getattr(resposta, extracao.campo_registros))
        resultado = {
            'trecho': trecho,
            'registros': [registro.model_dump() for registro in objetos],
            'modelos': objetos,
            'preenchido_pela_regex': preenchidos,
        }
        if extracao.conferir is not None:
            resultado['conferencia'] = extracao.conferir(trecho, resposta)
        resultados.append(resultado)
    return resultados


def achados(conferencia: dict | None) -> dict:
    """Só as chaves da conferência que apontam algo (lista ou dict não vazio)."""
    return {chave: valor for chave, valor in (conferencia or {}).items() if valor}
