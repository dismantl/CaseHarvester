"""Remove unused fields in ODYCVCIT

Revision ID: f8b3c9cf0c10
Revises: 4c53c17fe94c
Create Date: 2021-10-11 15:59:01.005157

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f8b3c9cf0c10'
down_revision = '4c53c17fe94c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ixh_odycvcit_sex_offender_registrations_case_number', table_name='odycvcit_sex_offender_registrations')
    op.drop_table('odycvcit_sex_offender_registrations')
    op.drop_column('odycvcit_charges', 'jail_death')
    op.drop_column('odycvcit_charges', 'jail_suspend_all_but_months')
    op.drop_column('odycvcit_charges', 'jail_cons_conc')
    op.drop_column('odycvcit_charges', 'jail_life')
    op.drop_column('odycvcit_charges', 'jail_suspend_all_but_years')
    op.drop_column('odycvcit_charges', 'jail_suspended_term')
    op.drop_column('odycvcit_charges', 'jail_suspend_all_but_hours')
    op.drop_column('odycvcit_charges', 'jail_suspend_all_but_days')
    op.drop_column('odycvcit_documents', 'filed_by')
    op.drop_column('odycvcit_involved_parties', 'removal_date')
    op.drop_column('odycvcit_involved_parties', 'removal_date_str')
    op.drop_column('odycvcit_involved_parties', 'appearance_date_str')
    op.drop_column('odycvcit_involved_parties', 'appearance_date')
    op.drop_column('odycvcit_services', 'service_status')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('odycvcit_services', sa.Column('service_status', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('odycvcit_involved_parties', sa.Column('appearance_date', sa.DATE(), autoincrement=False, nullable=True))
    op.add_column('odycvcit_involved_parties', sa.Column('appearance_date_str', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('odycvcit_involved_parties', sa.Column('removal_date_str', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('odycvcit_involved_parties', sa.Column('removal_date', sa.DATE(), autoincrement=False, nullable=True))
    op.add_column('odycvcit_documents', sa.Column('filed_by', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('odycvcit_charges', sa.Column('jail_suspend_all_but_days', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('odycvcit_charges', sa.Column('jail_suspend_all_but_hours', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('odycvcit_charges', sa.Column('jail_suspended_term', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('odycvcit_charges', sa.Column('jail_suspend_all_but_years', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('odycvcit_charges', sa.Column('jail_life', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('odycvcit_charges', sa.Column('jail_cons_conc', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('odycvcit_charges', sa.Column('jail_suspend_all_but_months', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('odycvcit_charges', sa.Column('jail_death', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.create_table('odycvcit_sex_offender_registrations',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('type', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('notes', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('case_number', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['case_number'], ['odycvcit.case_number'], name='odycvcit_sex_offender_registrations_case_number_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='odycvcit_sex_offender_registrations_pkey')
    )
    op.create_index('ixh_odycvcit_sex_offender_registrations_case_number', 'odycvcit_sex_offender_registrations', ['case_number'], unique=False)
    # ### end Alembic commands ###
