import typer
from datetime import datetime
from rich.markup import escape
from rich.pretty import Pretty
from rich import print
from raspar_doe import raspar_diario_oficial, doe_bruto
from database.repository.doe_bruto_repository import DiarioOficialBrutoRepository
from dados import publicacao, ato, auditoria

from diario_oficial.auditoria import auditar_edicao
from transformacao import separar_ato, get_conteudo_texto_link

from contextlib import redirect_stdout
from io import StringIO

app = typer.Typer()


@app.command()
def raspar_doe_bruto(data: str, save_db: bool = True, forcar: bool = False):
    """Esta função raspa dos dados e salva no banco de dados

    Args: \n
        data (str): Data 'DD-MM-YYYY' \n
        save_db (bool, optional): Indicar se salva ou não no banco. Padrão é True. \n
        forcar (bool, optional): Raspa mesmo que a data já esteja em doe_bruto. Não
        sobrescreve a linha existente: para regravar, apague-a antes. Padrão é False.

    Examples: \n
        >>> python diario_oficial/cli.py raspar-doe-bruto '12-11-2024' --no-save-db \n
        >>> python diario_oficial/cli.py raspar-doe-bruto '12-11-2024' --save-db \n
        >>> python diario_oficial/cli.py raspar-doe-bruto '12-11-2024' --forcar
    """
    data_str = data
    data = datetime.strptime(data_str, '%d-%m-%Y')
    if not forcar and doe_bruto.check_if_date_doe_coleted(data.date()) is not None:
        print(f'Data {data_str} já coletada. Nada a raspar '
              '(use --forcar para raspar novamente).')
        return

    print(f'Raspando os dados do Diário Oficial Bahia de {data_str}')
    with redirect_stdout(StringIO()):
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
        data_iso = f"{data[-4:]}-{data[3:5]}-{data[:2]}"
        registro = doe_bruto.check_if_date_doe_coleted(
            data=datetime.strptime(data_iso, '%Y-%m-%d'))
        if registro is None:
            # Sem doe_bruto não há o que transformar: falha de verdade (raspagem não rodou)
            print(f'[red]Nenhum doe_bruto coletado para {data}. '
                  f'Rode "raspar-doe-bruto {data}" antes.[/red]')
            raise typer.Exit(code=1)

        dados = doe_bruto.explodir_doe_bruto_json(data=data_iso)
        if not registro.existe:
            print(f'Não há edição do DOE em {data}. Nada a transformar.')
        elif not dados:
            print(f'Edição de {data} sem publicações das pastas selecionadas. '
                  'Nada a transformar.')
        else:
            print(dados)
            if save_db:
                # Salvando dados do do doe bruto em publicacao
                publicacao.save_data(dados)
        if save_db:
            # Marca como processado mesmo vazio, para não ficar pendente
            doe_bruto.update_doe_bruto_para_publicacao(id_doe=registro.id)

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
    print('Transformando em atos todas as publicações pendentes, de qualquer data.')
    lista_publicacao = publicacao.get_conteudo_link_processada_ato_null()

    # Coletando o conteudo textual de cada link
    for publicacao_ in lista_publicacao:
        # Coletando o conteudo texual do link
        texto = publicacao_.conteudo_link

        try:
            # Separar cada publicação em atos
            atos = separar_ato(texto)
            if not atos:
                # Não é falha ao salvar: o texto existe, mas o regex não reconhece o título
                print(f'Publicação {publicacao_.id} sem ato reconhecido pelo regex; '
                      f'continua pendente: {publicacao_.link}')
                continue
            for ato_ in atos:
                if ato_ != '':
                    objeto_ato = {'publicacao_id': publicacao_.id, 'conteudo_ato': ato_}
                    ato.save_data(objeto_ato)
        except Exception as e:
            print(f'Erro ao salvar atos da publicação {publicacao_.id}: {escape(str(e))}')
        else:
            print(f'Salvando ato da publicacao: {publicacao_.id}')
            publicacao.update_processada_para_ato(id_publicacao=publicacao_.id)


def _data_da_cli(valor: str):
    try:
        return datetime.strptime(valor, '%d-%m-%Y').date()
    except ValueError:
        raise typer.BadParameter(f'Data inválida: {valor} (use DD-MM-YYYY)')


def _imprimir_achados(achados):
    """Imprime o motivo de cada reprovação, com o trecho que localiza o problema."""
    for achado in achados:
        local = f' | Ato {achado.ato_id}' if achado.ato_id is not None else ''
        print(f'{achado.regra}{local}: {achado.descricao}')
        if achado.trecho:
            print(f'    {escape(achado.trecho)}')


def _imprimir_auditoria_link(publicacao_, relatorio):
    """Imprime a auditoria de um link: os atos separados, o resultado e os achados."""
    # O texto do DOE pode ter colchetes, que o rich leria como marcação
    print(
        f"\nPublicação {publicacao_.id} | {escape(publicacao_.nome_ato)}\n"
        f"{publicacao_.link}\n{'=' * 80}"
    )
    for ato_ in publicacao_.atos:
        print(f'\nAto {ato_.id}\n{escape(ato_.conteudo or "")}')

    if relatorio.resultado_publicacoes[publicacao_.id]:
        print(f'\n[green]Auditoria da publicação {publicacao_.id} aprovada.[/green]')
    else:
        print(f'\n[red]Auditoria da publicação {publicacao_.id} reprovada.[/red]')
        _imprimir_achados(relatorio.achados_da_publicacao(publicacao_.id))


@app.command()
def auditar_publicacao_ato(data: str, save_db: bool = True):
    """
    Esta função audita a separação em atos de cada link (publicação) coletado em um dia.
    Para cada link, imprime os atos separados, informa se a auditoria foi aprovada ou
    reprovada, com os achados que levaram à reprovação, e grava o resultado em
    publicacao.auditoria: True se todos os atos do link foram separados corretamente,
    False caso contrário. Só reprova diante de evidência de separação errada: texto fora
    dos atos, ato sem título, ato cortado ou dois atos juntos.

    Args: \n
        data (str): Data 'DD-MM-YYYY'. \n
        save_db (bool, optional): Indicar se grava ou não o resultado no banco. Padrão é True.

    Examples: \n
        >>> python diario_oficial/cli.py auditar-publicacao-ato 10-10-2026 \n
        >>> python diario_oficial/cli.py auditar-publicacao-ato 10-10-2026 --no-save-db
    """
    edicao = auditoria.get_edicao(_data_da_cli(data))

    if edicao is None:
        print(f'Nenhuma edição coletada em {data}.')
        return

    relatorio = auditar_edicao(edicao)

    if save_db:
        auditoria.update_auditoria(relatorio.resultado_publicacoes)

    if not edicao.publicacoes:
        print(f'Edição de {data} sem publicações.')

    for publicacao_ in edicao.publicacoes:
        _imprimir_auditoria_link(publicacao_, relatorio)

    # Achado da edição não pertence a nenhum link
    _imprimir_achados(relatorio.achados_da_publicacao(None))


if __name__ == '__main__':
    app()
