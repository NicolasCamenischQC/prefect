"""Add system column for block types

Revision ID: 7296741dff68
Revises: d335ad57d5ba
Create Date: 2022-06-20 12:39:21.112876

"""
import sqlalchemy as sa
from alembic import op

import prefect

# revision identifiers, used by Alembic.
revision = "7296741dff68"
down_revision = "d335ad57d5ba"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("block_type", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_system_block_type", sa.Boolean(), server_default="0", nullable=False
            )
        )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("block_type", schema=None) as batch_op:
        batch_op.drop_column("is_system_block_type")
    # ### end Alembic commands ###
