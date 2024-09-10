import requests
from bs4 import BeautifulSoup

def get_conteudo_texto_link(url: str) -> str:
    # Fazer uma requisição para obter o conteúdo da página
    response = requests.get(url)

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
        print(f"Erro ao acessar a página: {response.status_code}")

