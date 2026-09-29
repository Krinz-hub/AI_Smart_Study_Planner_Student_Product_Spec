"""008_assessments: questions, quizzes, and quiz_attempts tables

Revision ID: 008_assessments
Revises: 007_documents
Create Date: 2026-10-01 07:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008_assessments'
down_revision: Union[str, None] = '007_documents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. questions
    op.create_table(
        'questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('topics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_type', sa.String(length=32), nullable=False),
        sa.Column('difficulty', sa.String(length=32), nullable=False),
        sa.Column('predicted_difficulty', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('actual_difficulty', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('correct_answer', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_chunk_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('document_chunks.id', ondelete='SET NULL'), nullable=True),
        sa.Column('generation_model', sa.String(length=64), nullable=True),
        sa.Column('generation_version', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_questions_topic_id', 'questions', ['topic_id'])
    op.create_index('ix_questions_difficulty', 'questions', ['difficulty'])

    # 2. quizzes
    op.create_table(
        'quizzes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('topics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='GENERATED', nullable=False),
        sa.Column('score', sa.Numeric(precision=5, scale=3), nullable=True),
        sa.Column('accuracy', sa.Numeric(precision=5, scale=3), nullable=True),
        sa.Column('total_questions', sa.Integer(), nullable=False),
        sa.Column('time_spent_seconds', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_quizzes_user_id', 'quizzes', ['user_id'])
    op.create_index('ix_quizzes_topic_id', 'quizzes', ['topic_id'])

    # 3. quiz_attempts
    op.create_table(
        'quiz_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('quiz_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('answer', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('response_time_seconds', sa.Integer(), nullable=True),
        sa.Column('attempted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_quiz_attempts_user_id', 'quiz_attempts', ['user_id'])
    op.create_index('ix_quiz_attempts_quiz_id', 'quiz_attempts', ['quiz_id'])
    op.create_index('ix_quiz_attempts_question_id', 'quiz_attempts', ['question_id'])


def downgrade() -> None:
    op.drop_table('quiz_attempts')
    op.drop_table('quizzes')
    op.drop_table('questions')
