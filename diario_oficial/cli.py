import typer
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Optional
from rich.markup import escape
from rich.pretty import Pretty
from rich import print
from raspar_doe import raspar_diario_oficial, doe_bruto
from database.repository.doe_bruto_repository import DiarioOficialBrutoRepository
from dados import publicacao, ato, auditoria, log_erro

from diario_oficial.auditoria import auditar_edicao, inicio_do_texto
from transformacao import separar_ato, get_conteudo_texto_link
from util import dias_do_periodo

from contextlib import redirect_stdout
from io import StringIO

app = typer.Typer()

# Cada data abre um navegador: o padrão é o SE_NODE_MAX_SESSIONS do docker-compose.yaml
PROCESSOS_PIPELINE_PADRAO = 4


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
def transformar_doe_bruto_publicacao(
    data: str,
    transformar_publicacao: bool = True,
    save_db: bool = True,
    somente_data: bool = False,
):
    """
    Esta função pega todos os dados brutos não processados e
    transforma em publicação (tabela publicacao do banco de dados).

    Args:
        data (str): Data 'DD-MM-YYYY'
        tranformcar_publicacao (bool, optional): Realiza a transformação dos dados brutos em
        publicação. Defaults to False.
        somente_data (bool, optional): Coleta o conteúdo textual só dos links da edição de
        `data`, e não os pendentes de todas as datas. Defaults to False.

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
        lista_publicacao = publicacao.get_all_conteudo_link_none(
            data=_data_da_cli(data) if somente_data else None
        )

        # Coletando o conteudo textual de cada link
        for publicacao_ in lista_publicacao:
            # Coletando o conteudo texual do link
            texto = get_conteudo_texto_link(publicacao_.link)
            # Gravando o conteudo textual no banco
            publicacao.update_conteudo_link(id_publicacao=publicacao_.id, conteudo_link=texto)
    except TypeError:
        print('Não existe links de publicações para coletar conteudo textual.')


def _registrar_erro_separacao(publicacao_, tipo, descricao, trecho=None):
    """Grava o erro em log_erro; uma falha no log não interrompe as demais publicações."""
    linha = {
        'etapa': 'separacao',
        'tipo': tipo,
        'descricao': descricao,
        'trecho': trecho,
        'doe_bruto_id': publicacao_.doe_bruto_id,
        'publicacao_id': publicacao_.id,
        'ato_id': None,
    }
    try:
        log_erro.registrar([linha])
    except Exception as e:
        print(f'Erro ao gravar log da publicação {publicacao_.id}: {escape(str(e))}')


@app.command()
@staticmethod
def transformar_publicacao_ato(data: Optional[str] = None):
    """
    Esta função todas as publicações e transforma em atos.

    Args: \n
        data (str, optional): Data 'DD-MM-YYYY'. Se informada, processa só as publicações
        pendentes dessa edição. Padrão é processar as pendentes de qualquer data.
    """
    if data is None:
        print('Transformando em atos todas as publicações pendentes, de qualquer data.')
        lista_publicacao = publicacao.get_conteudo_link_processada_ato_null()
    else:
        print(f'Transformando em atos as publicações pendentes de {data}.')
        lista_publicacao = publicacao.get_conteudo_link_processada_ato_null(
            data=_data_da_cli(data)
        )

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
                _registrar_erro_separacao(
                    publicacao_,
                    'SEM_ATO_RECONHECIDO',
                    'O regex não reconheceu nenhum ato no texto da publicação.',
                    inicio_do_texto(texto) or None,
                )
                continue
            for ato_ in atos:
                if ato_ != '':
                    objeto_ato = {'publicacao_id': publicacao_.id, 'conteudo_ato': ato_}
                    ato.save_data(objeto_ato)
        except Exception as e:
            print(f'Erro ao salvar atos da publicação {publicacao_.id}: {escape(str(e))}')
            _registrar_erro_separacao(
                publicacao_, 'ERRO_NA_SEPARACAO', f'{type(e).__name__}: {e}'
            )
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
    False caso contrário. Os achados novos são gravados em processing.log_erro. Só reprova
    diante de evidência de separação errada: texto fora dos atos, ato sem título, ato
    cortado ou dois atos juntos.

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
        auditoria.salvar_relatorio(relatorio)

    if not edicao.publicacoes:
        print(f'Edição de {data} sem publicações.')

    for publicacao_ in edicao.publicacoes:
        _imprimir_auditoria_link(publicacao_, relatorio)

    # Achado da edição não pertence a nenhum link
    _imprimir_achados(relatorio.achados_da_publicacao(None))


def _raspar_com_nova_tentativa(data: str):
    """A sessão do Selenium às vezes cai no meio: tenta uma segunda vez."""
    try:
        raspar_doe_bruto(data)
    except Exception as e:
        print(f'Raspagem de {data} falhou ({type(e).__name__}); tentando de novo.')
        raspar_doe_bruto(data)


# Na ordem de execução. As etapas ficam restritas à data, senão processos simultâneos
# pegariam as mesmas pendências e gravariam os atos em duplicidade (processing.ato não
# tem restrição de unicidade).
ETAPAS_PIPELINE = {
    'raspar-doe-bruto': _raspar_com_nova_tentativa,
    'transformar-doe-bruto-publicacao': lambda data: transformar_doe_bruto_publicacao(
        data, somente_data=True
    ),
    'transformar-publicacao-ato': lambda data: transformar_publicacao_ato(data=data),
    'auditar-publicacao-ato': auditar_publicacao_ato,
}


def _executar_pipeline_data(data: str) -> tuple[str, str | None]:
    """Executa em sequência as etapas de uma data, parando na primeira que falhar.

    Roda em um processo próprio: redirect_stdout troca o sys.stdout do processo inteiro,
    então não pode ser usado por várias threads ao mesmo tempo.

    Returns:
        (saída impressa pelas etapas, descrição do erro ou None).
    """
    # A saída é devolvida inteira para as datas não se misturarem no terminal
    saida = StringIO()
    with redirect_stdout(saida):
        for nome, etapa in ETAPAS_PIPELINE.items():
            try:
                etapa(data)
            except Exception as e:
                return saida.getvalue(), f'{nome}: {type(e).__name__}: {e}'
    return saida.getvalue(), None


@app.command()
def executar_pipeline_periodo(
    data_inicio: str,
    data_fim: str,
    processos: int = typer.Option(
        PROCESSOS_PIPELINE_PADRAO,
        min=1,
        help='Datas processadas ao mesmo tempo. Acima de SE_NODE_MAX_SESSIONS, as '
        'sessões excedentes ficam na fila do Selenium.',
    ),
):
    """
    Executa o pipeline de cada data do período: raspagem, transformação em publicação,
    transformação em ato e auditoria. Datas diferentes rodam em paralelo; dentro de uma
    data, cada etapa termina antes de a seguinte começar. Se uma etapa falhar, as
    seguintes não rodam nessa data e as demais datas continuam. Termina com código 1 se
    alguma data falhar; basta rodar outra vez para refazer o que faltou.

    Args: \n
        data_inicio (str): Primeira data do período, 'DD-MM-YYYY'. \n
        data_fim (str): Última data do período, inclusive, 'DD-MM-YYYY'. O limite é ontem.

    Examples: \n
        >>> python diario_oficial/cli.py executar-pipeline-periodo 01-07-2026 31-07-2026 \n
        >>> python diario_oficial/cli.py executar-pipeline-periodo 01-07-2026 31-07-2026 --processos 2
    """
    # A edição de hoje pode não ter saído: gravada como inexistente, nunca seria refeita
    ontem = datetime.now().date() - timedelta(days=1)
    dias = dias_do_periodo(_data_da_cli(data_inicio), _data_da_cli(data_fim), ontem)
    if not dias:
        raise typer.BadParameter(
            f'Período vazio: {data_inicio} a {data_fim} (o limite é ontem).'
        )
    datas = [dia.strftime('%d-%m-%Y') for dia in dias]

    falhas = 0
    with ProcessPoolExecutor(max_workers=min(processos, len(datas))) as executor:
        futuros = {executor.submit(_executar_pipeline_data, d): d for d in datas}
        for futuro in as_completed(futuros):
            data = futuros[futuro]
            try:
                saida, erro = futuro.result()
            except Exception as e:  # o processo morreu, sem devolver a saída
                saida, erro = '', f'{type(e).__name__}: {e}'
            # A saída já foi formatada pelo rich e pode ter colchetes: vai sem marcação
            typer.echo(saida, nl=False)
            if erro is not None:
                falhas += 1
                typer.echo(f'Data {data} falhou em {erro}', err=True)

    print(f'{len(datas) - falhas} de {len(datas)} datas sem falha.')
    if falhas:
        raise typer.Exit(code=1)


if __name__ == '__main__':
    app()
