"""add template config

Revision ID: b2a07bec7093
Revises: 7af3a8daf911
Create Date: 2018-06-15 15:33:08.274550

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2a07bec7093'
down_revision = '7af3a8daf911'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('template', sa.Column('config', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('template', 'config')
    # ### end Alembic commands ###
