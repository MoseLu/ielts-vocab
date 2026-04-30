"""add feature wish tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'feature_wishes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username_snapshot', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=120), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_feature_wishes_created_at', 'feature_wishes', ['created_at'])
    op.create_index('ix_feature_wishes_status', 'feature_wishes', ['status'])
    op.create_index('ix_feature_wishes_title', 'feature_wishes', ['title'])
    op.create_index('ix_feature_wishes_user_id', 'feature_wishes', ['user_id'])
    op.create_table(
        'feature_wish_images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wish_id', sa.Integer(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=120), nullable=False),
        sa.Column('byte_length', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('thumbnail_object_key', sa.Text(), nullable=False),
        sa.Column('thumbnail_url', sa.Text(), nullable=False),
        sa.Column('full_object_key', sa.Text(), nullable=False),
        sa.Column('full_url', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['wish_id'], ['feature_wishes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_feature_wish_images_created_at', 'feature_wish_images', ['created_at'])
    op.create_index('ix_feature_wish_images_wish_id', 'feature_wish_images', ['wish_id'])


def downgrade():
    op.drop_index('ix_feature_wish_images_wish_id', table_name='feature_wish_images')
    op.drop_index('ix_feature_wish_images_created_at', table_name='feature_wish_images')
    op.drop_table('feature_wish_images')
    op.drop_index('ix_feature_wishes_user_id', table_name='feature_wishes')
    op.drop_index('ix_feature_wishes_title', table_name='feature_wishes')
    op.drop_index('ix_feature_wishes_status', table_name='feature_wishes')
    op.drop_index('ix_feature_wishes_created_at', table_name='feature_wishes')
    op.drop_table('feature_wishes')
