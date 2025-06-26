"""create prompt testing tables

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Criar tabelas do sistema de teste de prompts"""
    
    # Tabela principal de testes
    op.create_table('prompt_tests',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('user_id', sa.String(50), nullable=False),
        
        # Configuração do teste
        sa.Column('test_type', sa.String(20), nullable=False),
        sa.Column('test_name', sa.String(200)),
        sa.Column('base_prompt', sa.Text, nullable=False),
        
        # Configurações
        sa.Column('sample_size', sa.Integer, default=50),
        sa.Column('confidence_level', sa.Float, default=0.95),
        sa.Column('max_duration_hours', sa.Integer, default=24),
        sa.Column('auto_winner_threshold', sa.Float, default=0.2),
        
        # Métricas alvo
        sa.Column('target_metrics', sa.JSON, default=sa.text("'[]'::json")),
        
        # Status
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('winner_variant_id', sa.String(50)),
        
        # Resultados
        sa.Column('total_samples', sa.Integer, default=0),
        sa.Column('confidence_score', sa.Float),
        sa.Column('improvement_percentage', sa.Float),
        sa.Column('statistical_significance', sa.Boolean),
        sa.Column('optimal_prompt', sa.Text),
        
        # Metadados
        sa.Column('metadata', sa.JSON, default=sa.text("'{}'::json")),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime),
    )
    
    # Tabela de variantes
    op.create_table('prompt_variants',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('test_id', sa.String(50), nullable=False),
        sa.Column('variant_id', sa.String(50), nullable=False),
        
        # Configuração da variante
        sa.Column('prompt', sa.Text, nullable=False),
        sa.Column('style_modifiers', sa.JSON, default=sa.text("'[]'::json")),
        sa.Column('technical_params', sa.JSON, default=sa.text("'{}'::json")),
        sa.Column('weight', sa.Float, default=1.0),
        sa.Column('description', sa.Text),
        sa.Column('tags', sa.JSON, default=sa.text("'[]'::json")),
        
        # Estatísticas
        sa.Column('sample_count', sa.Integer, default=0),
        sa.Column('success_rate', sa.Float, default=0.0),
        sa.Column('avg_generation_time', sa.Float),
        sa.Column('avg_quality_score', sa.Float),
        sa.Column('total_cost', sa.Float, default=0.0),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['test_id'], ['prompt_tests.id']),
    )
    
    # Tabela de resultados
    op.create_table('prompt_test_results',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('test_id', sa.String(50), nullable=False),
        sa.Column('variant_id', sa.String(50), nullable=False),
        
        # Dados do resultado
        sa.Column('prompt_used', sa.Text, nullable=False),
        sa.Column('generation_time', sa.Float, nullable=False),
        sa.Column('output_url', sa.String(500)),
        sa.Column('provider_id', sa.String(100)),
        sa.Column('cost', sa.Float, default=0.0),
        
        # Métricas calculadas
        sa.Column('metrics', sa.JSON, default=sa.text("'{}'::json")),
        
        # Feedback do usuário
        sa.Column('user_rating', sa.Float),
        sa.Column('user_comments', sa.Text),
        sa.Column('preferred_aspects', sa.JSON, default=sa.text("'[]'::json")),
        sa.Column('suggested_improvements', sa.JSON, default=sa.text("'[]'::json")),
        
        # Metadados técnicos
        sa.Column('metadata', sa.JSON, default=sa.text("'{}'::json")),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['test_id'], ['prompt_tests.id']),
    )
    
    # Tabela de regras de otimização
    op.create_table('prompt_optimization_rules',
        sa.Column('id', sa.String(50), primary_key=True),
        
        # Configuração da regra
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('pattern', sa.Text, nullable=False),
        sa.Column('replacement', sa.Text, nullable=False),
        sa.Column('strategy', sa.String(50), nullable=False),
        sa.Column('confidence', sa.Float, default=0.5),
        sa.Column('description', sa.Text),
        
        # Estatísticas de uso
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('success_rate', sa.Float, default=0.0),
        sa.Column('avg_improvement', sa.Float, default=0.0),
        
        # Status
        sa.Column('is_active', sa.Boolean, default=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('last_used', sa.DateTime),
    )
    
    # Tabela de padrões aprendidos
    op.create_table('prompt_learning_patterns',
        sa.Column('id', sa.String(50), primary_key=True),
        
        # Padrão
        sa.Column('pattern_key', sa.String(200), nullable=False),
        sa.Column('base_prompt', sa.Text, nullable=False),
        sa.Column('optimized_prompt', sa.Text, nullable=False),
        
        # Performance
        sa.Column('performance_score', sa.Float, nullable=False),
        sa.Column('metrics_improvement', sa.JSON, default=sa.text("'{}'::json")),
        
        # Contexto
        sa.Column('applied_rules', sa.JSON, default=sa.text("'[]'::json")),
        sa.Column('test_id', sa.String(50)),
        
        # Uso
        sa.Column('usage_count', sa.Integer, default=1),
        sa.Column('last_used', sa.DateTime, default=sa.func.now()),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['test_id'], ['prompt_tests.id']),
    )
    
    # Tabela de analytics
    op.create_table('prompt_analytics',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('user_id', sa.String(50), nullable=False),
        
        # Período
        sa.Column('date', sa.DateTime, nullable=False),
        sa.Column('period_type', sa.String(20), default='daily'),
        
        # Métricas agregadas
        sa.Column('total_tests', sa.Integer, default=0),
        sa.Column('total_results', sa.Integer, default=0),
        sa.Column('avg_improvement', sa.Float, default=0.0),
        sa.Column('success_rate', sa.Float, default=0.0),
        sa.Column('total_cost', sa.Float, default=0.0),
        
        # Distribuição por tipo
        sa.Column('test_types_distribution', sa.JSON, default=sa.text("'{}'::json")),
        sa.Column('metrics_performance', sa.JSON, default=sa.text("'{}'::json")),
        
        # Top performers
        sa.Column('best_prompts', sa.JSON, default=sa.text("'[]'::json")),
        sa.Column('most_effective_rules', sa.JSON, default=sa.text("'[]'::json")),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now()),
    )
    
    # Índices para performance
    op.create_index('idx_user_status', 'prompt_tests', ['user_id', 'status'])
    op.create_index('idx_test_type', 'prompt_tests', ['test_type'])
    op.create_index('idx_created_at_tests', 'prompt_tests', ['created_at'])
    
    op.create_index('idx_test_variant', 'prompt_variants', ['test_id', 'variant_id'], unique=True)
    
    op.create_index('idx_test_created', 'prompt_test_results', ['test_id', 'created_at'])
    op.create_index('idx_variant_results', 'prompt_test_results', ['variant_id'])
    
    op.create_index('idx_strategy_active', 'prompt_optimization_rules', ['strategy', 'is_active'])
    op.create_index('idx_success_rate', 'prompt_optimization_rules', ['success_rate'])
    
    op.create_index('idx_pattern_performance', 'prompt_learning_patterns', ['pattern_key', 'performance_score'])
    op.create_index('idx_pattern_key', 'prompt_learning_patterns', ['pattern_key'])
    
    op.create_index('idx_user_date', 'prompt_analytics', ['user_id', 'date'], unique=True)
    op.create_index('idx_period_type', 'prompt_analytics', ['period_type'])


def downgrade():
    """Remover tabelas do sistema de teste de prompts"""
    
    # Remove índices
    op.drop_index('idx_period_type', table_name='prompt_analytics')
    op.drop_index('idx_user_date', table_name='prompt_analytics')
    
    op.drop_index('idx_pattern_key', table_name='prompt_learning_patterns')
    op.drop_index('idx_pattern_performance', table_name='prompt_learning_patterns')
    
    op.drop_index('idx_success_rate', table_name='prompt_optimization_rules')
    op.drop_index('idx_strategy_active', table_name='prompt_optimization_rules')
    
    op.drop_index('idx_variant_results', table_name='prompt_test_results')
    op.drop_index('idx_test_created', table_name='prompt_test_results')
    
    op.drop_index('idx_test_variant', table_name='prompt_variants')
    
    op.drop_index('idx_created_at_tests', table_name='prompt_tests')
    op.drop_index('idx_test_type', table_name='prompt_tests')
    op.drop_index('idx_user_status', table_name='prompt_tests')
    
    # Remove tabelas
    op.drop_table('prompt_analytics')
    op.drop_table('prompt_learning_patterns')
    op.drop_table('prompt_optimization_rules')
    op.drop_table('prompt_test_results')
    op.drop_table('prompt_variants')
    op.drop_table('prompt_tests') 