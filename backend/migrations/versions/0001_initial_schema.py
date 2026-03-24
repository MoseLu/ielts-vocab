"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-24

This migration represents the full database schema as of the Flask-Migrate
introduction. Existing databases should run `flask db stamp head` instead of
`flask db upgrade` to avoid re-creating tables that already exist.
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('tokens_revoked_before', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
    )

    # ── email_verification_codes ─────────────────────────────────────────────
    op.create_table(
        'email_verification_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('purpose', sa.String(length=30), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_email_verification_codes_email', 'email_verification_codes', ['email'])

    # ── user_progress (legacy day-based) ─────────────────────────────────────
    op.create_table(
        'user_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('day', sa.Integer(), nullable=False),
        sa.Column('current_index', sa.Integer(), nullable=True),
        sa.Column('correct_count', sa.Integer(), nullable=True),
        sa.Column('wrong_count', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'day', name='unique_user_day'),
    )

    # ── user_book_progress ───────────────────────────────────────────────────
    op.create_table(
        'user_book_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.String(length=50), nullable=False),
        sa.Column('current_index', sa.Integer(), nullable=True),
        sa.Column('correct_count', sa.Integer(), nullable=True),
        sa.Column('wrong_count', sa.Integer(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'book_id', name='unique_user_book'),
    )

    # ── user_chapter_progress ────────────────────────────────────────────────
    op.create_table(
        'user_chapter_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.String(length=50), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('words_learned', sa.Integer(), nullable=True),
        sa.Column('correct_count', sa.Integer(), nullable=True),
        sa.Column('wrong_count', sa.Integer(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'book_id', 'chapter_id', name='unique_user_book_chapter'),
    )

    # ── user_chapter_mode_progress ───────────────────────────────────────────
    op.create_table(
        'user_chapter_mode_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.String(length=50), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('mode', sa.String(length=30), nullable=False),
        sa.Column('correct_count', sa.Integer(), nullable=True),
        sa.Column('wrong_count', sa.Integer(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'book_id', 'chapter_id', 'mode',
                            name='unique_user_book_chapter_mode'),
    )

    # ── custom_books ─────────────────────────────────────────────────────────
    op.create_table(
        'custom_books',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── custom_book_chapters ─────────────────────────────────────────────────
    op.create_table(
        'custom_book_chapters',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('book_id', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['book_id'], ['custom_books.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── custom_book_words ────────────────────────────────────────────────────
    op.create_table(
        'custom_book_words',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chapter_id', sa.String(length=50), nullable=False),
        sa.Column('word', sa.String(length=100), nullable=False),
        sa.Column('phonetic', sa.String(length=100), nullable=True),
        sa.Column('pos', sa.String(length=50), nullable=True),
        sa.Column('definition', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['chapter_id'], ['custom_book_chapters.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── user_added_books ─────────────────────────────────────────────────────
    op.create_table(
        'user_added_books',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.String(length=50), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'book_id', name='unique_user_added_book'),
    )

    # ── user_wrong_words ─────────────────────────────────────────────────────
    op.create_table(
        'user_wrong_words',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('word', sa.String(length=100), nullable=False),
        sa.Column('phonetic', sa.String(length=100), nullable=True),
        sa.Column('pos', sa.String(length=50), nullable=True),
        sa.Column('definition', sa.Text(), nullable=True),
        sa.Column('wrong_count', sa.Integer(), nullable=True),
        sa.Column('listening_correct', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('listening_wrong',   sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('meaning_correct',   sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('meaning_wrong',     sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('dictation_correct', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('dictation_wrong',   sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'word', name='unique_user_wrong_word'),
    )

    # ── user_conversation_history ────────────────────────────────────────────
    op.create_table(
        'user_conversation_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── user_study_sessions ──────────────────────────────────────────────────
    op.create_table(
        'user_study_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('mode', sa.String(length=30), nullable=True),
        sa.Column('book_id', sa.String(length=100), nullable=True),
        sa.Column('chapter_id', sa.String(length=100), nullable=True),
        sa.Column('words_studied', sa.Integer(), nullable=True),
        sa.Column('correct_count', sa.Integer(), nullable=True),
        sa.Column('wrong_count', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── user_memory ──────────────────────────────────────────────────────────
    op.create_table(
        'user_memory',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('goals', sa.Text(), nullable=True),
        sa.Column('ai_notes', sa.Text(), nullable=True),
        sa.Column('conversation_summary', sa.Text(), nullable=True),
        sa.Column('summary_turn_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    # ── revoked_tokens ───────────────────────────────────────────────────────
    op.create_table(
        'revoked_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('jti', sa.String(length=64), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jti'),
    )
    op.create_index('ix_revoked_tokens_jti', 'revoked_tokens', ['jti'])

    # ── user_quick_memory_records ────────────────────────────────────────────
    op.create_table(
        'user_quick_memory_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('word', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False, server_default=sa.text("'unknown'")),
        sa.Column('first_seen', sa.BigInteger(), nullable=True),
        sa.Column('last_seen', sa.BigInteger(), nullable=True),
        sa.Column('known_count', sa.Integer(), nullable=True),
        sa.Column('unknown_count', sa.Integer(), nullable=True),
        sa.Column('next_review', sa.BigInteger(), nullable=True),
        sa.Column('fuzzy_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'word', name='unique_user_qm_word'),
    )

    # ── user_smart_word_stats ────────────────────────────────────────────────
    op.create_table(
        'user_smart_word_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('word', sa.String(length=100), nullable=False),
        sa.Column('listening_correct', sa.Integer(), nullable=True),
        sa.Column('listening_wrong',   sa.Integer(), nullable=True),
        sa.Column('meaning_correct',   sa.Integer(), nullable=True),
        sa.Column('meaning_wrong',     sa.Integer(), nullable=True),
        sa.Column('dictation_correct', sa.Integer(), nullable=True),
        sa.Column('dictation_wrong',   sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'word', name='unique_user_smart_word'),
    )

    # ── search_cache ─────────────────────────────────────────────────────────
    op.create_table(
        'search_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('query', sa.String(length=500), nullable=False),
        sa.Column('result', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('query'),
    )

    # ── user_learning_notes ──────────────────────────────────────────────────
    op.create_table(
        'user_learning_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('word_context', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_learning_notes_user_id', 'user_learning_notes', ['user_id'])

    # ── user_daily_summaries ─────────────────────────────────────────────────
    op.create_table(
        'user_daily_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.String(length=10), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'date', name='unique_user_date_summary'),
    )
    op.create_index('ix_user_daily_summaries_user_id', 'user_daily_summaries', ['user_id'])


def downgrade():
    op.drop_index('ix_user_daily_summaries_user_id', table_name='user_daily_summaries')
    op.drop_table('user_daily_summaries')
    op.drop_index('ix_user_learning_notes_user_id', table_name='user_learning_notes')
    op.drop_table('user_learning_notes')
    op.drop_table('search_cache')
    op.drop_table('user_smart_word_stats')
    op.drop_table('user_quick_memory_records')
    op.drop_index('ix_revoked_tokens_jti', table_name='revoked_tokens')
    op.drop_table('revoked_tokens')
    op.drop_table('user_memory')
    op.drop_table('user_study_sessions')
    op.drop_table('user_conversation_history')
    op.drop_table('user_wrong_words')
    op.drop_table('user_added_books')
    op.drop_table('custom_book_words')
    op.drop_table('custom_book_chapters')
    op.drop_table('custom_books')
    op.drop_table('user_chapter_mode_progress')
    op.drop_table('user_chapter_progress')
    op.drop_table('user_book_progress')
    op.drop_table('user_progress')
    op.drop_index('ix_email_verification_codes_email', table_name='email_verification_codes')
    op.drop_table('email_verification_codes')
    op.drop_table('users')
