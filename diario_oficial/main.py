from raspar_doe import coleta_doe_data
import datetime
from datetime import timedelta
from dados import doe_bruto, publicacao, ato
from transformacao import get_conteudo_texto_link, separar_ato

# Inicio 25/07/2015
data_inicio = datetime.date(2024, 10, 20)  # 2024, 3, 15 tem um caso especial
data_fim = datetime.date(2024, 10, 26)


def lista_data_processar(data_inicio: datetime, data_fim: datetime):
    """Calculando todos os dias entre a data inicial e final.

    Args:
        data_inicial (datetime): Data inicial
        data_final (datetime): Data final

    Returns:
        _type_: _description_
    """
    # Calculando o número de dias entre as duas datas
    delta = data_fim - data_inicio
    lista_data = [data_inicio + timedelta(days=i) for i in range(delta.days + 1)]

    return lista_data


def pipeline(data: datetime):
    print(f'Iniciando o processamendo de {data}')
    if data >= datetime.datetime.today().date():
        print('Data maior que a maior data disponível.')
        return

    try:
        coleta_doe_data(data=data)

        dados = doe_bruto.explodir_doe_bruto_json(data=data)

        # Salvando dados do do doe bruto em publicacao
        publicacao.save_data(dados)
        # Selecionar o id a partir da data da edicao (dt_edicao)
        id_doe_bruto = doe_bruto.check_if_date_doe_coleted(data=data).id
        # Atualizar doe_bruto_para_pucalicaçao
        doe_bruto.update_doe_bruto_para_publicacao(id_doe=id_doe_bruto)

        lista_publicacao = publicacao.get_all()

        # Coletando o conteudo textual de cada link
        for publicacao_ in lista_publicacao:
            # Coletando o conteudo texual do link
            texto = get_conteudo_texto_link(publicacao_.link)
            # Gravando o conteudo textual no banco
            publicacao.update_conteudo_link(id_publicacao=publicacao_.id, conteudo_link=texto)

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
                    # TODO criar um exceção para atos que estejam vazios
                    print(f"""
                            Não foi extraido nenhum ato da publicação. 
                            O regex não pegou nenhum padrão na publicacao de id: {publicacao_.id}""")
                    raise Exception
            except Exception as e:
                print('Erro ao salvar atos')
            else:
                print(f'Salvando ato da publicacao: {publicacao_.id}')
                publicacao.update_processada_para_ato(id_publicacao=publicacao_.id)

    except Exception as e:
        print('Erro inesparado no pipeline:', e)


# TODO Trazer o loop para cá e colocar o processamento da coleta e do resto do pipeline independente
# para ir preenchendo a tabela logo. Não esperar toda a coleta das datas para executar pipeline todo
def coletar_dado_data_inicio_fim(data_inicial: str, data_final: str):
    """Esta função raspa e salva os dados no banco a partir de uma data inicial e final
        Quando a data inicial é igual a final só executa uma única data

    Args:
        data_inicial (str): _description_
        data_final (str): _description_
    """
    while data_inicial <= data_final:
        pipeline(data=data_inicial)
        data_inicial += datetime.timedelta(days=1)


coletar_dado_data_inicio_fim(data_inicial=data_inicio, data_final=data_fim)
