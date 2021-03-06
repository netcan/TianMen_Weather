"""add user info

Revision ID: c4192dfdb156
Revises: d8067c07a983
Create Date: 2018-06-14 20:03:59.158474

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4192dfdb156'
down_revision = 'd8067c07a983'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('city', sa.String(length=64), nullable=True))
    op.add_column('user', sa.Column('country', sa.String(length=64), nullable=True))
    op.add_column('user', sa.Column('headimgurl', sa.String(length=120), nullable=True))
    op.add_column('user', sa.Column('nickname', sa.String(length=64), nullable=True))
    op.add_column('user', sa.Column('province', sa.String(length=64), nullable=True))
    op.add_column('user', sa.Column('sex', sa.Integer(), nullable=True))
    op.add_column('user', sa.Column('subscribe_scene', sa.String(length=64), nullable=True))
    op.add_column('user', sa.Column('subscribe_time', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'subscribe_time')
    op.drop_column('user', 'subscribe_scene')
    op.drop_column('user', 'sex')
    op.drop_column('user', 'province')
    op.drop_column('user', 'nickname')
    op.drop_column('user', 'headimgurl')
    op.drop_column('user', 'country')
    op.drop_column('user', 'city')
    # ### end Alembic commands ###
