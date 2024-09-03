from .doe_bruto_repository import DiarioOficialBrutoRepository
from ..configs.connection import DBConnectionHandler
from ..entity.publicacao import Publicacao

doe_bruto_repository = DiarioOficialBrutoRepository()

class PublicacaoRepository:
    def save_data(self, dados):

        publicacoes = []

        for item in dados:
            _publicacao = Publicacao(
                doe_nro_edicao=item.get("nro_edicao"),
                poder_id=item.get("poder"),
                adm_direta_id=item.get("adm_direta"),
                divisao_adm_direta_id=item.get("divisao_adm_direta"),
                adm_indireta_id=item.get("adm_indireta"),
                nome_ato=item.get("nome"),
                identificador_link=item.get("identificador"),
                link=item.get("link")
            )
            print(_publicacao)

            publicacoes.append(_publicacao)

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
