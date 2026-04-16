"""add exam tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'exam_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=40), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('owner', sa.String(length=120), nullable=True),
        sa.Column('repo', sa.String(length=120), nullable=True),
        sa.Column('ref', sa.String(length=120), nullable=True),
        sa.Column('root_path', sa.Text(), nullable=True),
        sa.Column('audio_root_path', sa.Text(), nullable=True),
        sa.Column('rights_status', sa.String(length=30), nullable=False, server_default='restricted_internal'),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_url'),
    )
    op.create_index('ix_exam_sources_source_type', 'exam_sources', ['source_type'])

    op.create_table(
        'exam_papers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('external_key', sa.String(length=255), nullable=False),
        sa.Column('collection_key', sa.String(length=120), nullable=True),
        sa.Column('collection_title', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('exam_kind', sa.String(length=40), nullable=False, server_default='academic'),
        sa.Column('series_number', sa.Integer(), nullable=True),
        sa.Column('test_number', sa.Integer(), nullable=True),
        sa.Column('parser_strategy', sa.String(length=40), nullable=False, server_default='multimodal'),
        sa.Column('publish_status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('rights_status', sa.String(length=30), nullable=False, server_default='restricted_internal'),
        sa.Column('import_confidence', sa.Float(), nullable=False, server_default='0'),
        sa.Column('answer_key_confidence', sa.Float(), nullable=False, server_default='0'),
        sa.Column('has_listening_audio', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['exam_sources.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_key'),
    )
    op.create_index('ix_exam_papers_publish_status', 'exam_papers', ['publish_status'])

    op.create_table(
        'exam_sections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('paper_id', sa.Integer(), nullable=False),
        sa.Column('section_type', sa.String(length=40), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('instructions_html', sa.Text(), nullable=True),
        sa.Column('html_content', sa.Text(), nullable=True),
        sa.Column('audio_asset_id', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0'),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['paper_id'], ['exam_papers.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'exam_passages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('html_content', sa.Text(), nullable=False),
        sa.Column('source_page_from', sa.Integer(), nullable=True),
        sa.Column('source_page_to', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0'),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['section_id'], ['exam_sections.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'exam_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=False),
        sa.Column('passage_id', sa.Integer(), nullable=True),
        sa.Column('group_key', sa.String(length=80), nullable=True),
        sa.Column('question_number', sa.Integer(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('question_type', sa.String(length=40), nullable=False, server_default='short_answer'),
        sa.Column('prompt_html', sa.Text(), nullable=False),
        sa.Column('blank_key', sa.String(length=80), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0'),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['section_id'], ['exam_sections.id']),
        sa.ForeignKeyConstraint(['passage_id'], ['exam_passages.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'exam_choices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('choice_key', sa.String(length=40), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('label', sa.String(length=80), nullable=True),
        sa.Column('content_html', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['exam_questions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('question_id', 'choice_key', name='unique_exam_choice_key'),
    )

    op.create_table(
        'exam_answer_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('answer_kind', sa.String(length=40), nullable=False, server_default='accepted_answer'),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('normalized_text', sa.String(length=255), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['exam_questions.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'exam_assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('paper_id', sa.Integer(), nullable=True),
        sa.Column('section_id', sa.Integer(), nullable=True),
        sa.Column('asset_key', sa.String(length=255), nullable=False),
        sa.Column('asset_kind', sa.String(length=40), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('content_type', sa.String(length=120), nullable=True),
        sa.Column('byte_length', sa.Integer(), nullable=True),
        sa.Column('checksum', sa.String(length=128), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['exam_sources.id']),
        sa.ForeignKeyConstraint(['paper_id'], ['exam_papers.id']),
        sa.ForeignKeyConstraint(['section_id'], ['exam_sections.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_key'),
    )

    op.create_table(
        'exam_review_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('paper_id', sa.Integer(), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=True),
        sa.Column('question_id', sa.Integer(), nullable=True),
        sa.Column('item_type', sa.String(length=60), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='warning'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['paper_id'], ['exam_papers.id']),
        sa.ForeignKeyConstraint(['section_id'], ['exam_sections.id']),
        sa.ForeignKeyConstraint(['question_id'], ['exam_questions.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'exam_ingestion_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='queued'),
        sa.Column('repo_url', sa.Text(), nullable=False),
        sa.Column('audio_repo_url', sa.Text(), nullable=True),
        sa.Column('parser_model', sa.String(length=120), nullable=True),
        sa.Column('stitch_model', sa.String(length=120), nullable=True),
        sa.Column('summary_json', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['exam_sources.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'exam_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('paper_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='in_progress'),
        sa.Column('objective_correct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('objective_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('auto_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('max_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('feedback_json', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['paper_id'], ['exam_papers.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'exam_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('attempt_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('selected_choices_json', sa.Text(), nullable=True),
        sa.Column('attachment_url', sa.Text(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('feedback_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['attempt_id'], ['exam_attempts.id']),
        sa.ForeignKeyConstraint(['question_id'], ['exam_questions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('attempt_id', 'question_id', name='unique_exam_attempt_response'),
    )


def downgrade():
    op.drop_table('exam_responses')
    op.drop_table('exam_attempts')
    op.drop_table('exam_ingestion_jobs')
    op.drop_table('exam_review_items')
    op.drop_table('exam_assets')
    op.drop_table('exam_answer_keys')
    op.drop_table('exam_choices')
    op.drop_table('exam_questions')
    op.drop_table('exam_passages')
    op.drop_table('exam_sections')
    op.drop_index('ix_exam_papers_publish_status', table_name='exam_papers')
    op.drop_table('exam_papers')
    op.drop_index('ix_exam_sources_source_type', table_name='exam_sources')
    op.drop_table('exam_sources')
