"""Misc field additions

Revision ID: 20e6f8ac26d5
Revises: 763fa67ee202
Create Date: 2023-04-05 12:04:16.399943

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20e6f8ac26d5'
down_revision = 'b8ca82cb953a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('odycrim_charges', sa.Column('notes', sa.String(), nullable=True))
    op.add_column('dstraf_dispositions', sa.Column('notes', sa.String(), nullable=True))
    op.add_column('dscr_charges', sa.Column('notes', sa.String(), nullable=True))
    op.add_column('odytraf_charges', sa.Column('notes', sa.String(), nullable=True))
    op.add_column('odycivil_judgment_statuses', sa.Column('comment', sa.String(), nullable=True))
    op.add_column('odycivil_judgments', sa.Column('judgment_details', sa.String(), nullable=True))


def downgrade():
    op.drop_column('odycivil_judgments', 'judgment_details')
    op.drop_column('odycivil_judgment_statuses', 'comment')
    op.drop_column('odytraf_charges', 'notes')
    op.drop_column('dscr_charges', 'notes')
    op.drop_column('dstraf_dispositions', 'notes')
    op.drop_column('odycrim_charges', 'notes')
