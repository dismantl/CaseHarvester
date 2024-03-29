"""Remove unused fields in DSTRAF

Revision ID: db345d84fc41
Revises: 67fc57997beb
Create Date: 2021-10-11 16:59:16.928524

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'db345d84fc41'
down_revision = '67fc57997beb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('dstraf', 'citation_number')
    op.drop_column('dstraf_charges', 'charge')
    op.drop_column('dstraf_dispositions', 'addition_charge')
    op.drop_column('dstraf_related_persons', 'attorney_firm')
    op.drop_column('dstraf_related_persons', 'agency_code')
    op.drop_column('dstraf_related_persons', 'officer_id')
    op.drop_column('dstraf_related_persons', 'agency_sub_code')
    op.drop_column('dstraf_related_persons', 'attorney_code')
    op.drop_column('dstraf_trials', 'trial_type')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('dstraf_trials', sa.Column('trial_type', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dstraf_related_persons', sa.Column('attorney_code', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('dstraf_related_persons', sa.Column('agency_sub_code', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dstraf_related_persons', sa.Column('officer_id', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dstraf_related_persons', sa.Column('agency_code', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dstraf_related_persons', sa.Column('attorney_firm', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dstraf_dispositions', sa.Column('addition_charge', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dstraf_charges', sa.Column('charge', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dstraf', sa.Column('citation_number', sa.VARCHAR(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
