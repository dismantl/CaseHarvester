"""update DSK8 table name typo; change complaint_number to string

Revision ID: b0b43970cbca
Revises: 1d0f3c93ce1f
Create Date: 2018-05-04 15:01:47.654701

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b0b43970cbca'
down_revision = '1d0f3c93ce1f'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('DKS8','DSK8')
    op.alter_column('DSK8', 'complaint_number', type_=sa.String)

def downgrade():
    op.alter_column('DSK8', 'complaint_number', type_=sa.BigInteger)
    op.rename_table('DSK8','DKS8')
