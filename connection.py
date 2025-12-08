import streamlit as st
import psycopg2
from psycopg2 import pool, sql
import pandas as pd
from datetime import datetime
from contextlib import contextmanager
import time

# --- POOL DE CONEXÕES EFICIENTE ---

@st.cache_resource
def init_connection_pool():
    """
    Inicializa um pool de conexões reutilizáveis.
    Melhor performance e gerenciamento de recursos.
    """
    try:
        connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host="aws-1-us-east-2.pooler.supabase.com",
            database=st.secrets["postgres"]["database"],
            user=st.secrets["postgres"]["user"],
            password=st.secrets["postgres"]["password"],
            port=st.secrets["postgres"]["port"],
            connect_timeout=10,
            options='-c statement_timeout=30000'  # 30 segundos timeout
        )
        return connection_pool
    except Exception as e:
        st.error(f"❌ Erro ao criar pool de conexões: {e}")
        return None

@contextmanager
def get_db_connection():
    """
    Context manager para conexões do pool.
    Garante que conexões sempre retornam ao pool.
    
    Uso:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT ...")
            # conexão retorna ao pool automaticamente
    """
    pool = init_connection_pool()
    if pool is None:
        yield None
        return
    
    conn = None
    try:
        conn = pool.getconn()
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"❌ Erro na conexão: {e}")
        yield None
    finally:
        if conn:
            try:
                pool.putconn(conn)
            except:
                pass

# --- FUNÇÕES HELPER OTIMIZADAS ---

def execute_query(query, params=None, fetch_data=False, retry=3):
    """
    Executa query com retry automático e tratamento robusto.
    
    Args:
        query: SQL query
        params: Parâmetros da query
        fetch_data: Se True, retorna DataFrame
        retry: Número de tentativas em caso de erro
    """
    for attempt in range(retry):
        try:
            with get_db_connection() as conn:
                if conn is None:
                    continue
                
                cur = conn.cursor()
                cur.execute(query, params or ())
                
                if fetch_data:
                    columns = [desc[0] for desc in cur.description]
                    data = cur.fetchall()
                    df = pd.DataFrame(data, columns=columns)
                    cur.close()
                    return df
                else:
                    conn.commit()
                    cur.close()
                    return True
                    
        except psycopg2.OperationalError as e:
            if attempt < retry - 1:
                time.sleep(0.5 * (attempt + 1))  # Backoff exponencial
                continue
            else:
                st.error(f"❌ Erro após {retry} tentativas: {e}")
                return None if fetch_data else False
        except Exception as e:
            st.error(f"❌ Erro ao executar query: {e}")
            return None if fetch_data else False
    
    return None if fetch_data else False

def execute_batch(queries_with_params, retry=3):
    """
    Executa múltiplas queries em uma única transação.
    Mais eficiente para operações em lote.
    
    Args:
        queries_with_params: Lista de tuplas (query, params)
    """
    for attempt in range(retry):
        try:
            with get_db_connection() as conn:
                if conn is None:
                    continue
                
                cur = conn.cursor()
                for query, params in queries_with_params:
                    cur.execute(query, params or ())
                
                conn.commit()
                cur.close()
                return True
                
        except Exception as e:
            if attempt < retry - 1:
                time.sleep(0.5 * (attempt + 1))
                continue
            else:
                st.error(f"❌ Erro em batch após {retry} tentativas: {e}")
                return False
    
    return False

# --- FETCH ALL DATA OTIMIZADO ---

def fetch_all_data():
    """
    Busca todos os dados em UMA ÚNICA conexão.
    Muito mais eficiente que múltiplas conexões.
    """
    data = {}
    
    try:
        with get_db_connection() as conn:
            if conn is None:
                return _get_empty_data()
            
            cur = conn.cursor()
            
            # 1. Staff
            cur.execute("SELECT * FROM staff")
            columns = [desc[0] for desc in cur.description]
            staff_data = cur.fetchall()
            df_staff = pd.DataFrame(staff_data, columns=columns)
            df_staff = df_staff.where(pd.notnull(df_staff), None)
            data['staff'] = df_staff.to_dict('records')
            
            # 2. Residents
            cur.execute("SELECT * FROM residents")
            columns = [desc[0] for desc in cur.description]
            res_data = cur.fetchall()
            df_res = pd.DataFrame(res_data, columns=columns)
            df_res = df_res.where(pd.notnull(df_res), None)
            data['residents'] = df_res.to_dict('records')
            
            # 3. Moves
            cur.execute("SELECT * FROM moves")
            columns = [desc[0] for desc in cur.description]
            moves_data = cur.fetchall()
            df_moves = pd.DataFrame(moves_data, columns=columns)
            df_moves = df_moves.where(pd.notnull(df_moves), None)
            data['moves'] = df_moves.to_dict('records')
            
            # 4. Secretaries
            cur.execute("SELECT * FROM secretaries")
            columns = [desc[0] for desc in cur.description]
            sec_data = cur.fetchall()
            df_sec = pd.DataFrame(sec_data, columns=columns)
            df_sec = df_sec.where(pd.notnull(df_sec), None)
            data['secretaries'] = df_sec.to_dict('records')
            
            # 5. Roles
            cur.execute("SELECT * FROM roles")
            columns = [desc[0] for desc in cur.description]
            roles_data = cur.fetchall()
            df_roles = pd.DataFrame(roles_data, columns=columns)
            data['roles'] = df_roles.to_dict('records')
            
            # 6. Notifications - TABELA NÃO EXISTE, retornar vazio
            data['notifications'] = []
            
            # 7. Attachments - tentar buscar, se não existir retornar vazio
            try:
                cur.execute("SELECT * FROM attachments")
                columns = [desc[0] for desc in cur.description]
                att_data = cur.fetchall()
                df_att = pd.DataFrame(att_data, columns=columns)
                data['attachments'] = df_att.to_dict('records')
            except:
                data['attachments'] = []
            
            cur.close()
            return data
            
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return _get_empty_data()

def _get_empty_data():
    """Retorna estrutura vazia de dados"""
    return {
        'staff': [],
        'residents': [],
        'moves': [],
        'secretaries': [],
        'roles': [],
        'notifications': [],
        'attachments': []
    }

# --- FUNÇÕES DE AUTENTICAÇÃO ---

def authenticate_user(email, password):
    """Autentica usuário"""
    query = "SELECT * FROM staff WHERE email = %s AND password = %s"
    df = execute_query(query, (email, password), fetch_data=True)
    
    if df is not None and not df.empty:
        user = df.iloc[0].to_dict()
        # Converter NaN para None
        for key, value in user.items():
            if pd.isna(value):
                user[key] = None
        return user
    return None

# --- FUNÇÕES DE STAFF ---

def insert_staff(staff_data):
    """Insere novo funcionário"""
    query = """
        INSERT INTO staff (name, email, password, role, jobTitle, secretaryId, branchName)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    params = (
        staff_data['name'],
        staff_data['email'],
        staff_data['password'],
        staff_data['role'],
        staff_data.get('jobTitle'),
        staff_data.get('secretaryId'),
        staff_data.get('branchName')
    )
    return execute_query(query, params)

def update_staff_details(staff_id, name, jobTitle, email, role):
    """Atualiza funcionário"""
    query = """
        UPDATE staff 
        SET name = %s, "jobTitle" = %s, email = %s, role = %s
        WHERE id = %s
    """
    return execute_query(query, (name, jobTitle, email, role, staff_id))

def delete_staff(staff_id):
    """Deleta funcionário"""
    query = "DELETE FROM staff WHERE id = %s"
    return execute_query(query, (staff_id,))

# --- FUNÇÕES DE RESIDENTS ---

def insert_resident(resident_data):
    """Insere novo morador"""
    query = """
        INSERT INTO residents (
            name, selo, contact, "originAddress", "originNumber", "originNeighborhood",
            "destAddress", "destNumber", "destNeighborhood", observation, 
            "moveDate", "moveTime", "secretaryId"
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    params = (
        resident_data['name'],
        resident_data.get('selo'),
        resident_data.get('contact'),
        resident_data.get('originAddress'),
        resident_data.get('originNumber'),
        resident_data.get('originNeighborhood'),
        resident_data.get('destAddress'),
        resident_data.get('destNumber'),
        resident_data.get('destNeighborhood'),
        resident_data.get('observation'),
        resident_data.get('moveDate'),
        resident_data.get('moveTime'),
        resident_data.get('secretaryId')
    )
    return execute_query(query, params)

def update_resident(resident_id, name, contact, observation):
    """Atualiza morador"""
    query = """
        UPDATE residents 
        SET name = %s, contact = %s, observation = %s
        WHERE id = %s
    """
    return execute_query(query, (name, contact, observation, resident_id))

def delete_resident(resident_id):
    """Deleta morador"""
    query = "DELETE FROM residents WHERE id = %s"
    return execute_query(query, (resident_id,))

# --- FUNÇÕES DE MOVES ---

def insert_move(move_data):
    """Insere nova OS"""
    query = """
        INSERT INTO moves (
            "residentId", date, time, metragem, "supervisorId", 
            "coordinatorId", "driverId", status, "secretaryId"
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    params = (
        move_data['residentId'],
        move_data['date'],
        move_data['time'],
        move_data.get('metragem', 0),
        move_data.get('supervisorId'),
        move_data.get('coordinatorId'),
        move_data.get('driverId'),
        move_data.get('status', 'A realizar'),
        move_data.get('secretaryId')
    )
    return execute_query(query, params)

def update_move_details(move_id, updates):
    """
    Atualiza campos específicos de uma OS.
    
    Args:
        move_id: ID da OS
        updates: Dict com campos a atualizar
    """
    if not updates:
        return False
    
    set_clause = ", ".join([f'"{k}" = %s' for k in updates.keys()])
    query = f"UPDATE moves SET {set_clause} WHERE id = %s"
    params = list(updates.values()) + [move_id]
    
    return execute_query(query, params)

def delete_move(move_id):
    """Deleta OS"""
    query = "DELETE FROM moves WHERE id = %s"
    return execute_query(query, (move_id,))

# --- FUNÇÕES DE SECRETARIES ---

def insert_secretary(secretary_data):
    """Insere nova secretária"""
    query = """
        INSERT INTO secretaries (name, branch)
        VALUES (%s, %s)
        RETURNING id
    """
    params = (secretary_data['name'], secretary_data.get('branch'))
    return execute_query(query, params)

def update_secretary(secretary_id, name, branch):
    """Atualiza secretária"""
    query = "UPDATE secretaries SET name = %s, branch = %s WHERE id = %s"
    return execute_query(query, (name, branch, secretary_id))

def delete_secretary(secretary_id):
    """Deleta secretária"""
    query = "DELETE FROM secretaries WHERE id = %s"
    return execute_query(query, (secretary_id,))

# --- FUNÇÕES DE NOTIFICAÇÕES ---

def insert_notification(notification_data):
    """Insere notificação (DUMMY - tabela não existe)"""
    # Tabela notifications não existe, apenas retornar True
    return True

def get_user_notifications(userId, unread_only=False):
    """Busca notificações do usuário (DUMMY - tabela não existe)"""
    # Tabela notifications não existe, retornar lista vazia
    return []

def mark_notification_read(notification_id):
    """Marca notificação como lida (DUMMY - tabela não existe)"""
    # Tabela notifications não existe, apenas retornar True
    return True

def get_unread_count(userId):
    """Conta notificações não lidas (DUMMY - tabela não existe)"""
    # Tabela notifications não existe, retornar 0
    return 0

# --- FUNÇÕES DE ANEXOS ---

def insert_attachment(attachment_data):
    """Insere anexo"""
    query = """
        INSERT INTO attachments ("moveId", "fileName", "fileData", "uploadedBy", "uploadedAt")
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """
    params = (
        attachment_data['moveId'],
        attachment_data['fileName'],
        attachment_data['fileData'],
        attachment_data['uploadedBy'],
        attachment_data.get('uploadedAt', datetime.now())
    )
    return execute_query(query, params)

def get_attachments_by_move(move_id):
    """Busca anexos de uma OS"""
    query = 'SELECT * FROM attachments WHERE "moveId" = %s'
    df = execute_query(query, (move_id,), fetch_data=True)
    return df.to_dict('records') if df is not None else []

def get_attachments(move_id):
    """Alias para get_attachments_by_move"""
    return get_attachments_by_move(move_id)

def get_attachment_data(attachment_id):
    """Busca dados de um anexo específico"""
    query = 'SELECT * FROM attachments WHERE id = %s'
    df = execute_query(query, (attachment_id,), fetch_data=True)
    return df.to_dict('records')[0] if df is not None and not df.empty else None

def delete_attachment(attachment_id):
    """Deleta anexo"""
    query = "DELETE FROM attachments WHERE id = %s"
    return execute_query(query, (attachment_id,))

# --- FUNÇÕES DE RELATÓRIOS ---

def get_report_data():
    """Retorna dados para relatórios"""
    try:
        with get_db_connection() as conn:
            if conn is None:
                return None
            
            cur = conn.cursor()
            
            # Dados de OSs por status
            cur.execute("""
                SELECT 
                    status,
                    COUNT(*) as total
                FROM moves
                GROUP BY status
            """)
            status_data = cur.fetchall()
            
            # Dados de OSs por mês
            cur.execute("""
                SELECT 
                    TO_CHAR(date, 'YYYY-MM') as mes,
                    COUNT(*) as total
                FROM moves
                WHERE date >= NOW() - INTERVAL '6 months'
                GROUP BY mes
                ORDER BY mes
            """)
            monthly_data = cur.fetchall()
            
            cur.close()
            
            return {
                'status': status_data,
                'monthly': monthly_data
            }
    except Exception as e:
        st.error(f"Erro ao buscar dados de relatório: {e}")
        return None

# --- FUNÇÕES DE INICIALIZAÇÃO ---

def init_db_structure(conn):
    """
    Cria as tabelas necessárias no banco de dados.
    Versão simplificada - apenas estrutura básica.
    """
    if conn is None:
        return
    
    try:
        cur = conn.cursor()
        
        # Tabela staff já existe, não precisa criar
        # Tabela residents já existe, não precisa criar
        # Tabela moves já existe, não precisa criar
        # Tabela secretaries já existe, não precisa criar
        # Tabela roles já existe, não precisa criar
        
        # Tabela attachments (criar se não existir)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id SERIAL PRIMARY KEY,
                "moveId" INTEGER REFERENCES moves(id) ON DELETE CASCADE,
                "fileName" TEXT NOT NULL,
                "fileData" BYTEA,
                "uploadedBy" INTEGER REFERENCES staff(id),
                "uploadedAt" TIMESTAMP DEFAULT NOW()
            );
        """)
        
        conn.commit()
        cur.close()
        
    except Exception as e:
        st.error(f"Erro ao inicializar estrutura: {e}")
        try:
            conn.rollback()
        except:
            pass

# --- FUNÇÕES HELPER ---

def ensure_secretary_id():
    """Garante que existe uma secretária padrão"""
    query = "SELECT id FROM secretaries LIMIT 1"
    df = execute_query(query, fetch_data=True)
    
    if df is not None and not df.empty:
        return df.iloc[0]['id']
    
    # Criar secretária padrão
    query = "INSERT INTO secretaries (name, branch) VALUES (%s, %s) RETURNING id"
    result = execute_query(query, ('Secretaria Padrão', 'Principal'), fetch_data=True)
    
    if result is not None and not result.empty:
        return result.iloc[0]['id']
    
    return None

# --- VERIFICAÇÃO DE SAÚDE DO BANCO ---

def check_database_health():
    """
    Verifica saúde da conexão com banco de dados.
    Retorna dict com estatísticas.
    """
    try:
        with get_db_connection() as conn:
            if conn is None:
                return {'status': 'error', 'message': 'Não foi possível conectar'}
            
            cur = conn.cursor()
            
            # Contar registros
            stats = {}
            
            cur.execute("SELECT COUNT(*) FROM staff")
            stats['staff_count'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM residents")
            stats['residents_count'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM moves")
            stats['moves_count'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM notifications")
            stats['notifications_count'] = cur.fetchone()[0]
            
            # Verificar índices
            cur.execute("""
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE schemaname = 'public'
            """)
            stats['indexes_count'] = cur.fetchone()[0]
            
            cur.close()
            
            return {
                'status': 'healthy',
                'stats': stats,
                'pool_size': init_connection_pool()._pool.__len__() if init_connection_pool() else 0
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

# --- OTIMIZAÇÃO: CRIAR ÍNDICES ---

def create_performance_indexes():
    """
    Cria índices para melhorar performance de queries frequentes.
    Execute uma vez após criar as tabelas.
    """
    indexes = [
        'CREATE INDEX IF NOT EXISTS idx_moves_resident ON moves("residentId")',
        'CREATE INDEX IF NOT EXISTS idx_moves_date ON moves(date)',
        'CREATE INDEX IF NOT EXISTS idx_moves_status ON moves(status)',
        'CREATE INDEX IF NOT EXISTS idx_staff_email ON staff(email)',
        'CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications("userId")',
        'CREATE INDEX IF NOT EXISTS idx_attachments_move ON attachments("moveId")',
    ]
    
    queries_params = [(idx, None) for idx in indexes]
    success = execute_batch(queries_params)
    
    if success:
        st.success("✅ Índices criados/atualizados com sucesso!")
    else:
        st.error("❌ Erro ao criar índices")
    
    return success
