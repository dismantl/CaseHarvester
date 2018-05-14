"""rename court_schedule table to dscr_court_schedule

Revision ID: 1d0f3c93ce1f
Revises: cb47a092cecb
Create Date: 2018-05-02 14:15:18.957017

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1d0f3c93ce1f'
down_revision = 'cb47a092cecb'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('court_schedule','dscr_court_schedule')


def downgrade():
    op.rename_table('dscr_court_schedule','court_schedule')
