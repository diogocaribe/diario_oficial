import typer
from datetime import datetime
from rich.pretty import Pretty
from rich import print
from raspar_doe import raspar_diario_oficial

from contextlib import redirect_stdout
from io import StringIO

app = typer.Typer()


@app.command()
def hello(name: str):
    print(f'Hello {name}')


@app.command()
def raspardoe(data: str):
    print(f'Raspando os dados do Diário Oficial Bahia de {data}')
    # Redireciona temporariamente a saída para uma variável
    with redirect_stdout(StringIO()):
        data = datetime.strptime(data, '%d-%m-%Y')
        resultado = raspar_diario_oficial(data)  # Os prints serão suprimidos

    # Exibe apenas o retorno final, sem os prints internos da função
    print(Pretty(resultado))


if __name__ == '__main__':
    app()
