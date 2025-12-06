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
    data['staff'] = df_staff.to_dict('records') if df_staff is not None else []
    
    # 2. Residents
    df_residents = execute_query("SELECT * FROM residents", fetch_data=True)
    data['residents'] = df_residents.to_dict('records') if df_residents is not None else []
    
    # 3. Moves
    df_moves = execute_query("SELECT * FROM moves", fetch_data=True)
    data['moves'] = df_moves.to_dict('records') if df_moves is not None else []
    
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
    query = """
        INSERT INTO moves (residentId, date, time, metragem, supervisorId, coordinatorId, driverId, status, secretaryId)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        data['residentId'], data['date'], data['time'], data['metragem'], data['supervisorId'], 
        data['coordinatorId'], data['driverId'], data['status'], data['secretaryId']
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
