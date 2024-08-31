from database.configs.connection import DBConnectionHandler
from database.entity.diario_oficial_bruto import DiarioOficialBruto
from datetime import datetime


class DiarioOficialBrutoRepository:
    def check_if_date_doe_coleted(self, data: datetime.date):
        """Verificar se o diario oficial daquela data foi coletado

        Raises:
            exception: _description_

        Returns:
            _type_: _description_
        """
        with DBConnectionHandler() as db:
            try:
                result = (
                    db.session.query(DiarioOficialBruto)
                    .filter(DiarioOficialBruto.data == data)
                    .first()
                )
                return result
            except Exception as exception:
                db.session.rollback()
                raise exception


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
