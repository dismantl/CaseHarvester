"""Remove unused columns from column_metadata

Revision ID: d00d41f1ae1f
Revises: bb071f4f29f2
Create Date: 2021-10-12 13:41:52.892572

"""
from alembic import op
import sqlalchemy as sa
import os


# revision identifiers, used by Alembic.
revision = 'd00d41f1ae1f'
down_revision = 'bb071f4f29f2'
branch_labels = None
depends_on = None


def upgrade():
    from mjcs.config import config
    from mjcs import models
    if os.getenv('CASEHARVESTER_ENV') == 'production':
        config.initialize_from_environment('production')
    else:
        config.initialize_from_environment('development')
    op.execute(models.ColumnMetadata.__table__.delete().where(
        sa.or_(
            sa.and_(
                models.ColumnMetadata.table == 'odycrim_documents',
                models.ColumnMetadata.column_name == 'filed_by'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'odycrim_involved_parties',
                models.ColumnMetadata.column_name.in_([
                    'removal_date_str', 'appearance_date', 'appearance_date_str', 'removal_date'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'odycrim_services',
                models.ColumnMetadata.column_name == 'service_status'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'odytraf',
                models.ColumnMetadata.column_name.in_([
                    'officer_name', 'citation_number', 'officer_id', 'agency_name'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'odytraf_charges',
                models.ColumnMetadata.column_name == 'jail_life_death'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'odytraf_documents',
                models.ColumnMetadata.column_name == 'filed_by'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'odytraf_involved_parties',
                models.ColumnMetadata.column_name.in_([
                    'appearance_date', 'removal_date', 'removal_date_str', 'appearance_date_str'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'odytraf_services',
                models.ColumnMetadata.column_name == 'service_status'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'odycivil_defendants',
                models.ColumnMetadata.column_name.in_([
                    'race', 'height', 'sex', 'weight'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'odycivil_documents',
                models.ColumnMetadata.column_name == 'filed_by'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'odycivil_services',
                models.ColumnMetadata.column_name == 'service_status'
            ),
            models.ColumnMetadata.table == 'odycvcit_sex_offender_registrations',
            sa.and_(
                models.ColumnMetadata.table == 'odycvcit_charges',
                models.ColumnMetadata.column_name.in_([
                    'jail_death', 'jail_suspend_all_but_months', 'jail_cons_conc', 'jail_life',
                    'jail_suspend_all_but_years', 'jail_suspended_term',
                    'jail_suspend_all_but_hours', 'jail_suspend_all_but_days'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'odycvcit_documents',
                models.ColumnMetadata.column_name == 'filed_by'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'odycvcit_involved_parties',
                models.ColumnMetadata.column_name.in_([
                    'removal_date', 'removal_date_str', 'appearance_date_str', 'appearance_date'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'odycvcit_services',
                models.ColumnMetadata.column_name == 'service_status'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dscr_related_persons',
                models.ColumnMetadata.column_name.in_([
                    'attorney_code', 'attorney_firm'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dscr_trials',
                models.ColumnMetadata.column_name == 'reason'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dscivil_related_persons',
                models.ColumnMetadata.column_name.in_([
                    'officer_id', 'agency_sub_code', 'agency_code'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dscivil_trials',
                models.ColumnMetadata.column_name.in_([
                    'reason', 'trial_type'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dscp_defendant_aliases',
                models.ColumnMetadata.column_name.in_([
                    'state', 'address_2', 'address_1', 'zip_code', 'city'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dscp_related_persons',
                models.ColumnMetadata.column_name.in_([
                    'state', 'attorney_firm', 'attorney_code', 'address_2', 'address_1', 'zip_code', 'city'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dscp_trials',
                models.ColumnMetadata.column_name == 'reason'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dstraf',
                models.ColumnMetadata.column_name == 'citation_number'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dstraf_charges',
                models.ColumnMetadata.column_name == 'charge'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dstraf_dispositions',
                models.ColumnMetadata.column_name == 'addition_charge'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dstraf_trials',
                models.ColumnMetadata.column_name == 'trial_type'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dstraf_related_persons',
                models.ColumnMetadata.column_name.in_([
                    'attorney_firm', 'agency_code', 'officer_id', 'agency_sub_code', 'attorney_code'
                ])
            ),
            models.ColumnMetadata.table == 'k_defendant_aliases',
            models.ColumnMetadata.table == 'k_plaintiffs',
            models.ColumnMetadata.table == 'k_district_case_numbers',
            sa.and_(
                models.ColumnMetadata.table == 'k_attorneys',
                models.ColumnMetadata.column_name == 'plaintiff_id'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'k_charges',
                models.ColumnMetadata.column_name.in_([
                    'converted_disposition', 'jail_start_date_str', 'jail_death', 'probable_cause',
                    'jail_suspended_term', 'agency_name',
                    'jail_cons_conc', 'jail_start_date', 'officer_id'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'k_defendants',
                models.ColumnMetadata.column_name.in_([
                    'business_org_name', 'party_number'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'k_related_persons',
                models.ColumnMetadata.column_name.in_([
                    'business_org_name', 'party_number'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'k_documents',
                models.ColumnMetadata.column_name == 'sequence_number'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'k_party_addresses',
                models.ColumnMetadata.column_name == 'plaintiff_id'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'k_party_alias',
                models.ColumnMetadata.column_name == 'plaintiff_id'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'cc_documents',
                models.ColumnMetadata.column_name == 'sequence_number'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dsk8_defendants',
                models.ColumnMetadata.column_name.in_([
                    'weight', 'height'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dsk8_related_persons',
                models.ColumnMetadata.column_name.in_([
                    'attorney_firm', 'agency_code', 'officer_id', 'agency_sub_code', 'attorney_code'
                ])
            ),
            sa.and_(
                models.ColumnMetadata.table == 'dsk8_trials',
                models.ColumnMetadata.column_name == 'trial_type'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'pg_attorneys',
                models.ColumnMetadata.column_name == 'address_2'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'pgv_defendants',
                models.ColumnMetadata.column_name == 'address_2'
            ),
            sa.and_(
                models.ColumnMetadata.table == 'pgv_plaintiffs',
                models.ColumnMetadata.column_name == 'address_2'
            )
        )
    ))


def downgrade():
    pass
