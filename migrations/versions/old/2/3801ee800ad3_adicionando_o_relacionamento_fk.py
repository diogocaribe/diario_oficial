"""adicionando o relacionamento fk

Revision ID: 3801ee800ad3
Revises: b32db4e52fff
Create Date: 2024-09-03 17:13:17.953224

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3801ee800ad3'
down_revision: Union[str, None] = 'b32db4e52fff'
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
