import pandas as pd
from database.configs.connection import DBConnectionHandler


# class DecrementoMunicipioRepository:
#     def select_all(self):
#         with DBConnectionHandler() as db:
#             try:
#                 data = db.session.query(DecrementoMunicipio).all()
#                 return data
#             except Exception as exception:
#                 db.session.rollback()
#                 raise exception

#     def df_select_all(self):
#         """
#         :param engine: SQLAlchemy database connection engine
#         :param query: Query to run
#         :param params: Query parameter list
#         :return: DataFrame
#         """
#         with DBConnectionHandler() as db:
#             try:
#                 # data = db.session.query(MonitoramentoDissolve).all()
#                 data = pd.read_sql(
#                             sql='SELECT id, nome, view_date, area_ha FROM vw_decremento_municipio;',
#                             con=db.get_engine(),
#                     index_col=["view_date"],
#                 )
#                 return data
#             except Exception as exception:
#                 db.session.rollback()
#                 raise exception
