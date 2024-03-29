"""Added subsequent_offense to dstraf_charges

Revision ID: 20ee054f0e99
Revises: 4394875fda45
Create Date: 2021-07-23 15:25:51.062257

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20ee054f0e99'
down_revision = '4394875fda45'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('dstraf_dispositions', sa.Column('subsequent_offense', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('dstraf_dispositions', 'subsequent_offense')
    # ### end Alembic commands ###
