"""
SETUP_DATABASE.PY
Coloque este arquivo na raiz do seu repositório GitHub
Acesse via: seu-app.streamlit.app?page=setup
"""

import streamlit as st
import psycopg2

def setup_database():
    st.title("🔧 Setup do Banco de Dados")
    st.warning("⚠️ Execute apenas UMA VEZ para configurar o banco!")
    
    if st.button("🚀 Corrigir Banco de Dados Agora", type="primary"):
        
        with st.spinner("Conectando ao banco..."):
            try:
                # Conectar usando secrets do Streamlit
                conn = psycopg2.connect(
                    host="db.fklqkmrcmsumjyrdjlib.supabase.co",
                    port=5432,
                    database="postgres",
                    user="postgres",
                    password=st.secrets["postgres"]["password"]
                )
                st.success("✅ Conectado ao banco!")
                
            except Exception as e:
                st.error(f"❌ Erro ao conectar: {e}")
                st.stop()
        
        # Lista de comandos SQL
        comandos = [
            ("Adicionar jobTitle", """
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='staff' AND column_name='jobTitle') THEN
                        ALTER TABLE staff ADD COLUMN "jobTitle" TEXT;
                    END IF;
                END $$;
            """),
            ("Adicionar branchName", """
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='staff' AND column_name='branchName') THEN
                        ALTER TABLE staff ADD COLUMN "branchName" TEXT;
                    END IF;
                END $$;
            """),
            ("Adicionar createdAt em staff", """
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='staff' AND column_name='createdAt') THEN
                        ALTER TABLE staff ADD COLUMN "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                    END IF;
                END $$;
            """),
            ("Adicionar completionDate", """
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='moves' AND column_name='completionDate') THEN
                        ALTER TABLE moves ADD COLUMN "completionDate" DATE;
                    END IF;
                END $$;
            """),
            ("Adicionar completionTime", """
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='moves' AND column_name='completionTime') THEN
                        ALTER TABLE moves ADD COLUMN "completionTime" TIME;
                    END IF;
                END $$;
            """),
            ("Adicionar createdAt em moves", """
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='moves' AND column_name='createdAt') THEN
                        ALTER TABLE moves ADD COLUMN "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                    END IF;
                END $$;
            """),
            ("🌟 Tornar secretaryId OPCIONAL", """
                DO $$ BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='moves' AND column_name='secretaryId' AND is_nullable='NO') THEN
                        ALTER TABLE moves ALTER COLUMN "secretaryId" DROP NOT NULL;
                    END IF;
                END $$;
            """),
            ("Criar tabela notifications", """
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    "userId" INTEGER NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    type TEXT DEFAULT 'info',
                    "isRead" BOOLEAN DEFAULT FALSE,
                    "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """),
            ("Criar índice notifications", """
                CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications("userId", "isRead");
            """),
            ("Criar tabela attachments", """
                CREATE TABLE IF NOT EXISTS attachments (
                    id SERIAL PRIMARY KEY,
                    "moveId" INTEGER NOT NULL REFERENCES moves(id) ON DELETE CASCADE,
                    filename TEXT NOT NULL,
                    filetype TEXT NOT NULL,
                    filedata BYTEA NOT NULL,
                    "uploadedBy" INTEGER REFERENCES staff(id),
                    "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """),
            ("Criar índice attachments", """
                CREATE INDEX IF NOT EXISTS idx_attachments_move ON attachments("moveId");
            """),
            ("Atualizar jobTitle", """
                UPDATE staff 
                SET "jobTitle" = CASE 
                    WHEN role='ADMIN' THEN 'Administrador'
                    WHEN role='SECRETARY' THEN 'Secretária'
                    WHEN role='SUPERVISOR' THEN 'Supervisor'
                    WHEN role='COORDINATOR' THEN 'Coordenador'
                    WHEN role='DRIVER' THEN 'Motorista'
                    ELSE role
                END
                WHERE "jobTitle" IS NULL;
            """),
        ]
        
        # Executar todos
        progress = st.progress(0)
        status = st.empty()
        
        sucessos = 0
        total = len(comandos)
        
        for i, (descricao, sql) in enumerate(comandos):
            status.text(f"⏳ {descricao}...")
            
            try:
                cur = conn.cursor()
                cur.execute(sql)
                conn.commit()
                cur.close()
                sucessos += 1
                status.text(f"✅ {descricao}")
            except Exception as e:
                if 'already exists' in str(e):
                    status.text(f"✅ {descricao} (já existe)")
                    sucessos += 1
                else:
                    status.text(f"⚠️ {descricao} - {str(e)[:50]}")
            
            progress.progress((i + 1) / total)
        
        # Verificar estrutura final
        st.divider()
        st.subheader("📊 Estrutura Final")
        
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                table_name,
                (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as num_columns
            FROM information_schema.tables t
            WHERE table_schema = 'public' 
            AND table_name IN ('staff', 'residents', 'moves', 'notifications', 'attachments')
            ORDER BY table_name;
        """)
        
        resultados = cur.fetchall()
        
        for tabela, colunas in resultados:
            st.success(f"✅ {tabela}: {colunas} colunas")
        
        cur.close()
        conn.close()
        
        # Resultado final
        st.divider()
        if sucessos == total:
            st.balloons()
            st.success("🎉 BANCO CORRIGIDO COM SUCESSO!")
            st.info("Agora você pode usar o app normalmente. Delete este arquivo setup_database.py do GitHub.")
        else:
            st.warning(f"⚠️ {sucessos}/{total} comandos executados")

if __name__ == "__main__":
    setup_database()
