import streamlit as st
import psycopg2
from psycopg2 import sql
import pandas as pd
from datetime import datetime

# --- Configuração de Conexão Segura ---

@st.cache_resource
def get_connection():
    """
    Cria e retorna uma conexão com o banco de dados PostgreSQL
    usando as credenciais de st.secrets.
    """
    try:
        conn = psycopg2.connect(
            host="aws-1-us-east-2.pooler.supabase.com",
            database=st.secrets["postgres"]["database"],
            user=st.secrets["postgres"]["user"],
            password=st.secrets["postgres"]["password"],
            port=st.secrets["postgres"]["port"]
        )
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

# --- Funções de Inicialização e Consulta ---

def init_db_structure(conn):
    """
    Cria as tabelas necessárias no banco de dados.
    Deve ser executado apenas uma vez.
    """
    if conn is None:
        return

    cur = conn.cursor()
    
    # Tabela staff (Funcionários)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            jobTitle TEXT,
            secretaryId INTEGER REFERENCES staff(id),
            branchName TEXT
        );
    """)

    # Tabela residents (Moradores/Clientes)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS residents (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            selo TEXT,
            contact TEXT,
            originAddress TEXT,
            originNumber TEXT,
            originNeighborhood TEXT,
            destAddress TEXT,
            destNumber TEXT,
            destNeighborhood TEXT,
            observation TEXT,
            moveDate DATE,
            moveTime TIME,
            secretaryId INTEGER REFERENCES staff(id)
        );
    """)

    # Tabela moves (Ordens de Serviço/Mudanças)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS moves (
            id SERIAL PRIMARY KEY,
            residentId INTEGER REFERENCES residents(id) NOT NULL,
            date DATE NOT NULL,
            time TIME NOT NULL,
            metragem NUMERIC,
            supervisorId INTEGER REFERENCES staff(id),
            coordinatorId INTEGER REFERENCES staff(id),
            driverId INTEGER REFERENCES staff(id),
            status TEXT NOT NULL,
            secretaryId INTEGER REFERENCES staff(id) NOT NULL,
            completionDate DATE,
            completionTime TIME
        );
    """)
    
    conn.commit()
    cur.close()

def execute_query(query, params=None, fetch_data=False):
    """
    Executa uma query SQL (INSERT, UPDATE, DELETE) ou retorna dados (SELECT).
    """
    conn = get_connection()
    if conn is None:
        return None if fetch_data else False

    try:
        cur = conn.cursor()
        cur.execute(query, params)
        
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
        st.error(f"Erro ao executar query: {e}")
        if conn:
            conn.rollback()
        return None if fetch_data else False

def fetch_all_data():
    """
    Busca todos os dados necessários para o estado inicial do aplicativo.
    """
    data = {}
    
    # 1. Staff
    df_staff = execute_query("SELECT * FROM staff", fetch_data=True)
    if df_staff is not None:
        # Substituir NaN por None
        df_staff = df_staff.where(pd.notnull(df_staff), None)
        data['staff'] = df_staff.to_dict('records')
    else:
        data['staff'] = []
    
    # 2. Residents
    df_residents = execute_query("SELECT * FROM residents", fetch_data=True)
    if df_residents is not None:
        df_residents = df_residents.where(pd.notnull(df_residents), None)
        data['residents'] = df_residents.to_dict('records')
    else:
        data['residents'] = []
    
    # 3. Moves
    df_moves = execute_query("SELECT * FROM moves", fetch_data=True)
    if df_moves is not None:
        df_moves = df_moves.where(pd.notnull(df_moves), None)
        data['moves'] = df_moves.to_dict('records')
    else:
        data['moves'] = []
    
    # 4. Roles (Hardcoded, pois é estático)
    data['roles'] = [
        {'id': 1, 'name': 'Administrador', 'permission': 'ADMIN'},
        {'id': 2, 'name': 'Secretária', 'permission': 'SECRETARY'},
        {'id': 3, 'name': 'Supervisor', 'permission': 'SUPERVISOR'},
        {'id': 4, 'name': 'Coordenador', 'permission': 'COORDINATOR'},
        {'id': 5, 'name': 'Motorista', 'permission': 'DRIVER'}
    ]
    
    return data

# --- Funções CRUD Específicas ---

def insert_staff(name, email, password, role, jobTitle, secretaryId=None, branchName=None):
    """Insere um novo funcionário."""
    query = """
        INSERT INTO staff (name, email, password, role, jobTitle, secretaryId, branchName)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    params = (name, email, password, role, jobTitle, secretaryId, branchName)
    return execute_query(query, params)

def insert_resident(data):
    """Insere um novo morador."""
    query = """
        INSERT INTO residents (name, selo, contact, originAddress, originNumber, originNeighborhood,
                               destAddress, destNumber, destNeighborhood, observation, moveDate, moveTime, secretaryId)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        data['name'], data['selo'], data['contact'], data['originAddress'], data['originNumber'], data['originNeighborhood'],
        data['destAddress'], data['destNumber'], data['destNeighborhood'], data['observation'], data['moveDate'], data['moveTime'], data['secretaryId']
    )
    return execute_query(query, params)

def insert_move(data):
    """Insere uma nova ordem de serviço."""
    # Garantir que secretaryId nunca seja None
    secretary_id = data.get('secretaryId')
    if secretary_id is None:
        # Tentar pegar do residentId
        conn = get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT \"secretaryId\" FROM residents WHERE id = %s", (data['residentId'],))
            result = cur.fetchone()
            cur.close()
            if result and result[0]:
                secretary_id = result[0]
            else:
                # Se ainda for None, usar ID 1 (admin padrão)
                secretary_id = 1
    
    query = """
        INSERT INTO moves (residentId, date, time, metragem, supervisorId, coordinatorId, driverId, status, secretaryId)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        data['residentId'], data['date'], data['time'], data['metragem'], data['supervisorId'], 
        data['coordinatorId'], data['driverId'], data['status'], secretary_id
    )
    return execute_query(query, params)

def update_move_status(move_id, status, completionDate=None, completionTime=None):
    """Atualiza o status de uma ordem de serviço."""
    query = """
        UPDATE moves
        SET status = %s, completionDate = %s, completionTime = %s
        WHERE id = %s
    """
    params = (status, completionDate, completionTime, move_id)
    return execute_query(query, params)

def update_move_details(move_id, metragem, status, completionDate=None, completionTime=None):
    """Atualiza detalhes editáveis de uma ordem de serviço."""
    query = """
        UPDATE moves
        SET metragem = %s, status = %s, completionDate = %s, completionTime = %s
        WHERE id = %s
    """
    params = (metragem, status, completionDate, completionTime, move_id)
    return execute_query(query, params)

def update_staff_details(staff_id, name, jobTitle, email, role):
    """Atualiza detalhes editáveis de um funcionário."""
    query = """
        UPDATE staff
        SET name = %s, jobTitle = %s, email = %s, role = %s
        WHERE id = %s
    """
    params = (name, jobTitle, email, role, staff_id)
    return execute_query(query, params)

# --- Funções de DELETE ---

# SUBSTITUA AS FUNÇÕES DE DELETE NO connection.py

def delete_staff(staff_id):
    """
    Deleta um funcionário.
    Antes de deletar, atualiza os registros que referenciam este funcionário.
    """
    conn = get_connection()
    if conn is None:
        return False
    
    try:
        cur = conn.cursor()
        
        # 1. Atualizar staff que tem este funcionário como secretária (setar NULL)
        cur.execute("UPDATE staff SET secretaryId = NULL WHERE secretaryId = %s", (staff_id,))
        
        # 2. Atualizar residents que tem este funcionário como secretária (setar NULL)
        cur.execute("UPDATE residents SET secretaryId = NULL WHERE secretaryId = %s", (staff_id,))
        
        # 3. Atualizar moves que tem este funcionário em qualquer função
        cur.execute("UPDATE moves SET supervisorId = NULL WHERE supervisorId = %s", (staff_id,))
        cur.execute("UPDATE moves SET coordinatorId = NULL WHERE coordinatorId = %s", (staff_id,))
        cur.execute("UPDATE moves SET driverId = NULL WHERE driverId = %s", (staff_id,))
        cur.execute("UPDATE moves SET secretaryId = NULL WHERE secretaryId = %s", (staff_id,))
        
        # 4. Agora pode deletar o funcionário
        cur.execute("DELETE FROM staff WHERE id = %s", (staff_id,))
        
        conn.commit()
        cur.close()
        return True
        
    except Exception as e:
        st.error(f"Erro ao deletar funcionário: {e}")
        if conn:
            conn.rollback()
        return False

def delete_resident(resident_id):
    """
    Deleta um morador.
    Antes de deletar, remove as ordens de serviço associadas.
    """
    conn = get_connection()
    if conn is None:
        return False
    
    try:
        cur = conn.cursor()
        
        # 1. Deletar ordens de serviço deste morador
        cur.execute("DELETE FROM moves WHERE residentId = %s", (resident_id,))
        
        # 2. Agora pode deletar o morador
        cur.execute("DELETE FROM residents WHERE id = %s", (resident_id,))
        
        conn.commit()
        cur.close()
        return True
        
    except Exception as e:
        st.error(f"Erro ao deletar morador: {e}")
        if conn:
            conn.rollback()
        return False

def delete_move(move_id):
    """Deleta uma ordem de serviço."""
    query = "DELETE FROM moves WHERE id = %s"
    params = (move_id,)
    return execute_query(query, params)

# ==============================================================================
# NOVAS FUNÇÕES - FUNCIONALIDADES ADICIONAIS
# ==============================================================================

# --- FUNÇÕES DE NOTIFICAÇÕES ---

def insert_notification(userId, title, message, type='info', link=None):
    """Cria uma nova notificação."""
    query = """
        INSERT INTO notifications (userId, title, message, type, link)
        VALUES (%s, %s, %s, %s, %s)
    """
    params = (userId, title, message, type, link)
    return execute_query(query, params)

def get_user_notifications(userId, unread_only=False):
    """Busca notificações de um usuário."""
    if unread_only:
        query = "SELECT * FROM notifications WHERE userId = %s AND isRead = FALSE ORDER BY createdAt DESC"
    else:
        query = "SELECT * FROM notifications WHERE userId = %s ORDER BY createdAt DESC LIMIT 50"
    
    df = execute_query(query, (userId,), fetch_data=True)
    return df.to_dict('records') if df is not None else []

def mark_notification_read(notification_id):
    """Marca notificação como lida."""
    query = "UPDATE notifications SET isRead = TRUE WHERE id = %s"
    return execute_query(query, (notification_id,))

def get_unread_count(userId):
    """Conta notificações não lidas."""
    query = "SELECT COUNT(*) as count FROM notifications WHERE userId = %s AND isRead = FALSE"
    df = execute_query(query, (userId,), fetch_data=True)
    return df['count'].iloc[0] if df is not None and not df.empty else 0

# --- FUNÇÕES DE ANEXOS ---

def insert_attachment(moveId, fileName, fileType, fileData, uploadedBy, description=None):
    """Adiciona um anexo (foto/documento) a uma OS."""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        query = """
            INSERT INTO attachments (moveId, fileName, fileType, fileData, uploadedBy, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cur.execute(query, (moveId, fileName, fileType, psycopg2.Binary(fileData), uploadedBy, description))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Erro ao inserir anexo: {e}")
        conn.rollback()
        return False

def get_attachments(moveId):
    """Busca todos os anexos de uma OS."""
    query = "SELECT id, fileName, fileType, uploadedBy, uploadedAt, description FROM attachments WHERE moveId = %s ORDER BY uploadedAt DESC"
    df = execute_query(query, (moveId,), fetch_data=True)
    return df.to_dict('records') if df is not None else []

def get_attachment_data(attachment_id):
    """Busca dados binários de um anexo específico."""
    query = "SELECT fileData, fileName, fileType FROM attachments WHERE id = %s"
    df = execute_query(query, (attachment_id,), fetch_data=True)
    if df is not None and not df.empty:
        return {
            'data': bytes(df['filedata'].iloc[0]),
            'name': df['filename'].iloc[0],
            'type': df['filetype'].iloc[0]
        }
    return None

def delete_attachment(attachment_id):
    """Deleta um anexo."""
    query = "DELETE FROM attachments WHERE id = %s"
    return execute_query(query, (attachment_id,))

# --- FUNÇÕES DE WHATSAPP ---

def mark_whatsapp_sent(move_id):
    """Marca que WhatsApp foi enviado para uma OS."""
    query = "UPDATE moves SET whatsappSent = TRUE, whatsappSentAt = CURRENT_TIMESTAMP WHERE id = %s"
    return execute_query(query, (move_id,))

def get_pending_whatsapp():
    """Busca OSs que precisam enviar WhatsApp."""
    query = """
        SELECT m.*, r.name as residentName, r.phone as residentPhone
        FROM moves m
        JOIN residents r ON m.residentId = r.id
        WHERE m.whatsappSent = FALSE 
        AND m.status = 'A realizar'
        AND r.phone IS NOT NULL
        ORDER BY m.date ASC
    """
    df = execute_query(query, fetch_data=True)
    return df.to_dict('records') if df is not None else []

# --- FUNÇÕES DE ROTA ---

def update_route_info(move_id, distance, duration, origin_lat, origin_lng, dest_lat, dest_lng):
    """Atualiza informações de rota de uma OS."""
    query = """
        UPDATE moves 
        SET distance = %s, estimatedDuration = %s, 
            originLat = %s, originLng = %s, 
            destLat = %s, destLng = %s
        WHERE id = %s
    """
    params = (distance, duration, origin_lat, origin_lng, dest_lat, dest_lng, move_id)
    return execute_query(query, params)

# --- FUNÇÕES DE RELATÓRIOS ---

def get_report_data(start_date=None, end_date=None):
    """Busca dados para relatórios."""
    base_query = """
        SELECT 
            m.*,
            r.name as clientName,
            r.originAddress,
            r.destAddress,
            s.name as supervisorName,
            c.name as coordinatorName,
            d.name as driverName,
            sec.name as secretaryName
        FROM moves m
        LEFT JOIN residents r ON m.residentId = r.id
        LEFT JOIN staff s ON m.supervisorId = s.id
        LEFT JOIN staff c ON m.coordinatorId = c.id
        LEFT JOIN staff d ON m.driverId = d.id
        LEFT JOIN staff sec ON m.secretaryId = sec.id
        WHERE 1=1
    """
    
    params = []
    if start_date:
        base_query += " AND m.date >= %s"
        params.append(start_date)
    if end_date:
        base_query += " AND m.date <= %s"
        params.append(end_date)
    
    base_query += " ORDER BY m.date DESC"
    
    df = execute_query(base_query, tuple(params) if params else None, fetch_data=True)
    return df if df is not None else pd.DataFrame()
