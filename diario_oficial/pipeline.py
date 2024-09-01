from raspar_doe import coleta_doe_data
import datetime
from dados import diario_oficial_bruto

data_inicial = datetime.date(2024, 1, 5)  # 2024, 3, 15 tem um caso especial
data_final = datetime.date(2024, 1, 30)


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
        coleta_doe_data(data=data_inicial)

        data_inicial += datetime.timedelta(days=1)


coletar_dado_data_inicio_fim(data_inicial=data_inicial, data_final=data_final)
