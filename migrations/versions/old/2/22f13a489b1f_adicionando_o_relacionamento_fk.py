"""adicionando o relacionamento fk

Revision ID: 22f13a489b1f
Revises: 813b3dccac02
Create Date: 2024-09-03 17:06:53.551748

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22f13a489b1f'
down_revision: Union[str, None] = '813b3dccac02'
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
