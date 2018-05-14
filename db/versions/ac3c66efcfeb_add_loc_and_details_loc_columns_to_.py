"""add loc and details_loc columns to cases db

Revision ID: ac3c66efcfeb
Revises:
Create Date: 2018-04-06 18:23:44.687705

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ac3c66efcfeb'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('cases', sa.Column('loc', sa.Integer))
    op.add_column('cases', sa.Column('detail_loc', sa.String))

def downgrade():
    op.drop_column('cases', 'loc')
    op.drop_column('cases', 'detail_loc')
