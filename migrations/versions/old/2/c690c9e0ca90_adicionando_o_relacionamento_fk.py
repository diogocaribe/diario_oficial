"""adicionando o relacionamento fk

Revision ID: c690c9e0ca90
Revises: 22f13a489b1f
Create Date: 2024-09-03 17:07:26.205326

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c690c9e0ca90'
down_revision: Union[str, None] = '22f13a489b1f'
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
