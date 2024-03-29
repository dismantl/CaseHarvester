"""Add column_metadata table

Revision ID: ed5fea32af69
Revises: cbaf431ce937
Create Date: 2021-08-04 07:57:19.210092

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ed5fea32af69'
down_revision = 'cbaf431ce937'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('column_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('table', sa.String(), nullable=False),
        sa.Column('column_name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('width_pixels', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('table', 'column_name', name='column_metadata_column_name_width_pixels_key')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('column_metadata')
    # ### end Alembic commands ###
