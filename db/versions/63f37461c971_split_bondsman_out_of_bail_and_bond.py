"""split bondsman out of bail_and_bond

Revision ID: 63f37461c971
Revises: 61f1f04c4f18
Create Date: 2018-05-04 22:45:26.859394

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '63f37461c971'
down_revision = '61f1f04c4f18'
branch_labels = None
depends_on = None

# from sqlalchemy.orm import sessionmaker
# from mjcs.models import DSK8BailAndBond, DSK8Bondsman
#
# def upgrade():
#     connection = op.get_bind()
#     db_factory = sessionmaker(bind = connection)
#     db = db_factory()
#     try:
#         for b in db.query(BailAndBond):
#             print('bail_and_bond',b.id)
#             if b.bail_bondsman or b.bondsman_address_1 or b.bondsman_city \
#                     or b.bondsman_state or b.bondsman_zip_code:
#                 bondsman = Bondsman(b.case_number, b.id)
#                 bondsman.name = b.bail_bondsman
#                 bondsman.address_1 = b.bondsman_address_1
#                 bondsman.city = b.bondsman_city
#                 bondsman.state = b.bondsman_state
#                 bondsman.zip_code = b.bondsman_zip_code
#                 db.add(bondsman)
#         db.commit()
#     except:
#         db.rollback()
#         raise
#     finally:
#         db.close()
#     print('Finished splitting out bondsman')
#     op.drop_column('bail_and_bond', 'bail_bondsman')
#     op.drop_column('bail_and_bond', 'bondsman_address_1')
#     op.drop_column('bail_and_bond', 'bondsman_address_2')
#     op.drop_column('bail_and_bond', 'bondsman_city')
#     op.drop_column('bail_and_bond', 'bondsman_state')
#     op.drop_column('bail_and_bond', 'bondsman_zip_code')
#
# def downgrade():
#     pass
