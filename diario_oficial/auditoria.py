"""Auditoria da separação das publicações em atos.

A pergunta é uma só: a publicação foi separada corretamente em atos? Por isso, uma regra
só reprova diante de evidência de separação errada: uma parte pequea do texto não esta contida
na transformação (um breve pedaço do inicio do ato, por exemplo)tado, dois atos
juntos ou fragmento. O tamanho do ato não é evidência: varia muito entre atos legítimos.

Regras, por nível, com a função que as aplica:

    Edição (auditar_edicao)
        EDICAO_NAO_TRANSFORMADA  edição raspada que não virou publicações
    Publicação (auditar_publicacao)
        CONTEUDO_NAO_COLETADO    sem texto; encerra a auditoria da publicação
        SEM_ATOS                 com texto, mas sem atos; também encerra a auditoria
        PROCESSAMENTO_PARCIAL    com atos, mas não marcada como processada
    Cobertura do texto (auditar_cobertura)
        TEXTO_FORA_DOS_ATOS      trecho da publicação que não está em nenhum ato, exceto
                                 o preâmbulo da Diretora Geral, removido de propósito
        ATO_FORA_DO_TEXTO        ato que não aparece, nesta ordem, na publicação
    Ato (auditar_ato)
        INICIO_SEM_TITULO        não começa com um título de ato
        ATO_CORTADO              termina no meio de uma frase, sem assinatura
        ATOS_JUNTOS              outro ato começa depois de uma assinatura

Fluxo: AuditoriaRepository.get_edicao monta a Edicao do dia, auditar_edicao devolve um
RelatorioDia e a CLI (auditar-publicacao-ato) imprime, para cada link (publicação), os
atos e se a auditoria foi aprovada ou reprovada, com os achados, e grava
RelatorioDia.resultado_publicacoes em publicacao.auditoria e os achados em
processing.log_erro (ver linhas_de_log).

As regras são heurísticas: um achado é um indício para conferir, não uma prova, e a
coluna publicacao.auditoria é saída deste código, não uma verificação humana. Para
avaliar uma regra, compare publicacao.conteudo_link com ato.conteudo_ato.

Este módulo não acessa banco nem rede.
"""

import re
from dataclasses import dataclass, field
from datetime import date

# Máximo de caracteres de texto guardados em Achado.trecho
TAMANHO_TRECHO = 80

# Tudo que separar_ato aceita como início. PORTARIA sem número é citação no corpo do ato.
INICIO_DE_ATO = re.compile(
    r'^(?:\(?\*\)?\s*)?'
    r'(?:P?ORTARIA\b.{0,30}?\bN[.ºo°]|EDITAL|EXTRATO|RETIFICAÇÃO|ERRATA|RESUMO|AVISO'
    r'|AUTORIZAÇÃO|RESOLUÇÃO|CONVOCAÇÃO|INSTRUÇÃO\s+NORMATIVA|TORNA\s+SEM\s+EFEITO'
    r'|DECISÃO|MOÇÃO|COMUNICADO|RECOMENDAÇÃO|DELIBERAÇÃO|NOTIFICAÇÃO\s+ADMINISTRATIVA'
    r'|(?:\d+ª\s+)?PRORROGAÇÃO\s+DO\s+CRONOGRAMA|CRONOGRAMA\s+PROCESSO\s+ELEITORAL'
    r'|LICENÇA\s+TRATAMENTO\s+DE\s+SAÚDE|RESULTADO\s+FINAL\s+DO\s+CHAMAMENTO'
    r'|ACORDO\s+DE\s+COOPERAÇÃO'
    r'|TERMO\s+DE\s+(?:APOSTILAMENTO|COMPROMISSO|INSTAURAÇÃO|ADESÃO)'
    r'|SECRETÁRIO\b|O\s+SECRETÁRIO\b|A\s+SECRET[AÁ]RIA\s+DO\s+MEIO\s+AMBIENTE'
    r'|SECRETARIA\s+DO\s+MEIO\s+AMBIENTE\s*-\s*RESULTADO\s+DE\s+JULGAMENTO'
    r'|CONSELHO\s+ESTADUAL\s+DO\s+MEIO\s+AMBIENTE\s*-\s*CEPRAM\.\s+ERRATA'
    r'|O\s+DIRETOR\s+GERAL\b|ADICIONAL\s+POR\s+TEMPO\s+DE\s+SERVIÇO)',
    re.IGNORECASE,
)

# Cargos que encerram um ato. Usado em ASSINATURA, que o compara sem diferenciar caixa
_CARGO = (
    r'Diretora?\s+Geral(?:\s+em\s+Exerc[ií]cio)?(?:\s+do\s+INEMA)?'
    r'|Secret[aá]ri[oa](?:\s+d[eo]\s+Meio\s+Ambiente(?:\s+do\s+Estado\s+da\s+Bahia)?)?'
    r'|Presidente'
    # Portarias do RH assinam com o nome e o órgão, sem o cargo
    r'|INST\s+DO\s+MEIO\s+AMB\s+E\s+RECURSOS\s+H[IÍ]DRICOS'
)
# Uma palavra com inicial maiúscula (fim do nome) seguida do cargo
ASSINATURA = re.compile(rf'[A-ZÀ-Ý][\wÀ-ÿ]+\s*[-–—.]?\s*(?i:{_CARGO})\b')

# Início de outro ato logo depois de uma assinatura. Anexos, coassinaturas e o número do
# processo não entram: fazem parte do mesmo ato. 'ORTARIA' existe no DOE (sem o P).
OUTRO_ATO = re.compile(
    r'(?:P?ORTARIA\s+N|EDITAL|EXTRATO|RETIFICAÇÃO|ERRATA|RESUMO|AVISO|RESOLUÇÃO'
    r'|CONVOCAÇÃO|INSTRUÇÃO\s+NORMATIVA|COMUNICADO|DECISÃO|TERMO\s+DE|TORNA\s+SEM'
    r'|O\s+(?:DIRETOR|SECRETÁRIO|INSTITUTO)|A\s+DIRETORA'
    r'|ADICIONAL\s+POR\s+TEMPO\s+DE\s+SERVIÇO)',
    re.IGNORECASE,
)

# Termina em palavra minúscula ou pontuação aberta: 'Todos nomeados pela'
FIM_INTERROMPIDO = re.compile(r'(?:\b[a-zà-ÿ]+|[,;:(–—-])$')

# Sobra que separar_ato deixa fora dos atos de propósito (texto já normalizado)
PREAMBULO_DA_DIRETORA = re.compile(
    r'A DIRETORA GERAL DO INSTITUTO.{0,300}?(?:DECIDE|RESOLVE) ?:?'
)


@dataclass
class Ato:
    """Ato já separado, como está em processing.ato.

    Attributes:
        id: id do ato
        conteudo: texto do ato (coluna conteudo_ato)
    """

    id: int
    conteudo: str | None


@dataclass
class Publicacao:
    """Publicação de uma edição, como está em processing.publicacao.

    Attributes:
        id: id da publicação
        nome_ato: nome da publicação no sumário do DOE
        conteudo_link: texto baixado do link; string vazia indica falha na coleta
        processada_para_ato: True depois que a separação em atos terminou
        atos: atos da publicação, na ordem em que foram gravados. auditar_cobertura
            depende dessa ordem
        link: endereço de onde conteudo_link foi baixado
    """

    id: int
    nome_ato: str
    conteudo_link: str | None
    processada_para_ato: bool | None
    atos: list[Ato] = field(default_factory=list)
    link: str = ''


@dataclass
class Edicao:
    """Edição do DOE de um dia, como está em processing.doe_bruto.

    Attributes:
        data: data da edição
        existe: False quando não há edição do DOE nessa data
        doe_bruto_para_publicacao: True depois da transformação em publicações
        publicacoes: publicações da edição
        id: id da edição em processing.doe_bruto
    """

    data: date
    existe: bool
    doe_bruto_para_publicacao: bool | None
    publicacoes: list[Publicacao] = field(default_factory=list)
    id: int | None = None


@dataclass
class Achado:
    """Indício de separação errada encontrado por uma regra.

    Attributes:
        regra: nome da regra (ver a lista no início do módulo)
        descricao: explicação do achado
        publicacao_id: publicação do achado; None em achado da edição
        ato_id: ato do achado; None em achado da edição ou da publicação inteira
        trecho: amostra do texto para localizar o problema, com até TAMANHO_TRECHO
            caracteres
    """

    regra: str
    descricao: str
    publicacao_id: int | None = None
    ato_id: int | None = None
    trecho: str = ''


@dataclass
class RelatorioDia:
    """Resultado da auditoria de uma edição.

    Attributes:
        edicao: edição auditada
        achados: achados de todas as regras, nos três níveis
    """

    edicao: Edicao
    achados: list[Achado]

    @property
    def aprovada(self) -> bool:
        """True se não há achados, inclusive em data sem edição ou sem publicações."""
        return not self.achados

    @property
    def resultado_publicacoes(self) -> dict[int, bool]:
        """Valor de publicacao.auditoria por publicação.

        True é auditoria aprovada: a publicação gerou atos e nada indica separação
        errada. Qualquer achado, ou nenhum ato, resulta em False. Achado da edição não
        tem publicacao_id, então não reprova nenhuma publicação.

        Returns:
            dict[int, bool]: id da publicação e resultado da auditoria
        """
        com_achado = {a.publicacao_id for a in self.achados}
        return {p.id: p.id not in com_achado for p in self.edicao.publicacoes}

    def achados_da_publicacao(self, publicacao_id: int | None) -> list[Achado]:
        """Achados de uma publicação; com None, os achados da própria edição."""
        return [a for a in self.achados if a.publicacao_id == publicacao_id]


def normalizar(texto: str | None) -> str:
    """Reduz qualquer espaço em branco (\\r\\n, espaço não separável...) a um espaço."""
    return ' '.join((texto or '').split())


def inicio_do_texto(texto: str | None) -> str:
    """Primeiros TAMANHO_TRECHO caracteres do texto normalizado."""
    return normalizar(texto)[:TAMANHO_TRECHO]


def auditar_ato(ato: Ato, publicacao_id: int) -> list[Achado]:
    """Procura evidência de que o ato foi cortado, é fragmento ou contém outro ato.

    Aplica as regras INICIO_SEM_TITULO, ATO_CORTADO e ATOS_JUNTOS. Olha só o texto do
    próprio ato; a comparação com o texto da publicação fica em auditar_cobertura.

    Args:
        ato (Ato): ato a auditar
        publicacao_id (int): id da publicação, para registrar nos achados

    Returns:
        list[Achado]: achados do ato; lista vazia se nada indica separação errada
    """
    texto = normalizar(ato.conteudo)
    achados = []

    def achado(regra, descricao, trecho):
        achados.append(Achado(regra, descricao, publicacao_id, ato.id, trecho))

    if not INICIO_DE_ATO.match(texto):
        achado(
            'INICIO_SEM_TITULO',
            'O ato não começa com um título: pode ser parte de outro ato.',
            texto[:TAMANHO_TRECHO],
        )

    assinaturas = list(ASSINATURA.finditer(texto))
    # Com assinatura no texto, o final minúsculo é de anexo ou tabela, não de corte
    if not assinaturas and FIM_INTERROMPIDO.search(texto):
        achado(
            'ATO_CORTADO',
            'O ato termina no meio de uma frase, sem assinatura.',
            texto[-TAMANHO_TRECHO:],
        )
    # Basta um achado por ato. A pontuação logo após a assinatura é ignorada
    for assinatura in assinaturas:
        depois = texto[assinatura.end() :].lstrip(' .;-–—]')
        if OUTRO_ATO.match(depois):
            achado(
                'ATOS_JUNTOS',
                'Outro ato começa depois de uma assinatura: não foi separado.',
                depois[:TAMANHO_TRECHO],
            )
            break
    return achados


def auditar_cobertura(publicacao: Publicacao) -> list[Achado]:
    """Confere se os atos, em ordem, cobrem todo o texto da publicação.

    Um ato repetido no próprio DOE é legítimo e passa. Linhas gravadas a mais não
    encontram outra ocorrência no texto e resultam em ATO_FORA_DO_TEXTO.

    A busca é exata, sem normalizar o texto. Só a sobra entre os atos é normalizada, de
    modo que espaço em branco entre dois atos não vira TEXTO_FORA_DOS_ATOS.

    Args:
        publicacao (Publicacao): publicação com os atos na ordem de gravação

    Returns:
        list[Achado]: um achado para cada ato não encontrado e cada trecho de sobra
    """
    conteudo = publicacao.conteudo_link or ''
    achados = []
    # Fim do último ato encontrado em conteudo; só avança quando um ato é encontrado
    cursor = 0

    def texto_fora(trecho):
        if PREAMBULO_DA_DIRETORA.fullmatch(trecho):
            return
        achados.append(
            Achado(
                'TEXTO_FORA_DOS_ATOS',
                f'{len(trecho)} caracteres da publicação não estão em nenhum ato.',
                publicacao.id,
                trecho=trecho[:TAMANHO_TRECHO],
            )
        )

    for ato in publicacao.atos:
        texto = ato.conteudo or ''
        posicao = conteudo.find(texto, cursor)
        if posicao == -1:
            achados.append(
                Achado(
                    'ATO_FORA_DO_TEXTO',
                    'O ato não aparece, nesta ordem, no texto da publicação.',
                    publicacao.id,
                    ato.id,
                    normalizar(texto)[:TAMANHO_TRECHO],
                )
            )
            continue
        if trecho := normalizar(conteudo[cursor:posicao]):
            texto_fora(trecho)
        cursor = posicao + len(texto)

    if trecho := normalizar(conteudo[cursor:]):
        texto_fora(trecho)
    return achados


def auditar_publicacao(publicacao: Publicacao) -> list[Achado]:
    """Audita uma publicação: coleta, processamento, cobertura do texto e cada ato.

    Sem texto ou sem atos a auditoria para no primeiro achado, porque as demais regras
    não teriam o que comparar.

    Args:
        publicacao (Publicacao): publicação a auditar, com seus atos

    Returns:
        list[Achado]: achados da publicação e dos seus atos
    """
    if not normalizar(publicacao.conteudo_link):
        # Em conteudo_link, string vazia significa falha na coleta (ver CLAUDE.md)
        return [
            Achado(
                'CONTEUDO_NAO_COLETADO',
                'A publicação está sem texto: não há o que separar em atos.',
                publicacao.id,
                trecho=publicacao.nome_ato[:TAMANHO_TRECHO],
            )
        ]
    if not publicacao.atos:
        return [
            Achado(
                'SEM_ATOS',
                'O texto foi coletado, mas nenhum ato foi extraído.',
                publicacao.id,
                trecho=inicio_do_texto(publicacao.conteudo_link),
            )
        ]

    achados = []
    if publicacao.processada_para_ato is not True:
        # A CLI grava ato por ato: um erro no meio deixa a publicação pela metade
        achados.append(
            Achado(
                'PROCESSAMENTO_PARCIAL',
                'Há atos gravados, mas a publicação não foi marcada como processada.',
                publicacao.id,
                trecho=publicacao.nome_ato[:TAMANHO_TRECHO],
            )
        )
    achados += auditar_cobertura(publicacao)
    for ato in publicacao.atos:
        achados += auditar_ato(ato, publicacao.id)
    return achados


def auditar_edicao(edicao: Edicao) -> RelatorioDia:
    """Audita uma edição e todas as suas publicações. Ponto de entrada do módulo.

    Uma data sem edição (existe=False) não gera achado: não há o que transformar.

    Args:
        edicao (Edicao): edição a auditar, com publicações e atos

    Returns:
        RelatorioDia: edição auditada e todos os achados encontrados
    """
    achados = []
    if edicao.existe and edicao.doe_bruto_para_publicacao is not True:
        achados.append(
            Achado(
                'EDICAO_NAO_TRANSFORMADA',
                'A edição foi raspada, mas ainda não foi transformada em publicações.',
            )
        )
    for publicacao in edicao.publicacoes:
        achados += auditar_publicacao(publicacao)
    return RelatorioDia(edicao, achados)


def linhas_de_log(relatorio: RelatorioDia) -> list[dict]:
    """Converte os achados do relatório em linhas de processing.log_erro.

    Args:
        relatorio (RelatorioDia): resultado da auditoria de uma edição

    Returns:
        list[dict]: uma linha por achado, com as colunas da tabela
    """
    return [
        {
            'etapa': 'auditoria',
            'tipo': achado.regra,
            'descricao': achado.descricao,
            'trecho': achado.trecho or None,
            'doe_bruto_id': relatorio.edicao.id,
            'publicacao_id': achado.publicacao_id,
            'ato_id': achado.ato_id,
        }
        for achado in relatorio.achados
    ]
