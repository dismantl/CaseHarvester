"""odycrim_charges.case_number non-nullable

Revision ID: 633f3939b99d
Revises: c376bfc09245
Create Date: 2021-07-06 12:22:03.692192

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '633f3939b99d'
down_revision = 'c376bfc09245'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('odycrim_charges', 'case_number',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('odycrim_charges', 'case_number',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###