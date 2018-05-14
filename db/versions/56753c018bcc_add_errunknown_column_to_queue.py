"""add errunknown column to queue

Revision ID: 56753c018bcc
Revises: ac3c66efcfeb
Create Date: 2018-04-07 16:07:21.229635

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '56753c018bcc'
down_revision = 'ac3c66efcfeb'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('queue', sa.Column('errunknown', sa.String))

def downgrade():
    op.drop_column('queue', 'errunknown')
