"""
Script para criar índices automaticamente
Descobre a estrutura do banco e cria os índices corretos
"""

import streamlit as st
import psycopg2

def criar_indices_automaticamente():
    """
    Descobre estrutura do banco e cria índices automaticamente
    """
    
    st.title("🔧 Criador Automático de Índices")
    
    st.markdown("""
    Este script vai:
    1. ✅ Conectar no banco
    2. ✅ Descobrir estrutura das tabelas
    3. ✅ Criar índices corretos
    4. ✅ Verificar se foram criados
    """)
    
    if st.button("🚀 Criar Índices Automaticamente", type="primary", use_container_width=True):
        
        with st.spinner("Conectando ao banco..."):
            try:
                # Conectar
                conn = psycopg2.connect(
                    host="aws-1-us-east-2.pooler.supabase.com",
                    database=st.secrets["postgres"]["database"],
                    user=st.secrets["postgres"]["user"],
                    password=st.secrets["postgres"]["password"],
                    port=st.secrets["postgres"]["port"]
                )
                
                cur = conn.cursor()
                st.success("✅ Conectado ao banco!")
                
                # 1. Descobrir estrutura
                st.subheader("📊 Estrutura das Tabelas")
                
                cur.execute("""
                    SELECT table_name, column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name IN ('moves', 'staff', 'notifications', 'attachments')
                    ORDER BY table_name, ordinal_position
                """)
                
                colunas = cur.fetchall()
                
                # Organizar por tabela
                estrutura = {}
                for table, col, dtype in colunas:
                    if table not in estrutura:
                        estrutura[table] = []
                    estrutura[table].append((col, dtype))
                
                # Mostrar estrutura
                for table, cols in estrutura.items():
                    with st.expander(f"📋 Tabela: {table}"):
                        for col, dtype in cols:
                            st.text(f"  • {col} ({dtype})")
                
                # 2. Identificar nomes corretos das colunas
                st.divider()
                st.subheader("🔍 Identificando Colunas")
                
                # Dicionário de mapeamento
                mapeamento = {}
                
                # Procurar em moves
                if 'moves' in estrutura:
                    cols_moves = [c[0] for c in estrutura['moves']]
                    
                    # residentId pode ser: residentId, residentid, resident_id
                    for possivel in ['residentId', 'residentid', 'resident_id', 'residentID']:
                        if possivel in cols_moves:
                            mapeamento['moves_resident'] = possivel
                            st.success(f"✅ moves: Coluna de resident = **{possivel}**")
                            break
                
                # Procurar em staff
                if 'staff' in estrutura:
                    cols_staff = [c[0] for c in estrutura['staff']]
                    
                    if 'email' in cols_staff:
                        mapeamento['staff_email'] = 'email'
                        st.success(f"✅ staff: Coluna de email = **email**")
                
                # Procurar em notifications
                if 'notifications' in estrutura:
                    cols_notif = [c[0] for c in estrutura['notifications']]
                    
                    for possivel in ['userId', 'userid', 'user_id', 'userID']:
                        if possivel in cols_notif:
                            mapeamento['notif_user'] = possivel
                            st.success(f"✅ notifications: Coluna de user = **{possivel}**")
                            break
                
                # Procurar em attachments
                if 'attachments' in estrutura:
                    cols_attach = [c[0] for c in estrutura['attachments']]
                    
                    for possivel in ['moveId', 'moveid', 'move_id', 'moveID']:
                        if possivel in cols_attach:
                            mapeamento['attach_move'] = possivel
                            st.success(f"✅ attachments: Coluna de move = **{possivel}**")
                            break
                
                # 3. Criar índices
                st.divider()
                st.subheader("⚡ Criando Índices")
                
                indices_criados = []
                erros = []
                
                # Função helper para criar índice
                def criar_indice(nome, tabela, coluna):
                    try:
                        # Adicionar aspas se tiver letras maiúsculas
                        if any(c.isupper() for c in coluna):
                            col_formatada = f'"{coluna}"'
                        else:
                            col_formatada = coluna
                        
                        query = f'CREATE INDEX IF NOT EXISTS {nome} ON {tabela}({col_formatada})'
                        cur.execute(query)
                        conn.commit()
                        return True, query
                    except Exception as e:
                        return False, str(e)
                
                # Índice 1: moves.residentId
                if 'moves_resident' in mapeamento:
                    sucesso, msg = criar_indice(
                        'idx_moves_resident',
                        'moves',
                        mapeamento['moves_resident']
                    )
                    if sucesso:
                        indices_criados.append(('idx_moves_resident', msg))
                        st.success(f"✅ idx_moves_resident")
                    else:
                        erros.append(('idx_moves_resident', msg))
                        st.error(f"❌ idx_moves_resident: {msg}")
                
                # Índice 2: moves.date
                sucesso, msg = criar_indice('idx_moves_date', 'moves', 'date')
                if sucesso:
                    indices_criados.append(('idx_moves_date', msg))
                    st.success(f"✅ idx_moves_date")
                else:
                    erros.append(('idx_moves_date', msg))
                    st.error(f"❌ idx_moves_date: {msg}")
                
                # Índice 3: moves.status
                sucesso, msg = criar_indice('idx_moves_status', 'moves', 'status')
                if sucesso:
                    indices_criados.append(('idx_moves_status', msg))
                    st.success(f"✅ idx_moves_status")
                else:
                    erros.append(('idx_moves_status', msg))
                    st.error(f"❌ idx_moves_status: {msg}")
                
                # Índice 4: staff.email
                if 'staff_email' in mapeamento:
                    sucesso, msg = criar_indice('idx_staff_email', 'staff', 'email')
                    if sucesso:
                        indices_criados.append(('idx_staff_email', msg))
                        st.success(f"✅ idx_staff_email")
                    else:
                        erros.append(('idx_staff_email', msg))
                        st.error(f"❌ idx_staff_email: {msg}")
                
                # Índice 5: notifications.userId
                if 'notif_user' in mapeamento:
                    sucesso, msg = criar_indice(
                        'idx_notifications_user',
                        'notifications',
                        mapeamento['notif_user']
                    )
                    if sucesso:
                        indices_criados.append(('idx_notifications_user', msg))
                        st.success(f"✅ idx_notifications_user")
                    else:
                        erros.append(('idx_notifications_user', msg))
                        st.error(f"❌ idx_notifications_user: {msg}")
                
                # Índice 6: attachments.moveId
                if 'attach_move' in mapeamento:
                    sucesso, msg = criar_indice(
                        'idx_attachments_move',
                        'attachments',
                        mapeamento['attach_move']
                    )
                    if sucesso:
                        indices_criados.append(('idx_attachments_move', msg))
                        st.success(f"✅ idx_attachments_move")
                    else:
                        erros.append(('idx_attachments_move', msg))
                        st.error(f"❌ idx_attachments_move: {msg}")
                
                # 4. Resumo
                st.divider()
                st.subheader("📊 Resumo")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("✅ Índices Criados", len(indices_criados))
                    if indices_criados:
                        with st.expander("Ver detalhes"):
                            for nome, query in indices_criados:
                                st.code(query, language="sql")
                
                with col2:
                    st.metric("❌ Erros", len(erros))
                    if erros:
                        with st.expander("Ver erros"):
                            for nome, erro in erros:
                                st.error(f"{nome}: {erro}")
                
                # 5. Verificar índices criados
                st.divider()
                st.subheader("✅ Verificação Final")
                
                cur.execute("""
                    SELECT indexname, tablename, indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                    AND indexname LIKE 'idx_%'
                    ORDER BY tablename, indexname
                """)
                
                indices = cur.fetchall()
                
                if indices:
                    st.success(f"🎉 {len(indices)} índices encontrados no banco!")
                    
                    for idx_name, table, idx_def in indices:
                        with st.expander(f"📌 {idx_name} ({table})"):
                            st.code(idx_def, language="sql")
                else:
                    st.warning("⚠️ Nenhum índice encontrado")
                
                # Fechar conexão
                cur.close()
                conn.close()
                
                st.success("✅ Processo concluído!")
                st.balloons()
                
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
                st.exception(e)

if __name__ == "__main__":
    criar_indices_automaticamente()
