"""009_exam_mode: exam_plans table

Revision ID: 009_exam_mode
Revises: 008_assessments
Create Date: 2026-10-01 08:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '009_exam_mode'
down_revision: Union[str, None] = '008_assessments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'exam_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('exam_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='PROPOSED', nullable=False),
        sa.Column('total_topics_covered', sa.Integer(), nullable=False),
        sa.Column('syllabus_coverage_pct', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('target_exam_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('daily_workload_minutes', sa.Integer(), nullable=False),
        sa.Column('workload_ceiling_minutes', sa.Integer(), server_default='360', nullable=False),
        sa.Column('rescue_actions', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('tasks_snapshot', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_exam_plans_user_id', 'exam_plans', ['user_id'])
    op.create_index('ix_exam_plans_exam_id', 'exam_plans', ['exam_id'])


def downgrade() -> None:
    op.drop_table('exam_plans')
