"""
Script de Diagnóstico e Otimização do Banco de Dados
Execute este script para verificar e otimizar o banco.
"""

import streamlit as st
from connection_v2 import (
    get_db_connection, 
    execute_query, 
    execute_batch,
    check_database_health,
    create_performance_indexes
)

def diagnose_and_optimize():
    """Página de diagnóstico e otimização"""
    
    st.title("🔧 Diagnóstico e Otimização do Banco")
    
    # Verificar saúde
    st.header("📊 Status do Banco")
    
    if st.button("🔍 Verificar Saúde", type="primary"):
        with st.spinner("Verificando..."):
            health = check_database_health()
            
            if health['status'] == 'healthy':
                st.success("✅ Banco de dados saudável!")
                
                stats = health['stats']
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("👥 Funcionários", stats['staff_count'])
                col2.metric("🏠 Moradores", stats['residents_count'])
                col3.metric("📦 OSs", stats['moves_count'])
                col4.metric("🔔 Notificações", stats['notifications_count'])
                
                st.info(f"📊 Índices ativos: {stats['indexes_count']}")
                st.info(f"🔌 Conexões no pool: {health.get('pool_size', 'N/A')}")
                
            else:
                st.error(f"❌ Erro: {health['message']}")
    
    st.divider()
    
    # Criar índices
    st.header("⚡ Otimização de Performance")
    
    st.markdown("""
    **Índices melhoram a velocidade de consultas:**
    - Buscas por cliente
    - Filtros por data
    - Filtros por status
    - Login de usuários
    """)
    
    if st.button("🚀 Criar/Atualizar Índices"):
        with st.spinner("Criando índices..."):
            success = create_performance_indexes()
            if success:
                st.balloons()
    
    st.divider()
    
    # Limpeza de dados
    st.header("🧹 Limpeza de Dados")
    
    col_clean1, col_clean2 = st.columns(2)
    
    with col_clean1:
        st.subheader("Notificações Antigas")
        if st.button("🗑️ Limpar Notificações >30 dias"):
            query = """
                DELETE FROM notifications 
                WHERE "createdAt" < NOW() - INTERVAL '30 days'
            """
            if execute_query(query):
                st.success("✅ Notificações antigas removidas!")
            else:
                st.error("❌ Erro ao limpar")
    
    with col_clean2:
        st.subheader("OSs sem Cliente")
        if st.button("🗑️ Limpar OSs Órfãs"):
            query = """
                DELETE FROM moves 
                WHERE "residentId" IS NULL 
                OR "residentId" NOT IN (SELECT id FROM residents)
            """
            if execute_query(query):
                st.success("✅ OSs órfãs removidas!")
            else:
                st.error("❌ Erro ao limpar")
    
    st.divider()
    
    # Estatísticas detalhadas
    st.header("📈 Estatísticas Detalhadas")
    
    if st.button("📊 Gerar Relatório"):
        with st.spinner("Gerando relatório..."):
            
            # OSs por status
            st.subheader("OSs por Status")
            query = """
                SELECT status, COUNT(*) as total 
                FROM moves 
                GROUP BY status
                ORDER BY total DESC
            """
            df = execute_query(query, fetch_data=True)
            if df is not None:
                st.dataframe(df, use_container_width=True)
            
            # OSs por mês
            st.subheader("OSs por Mês (últimos 6 meses)")
            query = """
                SELECT 
                    TO_CHAR(date, 'YYYY-MM') as mes,
                    COUNT(*) as total
                FROM moves
                WHERE date >= NOW() - INTERVAL '6 months'
                GROUP BY mes
                ORDER BY mes DESC
            """
            df = execute_query(query, fetch_data=True)
            if df is not None:
                st.dataframe(df, use_container_width=True)
            
            # Funcionários mais ativos
            st.subheader("Supervisores Mais Ativos")
            query = """
                SELECT 
                    s.name,
                    COUNT(m.id) as oss_supervisionadas
                FROM staff s
                LEFT JOIN moves m ON s.id = m."supervisorId"
                WHERE s.role IN ('ADMIN', 'SUPERVISOR')
                GROUP BY s.id, s.name
                ORDER BY oss_supervisionadas DESC
                LIMIT 10
            """
            df = execute_query(query, fetch_data=True)
            if df is not None:
                st.dataframe(df, use_container_width=True)
    
    st.divider()
    
    # Backup e restore
    st.header("💾 Backup e Restore")
    
    st.warning("⚠️ Funcionalidade de backup deve ser feita diretamente no Supabase Dashboard")
    st.markdown("""
    **Para fazer backup:**
    1. Acesse o Supabase Dashboard
    2. Vá em Database → Backups
    3. Clique em "Enable automatic backups"
    
    **Para restore:**
    1. Acesse o Supabase Dashboard
    2. Vá em Database → Backups
    3. Selecione um backup
    4. Clique em "Restore"
    """)
    
    st.divider()
    
    # Testes de conexão
    st.header("🔌 Testes de Conexão")
    
    if st.button("🧪 Testar Pool de Conexões"):
        with st.spinner("Testando..."):
            results = []
            
            for i in range(5):
                try:
                    with get_db_connection() as conn:
                        if conn:
                            cur = conn.cursor()
                            cur.execute("SELECT 1")
                            cur.fetchone()
                            cur.close()
                            results.append(f"✅ Teste {i+1}: OK")
                        else:
                            results.append(f"❌ Teste {i+1}: Falhou")
                except Exception as e:
                    results.append(f"❌ Teste {i+1}: {str(e)}")
            
            for result in results:
                st.write(result)
            
            if all("✅" in r for r in results):
                st.success("🎉 Todos os testes passaram!")
            else:
                st.error("⚠️ Alguns testes falharam")

if __name__ == "__main__":
    diagnose_and_optimize()
