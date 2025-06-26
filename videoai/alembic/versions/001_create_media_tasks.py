"""create media tasks tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Criar tabelas do sistema de tarefas de mídia"""
    
    # Tabela principal de tarefas
    op.create_table('media_tasks',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('user_id', sa.String(50), nullable=False),
        
        # Tipo e status
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), default='pending'),
        
        # Dados da requisição
        sa.Column('input_data', sa.JSON, nullable=False),
        sa.Column('output_data', sa.JSON),
        
        # Processamento
        sa.Column('provider_id', sa.String(100)),
        sa.Column('external_task_id', sa.String(200)),
        
        # Webhooks e notificações
        sa.Column('webhook_url', sa.String(500)),
        sa.Column('webhook_secret', sa.String(100)),
        sa.Column('webhook_attempts', sa.Integer, default=0),
        sa.Column('webhook_last_attempt', sa.DateTime),
        sa.Column('webhook_status', sa.String(20)),
        
        # Metadados e controle
        sa.Column('priority', sa.Integer, default=5),
        sa.Column('estimated_duration', sa.Float),
        sa.Column('actual_duration', sa.Float),
        sa.Column('estimated_cost', sa.Float, default=0.0),
        sa.Column('actual_cost', sa.Float, default=0.0),
        
        # Progress tracking
        sa.Column('progress', sa.Float, default=0.0),
        sa.Column('progress_message', sa.String(500)),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('expires_at', sa.DateTime),
        
        # Controle de erro e retry
        sa.Column('error_message', sa.Text),
        sa.Column('error_details', sa.JSON),
        sa.Column('retry_count', sa.Integer, default=0),
        sa.Column('max_retries', sa.Integer, default=3),
        sa.Column('retry_after', sa.DateTime),
        
        # Metadados adicionais
        sa.Column('metadata', sa.JSON, default=sa.text("'{}'::json")),
        sa.Column('tags', sa.JSON, default=sa.text("'[]'::json")),
    )
    
    # Tabela de logs
    op.create_table('task_logs',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('task_id', sa.String(50), nullable=False),
        
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_data', sa.JSON),
        sa.Column('message', sa.Text),
        
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['task_id'], ['media_tasks.id']),
    )
    
    # Tabela de dependências
    op.create_table('task_dependencies',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        
        sa.Column('dependent_task_id', sa.String(50), nullable=False),
        sa.Column('required_task_id', sa.String(50), nullable=False),
        
        sa.Column('dependency_type', sa.String(20), default='completion'),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['dependent_task_id'], ['media_tasks.id']),
        sa.ForeignKeyConstraint(['required_task_id'], ['media_tasks.id']),
    )
    
    # Índices para performance
    op.create_index('idx_user_status', 'media_tasks', ['user_id', 'status'])
    op.create_index('idx_task_type_status', 'media_tasks', ['task_type', 'status'])
    op.create_index('idx_created_at', 'media_tasks', ['created_at'])
    op.create_index('idx_priority_status', 'media_tasks', ['priority', 'status'])
    
    op.create_index('idx_task_id_created', 'task_logs', ['task_id', 'created_at'])
    
    op.create_index('idx_unique_dependency', 'task_dependencies', 
                   ['dependent_task_id', 'required_task_id'], unique=True)


def downgrade():
    """Remover tabelas do sistema de tarefas de mídia"""
    
    # Remove índices
    op.drop_index('idx_unique_dependency', table_name='task_dependencies')
    op.drop_index('idx_task_id_created', table_name='task_logs')
    op.drop_index('idx_priority_status', table_name='media_tasks')
    op.drop_index('idx_created_at', table_name='media_tasks')
    op.drop_index('idx_task_type_status', table_name='media_tasks')
    op.drop_index('idx_user_status', table_name='media_tasks')
    
    # Remove tabelas
    op.drop_table('task_dependencies')
    op.drop_table('task_logs')
    op.drop_table('media_tasks') 