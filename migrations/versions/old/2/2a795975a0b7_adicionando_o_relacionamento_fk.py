"""adicionando o relacionamento fk

Revision ID: 2a795975a0b7
Revises: 9bb1642a4520
Create Date: 2024-09-03 17:16:30.212044

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a795975a0b7'
down_revision: Union[str, None] = '9bb1642a4520'
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
