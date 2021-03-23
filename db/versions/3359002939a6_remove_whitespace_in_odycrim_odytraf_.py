"""Remove whitespace in odycrim/odytraf.court_system

Revision ID: 3359002939a6
Revises: df0221cb4562
Create Date: 2021-03-23 18:22:26.521555

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3359002939a6'
down_revision = 'df0221cb4562'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE odycrim SET court_system = trim(regexp_replace(court_system, '[\t\s]+', ' ', 'g'));")
    op.execute("UPDATE odytraf SET court_system = trim(regexp_replace(court_system, '[\t\s]+', ' ', 'g'));")


def downgrade():
    pass
