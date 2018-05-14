"""add property_address to bail_and_bond

Revision ID: 7ecafc40188c
Revises: 47dc91b89bfc
Create Date: 2018-05-04 16:38:00.799736

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7ecafc40188c'
down_revision = '47dc91b89bfc'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('bail_and_bond', sa.Column('property_address', sa.String))

def downgrade():
    op.drop_column('bail_and_bond', 'property_address')
