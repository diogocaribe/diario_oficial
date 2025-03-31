import typer
from datetime import datetime
from rich.pretty import Pretty
from rich import print
from raspar_doe import raspar_diario_oficial, doe_bruto
from database.repository.doe_bruto_repository import DiarioOficialBrutoRepository
from dados import publicacao, ato

from transformacao import separar_ato, get_conteudo_texto_link

from contextlib import redirect_stdout
from io import StringIO

app = typer.Typer()


@app.command()
def raspar_doe_bruto(data: str, save_db: bool = True):
    """Esta função raspa dos dados e salva no banco de dados

    Args: \n
        data (str): Data 'DD-MM-YYYY' \n
        save_db (bool, optional): Indicar se salva ou não no banco. Padrão é False.
    
    Examples: \n
        >>> python diario_oficial/cli.py raspar-doe-bruto '12-11-2024' --no-save-db \n
        >>> python diario_oficial/cli.py raspar-doe-bruto '12-11-2024' --save-db
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

    Examples:
        >>> python diario_oficial/cli.py transformar-doe-bruto-publicacao '12-11-2024' --no-transformar-publicacao --no-save-db
        >>> python diario_oficial/cli.py transformar-doe-bruto-publicacao '12-11-2024' --transformar-publicacao --save-db
    """
    print('Transformando dados brutos em publicações.')
    if transformar_publicacao:
        data = f"{data[-4:]}-{data[3:5]}-{data[:2]}"
        dados = doe_bruto.explodir_doe_bruto_json(data=data)
        print(dados)
        if save_db:
            # Salvando dados do do doe bruto em publicacao
            publicacao.save_data(dados)
            # Selecionar o id a partir da data da edicao (dt_edicao)
            id_doe_bruto = doe_bruto.check_if_date_doe_coleted(
                data=datetime.strptime(data, '%Y-%m-%d')).id
            doe_bruto.update_doe_bruto_para_publicacao(id_doe=id_doe_bruto)

    try:
        lista_publicacao = publicacao.get_all_conteudo_link_none()

        # Coletando o conteudo textual de cada link
        for publicacao_ in lista_publicacao:
            # Coletando o conteudo texual do link
            texto = get_conteudo_texto_link(publicacao_.link)
            # Gravando o conteudo textual no banco
            publicacao.update_conteudo_link(id_publicacao=publicacao_.id, conteudo_link=texto)
    except TypeError:
        print('Não existe links de publicações para coletar conteudo textual.')


@app.command()
@staticmethod
def transformar_publicacao_ato():
    """
    Esta função todas as publicações e transforma em atos.
    """
    print('Transformando publicacao em atos.')
    lista_publicacao = publicacao.get_conteudo_link_processada_ato_null()

    # Coletando o conteudo textual de cada link
    for publicacao_ in lista_publicacao:
        # Coletando o conteudo texual do link
        texto = publicacao_.conteudo_link

        try:
            # Separar cada publicação em atos
            atos = separar_ato(texto)
            if atos:
                for ato_ in atos:
                    if ato_ != '':
                        print(f"\n{publicacao_.id}\n{'='*80}\n{ato_}\n")
                        objeto_ato = {'publicacao_id': publicacao_.id, 'conteudo_ato': ato_}
                        ato.save_data(objeto_ato)
            else:
                print(f"""
                        Não foi extraido nenhum ato da publicação. 
                        O regex não pegou nenhum padrão na publicacao de id: {publicacao_.id}""")
                raise Exception
        except Exception:
            print('Erro ao salvar atos')
        else:
            print(f'Salvando ato da publicacao: {publicacao_.id}')
            publicacao.update_processada_para_ato(id_publicacao=publicacao_.id)


if __name__ == '__main__':
    app()
