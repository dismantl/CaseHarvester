"""Add second address field to k_party_addresses

Revision ID: 95589adca841
Revises: 9dbb2931da09
Create Date: 2021-08-23 07:05:28.272833

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '95589adca841'
down_revision = '9dbb2931da09'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('k_party_addresses', 'address', new_column_name='address_1')
    op.add_column('k_party_addresses', sa.Column('address_2', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('k_party_addresses', 'address_2')
    op.alter_column('k_party_addresses', 'address_1', new_column_name='address')
    # ### end Alembic commands ###
