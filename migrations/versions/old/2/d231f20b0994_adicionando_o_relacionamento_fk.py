"""adicionando o relacionamento fk

Revision ID: d231f20b0994
Revises: 88c22fa5144d
Create Date: 2024-09-03 17:24:42.151704

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd231f20b0994'
down_revision: Union[str, None] = '88c22fa5144d'
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
