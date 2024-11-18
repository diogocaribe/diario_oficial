import typer
from datetime import datetime
from rich.pretty import Pretty
from rich import print
from raspar_doe import raspar_diario_oficial, doe_bruto
from database.repository.doe_bruto_repository import DiarioOficialBrutoRepository

from contextlib import redirect_stdout
from io import StringIO

app = typer.Typer()


@app.command()
def salvar_doe_bruto_db(data: str, save_db: bool = False):
    """Esta função raspa dos dados e salva no banco de dados
    
    Ex: python diario_oficial/cli.py '12-11-2024'

    Args:
        data (str): Data 'DD-MM-YYYY'
        save_db (bool, optional): Indicar se salva ou não no banco. Padrão é False.
    """
    print(f'Raspando os dados do Diário Oficial Bahia de {data}')
    # with redirect_stdout(StringIO()):
    with redirect_stdout(StringIO()):
        data = datetime.strptime(data, '%d-%m-%Y')
        resultado = raspar_diario_oficial(data)  # Os prints serão suprimidos
        # Exibe apenas o retorno final, sem os prints internos da função
                
    print(Pretty(resultado))
    if save_db:
        dados = DiarioOficialBrutoRepository()
        try:
            # TODO como tratar a existência de uma data já coletada
            dados.save_data(**resultado)
        except Exception as e:
            print(f'Erro: {e}')


if __name__ == '__main__':
    app()
