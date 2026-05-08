"""add user oauth identities

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa


revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_oauth_identities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=30), nullable=False),
        sa.Column('openid', sa.String(length=128), nullable=False),
        sa.Column('unionid', sa.String(length=128), nullable=True),
        sa.Column('nickname', sa.String(length=120), nullable=True),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'openid', name='uq_user_oauth_provider_openid'),
    )
    op.create_index('ix_user_oauth_identities_user_id', 'user_oauth_identities', ['user_id'])
    op.create_index('ix_user_oauth_identities_unionid', 'user_oauth_identities', ['unionid'])
    op.create_index('ix_user_oauth_provider_unionid', 'user_oauth_identities', ['provider', 'unionid'])


def downgrade():
    op.drop_index('ix_user_oauth_provider_unionid', table_name='user_oauth_identities')
    op.drop_index('ix_user_oauth_identities_unionid', table_name='user_oauth_identities')
    op.drop_index('ix_user_oauth_identities_user_id', table_name='user_oauth_identities')
    op.drop_table('user_oauth_identities')
