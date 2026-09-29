"""005_learner_state: mastery_states, memory_states, and confidence_states

Revision ID: 005_learner_state
Revises: 004_events_audit
Create Date: 2026-10-01 04:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_learner_state'
down_revision: Union[str, None] = '004_events_audit'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. mastery_states
    op.create_table(
        'mastery_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('topics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mastery_probability', sa.Numeric(precision=4, scale=3), nullable=False, server_default='0.100'),
        sa.Column('confidence', sa.Numeric(precision=4, scale=3), nullable=False, server_default='0.000'),
        sa.Column('evidence_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('state', sa.String(length=32), nullable=False, server_default='UNKNOWN'),
        sa.Column('model_version', sa.String(length=32), nullable=False, server_default='bkt-v1'),
        sa.Column('last_assessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('user_id', 'topic_id', name='uq_mastery_user_topic'),
    )
    op.create_index('ix_mastery_states_user_id', 'mastery_states', ['user_id'])
    op.create_index('ix_mastery_states_topic_id', 'mastery_states', ['topic_id'])

    # 2. memory_states
    op.create_table(
        'memory_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('topics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stability', sa.Numeric(precision=8, scale=2), nullable=False, server_default='1.00'),
        sa.Column('difficulty', sa.Numeric(precision=4, scale=2), nullable=False, server_default='5.00'),
        sa.Column('retrievability', sa.Numeric(precision=4, scale=3), nullable=False, server_default='1.000'),
        sa.Column('next_review_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('fsrs_version', sa.String(length=32), nullable=False, server_default='fsrs-v4'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('user_id', 'topic_id', name='uq_memory_user_topic'),
    )
    op.create_index('ix_memory_states_user_id', 'memory_states', ['user_id'])
    op.create_index('ix_memory_states_topic_id', 'memory_states', ['topic_id'])

    # 3. confidence_states
    op.create_table(
        'confidence_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('topics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('self_confidence', sa.Numeric(precision=4, scale=3), nullable=False, server_default='0.500'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('user_id', 'topic_id', name='uq_confidence_user_topic'),
    )
    op.create_index('ix_confidence_states_user_id', 'confidence_states', ['user_id'])
    op.create_index('ix_confidence_states_topic_id', 'confidence_states', ['topic_id'])


def downgrade() -> None:
    op.drop_table('confidence_states')
    op.drop_table('memory_states')
    op.drop_table('mastery_states')
