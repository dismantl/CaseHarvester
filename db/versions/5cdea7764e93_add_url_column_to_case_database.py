"""add url column to case database

Revision ID: 5cdea7764e93
Revises: 56753c018bcc
Create Date: 2018-04-08 14:03:03.324969

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5cdea7764e93'
down_revision = '56753c018bcc'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('cases', sa.Column('url', sa.String))

def downgrade():
    op.drop_column('cases', 'url')
