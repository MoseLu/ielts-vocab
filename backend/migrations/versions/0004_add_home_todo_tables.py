"""add home todo tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_home_todo_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('plan_date', sa.String(length=10), nullable=False),
        sa.Column('pending_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('completed_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('carry_over_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_generated_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'plan_date', name='unique_user_home_todo_plan'),
    )
    op.create_index('ix_user_home_todo_plans_user_id', 'user_home_todo_plans', ['user_id'])
    op.create_index('ix_user_home_todo_plans_plan_date', 'user_home_todo_plans', ['plan_date'])
    op.create_index(
        'ix_user_home_todo_plans_last_generated_at',
        'user_home_todo_plans',
        ['last_generated_at'],
    )

    op.create_table(
        'user_home_todo_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('task_key', sa.String(length=40), nullable=False),
        sa.Column('kind', sa.String(length=40), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default=sa.text('100')),
        sa.Column('title', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('badge', sa.String(length=120), nullable=False),
        sa.Column('action_json', sa.Text(), nullable=True),
        sa.Column('steps_json', sa.Text(), nullable=True),
        sa.Column('evidence_json', sa.Text(), nullable=True),
        sa.Column('carry_over_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('rolled_over_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['user_home_todo_plans.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan_id', 'task_key', name='unique_user_home_todo_item'),
    )
    op.create_index('ix_user_home_todo_items_plan_id', 'user_home_todo_items', ['plan_id'])
    op.create_index('ix_user_home_todo_items_kind', 'user_home_todo_items', ['kind'])
    op.create_index('ix_user_home_todo_items_status', 'user_home_todo_items', ['status'])
    op.create_index('ix_user_home_todo_items_completed_at', 'user_home_todo_items', ['completed_at'])
    op.create_index('ix_user_home_todo_items_rolled_over_at', 'user_home_todo_items', ['rolled_over_at'])


def downgrade():
    op.drop_index('ix_user_home_todo_items_rolled_over_at', table_name='user_home_todo_items')
    op.drop_index('ix_user_home_todo_items_completed_at', table_name='user_home_todo_items')
    op.drop_index('ix_user_home_todo_items_status', table_name='user_home_todo_items')
    op.drop_index('ix_user_home_todo_items_kind', table_name='user_home_todo_items')
    op.drop_index('ix_user_home_todo_items_plan_id', table_name='user_home_todo_items')
    op.drop_table('user_home_todo_items')

    op.drop_index('ix_user_home_todo_plans_last_generated_at', table_name='user_home_todo_plans')
    op.drop_index('ix_user_home_todo_plans_plan_date', table_name='user_home_todo_plans')
    op.drop_index('ix_user_home_todo_plans_user_id', table_name='user_home_todo_plans')
    op.drop_table('user_home_todo_plans')
