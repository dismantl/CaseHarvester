"""Add judge fields to ODYCVCIT models

Revision ID: d79a86c541b0
Revises: 9d9dc9ba350c
Create Date: 2023-04-05 17:15:50.113602

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd79a86c541b0'
down_revision = '961f754ce080'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('odycvcit_bond_settings', sa.Column('judge', sa.String(), nullable=True))
    op.add_column('odycvcit_warrants', sa.Column('judge', sa.String(), nullable=True))
    op.add_column('odycvcit_court_schedule', sa.Column('judge', sa.String(), nullable=True))
    op.add_column('odycvcit_charges', sa.Column('plea_judge', sa.String(), nullable=True))
    op.add_column('odycvcit_charges', sa.Column('disposition_judge', sa.String(), nullable=True))
    op.add_column('odycvcit_charges', sa.Column('sentence_judge', sa.String(), nullable=True))


def downgrade():
    op.drop_column('odycvcit_charges', 'sentence_judge')
    op.drop_column('odycvcit_charges', 'disposition_judge')
    op.drop_column('odycvcit_charges', 'plea_judge')
    op.drop_column('odycvcit_court_schedule', 'judge')
    op.drop_column('odycvcit_warrants', 'judge')
    op.drop_column('odycvcit_bond_settings', 'judge')
