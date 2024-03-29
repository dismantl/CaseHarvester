"""Add jail_text to k_charges

Revision ID: cd14501526dc
Revises: 95589adca841
Create Date: 2021-08-23 08:13:09.871069

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'cd14501526dc'
down_revision = '95589adca841'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('k_charges', sa.Column('jail_text', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('k_charges', 'jail_text')
    # ### end Alembic commands ###
