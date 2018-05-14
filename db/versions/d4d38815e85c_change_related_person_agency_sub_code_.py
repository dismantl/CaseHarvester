"""change related_person agency_sub_code column to String

Revision ID: d4d38815e85c
Revises: 16eaf5eb169c
Create Date: 2018-04-26 12:57:20.638288

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4d38815e85c'
down_revision = '16eaf5eb169c'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('related_persons', 'agency_sub_code', type_=sa.String)


def downgrade():
    op.alter_column('related_persons', 'agency_sub_code', type_=sa.Integer)
