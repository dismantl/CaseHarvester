"""Update ODYCOSA and ODYCOA models

Revision ID: 961f754ce080
Revises: 5d6a58de067a
Create Date: 2023-04-05 12:13:57.808173

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '961f754ce080'
down_revision = '5d6a58de067a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('odycosa_involved_parties', sa.Column('DOB', sa.Date(), nullable=True))
    op.add_column('odycosa_involved_parties', sa.Column('DOB_str', sa.String(), nullable=True))
    op.add_column('odycosa_involved_parties', sa.Column('race', sa.String(), nullable=True))
    op.add_column('odycosa_involved_parties', sa.Column('sex', sa.String(), nullable=True))
    op.add_column('odycosa_involved_parties', sa.Column('height', sa.String(), nullable=True))
    op.add_column('odycosa_involved_parties', sa.Column('weight', sa.Integer(), nullable=True))
    op.add_column('odycosa_involved_parties', sa.Column('hair_color', sa.String(), nullable=True))
    op.add_column('odycosa_involved_parties', sa.Column('eye_color', sa.String(), nullable=True))
    op.drop_column('odycosa_involved_parties', 'agency_name')
    op.add_column('odycosa_judgments', sa.Column('judge_name', sa.String(), nullable=True))
    op.add_column('odycosa_court_schedule', sa.Column('panel_judges', sa.String(), nullable=True))
    op.add_column('odycosa_court_schedule', sa.Column('result', sa.String(), nullable=True))


def downgrade():
    op.drop_column('odycosa_court_schedule', 'result')
    op.drop_column('odycosa_court_schedule', 'panel_judges')
    op.drop_column('odycosa_judgments', 'judge_name')
    op.add_column('odycosa_involved_parties', sa.Column('agency_name', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column('odycosa_involved_parties', 'eye_color')
    op.drop_column('odycosa_involved_parties', 'hair_color')
    op.drop_column('odycosa_involved_parties', 'weight')
    op.drop_column('odycosa_involved_parties', 'height')
    op.drop_column('odycosa_involved_parties', 'sex')
    op.drop_column('odycosa_involved_parties', 'race')
    op.drop_column('odycosa_involved_parties', 'DOB_str')
    op.drop_column('odycosa_involved_parties', 'DOB')
