"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'organizations',
        sa.Column('org_id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'users',
        sa.Column('user_id', sa.Integer(), primary_key=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.org_id'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255)),
        sa.Column('role', sa.String(length=50), server_default='member'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table(
        'campaigns',
        sa.Column('campaign_id', sa.Integer(), primary_key=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.org_id'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('channel', sa.String(length=100)),
        sa.Column('start_date', sa.Date()),
    )

    op.create_table(
        'daily_metrics',
        sa.Column('metric_id', sa.Integer(), primary_key=True),
        sa.Column('campaign_id', sa.Integer(), sa.ForeignKey('campaigns.campaign_id'), nullable=False),
        sa.Column('metric_date', sa.Date(), nullable=False),
        sa.Column('clicks', sa.Integer(), server_default='0'),
        sa.Column('impressions', sa.Integer(), server_default='0'),
        sa.Column('cost', sa.Numeric(10, 2), server_default='0'),
        sa.Column('conversions', sa.Integer(), server_default='0'),
    )


def downgrade() -> None:
    op.drop_table('daily_metrics')
    op.drop_table('campaigns')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_table('users')
    op.drop_table('organizations')
