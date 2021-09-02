"""Add pg_dockets.docket_text

Revision ID: 5a9fc170dd16
Revises: ff6daa02db69
Create Date: 2021-09-01 19:33:13.314129

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5a9fc170dd16'
down_revision = 'ff6daa02db69'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('pg_dockets', sa.Column('docket_text', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('pg_dockets', 'docket_text')
    # ### end Alembic commands ###
