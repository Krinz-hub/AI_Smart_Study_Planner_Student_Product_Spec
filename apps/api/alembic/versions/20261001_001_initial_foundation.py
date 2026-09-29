"""001_initial_foundation: enable uuid-ossp and vector extensions

Revision ID: 001_initial_foundation
Revises: 
Create Date: 2026-10-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_foundation'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension for UUID primary keys
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    # Enable pgvector extension for embeddings
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector";')


def downgrade() -> None:
    # Downgrade drops extensions if required (safe to leave or drop)
    op.execute('DROP EXTENSION IF EXISTS "vector";')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp";')
