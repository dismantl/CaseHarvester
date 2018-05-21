"""adding amount_vehicle and tij_vehicle to cc_judgments

Revision ID: 26b295254ad0
Revises: d2239f7d4a65
Create Date: 2018-05-21 10:28:36.068341

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '26b295254ad0'
down_revision = 'd2239f7d4a65'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('cc_judgments', sa.Column('amount_vehicle', sa.Boolean(), nullable=True))
    op.add_column('cc_judgments', sa.Column('tij_vehicle', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('cc_judgments', 'tij_vehicle')
    op.drop_column('cc_judgments', 'amount_vehicle')
    # ### end Alembic commands ###
