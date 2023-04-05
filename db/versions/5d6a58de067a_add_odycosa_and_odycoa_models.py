"""Add ODYCOSA and ODYCOA models

Revision ID: 5d6a58de067a
Revises: c063d4f8fbf2
Create Date: 2023-04-05 12:12:21.386164

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d6a58de067a'
down_revision = 'c063d4f8fbf2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('odycosa',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('court_system', sa.String(), nullable=True),
    sa.Column('case_title', sa.String(), nullable=True),
    sa.Column('case_type', sa.String(), nullable=True),
    sa.Column('filing_date', sa.Date(), nullable=True),
    sa.Column('filing_date_str', sa.String(), nullable=True),
    sa.Column('case_status', sa.String(), nullable=True),
    sa.Column('tracking_numbers', sa.String(), nullable=True),
    sa.Column('authoring_judge', sa.String(), nullable=True),
    sa.Column('case_number', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['case_number'], ['cases.case_number'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_number')
    )
    op.create_index('ixh_odycosa_case_number', 'odycosa', ['case_number'], unique=False, postgresql_using='hash')
    op.create_table('odycosa_court_schedule',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('event_type', sa.String(), nullable=False),
    sa.Column('date', sa.Date(), nullable=True),
    sa.Column('date_str', sa.String(), nullable=True),
    sa.Column('time', sa.Time(), nullable=True),
    sa.Column('time_str', sa.String(), nullable=True),
    sa.Column('case_number', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['case_number'], ['odycosa.case_number'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ixh_odycosa_court_schedule_case_number', 'odycosa_court_schedule', ['case_number'], unique=False, postgresql_using='hash')
    op.create_table('odycosa_documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('file_date', sa.Date(), nullable=True),
    sa.Column('file_date_str', sa.String(), nullable=True),
    sa.Column('document_name', sa.String(), nullable=False),
    sa.Column('case_number', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['case_number'], ['odycosa.case_number'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ixh_odycosa_documents_case_number', 'odycosa_documents', ['case_number'], unique=False, postgresql_using='hash')
    op.create_table('odycosa_involved_parties',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('party_type', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('agency_name', sa.String(), nullable=True),
    sa.Column('address_1', sa.String(), nullable=True),
    sa.Column('address_2', sa.String(), nullable=True),
    sa.Column('city', sa.String(), nullable=True),
    sa.Column('state', sa.String(), nullable=True),
    sa.Column('zip_code', sa.String(), nullable=True),
    sa.Column('case_number', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['case_number'], ['odycosa.case_number'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ixh_odycosa_involved_parties_case_number', 'odycosa_involved_parties', ['case_number'], unique=False, postgresql_using='hash')
    op.create_table('odycosa_judgments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('judgment_event_type', sa.String(), nullable=True),
    sa.Column('issue_date', sa.Date(), nullable=True),
    sa.Column('issue_date_str', sa.String(), nullable=True),
    sa.Column('comment', sa.String(), nullable=True),
    sa.Column('case_number', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['case_number'], ['odycosa.case_number'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ixh_odycosa_judgment_case_number', 'odycosa_judgments', ['case_number'], unique=False, postgresql_using='hash')
    op.create_table('odycosa_reference_numbers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ref_num', sa.String(), nullable=False),
    sa.Column('ref_num_type', sa.String(), nullable=False),
    sa.Column('case_number', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['case_number'], ['odycosa.case_number'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ixh_odycosa_reference_numbers_case_number', 'odycosa_reference_numbers', ['case_number'], unique=False, postgresql_using='hash')
    op.create_table('odycosa_attorneys',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('appearance_date', sa.Date(), nullable=True),
    sa.Column('appearance_date_str', sa.String(), nullable=True),
    sa.Column('removal_date', sa.Date(), nullable=True),
    sa.Column('removal_date_str', sa.String(), nullable=True),
    sa.Column('address_1', sa.String(), nullable=True),
    sa.Column('address_2', sa.String(), nullable=True),
    sa.Column('address_3', sa.String(), nullable=True),
    sa.Column('city', sa.String(), nullable=True),
    sa.Column('state', sa.String(), nullable=True),
    sa.Column('zip_code', sa.String(), nullable=True),
    sa.Column('party_id', sa.Integer(), nullable=True),
    sa.Column('case_number', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['case_number'], ['odycosa.case_number'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['party_id'], ['odycosa_involved_parties.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ixh_odycosa_attorneys_case_number', 'odycosa_attorneys', ['case_number'], unique=False, postgresql_using='hash')
    op.create_table('odycoa',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('court_system', sa.String(), nullable=True),
    sa.Column('case_title', sa.String(), nullable=True),
    sa.Column('case_type', sa.String(), nullable=True),
    sa.Column('filing_date', sa.Date(), nullable=True),
    sa.Column('filing_date_str', sa.String(), nullable=True),
    sa.Column('case_status', sa.String(), nullable=True),
    sa.Column('tracking_numbers', sa.String(), nullable=True),
    sa.Column('authoring_judge', sa.String(), nullable=True),
    sa.Column('case_number', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['case_number'], ['cases.case_number'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_number')
    )
    op.create_index('ixh_odycoa_case_number', 'odycoa', ['case_number'], unique=False, postgresql_using='hash')
    op.create_table('odycoa_court_schedule',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('event_type', sa.String(), nullable=False),
    sa.Column('date', sa.Date(), nullable=True),
    sa.Column('date_str', sa.String(), nullable=True),
    sa.Column('time', sa.Time(), nullable=True),
    sa.Column('time_str', sa.String(), nullable=True),
    sa.Column('result', sa.String(), nullable=True),
    sa.Column('panel_judges', sa.String(), nullable=True),
    sa.Column('case_number', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['case_number'], ['odycoa.case_number'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ixh_odycoa_court_schedule_case_number', 'odycoa_court_schedule', ['case_number'], unique=False, postgresql_using='hash')
    op.create_table('odycoa_documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('file_date', sa.Date(), nullable=True),
    sa.Column('file_date_str', sa.String(), nullable=True),
    sa.Column('document_name', sa.String(), nullable=False),
    sa.Column('case_number', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['case_number'], ['odycoa.case_number'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ixh_odycoa_documents_case_number', 'odycoa_documents', ['case_number'], unique=False, postgresql_using='hash')
    op.create_table('odycoa_involved_parties',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('party_type', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('race', sa.String(), nullable=True),
    sa.Column('sex', sa.String(), nullable=True),
    sa.Column('height', sa.String(), nullable=True),
    sa.Column('weight', sa.Integer(), nullable=True),
    sa.Column('hair_color', sa.String(), nullable=True),
    sa.Column('eye_color', sa.String(), nullable=True),
    sa.Column('DOB', sa.Date(), nullable=True),
    sa.Column('DOB_str', sa.String(), nullable=True),
    sa.Column('address_1', sa.String(), nullable=True),
    sa.Column('address_2', sa.String(), nullable=True),
    sa.Column('city', sa.String(), nullable=True),
    sa.Column('state', sa.String(), nullable=True),
    sa.Column('zip_code', sa.String(), nullable=True),
    sa.Column('case_number', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['case_number'], ['odycoa.case_number'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ixh_odycoa_involved_parties_case_number', 'odycoa_involved_parties', ['case_number'], unique=False, postgresql_using='hash')
    op.create_table('odycoa_judgments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('judgment_event_type', sa.String(), nullable=True),
    sa.Column('judge_name', sa.String(), nullable=True),
    sa.Column('issue_date', sa.Date(), nullable=True),
    sa.Column('issue_date_str', sa.String(), nullable=True),
    sa.Column('comment', sa.String(), nullable=True),
    sa.Column('case_number', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['case_number'], ['odycoa.case_number'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ixh_odycoa_judgment_case_number', 'odycoa_judgments', ['case_number'], unique=False, postgresql_using='hash')
    op.create_table('odycoa_reference_numbers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ref_num', sa.String(), nullable=False),
    sa.Column('ref_num_type', sa.String(), nullable=False),
    sa.Column('case_number', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['case_number'], ['odycoa.case_number'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ixh_odycoa_reference_numbers_case_number', 'odycoa_reference_numbers', ['case_number'], unique=False, postgresql_using='hash')
    op.create_table('odycoa_attorneys',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('appearance_date', sa.Date(), nullable=True),
    sa.Column('appearance_date_str', sa.String(), nullable=True),
    sa.Column('removal_date', sa.Date(), nullable=True),
    sa.Column('removal_date_str', sa.String(), nullable=True),
    sa.Column('address_1', sa.String(), nullable=True),
    sa.Column('address_2', sa.String(), nullable=True),
    sa.Column('address_3', sa.String(), nullable=True),
    sa.Column('city', sa.String(), nullable=True),
    sa.Column('state', sa.String(), nullable=True),
    sa.Column('zip_code', sa.String(), nullable=True),
    sa.Column('party_id', sa.Integer(), nullable=True),
    sa.Column('case_number', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['case_number'], ['odycoa.case_number'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['party_id'], ['odycoa_involved_parties.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ixh_odycoa_attorneys_case_number', 'odycoa_attorneys', ['case_number'], unique=False, postgresql_using='hash')


def downgrade():
    op.drop_index('ixh_odycoa_attorneys_case_number', table_name='odycoa_attorneys', postgresql_using='hash')
    op.drop_table('odycoa_attorneys')
    op.drop_index('ixh_odycoa_reference_numbers_case_number', table_name='odycoa_reference_numbers', postgresql_using='hash')
    op.drop_table('odycoa_reference_numbers')
    op.drop_index('ixh_odycoa_judgment_case_number', table_name='odycoa_judgments', postgresql_using='hash')
    op.drop_table('odycoa_judgments')
    op.drop_index('ixh_odycoa_involved_parties_case_number', table_name='odycoa_involved_parties', postgresql_using='hash')
    op.drop_table('odycoa_involved_parties')
    op.drop_index('ixh_odycoa_documents_case_number', table_name='odycoa_documents', postgresql_using='hash')
    op.drop_table('odycoa_documents')
    op.drop_index('ixh_odycoa_court_schedule_case_number', table_name='odycoa_court_schedule', postgresql_using='hash')
    op.drop_table('odycoa_court_schedule')
    op.drop_index('ixh_odycoa_case_number', table_name='odycoa', postgresql_using='hash')
    op.drop_table('odycoa')
    op.drop_index('ixh_odycosa_attorneys_case_number', table_name='odycosa_attorneys', postgresql_using='hash')
    op.drop_table('odycosa_attorneys')
    op.drop_index('ixh_odycosa_reference_numbers_case_number', table_name='odycosa_reference_numbers', postgresql_using='hash')
    op.drop_table('odycosa_reference_numbers')
    op.drop_index('ixh_odycosa_judgment_case_number', table_name='odycosa_judgments', postgresql_using='hash')
    op.drop_table('odycosa_judgments')
    op.drop_index('ixh_odycosa_involved_parties_case_number', table_name='odycosa_involved_parties', postgresql_using='hash')
    op.drop_table('odycosa_involved_parties')
    op.drop_index('ixh_odycosa_documents_case_number', table_name='odycosa_documents', postgresql_using='hash')
    op.drop_table('odycosa_documents')
    op.drop_index('ixh_odycosa_court_schedule_case_number', table_name='odycosa_court_schedule', postgresql_using='hash')
    op.drop_table('odycosa_court_schedule')
    op.drop_index('ixh_odycosa_case_number', table_name='odycosa', postgresql_using='hash')
    op.drop_table('odycosa')
