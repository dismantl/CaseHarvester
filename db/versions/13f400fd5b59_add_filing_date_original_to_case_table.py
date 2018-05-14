"""add filing_date_original to case table

Revision ID: 13f400fd5b59
Revises: 5cdea7764e93
Create Date: 2018-04-13 12:15:49.218584

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '13f400fd5b59'
down_revision = '5cdea7764e93'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('cases', sa.Column('filing_date_original', sa.String))

def downgrade():
    op.drop_column('cases', 'filing_date_original')
