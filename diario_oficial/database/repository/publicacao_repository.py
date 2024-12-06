from .doe_bruto_repository import DiarioOficialBrutoRepository
from ..configs.connection import DBConnectionHandler
from ..entity.publicacao import Publicacao

from sqlalchemy.exc import IntegrityError
from psycopg import errors

doe_bruto_repository = DiarioOficialBrutoRepository()


class PublicacaoRepository:
    """Publicação é entendido como cada link do DOE.
    Nesse link pode existir um ou mais atos (portarias, etc.)
    """

    def save_data(self, dados):
        publicacoes = []

        for item in dados:
            publicacao = Publicacao(**item)
            publicacoes.append(publicacao)
        with DBConnectionHandler() as db:
            try:
                # Adicione todas as instâncias à sessão
                db.session.add_all(publicacoes)
                # Commit a transação
                db.session.commit()
                print('Transformação salva com sucesso.')
            except IntegrityError as e:
                # Verifica se a causa foi uma violação de unicidade
                if isinstance(e.orig, errors.UniqueViolation):
                    print('Erro: Publicacao já processada.')
                    db.session.rollback()  # Reverte a transação
                else:
                    print(f'Erro integridade publicação não identificada: {e}')
                    db.session.rollback()
            except Exception as exception:
                db.session.rollback()
                raise exception

    def get_all(self):
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
                # Commit a transação
                db.session.commit()
            except Exception as exception:
                db.session.rollback()
                raise exception

    def update_processada_para_ato(self, id_publicacao: int):
        """Processar cada conteúdo do link para separar em ato

        Args:
            id_publicacao (int): id da tabela publicacao

        Raises:
            exception: _description_
        """
        with DBConnectionHandler() as db:
            try:
                objeto = db.session.query(Publicacao).filter(Publicacao.id == id_publicacao).one()
                objeto.processada_para_ato = True
                # Commit a transação
                db.session.commit()
            except Exception as exception:
                db.session.rollback()
                raise exception

    def get_id_conteudo_link(self):
        with DBConnectionHandler() as db:
            try:
                # Adicione todas as instâncias à sessão
                resultado = db.session.query(Publicacao.id, Publicacao.conteudo_link).all()
                # Commit a transação
                return resultado
            except Exception as exception:
                raise exception
