"""add learning activity rollups

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-22
"""
from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_learning_daily_ledgers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('mode', sa.String(length=30), nullable=False, server_default=''),
        sa.Column('chapter_id', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('learning_date', sa.String(length=10), nullable=False),
        sa.Column('current_index', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('words_learned', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('correct_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('wrong_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('items_studied', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('duration_seconds', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('review_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('wrong_word_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('session_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_completed', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('answered_words', sa.Text(), nullable=True),
        sa.Column('queue_words', sa.Text(), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id',
            'book_id',
            'mode',
            'chapter_id',
            'learning_date',
            name='unique_user_learning_daily_scope',
        ),
    )
    op.create_index(
        'ix_user_learning_daily_ledgers_learning_date',
        'user_learning_daily_ledgers',
        ['learning_date'],
        unique=False,
    )
    op.create_index(
        'ix_user_learning_daily_ledgers_user_id',
        'user_learning_daily_ledgers',
        ['user_id'],
        unique=False,
    )

    op.create_table(
        'user_learning_chapter_rollups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.String(length=100), nullable=False),
        sa.Column('mode', sa.String(length=30), nullable=False),
        sa.Column('chapter_id', sa.String(length=100), nullable=False),
        sa.Column('current_index', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('words_learned', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('correct_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('wrong_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('items_studied', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('duration_seconds', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('review_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('wrong_word_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('session_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_completed', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('answered_words', sa.Text(), nullable=True),
        sa.Column('queue_words', sa.Text(), nullable=True),
        sa.Column('last_learning_date', sa.String(length=10), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id',
            'book_id',
            'mode',
            'chapter_id',
            name='unique_user_learning_chapter_rollup',
        ),
    )
    op.create_index(
        'ix_user_learning_chapter_rollups_user_id',
        'user_learning_chapter_rollups',
        ['user_id'],
        unique=False,
    )

    op.create_table(
        'user_learning_mode_rollups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.String(length=100), nullable=False),
        sa.Column('mode', sa.String(length=30), nullable=False),
        sa.Column('words_learned', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('correct_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('wrong_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('items_studied', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('duration_seconds', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('review_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('wrong_word_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('session_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('chapter_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_learning_date', sa.String(length=10), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'book_id', 'mode', name='unique_user_learning_mode_rollup'),
    )
    op.create_index(
        'ix_user_learning_mode_rollups_user_id',
        'user_learning_mode_rollups',
        ['user_id'],
        unique=False,
    )

    op.create_table(
        'user_learning_book_rollups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.String(length=100), nullable=False),
        sa.Column('current_index', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('words_learned', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('correct_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('wrong_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('items_studied', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('duration_seconds', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('review_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('wrong_word_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('session_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('mode_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_completed', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('last_learning_date', sa.String(length=10), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'book_id', name='unique_user_learning_book_rollup'),
    )
    op.create_index(
        'ix_user_learning_book_rollups_user_id',
        'user_learning_book_rollups',
        ['user_id'],
        unique=False,
    )

    op.create_table(
        'user_learning_user_rollups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('words_learned', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('correct_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('wrong_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('items_studied', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('duration_seconds', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('review_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('wrong_word_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('session_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('book_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('cross_book_pending_review_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_learning_date', sa.String(length=10), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(
        'ix_user_learning_user_rollups_user_id',
        'user_learning_user_rollups',
        ['user_id'],
        unique=True,
    )


def downgrade():
    op.drop_index('ix_user_learning_user_rollups_user_id', table_name='user_learning_user_rollups')
    op.drop_table('user_learning_user_rollups')
    op.drop_index('ix_user_learning_book_rollups_user_id', table_name='user_learning_book_rollups')
    op.drop_table('user_learning_book_rollups')
    op.drop_index('ix_user_learning_mode_rollups_user_id', table_name='user_learning_mode_rollups')
    op.drop_table('user_learning_mode_rollups')
    op.drop_index('ix_user_learning_chapter_rollups_user_id', table_name='user_learning_chapter_rollups')
    op.drop_table('user_learning_chapter_rollups')
    op.drop_index('ix_user_learning_daily_ledgers_user_id', table_name='user_learning_daily_ledgers')
    op.drop_index('ix_user_learning_daily_ledgers_learning_date', table_name='user_learning_daily_ledgers')
    op.drop_table('user_learning_daily_ledgers')
