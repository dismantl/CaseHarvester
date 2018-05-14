"""add fine to dsk8_charges

Revision ID: cd9aee766fbc
Revises: 1f9270433302
Create Date: 2018-05-04 16:11:45.626539

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cd9aee766fbc'
down_revision = '1f9270433302'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('dsk8_charges', sa.Column('fine', sa.Numeric))

def downgrade():
    op.drop_column('dsk8_charges', 'fine')
