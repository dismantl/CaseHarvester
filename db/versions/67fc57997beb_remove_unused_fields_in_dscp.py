"""Remove unused fields in DSCP

Revision ID: 67fc57997beb
Revises: 05688275b38c
Create Date: 2021-10-11 16:21:42.352090

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67fc57997beb'
down_revision = '05688275b38c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('dscp_defendant_aliases', 'state')
    op.drop_column('dscp_defendant_aliases', 'address_2')
    op.drop_column('dscp_defendant_aliases', 'address_1')
    op.drop_column('dscp_defendant_aliases', 'zip_code')
    op.drop_column('dscp_defendant_aliases', 'city')
    op.drop_column('dscp_related_persons', 'state')
    op.drop_column('dscp_related_persons', 'attorney_firm')
    op.drop_column('dscp_related_persons', 'attorney_code')
    op.drop_column('dscp_related_persons', 'address_2')
    op.drop_column('dscp_related_persons', 'address_1')
    op.drop_column('dscp_related_persons', 'zip_code')
    op.drop_column('dscp_related_persons', 'city')
    op.drop_column('dscp_trials', 'reason')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('dscp_trials', sa.Column('reason', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dscp_related_persons', sa.Column('city', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dscp_related_persons', sa.Column('zip_code', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dscp_related_persons', sa.Column('address_1', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dscp_related_persons', sa.Column('address_2', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dscp_related_persons', sa.Column('attorney_code', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('dscp_related_persons', sa.Column('attorney_firm', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dscp_related_persons', sa.Column('state', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dscp_defendant_aliases', sa.Column('city', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dscp_defendant_aliases', sa.Column('zip_code', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dscp_defendant_aliases', sa.Column('address_1', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dscp_defendant_aliases', sa.Column('address_2', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('dscp_defendant_aliases', sa.Column('state', sa.VARCHAR(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###