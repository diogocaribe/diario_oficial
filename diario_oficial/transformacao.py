import requests
from bs4 import BeautifulSoup
import re
import warnings


def get_conteudo_texto_link(url: str) -> str:
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')

    try:
        print(f"Acessando: {url} para obter conteúdo de texto...")
        response = requests.get(url, verify=False, timeout=(3, 10))

        if response.status_code == 200:
            # Decodifica o conteúdo e remove byte nulo
            html_content = response.content.decode('utf-8', errors='ignore').replace('\x00', '')

            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text()
            return text
        else:
            print(f'Erro ao acessar a página: {response.status_code}')
            return ""
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
}


# Preâmbulo que o DOE repete antes de uma portaria. Não pertence ao ato anterior nem ao
# seguinte, que começa no título: fica fora dos atos.
PREAMBULO_DA_DIRETORA = re.compile(
    r'A\s+DIRETORA\s+GERAL\s+DO\s+INSTITUTO.{0,300}?(?:DECIDE|RESOLVE)\s*:?\s*'
    r'(?=PORTARIA\s+N[.º°o])',
    re.DOTALL,
)


def _e_citacao(texto, inicio):
    """Indica se o termo em `inicio` é citação dentro do ato, e não início de outro."""
    anterior = texto[max(0, inicio - 30) : inicio]
    # Colado no texto anterior, como em '"...INSTRUÇÃO NORMATIVA Nº 1'
    if anterior and not anterior[-1].isspace():
        return True
    palavras = anterior.split()
    return bool(palavras) and palavras[-1].casefold() in PALAVRAS_DE_CITACAO


def separar_ato(texto):
    # Padrão para identificar o início de um ato (portaria, retificação, edital)
    # Com re.VERBOSE, espaços literais são ignorados: use \s+ entre as palavras.
    termos = r"""(?s:O\s+DIRETOR\s+GERAL\s+DO\s+INSTITUTO.{0,300}?(?:DECIDE|RESOLVE)\s*:?\s*PORTARIA\s+N[º°])|
                PORTARIA\s+N[ºo]\s+\d{1,3}(?:\.\d{3})?/\d{4}\s+-\s+Retificar\s+a\s+PORTARIA\s+N[ºo]\s+\d{1,3}(?:\.\d{3})?/\d{4}|PORTARIA\s*Nº\s*\d{2}.\d{3}/\d{4}\s+.*\s*Revogar.*\s*.*PORTARIA|PORTARIA\s+Nº\s+\d{2}.\d{3}/\d{4}|PORTARIA\s*Nº\s*\d{1,2}.\d{1,3}\s+DE\s+\d{1,2}.*\d{4}|Portaria\s+N[º°]\s+\d{8}|PORTARIA|
                EDITAL\s*DE\s+CONVOCAÇÃO|EDITAL\s*DE\s*NOTIFICAÇÃO|EDITAL\s*DE\s*PORTARIA\s*CONJUNTA|EDITAL|
                RETIFICAÇÃO|^Retificação\s+d[aeo]\b|
                ERRATA\s+(?:REFERENTE|DA|DO|DE|PORTARIA|d[aeo]\b)|
                RESUMO|
                AUTORIZAÇÃO\s+AVISO\s+DE\s+CONSULTA\s+PÚBLICA|AVISO\s+DE\s+CONSULTA\s+PÚBLICA|
                INSTRUÇÃO\s+NORMATIVA\s+N[º°o]|
                TORNA\s+SEM\s+EFEITO|
                DECISÃO\s*$|
                MOÇÃO|
                TERMO\s+DE\s+APOSTILAMENTO\s+DA\s+RESOLUÇÃO|
                TERMO\s+DE\s+COMPROMISSO|
                RESOLUÇÃO|
                EXTRATO|
                CONVOCAÇÃO|
                ^ADICIONAL\s+POR\s+TEMPO\s+DE\s+SERVIÇO|
                SECRETÁRIO\s+.*\s*RESOLVE.*
    """
    padrao_ato = rf'({termos})'

    # Encontrar todos os inícios de atos
    inicios_atos = [
        inicio
        for inicio in re.finditer(padrao_ato, texto, re.MULTILINE | re.VERBOSE)
        if not _e_citacao(texto, inicio.start())
    ]

    # Início do ato seguinte -> onde começa o preâmbulo que o antecede
    preambulos = {p.end(): p.start() for p in PREAMBULO_DA_DIRETORA.finditer(texto)}

    atos_separados = []

    # Separar os atos
    for i in range(len(inicios_atos)):
        inicio = inicios_atos[i].start()
        fim = inicios_atos[i + 1].start() if i + 1 < len(inicios_atos) else len(texto)
        fim = preambulos.get(fim, fim)
        ato = texto[inicio:fim].strip()
        atos_separados.append(ato)

    return atos_separados


# Função para processar e exibir os atos separados
def processar_atos(texto):
    atos = separar_ato(texto)
    for i, ato in enumerate(atos, 1):
        print(f"\n{'='*80}\n{ato}\n")
