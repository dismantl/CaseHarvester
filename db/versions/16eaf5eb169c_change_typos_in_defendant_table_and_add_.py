"""change typos in defendant table and add address_2 column'

Revision ID: 16eaf5eb169c
Revises: 466325744aaa
Create Date: 2018-04-26 12:27:55.976026

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '16eaf5eb169c'
down_revision = '466325744aaa'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('defendents','defendants')
    op.alter_column('defendants','defendent_name',new_column_name='defendant_name')
    op.alter_column('defendants','street_address',new_column_name='address_1')
    op.add_column('defendants', sa.Column('address_2', sa.String))

def downgrade():
    op.drop_column('defendants', 'address_2')
    op.alter_column('defendants','address_1',new_column_name='street_address')
    op.alter_column('defendants','defendant_name',new_column_name='defendent_name')
    op.rename_table('defendants','defendents')
