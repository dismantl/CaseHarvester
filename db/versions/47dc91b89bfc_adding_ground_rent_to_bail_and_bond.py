"""adding ground_rent to bail_and_bond

Revision ID: 47dc91b89bfc
Revises: cd9aee766fbc
Create Date: 2018-05-04 16:31:09.309299

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '47dc91b89bfc'
down_revision = 'cd9aee766fbc'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('bail_and_bond', sa.Column('ground_rent', sa.Numeric))

def downgrade():
    op.drop_column('bail_and_bond', 'ground_rent')
