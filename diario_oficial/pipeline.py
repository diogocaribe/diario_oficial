from diario_oficial_bruto import coletar_dado_data
import datetime

data_inicial = datetime.date(2024, 1, 15)  # 2024, 3, 15 tem um caso especial
data_final = datetime.date(2024, 1, 25)

coletar_dado_data(data_inicial=data_inicial, data_final=data_final)