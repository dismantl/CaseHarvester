"""add sentence_term to dsk8_charges

Revision ID: 007964aa8288
Revises: b0b43970cbca
Create Date: 2018-05-04 15:24:07.251836

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007964aa8288'
down_revision = 'b0b43970cbca'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('dsk8_charges', sa.Column('sentence_term', sa.String))

def downgrade():
    op.drop_column('dsk8_charges', 'sentence_term')
