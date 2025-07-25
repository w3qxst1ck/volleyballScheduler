"""add_tournaments

Revision ID: 2ac7b59604b6
Revises: e969545d2f6e
Create Date: 2025-07-13 14:20:57.319997

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2ac7b59604b6"
down_revision: Union[str, None] = "e969545d2f6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "tournaments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column(
            "date",
            sa.DateTime(),
            server_default=sa.text("TIMEZONE('utc', now())"),
            nullable=False,
        ),
        sa.Column("max_team_count", sa.Integer(), nullable=False),
        sa.Column("min_team_count", sa.Integer(), nullable=False),
        sa.Column("min_team_players", sa.Integer(), nullable=False),
        sa.Column("max_team_players", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tournaments_title"), "tournaments", ["title"], unique=False
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("team_leader_id", sa.Integer(), nullable=False),
        sa.Column("team_libero_id", sa.Integer(), nullable=True),
        sa.Column("reserve", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("TIMEZONE('utc', now())"),
            nullable=False,
        ),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tournament_id"], ["tournaments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_teams_title"), "teams", ["title"], unique=False)
    op.create_table(
        "teams_users",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "team_id"),
    )
    op.create_table(
        "tournament_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paid", sa.Boolean(), nullable=False),
        sa.Column("paid_confirm", sa.Boolean(), nullable=False),
        sa.Column(
            "paid_at",
            sa.DateTime(),
            server_default=sa.text("TIMEZONE('utc', now())"),
            nullable=False,
        ),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["tournament_id"], ["tournaments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id"),
    )
    op.add_column("users", sa.Column("gender", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("users", "gender")
    op.drop_table("tournament_payments")
    op.drop_table("teams_users")
    op.drop_index(op.f("ix_teams_title"), table_name="teams")
    op.drop_table("teams")
    op.drop_index(op.f("ix_tournaments_title"), table_name="tournaments")
    op.drop_table("tournaments")
    # ### end Alembic commands ###
