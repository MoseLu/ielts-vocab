"""add scoped learning state

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa


revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_scoped_quick_memory_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('scope_key', sa.String(length=180), nullable=False),
        sa.Column('scope_type', sa.String(length=30), nullable=False, server_default='user'),
        sa.Column('origin_scope', sa.Text(), nullable=True),
        sa.Column('book_id', sa.String(length=100), nullable=True),
        sa.Column('chapter_id', sa.String(length=100), nullable=True),
        sa.Column('day', sa.Integer(), nullable=True),
        sa.Column('word', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False, server_default='unknown'),
        sa.Column('first_seen', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('last_seen', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('known_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('unknown_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('next_review', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('fuzzy_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'scope_key', 'word', name='unique_user_scope_qm_word'),
    )
    op.create_index('ix_user_scoped_qm_user_id', 'user_scoped_quick_memory_records', ['user_id'])
    op.create_index('ix_user_scoped_qm_scope_key', 'user_scoped_quick_memory_records', ['scope_key'])
    op.create_index('ix_user_scoped_qm_scope_type', 'user_scoped_quick_memory_records', ['scope_type'])
    op.create_index('ix_user_scoped_qm_book_id', 'user_scoped_quick_memory_records', ['book_id'])
    op.create_index('ix_user_scoped_qm_chapter_id', 'user_scoped_quick_memory_records', ['chapter_id'])
    op.create_index('ix_user_scoped_qm_day', 'user_scoped_quick_memory_records', ['day'])
    op.create_index('ix_user_scoped_qm_word', 'user_scoped_quick_memory_records', ['word'])

    op.create_table(
        'user_scoped_wrong_words',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('scope_key', sa.String(length=180), nullable=False),
        sa.Column('scope_type', sa.String(length=30), nullable=False, server_default='user'),
        sa.Column('origin_scope', sa.Text(), nullable=True),
        sa.Column('book_id', sa.String(length=100), nullable=True),
        sa.Column('chapter_id', sa.String(length=100), nullable=True),
        sa.Column('day', sa.Integer(), nullable=True),
        sa.Column('word', sa.String(length=100), nullable=False),
        sa.Column('phonetic', sa.String(length=100), nullable=True),
        sa.Column('pos', sa.String(length=50), nullable=True),
        sa.Column('definition', sa.Text(), nullable=True),
        sa.Column('wrong_count', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('listening_correct', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('listening_wrong', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('meaning_correct', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('meaning_wrong', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('dictation_correct', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('dictation_wrong', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('dimension_state', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'scope_key', 'word', name='unique_user_scope_wrong_word'),
    )
    op.create_index('ix_user_scoped_wrong_words_user_id', 'user_scoped_wrong_words', ['user_id'])
    op.create_index('ix_user_scoped_wrong_words_scope_key', 'user_scoped_wrong_words', ['scope_key'])
    op.create_index('ix_user_scoped_wrong_words_scope_type', 'user_scoped_wrong_words', ['scope_type'])
    op.create_index('ix_user_scoped_wrong_words_book_id', 'user_scoped_wrong_words', ['book_id'])
    op.create_index('ix_user_scoped_wrong_words_chapter_id', 'user_scoped_wrong_words', ['chapter_id'])
    op.create_index('ix_user_scoped_wrong_words_day', 'user_scoped_wrong_words', ['day'])
    op.create_index('ix_user_scoped_wrong_words_word', 'user_scoped_wrong_words', ['word'])


def downgrade():
    op.drop_index('ix_user_scoped_wrong_words_word', table_name='user_scoped_wrong_words')
    op.drop_index('ix_user_scoped_wrong_words_day', table_name='user_scoped_wrong_words')
    op.drop_index('ix_user_scoped_wrong_words_chapter_id', table_name='user_scoped_wrong_words')
    op.drop_index('ix_user_scoped_wrong_words_book_id', table_name='user_scoped_wrong_words')
    op.drop_index('ix_user_scoped_wrong_words_scope_type', table_name='user_scoped_wrong_words')
    op.drop_index('ix_user_scoped_wrong_words_scope_key', table_name='user_scoped_wrong_words')
    op.drop_index('ix_user_scoped_wrong_words_user_id', table_name='user_scoped_wrong_words')
    op.drop_table('user_scoped_wrong_words')
    op.drop_index('ix_user_scoped_qm_word', table_name='user_scoped_quick_memory_records')
    op.drop_index('ix_user_scoped_qm_day', table_name='user_scoped_quick_memory_records')
    op.drop_index('ix_user_scoped_qm_chapter_id', table_name='user_scoped_quick_memory_records')
    op.drop_index('ix_user_scoped_qm_book_id', table_name='user_scoped_quick_memory_records')
    op.drop_index('ix_user_scoped_qm_scope_type', table_name='user_scoped_quick_memory_records')
    op.drop_index('ix_user_scoped_qm_scope_key', table_name='user_scoped_quick_memory_records')
    op.drop_index('ix_user_scoped_qm_user_id', table_name='user_scoped_quick_memory_records')
    op.drop_table('user_scoped_quick_memory_records')
