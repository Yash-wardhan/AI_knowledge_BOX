"""add citations to messages

Revision ID: b7c1d2e3f4a5
Revises: faeaf0afcf46
Create Date: 2026-11-19 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = 'faeaf0afcf46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Sources shown under an assistant answer; NULL for user messages and
    # for messages saved before this column existed.
    op.add_column(
        'messages',
        sa.Column('citations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('messages', 'citations')
