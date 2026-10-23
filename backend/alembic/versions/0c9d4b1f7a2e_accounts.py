"""accounts and meeting ownership

Revision ID: 0c9d4b1f7a2e
Revises: 4a3a767eaba2
Create Date: 2026-10-23 07:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0c9d4b1f7a2e'
down_revision: str | Sequence[str] | None = '4a3a767eaba2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False
    )
    op.create_index(
        op.f('ix_user_sessions_token_hash'),
        'user_sessions',
        ['token_hash'],
        unique=True,
    )

    # Meetings that predate accounts belong to nobody, and every route is about to be
    # scoped to an owner, so nothing could reach them afterwards. They are development
    # data; there is no production database as of this revision.
    op.execute('DELETE FROM meetings')
    op.add_column('meetings', sa.Column('owner_id', sa.Uuid(), nullable=False))
    op.create_foreign_key(
        'fk_meetings_owner_id_users',
        'meetings',
        'users',
        ['owner_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_index(op.f('ix_meetings_owner_id'), 'meetings', ['owner_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_meetings_owner_id'), table_name='meetings')
    op.drop_constraint('fk_meetings_owner_id_users', 'meetings', type_='foreignkey')
    op.drop_column('meetings', 'owner_id')
    op.drop_index(op.f('ix_user_sessions_token_hash'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    op.drop_table('user_sessions')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
