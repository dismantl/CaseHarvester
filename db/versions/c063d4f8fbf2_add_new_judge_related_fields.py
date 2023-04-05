"""Add new judge-related fields

Revision ID: c063d4f8fbf2
Revises: 20e6f8ac26d5
Create Date: 2023-04-05 12:07:03.377875

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c063d4f8fbf2'
down_revision = '20e6f8ac26d5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('odytraf', sa.Column('judicial_officer', sa.String(), nullable=True))
    op.add_column('odytraf_bond_settings', sa.Column('judge', sa.String(), nullable=True))
    op.add_column('odytraf_charges', sa.Column('plea_judge', sa.String(), nullable=True))
    op.add_column('odytraf_charges', sa.Column('disposition_judge', sa.String(), nullable=True))
    op.add_column('odytraf_charges', sa.Column('sentence_judge', sa.String(), nullable=True))
    op.add_column('odytraf_court_schedule', sa.Column('judge', sa.String(), nullable=True))
    op.add_column('odytraf_warrants', sa.Column('judge', sa.String(), nullable=True))
    op.add_column('odycrim', sa.Column('judicial_officer', sa.String(), nullable=True))
    op.add_column('odycrim_bond_settings', sa.Column('judge', sa.String(), nullable=True))
    op.add_column('odycrim_charges', sa.Column('sentence_judge', sa.String(), nullable=True))
    op.add_column('odycrim_charges', sa.Column('plea_judge', sa.String(), nullable=True))
    op.add_column('odycrim_charges', sa.Column('disposition_judge', sa.String(), nullable=True))
    op.add_column('odycrim_court_schedule', sa.Column('judge', sa.String(), nullable=True))
    op.add_column('odycrim_warrants', sa.Column('judge', sa.String(), nullable=True))
    op.add_column('odycivil', sa.Column('magistrate', sa.String(), nullable=True))
    op.add_column('odycivil', sa.Column('judicial_officer', sa.String(), nullable=True))
    op.add_column('odycivil_bond_settings', sa.Column('judge', sa.String(), nullable=True))
    op.add_column('odycivil_warrants', sa.Column('judge', sa.String(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('judge', sa.String(), nullable=True))
    op.add_column('odycivil_court_schedule', sa.Column('judge', sa.String(), nullable=True))


def downgrade():
    op.drop_column('odycivil_court_schedule', 'judge')
    op.drop_column('odycivil_judgments', 'judge')
    op.drop_column('odycivil_warrants', 'judge')
    op.drop_column('odycivil_bond_settings', 'judge')
    op.drop_column('odycivil', 'judicial_officer')
    op.drop_column('odycivil', 'magistrate')
    op.drop_column('odycrim_warrants', 'judge')
    op.drop_column('odycrim_court_schedule', 'judge')
    op.drop_column('odycrim_charges', 'disposition_judge')
    op.drop_column('odycrim_charges', 'plea_judge')
    op.drop_column('odycrim_charges', 'sentence_judge')
    op.drop_column('odycrim_bond_settings', 'judge')
    op.drop_column('odycrim', 'judicial_officer')
    op.drop_column('odytraf_warrants', 'judge')
    op.drop_column('odytraf_court_schedule', 'judge')
    op.drop_column('odytraf_charges', 'sentence_judge')
    op.drop_column('odytraf_charges', 'disposition_judge')
    op.drop_column('odytraf_charges', 'plea_judge')
    op.drop_column('odytraf_bond_settings', 'judge')
    op.drop_column('odytraf', 'judicial_officer')
