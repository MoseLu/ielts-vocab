"""add user learning events

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_learning_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('mode', sa.String(length=30), nullable=True),
        sa.Column('book_id', sa.String(length=100), nullable=True),
        sa.Column('chapter_id', sa.String(length=100), nullable=True),
        sa.Column('word', sa.String(length=100), nullable=True),
        sa.Column('item_count', sa.Integer(), nullable=True),
        sa.Column('correct_count', sa.Integer(), nullable=True),
        sa.Column('wrong_count', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('payload', sa.Text(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_learning_events_user_id', 'user_learning_events', ['user_id'])
    op.create_index('ix_user_learning_events_event_type', 'user_learning_events', ['event_type'])
    op.create_index('ix_user_learning_events_source', 'user_learning_events', ['source'])
    op.create_index('ix_user_learning_events_book_id', 'user_learning_events', ['book_id'])
    op.create_index('ix_user_learning_events_chapter_id', 'user_learning_events', ['chapter_id'])
    op.create_index('ix_user_learning_events_word', 'user_learning_events', ['word'])
    op.create_index('ix_user_learning_events_occurred_at', 'user_learning_events', ['occurred_at'])


def downgrade():
    op.drop_index('ix_user_learning_events_occurred_at', table_name='user_learning_events')
    op.drop_index('ix_user_learning_events_word', table_name='user_learning_events')
    op.drop_index('ix_user_learning_events_chapter_id', table_name='user_learning_events')
    op.drop_index('ix_user_learning_events_book_id', table_name='user_learning_events')
    op.drop_index('ix_user_learning_events_source', table_name='user_learning_events')
    op.drop_index('ix_user_learning_events_event_type', table_name='user_learning_events')
    op.drop_index('ix_user_learning_events_user_id', table_name='user_learning_events')
    op.drop_table('user_learning_events')
