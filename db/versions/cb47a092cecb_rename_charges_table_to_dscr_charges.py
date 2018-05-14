"""rename charges table to dscr_charges

Revision ID: cb47a092cecb
Revises: d4d38815e85c
Create Date: 2018-05-02 13:41:48.112140

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cb47a092cecb'
down_revision = 'd4d38815e85c'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('charges','dscr_charges')

def downgrade():
    op.rename_table('dscr_charges','charges')
