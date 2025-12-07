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
    """
    if conn is None:
        return

    cur = conn.cursor()
    
    # Tabela staff
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            secretaryId INTEGER REFERENCES staff(id)
        )
    """)
    
    # Tabela residents
    cur.execute("""
        CREATE TABLE IF NOT EXISTS residents (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            selo TEXT,
            contact TEXT,
            "originAddress" TEXT,
            "originNumber" TEXT,
            "originNeighborhood" TEXT,
            "destAddress" TEXT,
            "destNumber" TEXT,
            "destNeighborhood" TEXT,
            observation TEXT,
            "moveDate" DATE,
            "moveTime" TIME,
            "secretaryId" INTEGER REFERENCES staff(id)
        )
    """)
    
    # Tabela moves
    cur.execute("""
        CREATE TABLE IF NOT EXISTS moves (
            id SERIAL PRIMARY KEY,
            "residentId" INTEGER NOT NULL REFERENCES residents(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            time TIME,
            metragem DECIMAL(10,2) DEFAULT 0,
            "supervisorId" INTEGER REFERENCES staff(id),
            "coordinatorId" INTEGER REFERENCES staff(id),
            "driverId" INTEGER REFERENCES staff(id),
            status TEXT DEFAULT 'A realizar',
            "secretaryId" INTEGER REFERENCES staff(id)
        )
    """)
    
    conn.commit()
    cur.close()

def execute_query(query, params=None, fetch_data=False):
    """
    Executa uma query no banco de dados.
    """
    conn = get_connection()
    if conn is None:
        return None
    
    try:
        cur = conn.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        
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
        conn.rollback()
        return False

def fetch_all_data():
    """
    Busca todos os dados necessários.
    """
    data = {}
    
    # Staff
    df_staff = execute_query("SELECT * FROM staff", fetch_data=True)
    if df_staff is not None:
        df_staff = df_staff.where(pd.notnull(df_staff), None)
        data['staff'] = df_staff.to_dict('records')
    else:
        data['staff'] = []
    
    # Residents
    df_residents = execute_query("SELECT * FROM residents", fetch_data=True)
    if df_residents is not None:
        df_residents = df_residents.where(pd.notnull(df_residents), None)
        data['residents'] = df_residents.to_dict('records')
    else:
        data['residents'] = []
    
    # Moves
    df_moves = execute_query("SELECT * FROM moves", fetch_data=True)
    if df_moves is not None:
        df_moves = df_moves.where(pd.notnull(df_moves), None)
        data['moves'] = df_moves.to_dict('records')
    else:
        data['moves'] = []
    
    # Roles
    data['roles'] = [
        {'id': 1, 'name': 'Administrador', 'permission': 'ADMIN'},
        {'id': 2, 'name': 'Secretária', 'permission': 'SECRETARY'},
        {'id': 3, 'name': 'Supervisor', 'permission': 'SUPERVISOR'},
        {'id': 4, 'name': 'Coordenador', 'permission': 'COORDINATOR'},
        {'id': 5, 'name': 'Motorista', 'permission': 'DRIVER'}
    ]
    
    return data

# --- Funções CRUD ---

def insert_staff(name, email, password, role, secretaryId=None):
    """Insere um novo funcionário."""
    query = """
        INSERT INTO staff (name, email, password, role, "secretaryId")
        VALUES (%s, %s, %s, %s, %s)
    """
    params = (name, email, password, role, secretaryId)
    return execute_query(query, params)

def insert_resident(data):
    """Insere um novo morador."""
    query = """
        INSERT INTO residents (name, selo, contact, "originAddress", "originNumber", 
                             "originNeighborhood", "destAddress", "destNumber", 
                             "destNeighborhood", observation, "moveDate", "moveTime", "secretaryId")
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        data['name'], data.get('selo'), data.get('contact'),
        data.get('originAddress'), data.get('originNumber'), data.get('originNeighborhood'),
        data.get('destAddress'), data.get('destNumber'), data.get('destNeighborhood'),
        data.get('observation'), data.get('moveDate'), data.get('moveTime'),
        data.get('secretaryId')
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
            cur.execute('SELECT "secretaryId" FROM residents WHERE id = %s', (data['residentId'],))
            result = cur.fetchone()
            cur.close()
            if result and result[0]:
                secretary_id = result[0]
            else:
                secretary_id = 1
    
    query = """
        INSERT INTO moves (residentId, date, time, metragem, supervisorId, coordinatorId, 
                          driverId, status, secretaryId)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        data['residentId'], data['date'], data['time'], data['metragem'],
        data['supervisorId'], data['coordinatorId'], data['driverId'],
        data['status'], secretary_id
    )
    return execute_query(query, params)

def update_move_details(move_id, data):
    """Atualiza uma ordem de serviço."""
    query = """
        UPDATE moves
        SET metragem = %s, status = %s
        WHERE id = %s
    """
    params = (data.get('metragem', 0), data.get('status', 'A realizar'), move_id)
    return execute_query(query, params)

def update_staff_details(staff_id, name, jobTitle, email, role):
    """Atualiza um funcionário."""
    query = """
        UPDATE staff
        SET name = %s, email = %s, role = %s
        WHERE id = %s
    """
    params = (name, email, role, staff_id)
    return execute_query(query, params)

def delete_staff(staff_id):
    """Deleta um funcionário."""
    query = "DELETE FROM staff WHERE id = %s"
    return execute_query(query, (staff_id,))
