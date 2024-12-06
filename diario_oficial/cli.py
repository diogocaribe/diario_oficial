import typer
from datetime import datetime
from rich.pretty import Pretty
from rich import print
from raspar_doe import raspar_diario_oficial, doe_bruto, coleta_doe_data
from database.repository.doe_bruto_repository import DiarioOficialBrutoRepository
from dados import publicacao

from contextlib import redirect_stdout
from io import StringIO

app = typer.Typer()


@app.command()
def raspar_doe_bruto(data: str, save_db: bool = False):
    """Esta função raspa dos dados e salva no banco de dados

    Args: \n
        data (str): Data 'DD-MM-YYYY' \n
        save_db (bool, optional): Indicar se salva ou não no banco. Padrão é False.
    
    Examples: \n
        >>> python diario_oficial/cli.py '12-11-2024' \n
        >>> python diario_oficial/cli.py '12-11-2024' --save-db
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


@app.command()
def transformar_doe_bruto_publicacao(data: str, transformar_publicacao: bool = True, save_db: bool = True):
    """
    Esta função pega todos os dados brutos não processados e 
    transforma em publicação (tabela publicacao do banco de dados).

    Args:
        data (str): Data 'DD-MM-YYYY'
        tranformcar_publicacao (bool, optional): Realiza a transformação dos dados brutos em 
        publicação. Defaults to False.
    """
    print('Transformando dados brutos em publicações.')
    if transformar_publicacao:
        data = f"{data[-4:]}-{data[3:5]}-{data[:2]}"
        dados = doe_bruto.explodir_doe_bruto_json(data=data)
        print(dados)
        if save_db:
            # Salvando dados do do doe bruto em publicacao
            publicacao.save_data(dados)


if __name__ == '__main__':
    app()
