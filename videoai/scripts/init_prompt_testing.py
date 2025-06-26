#!/usr/bin/env python3
"""
Script de Inicialização do Sistema de Teste de Prompts
Configura banco de dados, regras de otimização e demonstra funcionamento
"""

import asyncio
import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao Python path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.database.session import create_tables, engine, SessionLocal
from app.services.prompt_testing import prompt_testing_service
from app.services.prompt_optimizer import prompt_optimizer_service
from app.models.prompt_testing import (
    PromptTest, PromptVariant, PromptTestResult, 
    PromptOptimizationRule, PromptLearningPattern
)


async def setup_database():
    """Configura o banco de dados para teste de prompts"""
    print("🗄️  Configurando banco de dados para teste de prompts...")
    
    try:
        # Cria as tabelas
        create_tables()
        print("   ✅ Tabelas criadas com sucesso")
        
        # Testa conexão
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print(f"   ✅ Conexão testada: {result.fetchone()}")
        
        # Verifica se tabelas específicas existem
        inspector = engine.dialect.get_table_names(engine.connect())
        expected_tables = [
            'prompt_tests', 'prompt_variants', 'prompt_test_results',
            'prompt_optimization_rules', 'prompt_learning_patterns', 'prompt_analytics'
        ]
        
        existing_tables = [table for table in expected_tables if table in inspector]
        print(f"   📊 Tabelas encontradas: {len(existing_tables)}/{len(expected_tables)}")
        
        for table in existing_tables:
            print(f"      ✅ {table}")
        
        if len(existing_tables) < len(expected_tables):
            missing = set(expected_tables) - set(existing_tables)
            print(f"   ⚠️  Tabelas em falta: {missing}")
            print("   💡 Execute: alembic upgrade head")
        
    except Exception as e:
        print(f"   ❌ Erro ao configurar banco: {e}")
        return False
    
    return True


async def setup_optimization_rules():
    """Configura regras de otimização no banco de dados"""
    print("\n🔧 Configurando regras de otimização...")
    
    try:
        db = SessionLocal()
        
        # Verifica se já existem regras
        existing_rules = db.query(PromptOptimizationRule).count()
        
        if existing_rules > 0:
            print(f"   ✅ {existing_rules} regras já existem no banco")
            return True
        
        # Obtém regras do serviço de otimização
        optimizer_rules = prompt_optimizer_service.optimization_rules
        
        # Insere regras no banco
        for rule in optimizer_rules:
            db_rule = PromptOptimizationRule(
                name=rule.name,
                pattern=rule.pattern,
                replacement=rule.replacement,
                strategy=rule.strategy.value,
                confidence=rule.confidence,
                description=rule.description,
                usage_count=rule.usage_count,
                success_rate=rule.success_rate
            )
            db.add(db_rule)
        
        db.commit()
        print(f"   ✅ {len(optimizer_rules)} regras inseridas no banco")
        
        # Estatísticas por estratégia
        strategies = {}
        for rule in optimizer_rules:
            strategy = rule.strategy.value
            strategies[strategy] = strategies.get(strategy, 0) + 1
        
        print(f"   📊 Regras por estratégia:")
        for strategy, count in strategies.items():
            print(f"      {strategy}: {count} regras")
        
        db.close()
        
    except Exception as e:
        print(f"   ❌ Erro ao configurar regras: {e}")
        return False
    
    return True


async def demo_prompt_optimization():
    """Demonstra otimização de prompts"""
    print("\n💡 Demonstrando otimização de prompts...")
    
    test_prompts = [
        "a cat",
        "beautiful woman portrait",
        "robot in city",
        "mountain landscape with lake",
        "abstract geometric art"
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        try:
            print(f"\n   {i}. Prompt: '{prompt}'")
            
            # Analisa o prompt
            analysis = await prompt_optimizer_service.analyze_prompt(prompt)
            print(f"      📊 Complexidade: {analysis.complexity_score:.2f}")
            print(f"      📝 Palavras: {analysis.word_count}")
            print(f"      🎨 Palavras de estilo: {len(analysis.style_keywords)}")
            print(f"      ⭐ Palavras de qualidade: {len(analysis.quality_keywords)}")
            
            # Otimiza o prompt
            optimization = await prompt_optimizer_service.optimize_prompt(prompt)
            print(f"      ✨ Otimizado: '{optimization.optimized_prompt}'")
            print(f"      📈 Melhoria esperada: +{optimization.expected_improvement:.1f}%")
            print(f"      🔧 Regras aplicadas: {len(optimization.applied_rules)}")
            
            if optimization.applied_rules:
                print(f"         {', '.join(optimization.applied_rules[:3])}")
            
        except Exception as e:
            print(f"   ❌ Erro no prompt {i}: {e}")


async def demo_ab_test():
    """Demonstra criação e execução de teste A/B"""
    print("\n🧪 Demonstrando teste A/B...")
    
    try:
        from app.services.prompt_testing import TestConfiguration, PromptVariant, TestType, MetricType
        
        # Configura teste A/B
        variants = [
            PromptVariant(
                id="original",
                prompt="a beautiful landscape",
                style_modifiers=[],
                technical_params={},
                description="Prompt original"
            ),
            PromptVariant(
                id="optimized",
                prompt="a beautiful landscape, high quality, detailed, artistic masterpiece",
                style_modifiers=["artistic", "detailed"],
                technical_params={"quality": "hd"},
                description="Prompt otimizado"
            )
        ]
        
        config = TestConfiguration(
            test_id="demo_ab_test",
            test_type=TestType.AB_TEST,
            base_prompt="a beautiful landscape",
            variants=variants,
            target_metrics=[MetricType.IMAGE_QUALITY, MetricType.AESTHETIC_SCORE],
            sample_size=6,  # Pequeno para demo
            metadata={"demo": True}
        )
        
        # Cria teste
        test_id = await prompt_testing_service.create_ab_test(config)
        print(f"   ✅ Teste A/B criado: {test_id}")
        
        # Executa algumas iterações
        print(f"   🔄 Executando iterações...")
        
        for i in range(6):
            result = await prompt_testing_service.run_test_iteration(test_id, "demo_user")
            variant = result["variant_tested"]
            progress = f"{result['total_samples']}/{result['target_samples']}"
            print(f"      Iteração {i+1}: {variant} | {progress}")
            
            if result.get("analysis"):
                print(f"   🏆 Vencedor: {result['analysis']['winner_variant_id']}")
                break
        
        # Análise final
        print(f"   📊 Analisando resultados...")
        analysis = await prompt_testing_service.analyze_test_results(test_id)
        
        print(f"      🏆 Vencedor: {analysis.winner_variant_id}")
        print(f"      📈 Melhoria: {analysis.improvement_percentage:.1f}%")
        print(f"      ✨ Prompt final: '{analysis.optimal_prompt}'")
        
    except Exception as e:
        print(f"   ❌ Erro no teste A/B: {e}")


async def demo_iterative_refinement():
    """Demonstra refinamento iterativo"""
    print("\n🔄 Demonstrando refinamento iterativo...")
    
    try:
        from app.services.prompt_testing import MetricType
        
        base_prompt = "a robot in a garden"
        
        # Cria teste iterativo
        test_id = await prompt_testing_service.create_iterative_refinement(
            base_prompt=base_prompt,
            target_metric=MetricType.IMAGE_QUALITY,
            iterations=4
        )
        
        print(f"   ✅ Refinamento criado: {test_id}")
        print(f"   📝 Prompt base: '{base_prompt}'")
        
        # Executa refinamento
        print(f"   🔄 Executando refinamento...")
        
        for i in range(8):  # 2 amostras por iteração
            result = await prompt_testing_service.run_test_iteration(test_id, "demo_user")
            variant = result["variant_tested"]
            progress = f"{result['total_samples']}/{result['target_samples']}"
            print(f"      Iteração {i+1}: {variant} | {progress}")
            
            if result["total_samples"] >= result["target_samples"]:
                break
        
        # Análise do refinamento
        print(f"   📊 Analisando refinamento...")
        analysis = await prompt_testing_service.analyze_test_results(test_id)
        
        print(f"      🎯 Melhor versão: {analysis.winner_variant_id}")
        print(f"      📈 Melhoria: {analysis.improvement_percentage:.1f}%")
        print(f"      ✨ Resultado: '{analysis.optimal_prompt}'")
        
    except Exception as e:
        print(f"   ❌ Erro no refinamento: {e}")


async def show_system_stats():
    """Mostra estatísticas do sistema"""
    print("\n📊 Estatísticas do Sistema")
    print("=" * 50)
    
    try:
        # Estatísticas do serviço de teste
        test_history = prompt_testing_service.get_test_history()
        print(f"🧪 Testes Ativos: {test_history['active_tests']}")
        print(f"📊 Total de Resultados: {test_history['total_results']}")
        
        # Estatísticas do otimizador
        optimizer_stats = prompt_optimizer_service.get_optimization_stats()
        print(f"\n🔧 Regras de Otimização:")
        print(f"   Total: {optimizer_stats['total_rules']}")
        print(f"   Ativas: {optimizer_stats['active_rules']}")
        print(f"   Padrões Aprendidos: {optimizer_stats['learned_patterns']}")
        
        print(f"\n📈 Top Regras:")
        for rule in optimizer_stats['top_performing_rules'][:3]:
            print(f"   {rule['name']}: {rule['success_rate']:.1%} sucesso ({rule['usage_count']} usos)")
        
        print(f"\n🎯 Performance por Estratégia:")
        for strategy, stats in optimizer_stats['strategy_stats'].items():
            if stats['total_usage'] > 0:
                print(f"   {strategy}: {stats['avg_success_rate']:.1%} média, {stats['total_usage']} usos")
        
    except Exception as e:
        print(f"❌ Erro nas estatísticas: {e}")


async def main():
    """Função principal"""
    print("🧪 Inicializando Sistema de Teste e Refinamento de Prompts")
    print("=" * 60)
    
    success = True
    
    # Setup do banco
    if not await setup_database():
        success = False
    
    # Setup das regras
    if success and not await setup_optimization_rules():
        success = False
    
    # Demonstrações
    if success:
        await demo_prompt_optimization()
        await demo_ab_test()
        await demo_iterative_refinement()
    
    # Estatísticas
    await show_system_stats()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Sistema de Teste de Prompts inicializado com sucesso!")
        print("\n🎯 Próximos passos:")
        print("   1. Execute a API: uvicorn app.main:app --reload")
        print("   2. Acesse a documentação: http://localhost:8000/docs")
        print("   3. Teste os endpoints: /api/v1/prompt-testing/")
        print("   4. Execute o demo: python examples/prompt_testing_demo.py")
        print("\n💡 Funcionalidades disponíveis:")
        print("   🎯 Testes A/B automatizados")
        print("   🔄 Refinamento iterativo")
        print("   🎲 Testes multivariáveis")
        print("   💡 Otimização automática")
        print("   📊 Analytics detalhados")
        print("   🧠 Aprendizado de padrões")
    else:
        print("❌ Falha na inicialização!")
        return 1
    
    return 0


if __name__ == "__main__":
    print("🎭 Sistema de Teste e Refinamento de Prompts - VideoAI")
    print("   Versão: 1.0.0 (Tarefa 3.4)")
    print("   Autor: VideoAI Team")
    print()
    
    # Executa
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 