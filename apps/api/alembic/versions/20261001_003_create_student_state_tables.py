"""003_create_student_state_tables: student profiles, subjects, topics, relationships, exams, availability, goals

Revision ID: 003_create_student_state_tables
Revises: 002_create_users_table
Create Date: 2026-10-01 02:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_create_student_state_tables'
down_revision: Union[str, None] = '002_create_users_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. student_profiles
    op.create_table(
        'student_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('institution', sa.Text(), nullable=True),
        sa.Column('degree', sa.Text(), nullable=True),
        sa.Column('semester', sa.Text(), nullable=True),
        sa.Column('branch', sa.Text(), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_student_profiles_user_id', 'student_profiles', ['user_id'])

    # 2. subjects
    op.create_table(
        'subjects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_subjects_user_id', 'subjects', ['user_id'])

    # 3. topics
    op.create_table(
        'topics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('topics.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('syllabus_weight', sa.Numeric(precision=5, scale=2), nullable=True, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_topics_subject_id', 'topics', ['subject_id'])
    op.create_index('ix_topics_parent_topic_id', 'topics', ['parent_topic_id'])

    # 4. topic_relationships
    op.create_table(
        'topic_relationships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('topics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('topics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=3, scale=2), nullable=False, server_default='1.0'),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='manual'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_topic_rel_source', 'topic_relationships', ['source_topic_id'])
    op.create_index('ix_topic_rel_target', 'topic_relationships', ['target_topic_id'])

    # 5. exams
    op.create_table(
        'exams',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('exam_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_exams_user_id', 'exams', ['user_id'])
    op.create_index('ix_exams_subject_id', 'exams', ['subject_id'])

    # 6. availability_windows
    op.create_table(
        'availability_windows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('weekday', sa.SmallInteger(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )
    op.create_index('ix_availability_windows_user_id', 'availability_windows', ['user_id'])

    # 7. goals
    op.create_table(
        'goals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subjects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('topics.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_value', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('priority', sa.Numeric(precision=5, scale=2), nullable=False, server_default='1.0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_goals_user_id', 'goals', ['user_id'])


def downgrade() -> None:
    op.drop_table('goals')
    op.drop_table('availability_windows')
    op.drop_table('exams')
    op.drop_table('topic_relationships')
    op.drop_table('topics')
    op.drop_table('subjects')
    op.drop_table('student_profiles')
