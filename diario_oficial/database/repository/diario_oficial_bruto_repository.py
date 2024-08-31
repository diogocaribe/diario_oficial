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

    def save_data(self, **kwargs):

        with DBConnectionHandler() as db:
            try:
                dados = DiarioOficialBruto(**kwargs)
                db.session.add(dados)
                db.session.commit()
            except Exception as exception:
                db.session.rollback()
                raise exception

