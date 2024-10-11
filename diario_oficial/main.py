from raspar_doe import coleta_doe_data
import datetime
from datetime import timedelta
from dados import doe_bruto, publicacao, ato
from transformacao import get_conteudo_texto_link, separar_ato

# Inicio 25/07/2015
data_inicio = datetime.date(2024, 1, 1)  # 2024, 3, 15 tem um caso especial
data_fim = datetime.date(2024, 12, 31)


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
        print(data_inicial)
        coleta_doe_data(data=data_inicial)

        dados = doe_bruto.explodir_doe_bruto_json(data=data_inicial)

        # Salvando dados do do doe bruto em publicacao
        publicacao.save_data(dados)
        # Selecionar o id a partir da data da edicao (dt_edicao)
        id_doe_bruto = doe_bruto.check_if_date_doe_coleted(data=data_inicial).id
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
                for ato_ in enumerate(atos, 1):
                    # TODO Os atos estão duplicando com a nova execução do script. Avaliar um valor
                    # unico para que não ocorra a repetição.
                    print(f"\n{publicacao_.id}\n{'='*80}\n{ato_[1]}\n")
                    objeto_ato = {'publicacao_id': publicacao_.id, 'conteudo_ato': ato_[1]}
                    ato.save_data(objeto_ato)
            except Exception as e:
                print('Erro ao salvar atos', e)
            else:
                print('Sem erros')
                publicacao.update_processada_para_ato(id_publicacao=publicacao_.id)

            

        data_inicial += datetime.timedelta(days=1)


coletar_dado_data_inicio_fim(data_inicial=data_inicio, data_final=data_fim)
