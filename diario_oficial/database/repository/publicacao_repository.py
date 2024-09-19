from .doe_bruto_repository import DiarioOficialBrutoRepository
from ..configs.connection import DBConnectionHandler
from ..entity.publicacao import Publicacao

doe_bruto_repository = DiarioOficialBrutoRepository()


class PublicacaoRepository:
    """Publicação é entendido como cada link do DOE.
    Nesse link pode existir um ou mais atos (portarias, etc.)
    """

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
                print('Dados inseridos com sucesso!')
            except Exception as exception:
                db.session.rollback()
                raise exception

    def get_link(self):
        with DBConnectionHandler() as db:
            try:
                # Adicione todas as instâncias à sessão
                resultado = (
                    db.session.query(Publicacao).filter(Publicacao.conteudo_link.is_(None)).all()
                )
                # Commit a transação
                return resultado
            except Exception as exception:
                raise exception
            

    def update_conteudo_link(self, id_publicacao: int, conteudo_link: str):
        with DBConnectionHandler() as db:
            try:
                objeto = db.session.query(Publicacao).filter(Publicacao.id == id_publicacao).one()
                objeto.conteudo_link = conteudo_link
                print(conteudo_link)
                # Commit a transação
                db.session.commit()
                print('Conteúdo inseridos com sucesso!')

            except Exception as exception:
                db.session.rollback()
                raise exception

    def get_conteudo_link(self):
        with DBConnectionHandler() as db:
            try:
                # Adicione todas as instâncias à sessão
                resultado = (
                    db.session.query(Publicacao.conteudo_link).all()
                )
                # Commit a transação
                return resultado
            except Exception as exception:
                raise exception