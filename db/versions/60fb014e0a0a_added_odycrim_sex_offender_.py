"""Added odycrim_sex_offender_registrations table

Revision ID: 60fb014e0a0a
Revises: d8738272f350
Create Date: 2021-07-03 17:20:14.005447

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '60fb014e0a0a'
down_revision = 'd8738272f350'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('odycrim_sex_offender_registrations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(), nullable=True),
    sa.Column('case_number', sa.String(), nullable=True),
    sa.Column('notes', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['case_number'], ['odycrim.case_number'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ixh_odycrim_sex_offender_registrations_case_number', 'odycrim_sex_offender_registrations', ['case_number'], unique=False, postgresql_using='hash')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ixh_odycrim_sex_offender_registrations_case_number', table_name='odycrim_sex_offender_registrations')
    op.drop_table('odycrim_sex_offender_registrations')
    # ### end Alembic commands ###
