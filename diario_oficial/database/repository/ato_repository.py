from .doe_bruto_repository import DiarioOficialBrutoRepository
from ..configs.connection import DBConnectionHandler
from ..entity.ato import Ato

doe_bruto_repository = DiarioOficialBrutoRepository()


class AtoRepository:
    """Publicação é entendido como cada link do DOE.
    Nesse link pode existir um ou mais atos (portarias, etc.)
    """

    def save_data(self, dados):
        atos = []

        for item in dados:
            ato = Ato(**item)
            # print(publicacao)
            atos.append(ato)
            print(ato)

        with DBConnectionHandler() as db:
            try:
                # Adicione todas as instâncias à sessão
                db.session.add_all(atos)
                # Commit a transação
                db.session.commit()
                print('Dados inseridos com sucesso!')
            except Exception as exception:
                db.session.rollback()
                raise exception