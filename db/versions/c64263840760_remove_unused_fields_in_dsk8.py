"""Remove unused fields in DSK8

Revision ID: c64263840760
Revises: a68a233d6b44
Create Date: 2021-10-12 09:06:59.559153

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c64263840760'
down_revision = 'a68a233d6b44'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('dsk8_defendants', 'weight')
    op.drop_column('dsk8_defendants', 'height')
    op.drop_column('dsk8_related_persons', 'agency_code')
    op.drop_column('dsk8_related_persons', 'agency_sub_code')
    op.drop_column('dsk8_related_persons', 'attorney_firm')
    op.drop_column('dsk8_related_persons', 'attorney_code')
    op.drop_column('dsk8_related_persons', 'officer_id')
    op.drop_column('dsk8_trials', 'trial_type')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('dsk8_trials', sa.Column('trial_type', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dsk8_related_persons', sa.Column('officer_id', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dsk8_related_persons', sa.Column('attorney_code', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('dsk8_related_persons', sa.Column('attorney_firm', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dsk8_related_persons', sa.Column('agency_sub_code', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dsk8_related_persons', sa.Column('agency_code', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dsk8_defendants', sa.Column('height', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('dsk8_defendants', sa.Column('weight', sa.INTEGER(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
