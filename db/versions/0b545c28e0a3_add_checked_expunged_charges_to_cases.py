"""Add checked_expunged_charges to cases

Revision ID: 0b545c28e0a3
Revises: e12e27cc98a6
Create Date: 2021-07-22 11:38:19.928899

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0b545c28e0a3'
down_revision = 'e12e27cc98a6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cases', sa.Column('checked_expunged_charges', sa.Boolean(), server_default='false', nullable=False))


def downgrade():
    op.drop_column('cases', 'checked_expunged_charges')
