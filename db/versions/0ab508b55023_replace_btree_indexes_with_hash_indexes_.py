"""replace btree indexes with hash indexes on case_number columns

Revision ID: 0ab508b55023
Revises: 34ade64cc602
Creating Date: 2020-05-06 17:54:46.543288

"""
from alembic import op
import sqlalchemy as sa
import os

# revision identifiers, used by Alembic.
revision = '0ab508b55023'
down_revision = '34ade64cc602'
branch_labels = None
depends_on = None


def get_model_names():
    from mjcs.config import config
    from mjcs import models
    if os.getenv('CASEHARVESTER_ENV') == 'production':
        config.initialize_from_environment('production')
    else:
        config.initialize_from_environment('development')
    model_exports = models.__dict__.keys()
    secondary_model_names = list(filter(lambda x: x if x.isupper() else None, model_exports))
    secondary_models = [models.__dict__[model_name] for model_name in secondary_model_names]
    tertiary_models = [models.__dict__[model_name] for model_name in filter(lambda x: x if x[:2].isupper() and x not in secondary_model_names else None, model_exports)]
    return secondary_models, tertiary_models


def upgrade():
    secondary_models, tertiary_models = get_model_names()

    print('[+] Adding hash index on cases.case_number')
    op.create_index(op.f('ixh_cases_case_number'), 'cases', ['case_number'], postgresql_using='hash')

    print('[+] Creating index on cases.filing_date for rescraping date ranges')
    op.create_index(op.f('ix_cases_filing_date'), 'cases', ['filing_date'], unique=False)

    for model in tertiary_models:
        print(f'[+] Dropping existing btree indexes for {model.__tablename__}')
        op.drop_index(f'ix_{model.__tablename__}_case_number', table_name=model.__tablename__)

        print('[+] Temporarily dropping foreign key constraints since they depend on the current btree index')
        op.drop_constraint(f'{model.__tablename__}_case_number_fkey', table_name=model.__tablename__)
    
    for model in secondary_models:
        print(f'[+] Dropping existing btree indexes for {model.__tablename__}')
        op.drop_index(f'ix_{model.__tablename__}_case_number', table_name=model.__tablename__)
    
        print(f'[+] Adding hash indexes on case_number columns for {model.__tablename__}')
        op.create_index(op.f(f'ixh_{model.__tablename__}_case_number'), model.__tablename__, ['case_number'], postgresql_using='hash')

        print('[+] Adding unique constraint to case_number column so foreign keys from teriary tables allowed')
        op.create_unique_constraint(op.f(f'uq_{model.__tablename__}_case_number'), model.__tablename__, ['case_number'])
    
    for model in tertiary_models:
        print('[+] Restoring foreign key constraints')
        op.create_foreign_key(
            op.f(f'{model.__tablename__}_case_number_fkey'),
            source_table=model.__tablename__,
            referent_table=model.__tablename__.split('_')[0],
            local_cols=['case_number'],
            remote_cols=['case_number'],
            ondelete='CASCADE'
        )

        print(f'[+] Adding hash indexes on case_number columns for {model.__tablename__}')
        op.create_index(op.f(f'ixh_{model.__tablename__}_case_number'), model.__tablename__, ['case_number'], postgresql_using='hash')

    print('[+] Dropping extraneous indexes on scraper tables')
    op.drop_index('ix_scrape_versions_case_number', table_name='scrape_versions')
    op.drop_index('ix_scrapes_case_number', table_name='scrapes')


def downgrade():
    secondary_models, tertiary_models = get_model_names()

    print('[+] Restoring scraper table indexes')
    op.create_index(op.f('ix_scrapes_case_number'), 'scrapes', ['case_number'])
    op.create_index(op.f('ix_scrape_versions_case_number'), 'scrape_versions', ['case_number'])

    for model in tertiary_models:
        print(f'[+] Dropping hash indexes for {model.__tablename__}')
        op.drop_index(f'ixh_{model.__tablename__}_case_number', model.__tablename__)

        print('[+] Temporarily dropping foreign key constraints')
        op.drop_constraint(f'{model.__tablename__}_case_number_fkey', table_name=model.__tablename__)
    
    for model in secondary_models:
        print(f'[+] Dropping unique constraint for {model.__tablename__}')
        op.drop_constraint(f'uq_{model.__tablename__}_case_number', model.__tablename__)

        print(f'[+] Dropping hash indexes for {model.__tablename__}')
        op.drop_index(f'ixh_{model.__tablename__}_case_number', table_name=model.__tablename__)

        print(f'[+] Adding btree indexes for {model.__tablename__}')
        op.create_index(op.f(f'ix_{model.__tablename__}_case_number'), model.__tablename__, ['case_number'])
    
    for model in tertiary_models:
        print('[+] Restoring foreign key constraints')
        op.create_foreign_key(
            op.f(f'{model.__tablename__}_case_number_fkey'),
            source_table=model.__tablename__,
            referent_table=model.__tablename__.split('_')[0],
            local_cols=['case_number'],
            remote_cols=['case_number'],
            ondelete='CASCADE'
        )
        
        print(f'[+] Adding btree indexes for {model.__tablename__}')
        op.create_index(op.f(f'ix_{model.__tablename__}_case_number'), model.__tablename__, ['case_number'])

    print('[+] Dropping hash index on cases table')
    op.drop_index('ix_cases_filing_date', 'cases')
    op.drop_index('ixh_cases_case_number', 'cases')