from raspar_doe import coleta_doe_data
import datetime
from dados import doe_bruto, publicacao, ato
from transformacao import get_conteudo_texto_link, separar_ato

# Inicio 25/07/2015
data_inicial = datetime.date(2024, 1, 1)  # 2024, 3, 15 tem um caso especial
data_final = datetime.date(2024, 12, 31)


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

        dados = doe_bruto.explodir_doe_bruto_json(data=data_inicial)
        try:
            publicacao.save_data(dados)
        except Exception as e:
            # Trata quaisquer outros erros não esperados
            print(f'Erro inesperado: {e}')

        lista_link = publicacao.get_link()

        for link in lista_link:
            texto = get_conteudo_texto_link(link.link)
            publicacao.update_conteudo_link(id_publicacao=link.id, conteudo_link=texto)

        lista_conteudo_link = publicacao.get_id_conteudo_link()

        for id, conteudo in lista_conteudo_link:
            atos = separar_ato(conteudo)
            for i, ato_ in enumerate(atos, 1):
                # TODO Os atos estão duplicando com a nova execução do script. Avaliar um valor
                # unico para que não ocorra a repetição.
                print(f"\n{id}\n{'='*80}\n{ato_}\n")
                ato__ = {'publicacao_id': id, 'conteudo_ato': ato_}
                ato.save_data(ato__)

        data_inicial += datetime.timedelta(days=1)


coletar_dado_data_inicio_fim(data_inicial=data_inicial, data_final=data_final)
