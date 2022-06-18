"""Add block schema indexes

Revision ID: d335ad57d5ba
Revises: 61c76ee09e02
Create Date: 2022-06-17 20:44:09.726661

"""
import sqlalchemy as sa
from alembic import op

import prefect

# revision identifiers, used by Alembic.
revision = "d335ad57d5ba"
down_revision = "61c76ee09e02"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(
        op.f("ix_block_schema__block_type_id"),
        "block_schema",
        ["block_type_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_block_schema__created"), "block_schema", ["created"], unique=False
    )

    # there is already a unique index on this column, so this btree index is redundant
    op.drop_index(op.f("ix_block_schema__checksum"), table_name="block_schema")

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_block_schema__created"), table_name="block_schema")
    op.drop_index(op.f("ix_block_schema__block_type_id"), table_name="block_schema")
    op.create_index(
        op.f("ix_block_schema__checksum"), "block_schema", ["checksum"], unique=False
    )
    # ### end Alembic commands ###
