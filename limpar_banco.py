"""
Script para Limpar Banco de Dados
Execute com: streamlit run limpar_banco.py
"""

import streamlit as st
import sys
import time

# Importar connection
try:
    from connection import get_connection, fetch_all_data
except:
    st.error("❌ Não foi possível importar connection.py")
    st.stop()

def main():
    st.set_page_config(
        page_title="Limpar Banco", 
        page_icon="🗑️",
        layout="centered"
    )
    
    st.title("🗑️ Limpar Banco de Dados")
    
    st.warning("""
    ### ⚠️ **ATENÇÃO: AÇÃO IRREVERSÍVEL!**
    
    Este script irá deletar **PERMANENTEMENTE**:
    - 📎 Todos os anexos
    - 📦 Todas as Ordens de Serviço
    - 🏠 Todos os moradores
    
    **Não será possível recuperar os dados!**
    
    ⚠️ **USUÁRIOS E STAFF NÃO SERÃO DELETADOS**
    """)
    
    # Carregar dados atuais
    if st.button("🔄 Atualizar Contadores"):
        st.rerun()
    
    try:
        data = fetch_all_data()
        
        moves = data.get('moves', [])
        residents = data.get('residents', [])
        attachments = data.get('attachments', [])
        
        # Mostrar estatísticas
        st.markdown("### 📊 Dados Atuais:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "📦 Ordens de Serviço",
                len(moves),
                help="Total de OSs no banco"
            )
        
        with col2:
            st.metric(
                "🏠 Moradores",
                len(residents),
                help="Total de moradores cadastrados"
            )
        
        with col3:
            st.metric(
                "📎 Anexos",
                len(attachments),
                help="Total de arquivos anexados"
            )
        
        # Detalhes das OSs
        if moves:
            with st.expander("📦 Ver detalhes das OSs"):
                status_counts = {}
                for m in moves:
                    status = m.get('status', 'N/A')
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                st.write("**OSs por status:**")
                for status, count in status_counts.items():
                    st.write(f"- {status}: {count}")
        
        st.markdown("---")
        
        # Opções de limpeza
        st.markdown("### 🎯 Opções de Limpeza:")
        
        opcao = st.radio(
            "O que deseja deletar?",
            [
                "🗑️ TUDO (Anexos + OSs + Moradores)",
                "📦 Apenas OSs (mantém moradores)",
                "✅ Apenas OSs Concluídas",
                "🏠 Apenas Moradores sem OS"
            ]
        )
        
        st.markdown("---")
        
        # Confirmação em 2 etapas
        st.markdown("### ✋ Confirmação:")
        
        confirmar1 = st.checkbox(
            "☑️ Eu entendo que esta ação é IRREVERSÍVEL",
            value=False
        )
        
        if confirmar1:
            palavra_magica = st.text_input(
                "Digite **DELETAR** para confirmar:",
                help="Digite exatamente: DELETAR (maiúsculas)",
                max_chars=7
            )
            
            if palavra_magica == "DELETAR":
                if st.button("🗑️ EXECUTAR LIMPEZA", type="primary", use_container_width=True):
                    executar_limpeza(opcao, moves, residents, attachments)
            else:
                if palavra_magica:
                    st.error("❌ Texto incorreto. Digite: DELETAR")
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")

def executar_limpeza(opcao, moves, residents, attachments):
    """Executa a limpeza baseada na opção escolhida"""
    
    with st.spinner("🔄 Executando limpeza..."):
        try:
            conn = get_connection()
            if not conn:
                st.error("❌ Erro ao conectar no banco")
                return
            
            cur = conn.cursor()
            
            deleted_att = 0
            deleted_moves = 0
            deleted_res = 0
            
            if opcao == "🗑️ TUDO (Anexos + OSs + Moradores)":
                # 1. Attachments
                cur.execute("DELETE FROM attachments")
                deleted_att = cur.rowcount
                
                # 2. Moves
                cur.execute("DELETE FROM moves")
                deleted_moves = cur.rowcount
                
                # 3. Residents
                cur.execute("DELETE FROM residents")
                deleted_res = cur.rowcount
                
                # 4. Resetar sequences
                cur.execute("ALTER SEQUENCE attachments_id_seq RESTART WITH 1")
                cur.execute("ALTER SEQUENCE moves_id_seq RESTART WITH 1")
                cur.execute("ALTER SEQUENCE residents_id_seq RESTART WITH 1")
                
                conn.commit()
                
                st.success(f"""
                ### ✅ Limpeza Completa Executada!
                
                📎 **{deleted_att}** anexos deletados
                
                📦 **{deleted_moves}** OSs deletadas
                
                🏠 **{deleted_res}** moradores deletados
                
                🔄 **IDs resetados** para começar do 1
                """)
            
            elif opcao == "📦 Apenas OSs (mantém moradores)":
                # 1. Attachments
                cur.execute("DELETE FROM attachments")
                deleted_att = cur.rowcount
                
                # 2. Moves
                cur.execute("DELETE FROM moves")
                deleted_moves = cur.rowcount
                
                # 3. Resetar sequences
                cur.execute("ALTER SEQUENCE attachments_id_seq RESTART WITH 1")
                cur.execute("ALTER SEQUENCE moves_id_seq RESTART WITH 1")
                
                conn.commit()
                
                st.success(f"""
                ### ✅ OSs Deletadas!
                
                📎 **{deleted_att}** anexos deletados
                
                📦 **{deleted_moves}** OSs deletadas
                
                🏠 **Moradores mantidos** (prontos para novo agendamento)
                """)
            
            elif opcao == "✅ Apenas OSs Concluídas":
                # Buscar IDs das OSs concluídas
                cur.execute("SELECT id FROM moves WHERE status = 'Concluído'")
                move_ids = [row[0] for row in cur.fetchall()]
                
                if move_ids:
                    # Deletar attachments dessas OSs
                    cur.execute(
                        f"DELETE FROM attachments WHERE moveid = ANY(ARRAY{move_ids})"
                    )
                    deleted_att = cur.rowcount
                    
                    # Deletar OSs
                    cur.execute("DELETE FROM moves WHERE status = 'Concluído'")
                    deleted_moves = cur.rowcount
                    
                    conn.commit()
                    
                    st.success(f"""
                    ### ✅ OSs Concluídas Deletadas!
                    
                    📎 **{deleted_att}** anexos deletados
                    
                    📦 **{deleted_moves}** OSs concluídas deletadas
                    
                    📋 **OSs pendentes/em andamento mantidas**
                    """)
                else:
                    st.info("ℹ️ Nenhuma OS concluída encontrada")
            
            elif opcao == "🏠 Apenas Moradores sem OS":
                # Buscar moradores sem OS
                cur.execute("""
                    SELECT id FROM residents 
                    WHERE id NOT IN (
                        SELECT DISTINCT residentid FROM moves
                    )
                """)
                resident_ids = [row[0] for row in cur.fetchall()]
                
                if resident_ids:
                    cur.execute(
                        f"DELETE FROM residents WHERE id = ANY(ARRAY{resident_ids})"
                    )
                    deleted_res = cur.rowcount
                    
                    conn.commit()
                    
                    st.success(f"""
                    ### ✅ Moradores sem OS Deletados!
                    
                    🏠 **{deleted_res}** moradores deletados
                    
                    📋 **Moradores com OS mantidos**
                    """)
                else:
                    st.info("ℹ️ Todos os moradores têm OSs vinculadas")
            
            cur.close()
            conn.close()
            
            st.balloons()
            
            st.info("""
            ### 🔄 Próximos Passos:
            
            1. Feche esta página
            2. Volte para o app principal
            3. Atualize a página (F5)
            4. Os dados estarão limpos
            """)
            
            time.sleep(3)
            
        except Exception as e:
            st.error(f"❌ Erro durante limpeza: {e}")
            st.code(str(e))
            try:
                conn.rollback()
            except:
                pass

if __name__ == "__main__":
    main()
