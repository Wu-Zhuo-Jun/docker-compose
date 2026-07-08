"""create chat and document review tables

Revision ID: a1b2c3d4e5f6
Revises: 9057f05d66ea
Create Date: 2026-07-08 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9057f05d66ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create chat_sessions, chat_messages, document_reviews, pending_documents tables."""

    # 1. Create chat_sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(255), server_default='新对话'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_chat_sessions_id', 'chat_sessions', ['id'])
    op.create_index('ix_chat_sessions_user_id', 'chat_sessions', ['user_id'])

    # 2. Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_chat_messages_id', 'chat_messages', ['id'])
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'])

    # 3. Add role column to users table (if not exists)
    # Note: This is already in the User model, but we need to ensure it exists
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(64) DEFAULT 'user'")

    # 4. Create document_reviews table
    op.create_table(
        'document_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('doc_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('uploader_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('reviewer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('review_comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_document_reviews_id', 'document_reviews', ['id'])
    op.create_index('ix_document_reviews_doc_id', 'document_reviews', ['doc_id'])
    op.create_index('ix_document_reviews_uploader_id', 'document_reviews', ['uploader_id'])
    op.create_index('ix_document_reviews_status', 'document_reviews', ['status'])

    # 5. Create pending_documents table
    op.create_table(
        'pending_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('doc_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('uploader_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_pending_documents_id', 'pending_documents', ['id'])
    op.create_index('ix_pending_documents_doc_id', 'pending_documents', ['doc_id'])
    op.create_index('ix_pending_documents_uploader_id', 'pending_documents', ['uploader_id'])


def downgrade() -> None:
    """Drop chat_sessions, chat_messages, document_reviews, pending_documents tables."""
    op.drop_table('pending_documents')
    op.drop_table('document_reviews')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
