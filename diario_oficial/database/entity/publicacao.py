from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from diario_oficial.database.entity.dominio import (
    DivisaoAdministracaoDireta,
    AdministracaoDireta,
    Poder,
    TipoPublicacao,
    AdministracaoIndireta,
)
from diario_oficial.database.entity.doe_bruto import DiarioOficialBruto
# from diario_oficial.database.entity.ato import Ato


from ..configs.base import Base


class Publicacao(Base):
    """_summary_

    Args:
        Base (_type_): _description_

    Returns:
        _type_: _description_
    """

    __tablename__ = 'publicacao'
    __table_args__ = {'schema': 'processing'}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    doe_bruto_id: Mapped[int] = mapped_column(ForeignKey('processing.doe_bruto.id'), nullable=False)
    poder_id: Mapped[int] = mapped_column(ForeignKey('dominio.poder.id'), nullable=False)
    adm_direta_id: Mapped[int] = mapped_column(ForeignKey('dominio.adm_direta.id'), nullable=True)
    adm_indireta_id: Mapped[int] = mapped_column(
        ForeignKey('dominio.adm_indireta.id'), nullable=True
    )
    divisao_adm_direta_id: Mapped[int] = mapped_column(
        ForeignKey('dominio.divisao_adm_direta.id'), nullable=True
    )
    tipo_publicacao_id: Mapped[int] = mapped_column(
        ForeignKey('dominio.tipo_publicacao.id'), nullable=True
    )
    nome_ato: Mapped[str]
    identificador_link: Mapped[str] = mapped_column(unique=True)
    link: Mapped[str]
    conteudo_link: Mapped[str] = mapped_column(nullable=True)
    processada_para_ato: Mapped[bool] = mapped_column(nullable=True,
        comment='Indicação se ocorreu o processamento do conteúdo da publicacao para ato.')

    poder = relationship('Poder', back_populates='publicacao')
    adm_direta = relationship('AdministracaoDireta', back_populates='publicacao')
    adm_indireta = relationship('AdministracaoIndireta', back_populates='publicacao')
    divisao_adm_direta = relationship('DivisaoAdministracaoDireta', back_populates='publicacao')
    tipo_publicacao = relationship('TipoPublicacao', back_populates='publicacao')
    
    doe_bruto = relationship('DiarioOficialBruto', backref='processing.publicacao')

    def __repr__(self):
        return f'Publicação [Identificador={self.doe_bruto_id}, nome={self.nome_ato}]'
