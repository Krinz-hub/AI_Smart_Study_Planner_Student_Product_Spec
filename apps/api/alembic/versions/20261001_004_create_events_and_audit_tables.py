"""004_events_audit: learner events and audit logs

Revision ID: 004_events_audit
Revises: 003_create_student_state_tables
Create Date: 2026-10-01 03:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_events_audit'
down_revision: Union[str, None] = '003_create_student_state_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Expand alembic_version version_num column size to 128 characters
    op.execute('ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128);')

    # 1. learner_events
    op.create_table(
        'learner_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('entity_type', sa.String(length=64), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('evidence_category', sa.String(length=32), nullable=False, server_default='BEHAVIOR'),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_learner_events_user_id', 'learner_events', ['user_id'])
    op.create_index('ix_learner_events_event_type', 'learner_events', ['event_type'])
    op.create_index('ix_learner_events_entity_id', 'learner_events', ['entity_id'])
    op.create_index('ix_learner_events_idempotency_key', 'learner_events', ['idempotency_key'], unique=True)
    op.create_index('ix_learner_events_created_at', 'learner_events', ['created_at'])

    # 2. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('actor_type', sa.String(length=32), nullable=False, server_default='student'),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('entity_type', sa.String(length=64), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('learner_events')
