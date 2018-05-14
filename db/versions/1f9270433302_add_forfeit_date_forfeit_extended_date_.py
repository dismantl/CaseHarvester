"""add forfeit_date, forfeit_extended_date, and days_extended to bail_and_bond table

Revision ID: 1f9270433302
Revises: 6d10dfbbb648
Create Date: 2018-05-04 15:47:20.718907

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1f9270433302'
down_revision = '6d10dfbbb648'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('bail_and_bond', sa.Column('forfeit_date', sa.Date))
    op.add_column('bail_and_bond', sa.Column('forfeit_date_str', sa.String))
    op.add_column('bail_and_bond', sa.Column('forfeit_extended_date', sa.Date))
    op.add_column('bail_and_bond', sa.Column('forfeit_extended_date_str', sa.String))
    op.add_column('bail_and_bond', sa.Column('days_extended', sa.Integer))

def downgrade():
    op.drop_column('bail_and_bond', 'days_extended')
    op.drop_column('bail_and_bond', 'forfeit_extended_date_str')
    op.drop_column('bail_and_bond', 'forfeit_extended_date')
    op.drop_column('bail_and_bond', 'forfeit_date_str')
    op.drop_column('bail_and_bond', 'forfeit_date')
