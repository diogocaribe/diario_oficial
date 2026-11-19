"""Cadeia do LangChain que extrai um esquema Pydantic de um texto com o Ollama local."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel


def criar_extrator(
    esquema: type[BaseModel],
    instrucoes: str,
    modelo: str = 'qwen3:14b',
    base_url: str = 'http://localhost:11434',
    num_ctx: int = 8192,
    temperature: float = 0.0,
    top_k: int = 10,
    top_p: float = 0.5,
    repeat_penalty: float = 1.0,
    num_predict: int = 6144,
    seed: int = 42,
    reasoning: bool = False,
) -> Runnable:
    """Prompt + ChatOllama com saída estruturada em ``esquema``.

    ``instrucoes`` vai como mensagem de sistema e o texto a extrair entra na
    variável ``{trecho}`` da mensagem do usuário. O esquema vira o ``format`` do
    Ollama e a geração fica presa à gramática do JSON.

    Os padrões são para cópia fiel, não para texto criativo:

    - ``temperature=0`` escolhe sempre o token mais provável; ``top_k`` e ``top_p``
      cortam os tokens improváveis caso a temperatura seja aumentada.
    - ``repeat_penalty=1.0`` desliga a penalidade de repetição (o padrão do Ollama é
      1.1). Copiar é repetir tokens do trecho: com a penalidade, o modelo tende a
      trocar dígitos de documentos, processos e coordenadas que já apareceram.
    - ``num_predict`` limita a resposta, para o modelo não entrar em laço gerando
      coordenadas ou espécies sem fim. Cada par de coordenadas custa uns 40 tokens:
      6144 cabe o maior polígono da série (112 vértices, ato 10519) e, somado ao
      prompt, ainda fica dentro do ``num_ctx`` de 8192. Limite menor corta o JSON e a
      extração do trecho falha.
    - ``seed`` fixa a amostragem, para a mesma entrada dar a mesma saída.
    - ``mirostat=0`` mantém a amostragem controlada por ``top_k``/``top_p``.
    - ``reasoning=False`` desliga o modo de raciocínio dos modelos que o têm (Qwen3).
      Ligado, o modelo gasta o ``num_predict`` pensando antes do JSON e a resposta
      sai cortada. Em modelos sem esse modo (Llama 3) não muda nada.
    """
    from langchain_ollama import ChatOllama

    llm = ChatOllama(
        model=modelo,
        base_url=base_url,
        num_ctx=num_ctx,
        temperature=temperature,
        top_k=top_k,
        top_p=top_p,
        repeat_penalty=repeat_penalty,
        num_predict=num_predict,
        seed=seed,
        mirostat=0,
        reasoning=reasoning,
    )
    prompt = ChatPromptTemplate.from_messages(
        [('system', instrucoes), ('human', 'Trecho:\n{trecho}')]
    )
    return prompt | llm.with_structured_output(esquema, method='json_schema')
