"""Contrato comum das extrações e a função que roda qualquer uma delas.

Cada extração (um subtipo de auto em ``auto_infracao``, ou o módulo de outro tipo de
ato) descreve o que é dela numa ``Extracao``: o tipo de ato (sigla de
``dominio.tipo_ato``) e a pasta do DOE (``dominio.tipo_publicacao``) de onde vêm os
atos, o esquema e as instruções do modelo, como cortar o texto em trechos e como
conferir a resposta. ``extrair`` é igual para
todas: corta o texto, chama o modelo por trecho e guarda o erro do trecho que falhar.

Quando o texto segue um modelo fixo (as outorgas), a extração principal é a regex
(``extrair_pela_regex``) e o modelo de linguagem só é chamado para os campos
obrigatórios que ela deixou vazios (``campos_vazios``); a resposta do modelo só
preenche esses campos (``preencher_vazios_pelo_modelo``).
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from langchain_core.runnables import Runnable, RunnableLambda
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
    - ``entidade``: classe onde cada registro é gravado (ex.: ``AutoInterdicao`` de
      ``database/entity/auto_infracao.py``, ``Outorga`` de
      ``database/entity/recurso_hidrico.py``); ``None`` se a extração não grava.
    - ``extrair_pela_regex``: lê o trecho sem o modelo e devolve o ``esquema``. Com
      ela, o modelo só é chamado se ``campos_vazios`` apontar algum campo obrigatório
      vazio, e só esses campos são copiados da resposta dele.
    - ``campos_vazios``: caminhos dos campos obrigatórios vazios na resposta da regex
      (ex.: ``outorgas.0.usos.1.pontos.0.captacao_horas_dia``).
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
    extrair_pela_regex: Callable[[str], BaseModel] | None = None
    campos_vazios: Callable[[BaseModel], list[str]] | None = None

    def criar_extrator(self, **parametros) -> Runnable:
        """``extracao.llm.criar_extrator`` com o esquema e as instruções desta extração.

        ``parametros`` vão para o ``ChatOllama`` (modelo, base_url, num_ctx...). Com
        ``extrair_pela_regex``, o extrator roda a regex e só chama o modelo para os
        campos vazios; devolve uma ``RespostaDaRegex``.
        """
        modelo = llm.criar_extrator(self.esquema, self.instrucoes, **parametros)
        if self.extrair_pela_regex is None:
            return modelo
        return RunnableLambda(
            lambda entrada: regex_com_modelo(entrada['trecho'], self, modelo)
        )


@dataclass
class RespostaDaRegex:
    """Resposta da regex, com os campos que o modelo preencheu e o erro dele."""

    resposta: BaseModel
    preenchido_pelo_modelo: list[str] = field(default_factory=list)
    erro_modelo: str | None = None


def _no_caminho(objeto, partes: list[str]):
    """O valor em ``partes`` (atributos e índices de lista), ou ``None`` se não houver."""
    for parte in partes:
        if isinstance(objeto, list):
            if not parte.isdigit() or int(parte) >= len(objeto):
                return None
            objeto = objeto[int(parte)]
        elif objeto is None or not hasattr(objeto, parte):
            return None
        else:
            objeto = getattr(objeto, parte)
    return objeto


def preencher_vazios_pelo_modelo(
    resposta: BaseModel, do_modelo: BaseModel, caminhos: list[str]
) -> tuple[BaseModel, list[str]]:
    """Copia do modelo só os campos de ``caminhos`` que estão vazios na ``resposta``.

    Campo que o modelo também deixou vazio, ou caminho que não existe na resposta dele
    (ele achou menos usos ou pontos), fica como está. A resposta é validada de novo no
    fim, para os validadores calcularem o que depende do valor copiado (ex.: a vazão
    na outra unidade). Devolve a resposta e os caminhos preenchidos.
    """
    preenchidos = []
    for caminho in caminhos:
        *pai, nome = caminho.split('.')
        destino = _no_caminho(resposta, pai)
        valor = _no_caminho(do_modelo, caminho.split('.'))
        if destino is None or valor in (None, [], ''):
            continue
        if getattr(destino, nome, None) not in (None, [], ''):
            continue
        setattr(destino, nome, valor)
        preenchidos.append(caminho)
    if preenchidos:
        resposta = type(resposta).model_validate(resposta.model_dump())
    return resposta, preenchidos


def regex_com_modelo(
    trecho: str, extracao: Extracao, modelo: Runnable
) -> RespostaDaRegex:
    """Roda a regex e, se faltar campo obrigatório, pede ao modelo só esses campos.

    Se o modelo falhar (Ollama fora do ar, saída fora do esquema), fica a resposta da
    regex e o erro vai em ``erro_modelo``.
    """
    resposta = extracao.extrair_pela_regex(trecho)
    vazios = extracao.campos_vazios(resposta) if extracao.campos_vazios else []
    if not vazios:
        return RespostaDaRegex(resposta)
    try:
        do_modelo = modelo.invoke({'trecho': trecho})
    except Exception as erro:
        return RespostaDaRegex(resposta, erro_modelo=repr(erro))
    resposta, preenchidos = preencher_vazios_pelo_modelo(resposta, do_modelo, vazios)
    return RespostaDaRegex(resposta, preenchidos)


def extrair(texto: str | None, extracao: Extracao, extrator: Runnable) -> list[dict]:
    """Extrai os registros de cada trecho do texto.

    Devolve um dict por trecho, com ``trecho``, ``registros`` (dicts do esquema) e
    ``modelos`` (os mesmos registros como objetos Pydantic, para a gravação), mais
    ``preenchido_pela_regex`` (campos que o modelo deixou vazios e a regex preencheu),
    ``preenchido_pelo_modelo`` (o contrário, nas extrações pela regex),
    ``conferencia`` quando a extração tem conferência, ou ``erro`` quando o modelo
    falhou nesse trecho (saída fora do esquema, Ollama fora do ar...). Nas extrações
    pela regex, a falha do modelo não descarta o trecho: vai em ``erro_modelo``.
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
                    'preenchido_pelo_modelo': [],
                    'erro': repr(erro),
                }
            )
            continue
        pelo_modelo, erro_modelo = [], None
        if isinstance(resposta, RespostaDaRegex):
            pelo_modelo, erro_modelo = (
                resposta.preenchido_pelo_modelo,
                resposta.erro_modelo,
            )
            resposta = resposta.resposta
        preenchidos = []
        if extracao.preencher_vazios_pela_regex is not None:
            preenchidos = extracao.preencher_vazios_pela_regex(trecho, resposta)
        objetos = list(getattr(resposta, extracao.campo_registros))
        resultado = {
            'trecho': trecho,
            'registros': [registro.model_dump() for registro in objetos],
            'modelos': objetos,
            'preenchido_pela_regex': preenchidos,
            'preenchido_pelo_modelo': pelo_modelo,
        }
        if erro_modelo is not None:
            resultado['erro_modelo'] = erro_modelo
        if extracao.conferir is not None:
            resultado['conferencia'] = extracao.conferir(trecho, resposta)
        resultados.append(resultado)
    return resultados


def achados(conferencia: dict | None) -> dict:
    """Só as chaves da conferência que apontam algo (lista ou dict não vazio)."""
    return {chave: valor for chave, valor in (conferencia or {}).items() if valor}
