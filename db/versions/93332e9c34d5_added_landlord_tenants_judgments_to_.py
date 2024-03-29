"""Added LandLord Tenants judgments to odycivil_judgments

Revision ID: 93332e9c34d5
Revises: 0327e0a1ca6a
Create Date: 2021-07-02 17:40:11.384169

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '93332e9c34d5'
down_revision = '0327e0a1ca6a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('odycivil_judgments', sa.Column('costs', sa.Boolean(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('judgment_for', sa.String(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('monetary_judgment', sa.Boolean(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('party', sa.String(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('possession', sa.Boolean(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('premise_description', sa.String(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('stay_of_execution_until', sa.Date(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('stay_of_execution_until_str', sa.String(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('stay_upon_filing_of_bond', sa.Boolean(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('appeal_bond_amount', sa.Numeric(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('costs_', sa.Numeric(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('court_costs', sa.Numeric(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('judgment', sa.String(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('stay_details', sa.String(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('judgment_expiration_date', sa.Date(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('judgment_expiration_date_str', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('odycivil_judgments', 'judgment_expiration_date_str')
    op.drop_column('odycivil_judgments', 'judgment_expiration_date')
    op.drop_column('odycivil_judgments', 'stay_upon_filing_of_bond')
    op.drop_column('odycivil_judgments', 'stay_of_execution_until_str')
    op.drop_column('odycivil_judgments', 'stay_of_execution_until')
    op.drop_column('odycivil_judgments', 'premise_description')
    op.drop_column('odycivil_judgments', 'possession')
    op.drop_column('odycivil_judgments', 'party')
    op.drop_column('odycivil_judgments', 'monetary_judgment')
    op.drop_column('odycivil_judgments', 'judgment_for')
    op.drop_column('odycivil_judgments', 'costs')
    op.drop_column('odycivil_judgments', 'stay_details')
    op.drop_column('odycivil_judgments', 'judgment')
    op.drop_column('odycivil_judgments', 'court_costs')
    op.drop_column('odycivil_judgments', 'costs_')
    op.drop_column('odycivil_judgments', 'appeal_bond_amount')
    # ### end Alembic commands ###
