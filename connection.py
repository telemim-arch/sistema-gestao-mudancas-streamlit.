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
    """Inicializa pool de conexões"""
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
            options='-c statement_timeout=30000'
        )
        return connection_pool
    except Exception as e:
        st.error(f"❌ Erro ao criar pool: {e}")
        return None

@contextmanager
def get_db_connection():
    """Context manager para conexões"""
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

def get_connection():
    """Função legada compatível - retorna conexão do pool"""
    pool = init_connection_pool()
    if pool:
        return pool.getconn()
    return None

def execute_query(query, params=None, fetch_data=False, retry=3):
    """Executa query com retry"""
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
                    
        except Exception as e:
            if attempt < retry - 1:
                time.sleep(0.5 * (attempt + 1))
                continue
            else:
                st.error(f"❌ Erro: {e}")
                return None if fetch_data else False
    
    return None if fetch_data else False

# --- FETCH ALL DATA ---

def fetch_all_data():
    """Busca todos os dados"""
    data = {}
    
    try:
        with get_db_connection() as conn:
            if conn is None:
                return {
                    'staff': [], 'residents': [], 'moves': [],
                    'secretaries': [], 'roles': [], 'notifications': [], 'attachments': []
                }
            
            cur = conn.cursor()
            
            # Staff
            cur.execute("SELECT * FROM staff")
            columns = [desc[0] for desc in cur.description]
            df = pd.DataFrame(cur.fetchall(), columns=columns)
            data['staff'] = df.where(pd.notnull(df), None).to_dict('records')
            
            # Residents
            cur.execute("SELECT * FROM residents")
            columns = [desc[0] for desc in cur.description]
            df = pd.DataFrame(cur.fetchall(), columns=columns)
            data['residents'] = df.where(pd.notnull(df), None).to_dict('records')
            
            # Moves
            cur.execute("SELECT * FROM moves")
            columns = [desc[0] for desc in cur.description]
            df = pd.DataFrame(cur.fetchall(), columns=columns)
            data['moves'] = df.where(pd.notnull(df), None).to_dict('records')
            
            # Secretaries
            cur.execute("SELECT * FROM secretaries")
            columns = [desc[0] for desc in cur.description]
            df = pd.DataFrame(cur.fetchall(), columns=columns)
            data['secretaries'] = df.where(pd.notnull(df), None).to_dict('records')
            
            # Roles
            cur.execute("SELECT * FROM roles")
            columns = [desc[0] for desc in cur.description]
            df = pd.DataFrame(cur.fetchall(), columns=columns)
            data['roles'] = df.to_dict('records')
            
            # Notifications (não existe - retornar vazio)
            data['notifications'] = []
            
            # Attachments (tentar buscar)
            try:
                cur.execute("SELECT * FROM attachments")
                columns = [desc[0] for desc in cur.description]
                df = pd.DataFrame(cur.fetchall(), columns=columns)
                data['attachments'] = df.to_dict('records')
            except:
                data['attachments'] = []
            
            cur.close()
            return data
            
    except Exception as e:
        st.error(f"❌ Erro ao carregar: {e}")
        return {
            'staff': [], 'residents': [], 'moves': [],
            'secretaries': [], 'roles': [], 'notifications': [], 'attachments': []
        }

# --- AUTENTICAÇÃO ---

def authenticate_user(email, password):
    """Autentica usuário"""
    query = "SELECT * FROM staff WHERE email = %s AND password = %s"
    df = execute_query(query, (email, password), fetch_data=True)
    
    if df is not None and not df.empty:
        user = df.iloc[0].to_dict()
        for key, value in user.items():
            if pd.isna(value):
                user[key] = None
        return user
    return None

# --- STAFF ---

def insert_staff(staff_data):
    """Insere funcionário"""
    query = """
        INSERT INTO staff (name, email, password, role, jobTitle, secretaryId, branchName)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    params = (
        staff_data['name'], staff_data['email'], staff_data['password'],
        staff_data['role'], staff_data.get('jobTitle'),
        staff_data.get('secretaryId'), staff_data.get('branchName')
    )
    return execute_query(query, params)

def update_staff_details(staff_id, name, jobTitle, email, role):
    """Atualiza funcionário"""
    query = "UPDATE staff SET name = %s, jobTitle = %s, email = %s, role = %s WHERE id = %s"
    return execute_query(query, (name, jobTitle, email, role, staff_id))

def delete_staff(staff_id):
    """Deleta funcionário"""
    query = "DELETE FROM staff WHERE id = %s"
    return execute_query(query, (staff_id,))

# --- RESIDENTS ---

def insert_resident(resident_data):
    """Insere morador"""
    query = """
        INSERT INTO residents (
            name, selo, contact, originAddress, originNumber, originNeighborhood,
            destAddress, destNumber, destNeighborhood, observation, 
            moveDate, moveTime, secretaryId
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    params = (
        resident_data['name'], resident_data.get('selo'), resident_data.get('contact'),
        resident_data.get('originAddress'), resident_data.get('originNumber'),
        resident_data.get('originNeighborhood'), resident_data.get('destAddress'),
        resident_data.get('destNumber'), resident_data.get('destNeighborhood'),
        resident_data.get('observation'), resident_data.get('moveDate'),
        resident_data.get('moveTime'), resident_data.get('secretaryId')
    )
    
    try:
        with get_db_connection() as conn:
            if conn:
                cur = conn.cursor()
                cur.execute(query, params)
                result = cur.fetchone()
                conn.commit()
                cur.close()
                return result[0] if result else None
    except Exception as e:
        st.error(f"Erro ao inserir morador: {e}")
        return None

def update_resident(resident_id, name, contact, observation):
    """Atualiza morador"""
    query = "UPDATE residents SET name = %s, contact = %s, observation = %s WHERE id = %s"
    return execute_query(query, (name, contact, observation, resident_id))

def delete_resident(resident_id):
    """Deleta morador"""
    query = "DELETE FROM residents WHERE id = %s"
    return execute_query(query, (resident_id,))

# --- MOVES ---

def insert_move(move_data):
    """Insere OS"""
    query = """
        INSERT INTO moves (
            residentId, date, time, metragem, supervisorId, 
            coordinatorId, driverId, status, secretaryId
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    params = (
        move_data['residentId'], move_data['date'], move_data['time'],
        move_data.get('metragem', 0), move_data.get('supervisorId'),
        move_data.get('coordinatorId'), move_data.get('driverId'),
        move_data.get('status', 'A realizar'), move_data.get('secretaryId')
    )
    
    try:
        with get_db_connection() as conn:
            if conn:
                cur = conn.cursor()
                cur.execute(query, params)
                result = cur.fetchone()
                conn.commit()
                cur.close()
                return result[0] if result else None
    except Exception as e:
        st.error(f"Erro ao inserir OS: {e}")
        return None

def update_move_details(move_id, updates):
    """Atualiza campos de uma OS"""
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

# --- SECRETARIES ---

def insert_secretary(secretary_data):
    """Insere secretária"""
    query = "INSERT INTO secretaries (name, branch) VALUES (%s, %s) RETURNING id"
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

# --- NOTIFICAÇÕES (DUMMY - TABELA NÃO EXISTE) ---

def insert_notification(notification_data):
    """Insere notificação (DUMMY)"""
    return True

def get_user_notifications(userId, unread_only=False):
    """Busca notificações (DUMMY)"""
    return []

def mark_notification_read(notification_id):
    """Marca notificação como lida (DUMMY)"""
    return True

def get_unread_count(userId):
    """Conta notificações não lidas (DUMMY)"""
    return 0

# --- ANEXOS ---

def insert_attachment(attachment_data):
    """Insere anexo"""
    query = """
        INSERT INTO attachments (moveId, fileName, fileData, uploadedBy, uploadedAt)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """
    params = (
        attachment_data['moveId'], attachment_data['fileName'],
        attachment_data['fileData'], attachment_data['uploadedBy'],
        attachment_data.get('uploadedAt', datetime.now())
    )
    return execute_query(query, params)

def get_attachments(move_id):
    """Busca anexos de uma OS"""
    query = 'SELECT * FROM attachments WHERE moveId = %s'
    df = execute_query(query, (move_id,), fetch_data=True)
    return df.to_dict('records') if df is not None else []

def get_attachment_data(attachment_id):
    """Busca dados de um anexo"""
    query = 'SELECT * FROM attachments WHERE id = %s'
    df = execute_query(query, (attachment_id,), fetch_data=True)
    return df.to_dict('records')[0] if df is not None and not df.empty else None

def delete_attachment(attachment_id):
    """Deleta anexo"""
    query = "DELETE FROM attachments WHERE id = %s"
    return execute_query(query, (attachment_id,))

# --- RELATÓRIOS ---

def get_report_data():
    """Retorna dados para relatórios"""
    try:
        with get_db_connection() as conn:
            if conn is None:
                return None
            
            cur = conn.cursor()
            
            # OSs por status
            cur.execute("SELECT status, COUNT(*) as total FROM moves GROUP BY status")
            status_data = cur.fetchall()
            
            # OSs por mês
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
        return None

# --- INICIALIZAÇÃO ---

def init_db_structure(conn):
    """Inicializa estrutura do banco (simplificado)"""
    if conn is None:
        return
    
    try:
        cur = conn.cursor()
        
        # Criar tabela attachments se não existir
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id SERIAL PRIMARY KEY,
                moveId INTEGER REFERENCES moves(id) ON DELETE CASCADE,
                fileName TEXT NOT NULL,
                fileData BYTEA,
                uploadedBy INTEGER REFERENCES staff(id),
                uploadedAt TIMESTAMP DEFAULT NOW()
            );
        """)
        
        conn.commit()
        cur.close()
        
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
