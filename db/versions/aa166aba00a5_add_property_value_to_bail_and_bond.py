"""add property_value to bail_and_bond

Revision ID: aa166aba00a5
Revises: 7ecafc40188c
Create Date: 2018-05-04 16:50:47.586934

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aa166aba00a5'
down_revision = '7ecafc40188c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('bail_and_bond', sa.Column('property_value', sa.Numeric))

def downgrade():
    op.drop_column('bail_and_bond', 'property_value')
