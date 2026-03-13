"""Add profile_image_url to users table

Revision ID: 2a8f36c5d8e4
Revises: 43db49eabe07
Create Date: 2026-03-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a8f36c5d8e4'
down_revision: Union[str, Sequence[str], None] = '43db49eabe07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('profile_image_url', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'profile_image_url')
