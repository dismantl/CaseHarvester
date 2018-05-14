"""change type of tracking_number column in DSCR

Revision ID: 466325744aaa
Revises: da858bf1a1b3
Create Date: 2018-04-26 10:20:54.975328

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '466325744aaa'
down_revision = 'da858bf1a1b3'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('DSCR', 'tracking_number', type_=sa.BigInteger)


def downgrade():
    op.alter_column('DSCR', 'tracking_number', type_=sa.Integer)
