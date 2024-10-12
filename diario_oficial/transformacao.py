import requests
from bs4 import BeautifulSoup
import re
import warnings


def get_conteudo_texto_link(url: str) -> str:
    # Fazer uma requisição para obter o conteúdo da página
    # TODO Verificar o ssl no ambiente de produção.
    # Suprime avisos de verificação de SSL
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")
    response = requests.get(url, verify=False)

    # Verificar se a requisição foi bem-sucedida
    if response.status_code == 200:
        # Obter o conteúdo HTML da página
        html_content = response.text

        # Crie um objeto BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extraia o texto
        text = soup.get_text()

        return text
    else:
        print(f'Erro ao acessar a página: {response.status_code}')


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
    inicios_atos = list(re.finditer(padrao_ato, texto, re.MULTILINE ))

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


"""
Erros que encontrei na separação dos atos
================================================================================
PORTARIA Nº 11.155/2016 - Revogar, a partir desta
data, a


================================================================================
PORTARIA Nº 9.324/2015, publicada no D.O.E.  de 27.02.2015, página 35.


================================================================================
PORTARIA Nº 11.151/2016 - Revogar, a partir desta
data, a


================================================================================
PORTARIA Nº 8811/2014, publicada no D.O.E.  de 22 e 23.11.2014, página
39.

#

DIRETORA GERAL DO INSTITUTO DO MEIO AMBIENTE E RECURSOS HÍDRICOS - INEMA, no uso de suas atribuições, tendo em
vista o que consta no Processo SEI nº 009.0227.2022.0077842-66, bem como no
art. 7º do Decreto nº 21.072, de 24 de janeiro de 2022, RESOLVE:


================================================================================
PORTARIA
Nº 27.788/2023 - Art.1º -
Publicar listas provisórias contendo os números de matrícula dos servidores
pertencentes às carreiras de Auxiliar Administrativo e Técnico Administrativo,
integrantes do Grupo Ocupacional Técnico Administrativo, lotados neste
Instituto, que não foram promovidos no 2º Processo Extraordinário de Avaliação
de Desempenho Funcional do ano de 2022, com as respectivas justificativas.

"""
