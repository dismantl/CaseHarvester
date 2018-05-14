"""added scrape and parse timestamps to case table

Revision ID: da858bf1a1b3
Revises: 13f400fd5b59
Create Date: 2018-04-20 23:36:17.775501

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'da858bf1a1b3'
down_revision = '13f400fd5b59'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cases', sa.Column('last_scrape', sa.DateTime))
    op.add_column('cases', sa.Column('last_parse', sa.DateTime))


def downgrade():
    op.drop_column('cases', 'last_scrape')
    op.drop_column('cases', 'last_parse')
