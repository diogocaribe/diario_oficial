"""Pessoa citada nos atos, no esquema ``public``: comum a todas as extrações.

Fica fora do esquema de um tipo de ato (como ``auto_infracao``) porque a mesma pessoa
pode aparecer em atos de tipos diferentes. Sem ``schema`` em ``__table_args__``: o
Alembic reflete as tabelas do esquema padrão sem nome de esquema, e ``'public'``
explícito faria o autogenerate propor apagar e recriar a tabela.
"""

from sqlalchemy import CheckConstraint, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from diario_oficial.database.configs.base import Base


class Pessoa(Base):
    """Pessoa física ou jurídica, única pelo documento quando ele existe."""

    __tablename__ = 'pessoa'
    __table_args__ = (
        CheckConstraint(
            "tipo_documento IN ('CPF', 'CNPJ', 'RG')", name='tipo_documento'
        ),
        Index(
            'uq_pessoa_documento',
            'tipo_documento',
            'nro_documento',
            unique=True,
            postgresql_where=text('nro_documento IS NOT NULL'),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(
        Text, nullable=False, comment='Nome da primeira vez em que a pessoa apareceu.'
    )
    tipo_documento: Mapped[str | None] = mapped_column(Text)
    nro_documento: Mapped[str | None] = mapped_column(
        Text, comment='Só os dígitos, para CPF e CNPJ.'
    )
