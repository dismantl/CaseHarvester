"""add release_date and release_reason to bail_and_bond table

Revision ID: 6d10dfbbb648
Revises: 007964aa8288
Create Date: 2018-05-04 15:30:29.619879

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d10dfbbb648'
down_revision = '007964aa8288'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('bail_and_bond', sa.Column('release_date', sa.Date))
    op.add_column('bail_and_bond', sa.Column('release_date_str', sa.String))
    op.add_column('bail_and_bond', sa.Column('release_reason', sa.String))

def downgrade():
    op.drop_column('bail_and_bond', 'release_reason')
    op.drop_column('bail_and_bond', 'release_date_str')
    op.drop_column('bail_and_bond', 'release_date')
