"""Create image provider tables

Revision ID: create_image_provider_tables
Revises: 
Create Date: 2025-06-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_image_provider_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create enum type for provider types
    provider_type_enum = postgresql.ENUM(
        'openai', 'piapi', 'stable_diffusion', 'getimg', 'replicate',
        name='providertype'
    )
    provider_type_enum.create(op.get_bind())
    
    # Create image_provider_configs table
    op.create_table('image_provider_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('provider_type', sa.Enum('openai', 'piapi', 'stable_diffusion', 'getimg', 'replicate', name='providertype'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('api_key', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_default', sa.Boolean(), default=False),
        sa.Column('endpoint_url', sa.String(), nullable=True),
        sa.Column('model_id', sa.String(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('cost_per_image', sa.Float(), nullable=True),
        sa.Column('credits_remaining', sa.Float(), nullable=True),
        sa.Column('last_credit_check', sa.DateTime(), nullable=True),
        sa.Column('rate_limit_rpm', sa.Integer(), default=60),
        sa.Column('max_batch_size', sa.Integer(), default=1),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on is_active and is_default
    op.create_index('idx_active_default', 'image_provider_configs', ['is_active', 'is_default'])
    
    # Create image_generation_jobs table
    op.create_table('image_generation_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('provider_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('prompt', sa.String(), nullable=False),
        sa.Column('negative_prompt', sa.String(), nullable=True),
        sa.Column('width', sa.Integer(), default=1024),
        sa.Column('height', sa.Integer(), default=1024),
        sa.Column('num_images', sa.Integer(), default=1),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), default='pending'),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('image_urls', sa.JSON(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('generation_time', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['provider_id'], ['image_provider_configs.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_job_status', 'image_generation_jobs', ['status'])
    op.create_index('idx_job_user', 'image_generation_jobs', ['user_id'])
    op.create_index('idx_job_created', 'image_generation_jobs', ['created_at'])


def downgrade():
    # Drop tables
    op.drop_table('image_generation_jobs')
    op.drop_table('image_provider_configs')
    
    # Drop enum type
    provider_type_enum = postgresql.ENUM(
        'openai', 'piapi', 'stable_diffusion', 'getimg', 'replicate',
        name='providertype'
    )
    provider_type_enum.drop(op.get_bind())
