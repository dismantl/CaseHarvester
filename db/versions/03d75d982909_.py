"""bugfix

Revision ID: 03d75d982909
Revises: aaa83181c4a5
Create Date: 2021-07-14 12:51:56.865399

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03d75d982909'
down_revision = '633f3939b99d'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
    UPDATE
        cases 
    SET
        last_scrape = NULL 
    WHERE
        case_number IN 
        (
            SELECT
                case_number 
            FROM
                scrapes 
                JOIN
                    cases USING (case_number) 
            WHERE
                last_scrape IS NOT NULL 
            GROUP BY
                case_number 
            HAVING
                COUNT(s3_version_id) = 0
        )
    """))
    op.execute(sa.text("""
    UPDATE
        cases 
    SET
        scrape_exempt = TRUE 
    WHERE
        case_number IN 
        (
            SELECT
                case_number 
            FROM
                scrapes 
            GROUP BY
                case_number 
            HAVING
                COUNT(s3_version_id) = 0 
                AND COUNT(error) >= 3
        )
    """))


def downgrade():
    pass
