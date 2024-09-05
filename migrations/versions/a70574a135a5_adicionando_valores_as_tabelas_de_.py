"""adicionando valores as tabelas de dominio

Revision ID: a70574a135a5
Revises: 134e1f1bf7a3
Create Date: 2024-09-05 17:57:36.439863

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a70574a135a5'
down_revision: Union[str, None] = '134e1f1bf7a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Inserir dados na tabela 'adm_direta'
    op.execute(
        sa.text("""
            INSERT INTO dominio.adm_direta (nome, sigla) VALUES
            ('SECRETARIA DO MEIO AMBIENTE', 'SEMA'),
            ('SECRETARIA DE EDUCAÇÃO', 'SEC')
            ON CONFLICT (nome) DO NOTHING
        """)
    )

    # Inserir dados na tabela 'adm_indireta'
    op.execute(
        sa.text("""
            INSERT INTO dominio.adm_indireta (nome, sigla) VALUES
            ('Instituto do Meio Ambiente e Recursos Hídricos - INEMA', 'INEMA')
            ON CONFLICT (nome) DO NOTHING
        """)
    )

    # Inserir dados na tabela 'orgao_adm_indireta'
    op.execute(
        sa.text("""
            INSERT INTO dominio.divisao_adm_direta (nome, sigla) VALUES
            ('Diretoria Geral', 'DG'),
            ('Diretoria Administrativa', 'DIRAF'),
            ('Atos Administrativos', '')
            ON CONFLICT (nome) DO NOTHING
        """)
    )

    op.execute(
        sa.text("""
            INSERT INTO dominio.tipo_publicacao (nome, sigla) VALUES
            ('Portarias', ''),
            ('Outros', ''),
            ('Resoluções', '')
            ON CONFLICT (nome) DO NOTHING
        """)
    )

    # Itera sobre cada valor e executa o INSERT
    op.execute(
        sa.text("""
            INSERT INTO dominio.poder (nome) VALUES 
                ('EXECUTIVO'), 
                ('LEGISLATIVO'), 
                ('JUDICIÁRIO')
                ON CONFLICT (nome) DO NOTHING
            """)
    )


def downgrade() -> None:
    # Remover dados da tabela 'poder'
    op.execute(
        sa.text("""
        DELETE FROM dominio.poder
        WHERE nome IN ('EXECUTIVO', 'LEGISLATIVO', 'JUDICIÁRIO')
        """)
    )

    # Remover dados da tabela 'tipo_publicacao'
    op.execute(
        sa.text("""
        DELETE FROM dominio.tipo_publicacao
        WHERE nome IN ('Portarias', 'Outros', 'Resoluções')
        """)
    )

    # Remover dados da tabela 'divisao_adm_direta'
    op.execute(
        sa.text("""
        DELETE FROM dominio.divisao_adm_direta
        WHERE nome IN ('Diretoria Geral', 'Diretoria Administrativa', 'Atos Administrativos')
        """)
    )

    # Remover dados da tabela 'adm_indireta'
    op.execute(
        sa.text("""
        DELETE FROM dominio.adm_indireta
        WHERE nome = 'Instituto do Meio Ambiente e Recursos Hídricos - INEMA'
        """)
    )

    # Remover dados da tabela 'adm_direta'
    op.execute(
        sa.text("""
        DELETE FROM dominio.adm_direta
        WHERE nome IN ('SECRETARIA DO MEIO AMBIENTE', 'SECRETARIA DE EDUCAÇÃO')
        """)
    )
