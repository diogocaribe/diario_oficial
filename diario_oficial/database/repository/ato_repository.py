from database.configs.connection import DBConnectionHandler
from database.entity.ato import Ato


class AtoRepository:
    """Publicação é entendido como cada link do DOE.
    Nesse link pode existir um ou mais atos (portarias, etc.)
    """
    def save_data(self, dados):
        ato = Ato(**dados)
        # print(publicacao)
        print(ato)

        with DBConnectionHandler() as db:
            try:
                # Adicione todas as instâncias à sessão
                db.session.add(ato)
                # Commit a transação
                db.session.commit()
                print('Dados inseridos com sucesso!')
            except Exception as exception:
                db.session.rollback()
                raise exception
