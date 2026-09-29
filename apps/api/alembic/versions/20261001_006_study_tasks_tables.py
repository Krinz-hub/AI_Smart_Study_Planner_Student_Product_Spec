"""006_study_tasks: study_tasks and study_sessions tables

Revision ID: 006_study_tasks
Revises: 005_learner_state
Create Date: 2026-10-01 05:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006_study_tasks'
down_revision: Union[str, None] = '005_learner_state'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. study_tasks
    op.create_table(
        'study_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('topics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('objective', sa.Text(), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('planned_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('planned_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('priority', sa.Numeric(precision=5, scale=3), nullable=False, server_default='0.500'),
        sa.Column('priority_version', sa.String(length=32), nullable=False, server_default='priority-v1'),
        sa.Column('reason', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='PENDING'),
        sa.Column('locked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('plan_version', sa.String(length=32), nullable=False, server_default='plan-v1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_study_tasks_user_id', 'study_tasks', ['user_id'])
    op.create_index('ix_study_tasks_subject_id', 'study_tasks', ['subject_id'])
    op.create_index('ix_study_tasks_topic_id', 'study_tasks', ['topic_id'])
    op.create_index('ix_study_tasks_planned_start', 'study_tasks', ['planned_start'])
    op.create_index('ix_study_tasks_status', 'study_tasks', ['status'])

    # 2. study_sessions
    op.create_table(
        'study_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('study_tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_status', sa.String(length=32), nullable=False, server_default='COMPLETED'),
        sa.Column('self_rating', sa.Numeric(precision=3, scale=2), nullable=True),
    )
    op.create_index('ix_study_sessions_user_id', 'study_sessions', ['user_id'])
    op.create_index('ix_study_sessions_task_id', 'study_sessions', ['task_id'])


def downgrade() -> None:
    op.drop_table('study_sessions')
    op.drop_table('study_tasks')
