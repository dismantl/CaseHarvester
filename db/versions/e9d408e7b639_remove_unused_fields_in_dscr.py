"""Remove unused fields in DSCR

Revision ID: e9d408e7b639
Revises: f8b3c9cf0c10
Create Date: 2021-10-11 16:06:20.777095

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e9d408e7b639'
down_revision = 'f8b3c9cf0c10'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('dscr_related_persons', 'attorney_code')
    op.drop_column('dscr_related_persons', 'attorney_firm')
    op.drop_column('dscr_trials', 'reason')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('dscr_trials', sa.Column('reason', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dscr_related_persons', sa.Column('attorney_firm', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dscr_related_persons', sa.Column('attorney_code', sa.INTEGER(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
