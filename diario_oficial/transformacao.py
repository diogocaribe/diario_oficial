import requests
from bs4 import BeautifulSoup
import re
import warnings


def get_conteudo_texto_link(url: str) -> str | None:
    """Baixa o texto de um link do DOE.

    Args:
        url (str): link da publicação

    Returns:
        str | None: o texto da página; None se o link é um PDF, que fica fora do
        pipeline; string vazia se a coleta falhou
    """
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')

    try:
        print(f"Acessando: {url} para obter conteúdo de texto...")
        # stream: o cabeçalho já identifica o PDF, sem baixar o arquivo
        with requests.get(url, verify=False, timeout=(3, 10), stream=True) as response:
            if response.status_code != 200:
                print(f'Erro ao acessar a página: {response.status_code}')
                return ""

            if (
                'pdf' in response.headers.get('Content-Type', '').lower()
                or response.content.lstrip().startswith(b'%PDF')
            ):
                print(f'Link é um PDF, não será coletado: {url}')
                return None

            # Decodifica o conteúdo e remove byte nulo
            html_content = response.content.decode('utf-8', errors='ignore').replace('\x00', '')

            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text()
    except requests.RequestException as e:
        print(f'Erro de rede ao buscar conteúdo de {url}: {e}')
        return ""
    except Exception as e:
        print(f'Erro inesperado: {e}')
        return ""


# Palavra antes do termo que indica citação no corpo ('nomeados pela PORTARIA Nº ...'),
# e não início de ato. Título de ato vem depois de fim de frase ou de assinatura.
PALAVRAS_DE_CITACAO = {
    'a', 'à', 'as', 'às', 'o', 'os', 'da', 'das', 'de', 'do', 'dos', 'na', 'nas', 'no',
    'nos', 'pela', 'pelas', 'pelo', 'pelos', 'e', 'ou', 'em', 'com', 'sob', 'esta',
    'desta', 'nesta', 'referida', 'citada', 'mencionada', 'mediante', 'conforme', 'vide',
    'ao', 'aos', 'presente', 'referente', 'proclamou',
}

# Trecho antes do termo em que ele é conteúdo do ato: o valor de um campo, o texto
# corrigido por uma errata ('Onde se lê: PORTARIA Nº ...') ou um artigo ('Art. 1º - TORNA
# SEM EFEITO ...').
CONTEXTO_DE_CITACAO = re.compile(
    r'(?:onde\s+se\s+l[êe]|leia-se|finalidade)\s*:?\s*["“]?\s*$'
    r'|\bart\.?\s*\d+[º°]?\s*[-–]?\s*$',
    re.IGNORECASE,
)

# 'RESOLVE:PORTARIA Nº ...': o título vem colado ao fim do preâmbulo, e não é citação
FIM_DE_PREAMBULO = re.compile(r'(?:RESOLVE|DECIDE)\s*:$')


# Preâmbulo que o DOE repete antes de uma portaria. Não pertence ao ato anterior nem ao
# seguinte, que começa no título: fica fora dos atos. 'O DIRETOR GERAL DO INSTITUTO', sem
# 'EM EXERCÍCIO', não entra: esse preâmbulo abre o ato (ver separar_ato).
PREAMBULO_DE_PORTARIA = re.compile(
    r'(?:A\s+DIRETORA\s+GERAL(?:,?\s+EM\s+EXERCÍCIO,?)?\s+DO\s+INSTITUTO'
    r'|A\s+Diretora\s+Geral\s+do\s+INSTITUTO'
    r'|O\s+SECRETÁRIO\s+D[EO]\s+MEIO\s+AMBIENTE'
    r'|O\s+DIRETOR\s+GERAL,?\s+(?:EM\s+EXERC\w+,?|SUBSTITUTO)\s+DO\s+INSTITUTO)'
    r'(?:(?!(?i:RESOLVE|DECIDE)).){0,1200}(?i:DECIDE|RESOLVE)\s*:?\s*'
    r'(?=PORTARIA\s+(?:CONJUNTA|N[.º°o]))',
    re.DOTALL,
)

# Título que o DOE repete, sem corpo, antes do título completo do mesmo ato
# ('RESOLUÇÃO Nº 056/2024' seguido de 'RESOLUÇÃO FERFA Nº 56 DE 13 DE SETEMBRO...').
TITULO_SEM_CORPO = re.compile(
    r'EDITAL\s+DE\s+NOTIFICAÇÃO'
    r'|EDITAL\s+DE\s+CONVOCAÇÃO(?:\s+PROCESSO\s+SELETIVO\s+SIMPLIFICADO)?'
    r'|EDITAL\s+(?:Nº\s*)?[\d/]+\s*-?'
    r'|EDITAL\s+DE\s+\d{1,2}\s+DE\s+\w+\s+DE\s+\d{4}'
    r'|RESOLUÇÃO(?:\s+[A-Z]+)?\s+N[.º°]+\s*[\d/ ]+'
    r'|RESUMO'
    r'|TERMO\s+ADITIVO\s+(?:DO\s+)?TCCA\s+Nº\s*[\d/]+[\s​]*'
    r'|AVISO\s+DE\s+PRORROGAÇÃO\s+DE\s+PRAZOS\s+E\s+ALTERAÇÃO\s+DE\s+CRONOGRAMA'
)


# Títulos que só valem na abertura da publicação: no corpo dos atos são citações comuns
# ('Conceder AUTORIZAÇÃO DE SUPRESSÃO', 'no âmbito do Acordo de Cooperação Técnica nº 09').
# Usado em separar_ato, com re.VERBOSE: use \s+ entre as palavras.
TITULOS_DE_ABERTURA = r"""
    Acordo\s+de\s+Cooperação(?:\s+Técnica)?\s+n[º°]|
    Instrução\s+Normativa\s+[A-Z/]+\s+N[º°o]|
    AUTORIZAÇÃO\s+A\s+SECRET[AÁ]RIA|
    AUTORIZAÇÃO\s+DE\s+CONSULTA|
    A\s+SECRET[AÁ]RIA\s+DO\s+MEIO\s+AMBIENTE|
    (?s:O\s+SECRETÁRIO\b.{0,300}?\sRESOLVEM?\s(?!PORTARIA))|
    SECRETARIA\s+DO\s+MEIO\s+AMBIENTE\s*-\s*RESULTADO\s+DE\s+JULGAMENTO|
    Extrato\s+d[eo]\s|Resumo\s+d[eo]\s|
    Portaria\s+n[º°]|Na\s+Portaria\s+n[º°]|Errata\s+da\s+Portaria|
    ERRATA\s+(?:-|Processo)|
    Tornar\s+sem\s+efeito|
    PORTARIAS\s+DO\s+DIRETOR|
    TERMO\s+DE\s+(?:CESSÃO|DECISÃO)|DECISÃO\s+TERMO|
    (?:[\wº°]+\s+)?TERMO\s+ADITIVO|
    INTIMAÇÃO\s+-|
    PROTOCOLO\s+DE\s+INTENÇÕES|
    NOTA\s+DE\s+ALERTA|
    LISTA\s+(?:PRÉVIA|FINAL)\s+DE\s+HABILITADOS|
    EDITAIS\s+DE\s+ELEIÇÃO|
    PRORROGAÇÃO\s+DE\s+PRAZO|
    CONCESSÃO\s+AUXÍLIO|
    ALTERAÇÃO\s+DO\s+NOME|
    (?:Salvador,\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\.?\s+)?
    (?:A\s+Comissão\s+Eleitoral|As\s+Comissões\s+Eleitorais|Os\s+Comitês\s+de\s+Bacias|
    (?s:O\s+I(?:NSTITUTO|nstituto)\s.{0,80}?informa\s+sobre\s+a\s+(?:altera|ALTERA)))
"""


def _e_citacao(texto, inicio):
    """Indica se o termo em `inicio` é citação dentro do ato, e não início de outro."""
    anterior = texto[max(0, inicio - 30) : inicio]
    if FIM_DE_PREAMBULO.search(anterior):
        return False
    # Colado no texto anterior, como em '"...INSTRUÇÃO NORMATIVA Nº 1'
    if anterior and not anterior[-1].isspace():
        return True
    if CONTEXTO_DE_CITACAO.search(anterior):
        return True
    palavras = anterior.split()
    return bool(palavras) and palavras[-1].casefold() in PALAVRAS_DE_CITACAO


def _unir_titulo_sem_corpo(texto, inicios):
    """Descarta o início que vem logo depois de um título sem corpo, que abre o mesmo ato."""
    unidos = []
    for inicio in inicios:
        if unidos and TITULO_SEM_CORPO.fullmatch(texto[unidos[-1] : inicio].strip()):
            continue
        unidos.append(inicio)
    return unidos


def separar_ato(texto):
    # Padrão para identificar o início de um ato (portaria, retificação, edital)
    # Com re.VERBOSE, espaços literais são ignorados: use \s+ entre as palavras.
    termos = r"""(?s:O\s+DIRETOR\s+GERAL\s+DO\s+INSTITUTO.{0,300}?(?:DECIDE|RESOLVE)\s*:?\s*PORTARIA\s+N[º°])|
                PORTARIA\s+N[ºo]\s+\d{1,3}(?:\.\d{3})?/\d{4}\s+-\s+Retificar\s+a\s+PORTARIA\s+N[ºo]\s+\d{1,3}(?:\.\d{3})?/\d{4}|PORTARIA\s*Nº\s*\d{2}.\d{3}/\d{4}\s+.*\s*Revogar.*\s*.*PORTARIA|PORTARIA\s+Nº\s+\d{2}.\d{3}/\d{4}|PORTARIA\s*Nº\s*\d{1,2}.\d{1,3}\s+DE\s+\d{1,2}.*\d{4}|Portaria\s+N[º°]\s+\d{5,8}|PORTARIA(?=\s+(?:CONJUNTA|(?:[A-Z/]+\s+){0,3}[Nn][.º°o]|\d))|
                \(?\*\)?\s*(?:PORTARIA|EDITAL|RESOLUÇÃO|EXTRATO)|
                (?<!\S)(?:ORTARIA|POTARIA)\s+N|
                EDITAL\s*DE\s+CONVOCAÇÃO|EDITAL\s*DE\s*NOTIFICAÇÃO|EDITAL\s*DE\s*PORTARIA\s*CONJUNTA|EDITAL|
                RETIFICAÇÃO|^Retificação\s+d[aeo]\b|
                ERRATA\s+(?:REFERENTE|referente|DA|DO|DE|AO|PORTARIA|d[aeo]\b)|
                RESUMO|
                AUTORIZAÇÃO\s+AVISO\s+DE\s+CONSULTA\s+PÚBLICA|AVISO\s+DE\s+CONSULTA\s+PÚBLICA|
                AVISO\s+DE\s+CHAMAMENTO\s+PÚBLICO|
                AVISO\s+DE\s+PRORROGAÇÃO|
                AUTORIZAÇÃO\s+A\s+SECRET[AÁ]RIA\s+DO\s+MEIO\s+AMBIENTE\s+DO\s+ESTADO(?:\s+DA\s+BAHIA)?,?\s+torna|
                CONSELHO\s+ESTADUAL\s+DO\s+MEIO\s+AMBIENTE\s*-\s*CEPRAM\.?\s+Errata|
                RESULTADO\s+FINAL\s+DO\s+CHAMAMENTO|
                INSTRUÇÃO\s+NORMATIVA(?:\s+CONJUNTA)?(?:\s+[A-Z/]+)?\s+N[º°o]|
                TORNA\s+SEM\s+EFEITO|
                DECISÃO\s*$|
                MOÇÃO|
                COMUNICADO\b|
                RECOMENDAÇÃO\s+(?:[A-Z]+\s+)?N[º°o]|
                DELIBERAÇÃO\s+N[º°o]|
                (?:\d+ª\s+)?PRORROGAÇÃO\s+DO\s+CRONOGRAMA|
                E?CRONOGRAMA\s+PROCESSO\s+ELEITORAL|
                NOTIFICAÇÃO\s+ADMINISTRATIVA|
                LICENÇA\s+TRATAMENTO\s+DE\s+SAÚDE|
                LICENÇA\s+M[ÉÊE]DICA\s+(?:DEFERIDA|CONCEDIDA)|
                APOSTILA\s+N|
                TERMO\s+DE\s+APOSTILAMENTO\s+DA\s+RESOLUÇÃO|
                TERMO\s+DE\s+COMPROMISSO|
                TERMO\s+DE\s+INSTAURAÇÃO|
                TERMO\s+DE\s+ADESÃO\s+E\s+COMPROMISSO|
                (?:PRIMEIRO|SEGUNDO|TERCEIRO|QUARTO|QUINTO|\d+[º°])\s+TERMO\s+ADITIVO\s+AO|
                (?s:A\s+Diretora\s+Geral\s+do\s+INSTITUTO.{0,200}?RESOLVE:\s+Retificar)|
                RESOLUÇÃO|
                EXTRATO|
                CONVOCAÇÃO|
                ^ADICIONAL\s+POR\s+TEMPO\s+DE\s+SERVIÇO|
                SECRETÁRIO\s+.*\s*RESOLVE.*
    """
    padrao_ato = rf'({termos}|\A\s*(?:{TITULOS_DE_ABERTURA}))'

    # Encontrar todos os inícios de atos
    inicios_atos = _unir_titulo_sem_corpo(
        texto,
        [
            inicio.start()
            for inicio in re.finditer(padrao_ato, texto, re.MULTILINE | re.VERBOSE)
            if not _e_citacao(texto, inicio.start())
        ],
    )

    # Início do ato seguinte -> onde começa o preâmbulo que o antecede
    preambulos = {p.end(): p.start() for p in PREAMBULO_DE_PORTARIA.finditer(texto)}

    atos_separados = []

    # Separar os atos
    for i in range(len(inicios_atos)):
        inicio = inicios_atos[i]
        fim = inicios_atos[i + 1] if i + 1 < len(inicios_atos) else len(texto)
        fim = preambulos.get(fim, fim)
        ato = texto[inicio:fim].strip()
        atos_separados.append(ato)

    return atos_separados


# Função para processar e exibir os atos separados
def processar_atos(texto):
    atos = separar_ato(texto)
    for i, ato in enumerate(atos, 1):
        print(f"\n{'='*80}\n{ato}\n")
