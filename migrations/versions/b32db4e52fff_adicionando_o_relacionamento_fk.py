"""adicionando o relacionamento fk

Revision ID: b32db4e52fff
Revises: c690c9e0ca90
Create Date: 2024-09-03 17:11:32.836869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b32db4e52fff'
down_revision: Union[str, None] = 'c690c9e0ca90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
