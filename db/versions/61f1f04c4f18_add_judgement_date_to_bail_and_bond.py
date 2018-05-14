"""add judgement_date to bail_and_bond

Revision ID: 61f1f04c4f18
Revises: aa166aba00a5
Create Date: 2018-05-04 19:39:23.548178

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '61f1f04c4f18'
down_revision = 'aa166aba00a5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('bail_and_bond', sa.Column('judgment_date', sa.Date))
    op.add_column('bail_and_bond', sa.Column('judgment_date_str', sa.String))


def downgrade():
    op.drop_column('bail_and_bond', 'judgment_date_str')
    op.drop_column('bail_and_bond', 'judgment_date')
