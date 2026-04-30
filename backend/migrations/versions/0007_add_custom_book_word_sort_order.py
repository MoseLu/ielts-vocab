"""add custom book word sort order

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'custom_book_words',
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
    )
    connection = op.get_bind()
    rows = connection.execute(sa.text(
        'SELECT id, chapter_id FROM custom_book_words ORDER BY chapter_id ASC, id ASC'
    )).all()
    current_chapter = None
    current_order = 0
    for word_id, chapter_id in rows:
        if chapter_id != current_chapter:
            current_chapter = chapter_id
            current_order = 0
        connection.execute(
            sa.text('UPDATE custom_book_words SET sort_order = :sort_order WHERE id = :id'),
            {'sort_order': current_order, 'id': word_id},
        )
        current_order += 1


def downgrade():
    op.drop_column('custom_book_words', 'sort_order')
