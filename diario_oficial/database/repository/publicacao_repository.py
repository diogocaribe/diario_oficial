from .doe_bruto_repository import DiarioOficialBrutoRepository
from ..configs.connection import DBConnectionHandler
from ..entity.publicacao import Publicacao

doe_bruto_repository = DiarioOficialBrutoRepository()

class PublicacaoRepository:
    def save_data(self, dados):

        publicacoes = []

        for item in dados:
            publicacao = Publicacao(**item)
            # print(publicacao)

            publicacoes.append(publicacao)

            print(publicacoes)

        with DBConnectionHandler() as db:
            try:
                # Adicione todas as instâncias à sessão
                db.session.add_all(publicacoes)
                # Commit a transação
                db.session.commit()
                print("Dados inseridos com sucesso!")
            except Exception as exception:
                db.session.rollback()
                raise exception
