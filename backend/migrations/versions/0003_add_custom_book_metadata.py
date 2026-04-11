"""add custom book metadata

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-11
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_chapter_progress') as batch_op:
        batch_op.alter_column(
            'chapter_id',
            existing_type=sa.Integer(),
            type_=sa.String(length=50),
            existing_nullable=False,
        )
    with op.batch_alter_table('user_chapter_mode_progress') as batch_op:
        batch_op.alter_column(
            'chapter_id',
            existing_type=sa.Integer(),
            type_=sa.String(length=50),
            existing_nullable=False,
        )

    op.add_column('custom_books', sa.Column('education_stage', sa.String(length=50), nullable=True))
    op.add_column('custom_books', sa.Column('exam_type', sa.String(length=50), nullable=True))
    op.add_column('custom_books', sa.Column('ielts_skill', sa.String(length=50), nullable=True))
    op.add_column(
        'custom_books',
        sa.Column('share_enabled', sa.Boolean(), nullable=False, server_default=sa.text('0')),
    )
    op.add_column(
        'custom_books',
        sa.Column('chapter_word_target', sa.Integer(), nullable=False, server_default=sa.text('15')),
    )
    op.add_column(
        'custom_book_words',
        sa.Column('is_incomplete', sa.Boolean(), nullable=False, server_default=sa.text('0')),
    )


def downgrade():
    op.drop_column('custom_book_words', 'is_incomplete')
    op.drop_column('custom_books', 'chapter_word_target')
    op.drop_column('custom_books', 'share_enabled')
    op.drop_column('custom_books', 'ielts_skill')
    op.drop_column('custom_books', 'exam_type')
    op.drop_column('custom_books', 'education_stage')
    with op.batch_alter_table('user_chapter_mode_progress') as batch_op:
        batch_op.alter_column(
            'chapter_id',
            existing_type=sa.String(length=50),
            type_=sa.Integer(),
            existing_nullable=False,
        )
    with op.batch_alter_table('user_chapter_progress') as batch_op:
        batch_op.alter_column(
            'chapter_id',
            existing_type=sa.String(length=50),
            type_=sa.Integer(),
            existing_nullable=False,
        )
