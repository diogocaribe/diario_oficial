import requests
from bs4 import BeautifulSoup
import re
import warnings


def get_conteudo_texto_link(url: str) -> str:
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')

    try:
        print(f"Tentando acessar: {url}")
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


def separar_ato(texto):
    # Padrão para identificar o início de um ato (portaria, retificação, edital)
    termos = """PORTARIA\s+N[ºo]\s+\d{1,3}(?:\.\d{3})?/\d{4}\s+-\s+Retificar\s+a\s+PORTARIA\s+N[ºo]\s+\d{1,3}(?:\.\d{3})?/\d{4}|PORTARIA\s*Nº\s*\d{2}.\d{3}/\d{4}\s+.*\s*Revogar.*\s*.*PORTARIA|PORTARIA\s+Nº\s+\d{2}.\d{3}/\d{4}|PORTARIA\s*Nº\s*\d{1,2}.\d{1,3}\s+DE\s+\d{1,2}.*\d{4}|Portaria\s+Nº\s+\d{8}|PORTARIA|
                EDITAL\s*DE\s+CONVOCAÇÃO|EDITAL\s*DE\s*NOTIFICAÇÃO|EDITAL\s*DE\s*PORTARIA\s*CONJUNTA|EDITAL|
                RETIFICAÇÃO|
                ERRATA REFERENTE|
                RESUMO|RESUMO DO TERMO DE COMPROMISSO|
                AVISO DE CONSULTA PÚBLICA|AUTORIZAÇÃO AVISO DE CONSULTA PÚBLICA|
                RESOLUÇÃO|
                EXTRATO DE TERMO DE COMPROMISSO| EXTRATO|
                CONVOCAÇÃO|
                AUTORIZAÇÃO AVISO DE CONSULTA PÚBLICA|
                SECRETÁRIO\s+.*\s*RESOLVE.*
    """
    padrao_ato = rf'({termos})'

    # Encontrar todos os inícios de atos
    inicios_atos = list(re.finditer(padrao_ato, texto, re.MULTILINE | re.VERBOSE))

    atos_separados = []

    # Separar os atos
    for i in range(len(inicios_atos)):
        inicio = inicios_atos[i].start()
        fim = inicios_atos[i + 1].start() if i + 1 < len(inicios_atos) else len(texto)
        ato = texto[inicio:fim].strip()
        atos_separados.append(ato)

    return atos_separados


# Função para processar e exibir os atos separados
def processar_atos(texto):
    atos = separar_ato(texto)
    for i, ato in enumerate(atos, 1):
        print(f"\n{'='*80}\n{ato}\n")
