"""apagando o endereço junto com o auto de infração

O endereço (do autuado e do local da infração) é um fato do auto e não é
compartilhado entre autos. Como a FK fica no auto, apagar o auto não apaga o
endereço, que ficaria órfão. O trigger apaga os endereços do auto depois que ele é
apagado, inclusive em cascata (reprocessamento do ato ou do trecho). A pessoa
continua: ela pode estar em outros autos (FK RESTRICT).

Revision ID: c4e8a1d6f2b7
Revises: b2d7f4a9c1e6
Create Date: 2026-11-23 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c4e8a1d6f2b7'
down_revision: Union[str, None] = 'b2d7f4a9c1e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text('''
        CREATE OR REPLACE FUNCTION auto_infracao.apagar_endereco_do_auto()
        RETURNS TRIGGER AS $$
        BEGIN
            DELETE FROM auto_infracao.endereco e
            WHERE e.id IN (OLD.local_infracao_id, OLD.endereco_autuado_id);
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;
    ''')
    )
    op.execute(
        sa.text('''
        CREATE TRIGGER after_delete_apagar_endereco_do_auto
        AFTER DELETE ON auto_infracao.auto_infracao
        FOR EACH ROW
        EXECUTE FUNCTION auto_infracao.apagar_endereco_do_auto();
    ''')
    )
    # Endereços que já ficaram órfãos antes do trigger
    op.execute(
        sa.text('''
        DELETE FROM auto_infracao.endereco e
        WHERE NOT EXISTS (
            SELECT 1 FROM auto_infracao.auto_infracao a
            WHERE e.id IN (a.local_infracao_id, a.endereco_autuado_id)
        );
    ''')
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            'DROP TRIGGER after_delete_apagar_endereco_do_auto '
            'ON auto_infracao.auto_infracao;'
        )
    )
    op.execute(sa.text('DROP FUNCTION auto_infracao.apagar_endereco_do_auto();'))
