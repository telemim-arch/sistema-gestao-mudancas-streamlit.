import streamlit as st
import pandas as pd
from datetime import datetime
import time
from connection import (
    fetch_all_data, init_db_structure, insert_staff, insert_resident,
    insert_move, update_move_details, get_connection, delete_staff,
    update_staff_details
)

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Telemim Mudanças", page_icon="🚛", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
    }
    .stButton>button[kind="primary"] {
        background-color: #1E88E5 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- CONSTANTES ---
ROLES = {
    'ADMIN': 'Administrador',
    'SECRETARY': 'Secretária',
    'SUPERVISOR': 'Supervisor',
    'COORDINATOR': 'Coordenador',
    'DRIVER': 'Motorista'
}

# --- INICIALIZAÇÃO ---
if 'data' not in st.session_state:
    conn = get_connection()
    if conn:
        init_db_structure(conn)
        data = fetch_all_data()
        
        if not data or not data.get('staff'):
            insert_staff('Administrador', 'admin@telemim.com', '123', 'ADMIN', None)
            data = fetch_all_data()
        
        st.session_state.data = data
    else:
        st.error("Não foi possível conectar ao banco de dados.")
        st.session_state.data = {'staff': [], 'residents': [], 'moves': [], 'roles': []}

if 'user' not in st.session_state:
    st.session_state.user = None

# --- FUNÇÕES AUXILIARES ---

def get_current_scope_id():
    user = st.session_state.user
    if not user: return None
    if user['role'] == 'ADMIN': return None
    if user['role'] == 'SECRETARY': return user['id']
    return user.get('secretaryId')

def ensure_secretary_id():
    """Garante que sempre retorne um secretaryId válido"""
    user = st.session_state.user
    data = st.session_state.data
    
    if user['role'] == 'ADMIN':
        secretaries = [s for s in data['staff'] if s['role'] == 'SECRETARY']
        if secretaries:
            return secretaries[0]['id']
        else:
            return user['id']
    elif user['role'] == 'SECRETARY':
        return user['id']
    else:
        return user.get('secretaryId') or user['id']

def filter_by_scope(data_list, key='secretaryId'):
    scope = get_current_scope_id()
    if scope is None: return data_list
    return [item for item in data_list if str(item.get(key)) == str(scope) or str(item.get('id')) == str(scope)]

def get_name_by_id(data_list, id_val):
    if not id_val:
        return "N/A"
    item = next((x for x in data_list if x['id'] == id_val), None)
    return item['name'] if item else "N/A"

# --- TELA DE LOGIN ---

def login_screen():
    col_logo = st.columns([1, 1, 1])
    with col_logo[1]:
        try:
            st.image("Telemim_logo.png", width=250)
        except:
            st.markdown("<h1 style='text-align: center; color: #FF4B1F;'>🚛 TELEMIM</h1>", unsafe_allow_html=True)
    
    st.markdown("<h3 style='text-align: center; color: #666;'>Sistema de Gestão de Mudanças</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("📧 Email", placeholder="seu@email.com")
            password = st.text_input("🔑 Senha", type="password")
            submit = st.form_submit_button("🚪 Entrar", type="primary", use_container_width=True)
            
            if submit:
                user = next((u for u in st.session_state.data['staff'] 
                           if u['email'].lower() == email.lower() and u['password'] == password), None)
                if user:
                    st.session_state.user = user
                    st.success(f"✅ Bem-vindo, {user['name']}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Credenciais inválidas.")
        
        st.info("💡 Teste: admin@telemim.com / 123")

# --- DASHBOARD ---

def dashboard():
    st.title("📊 Painel de Controle")
    
    moves = filter_by_scope(st.session_state.data['moves'])
    
    col1, col2, col3 = st.columns(3)
    
    todo = len([m for m in moves if m['status'] == 'A realizar'])
    doing = len([m for m in moves if m['status'] == 'Realizando'])
    done = len([m for m in moves if m['status'] == 'Concluído'])
    
    with col1:
        st.metric("📋 A Realizar", todo)
    with col2:
        st.metric("🔄 Realizando", doing)
    with col3:
        st.metric("✅ Concluídas", done)
    
    st.divider()
    
    st.subheader("🔍 Buscar Mudanças")
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        search_query = st.text_input("Buscar por nome", "")
    with col_f2:
        filter_status = st.selectbox("Filtrar por Status", ["Todos", "A realizar", "Realizando", "Concluído"])
    
    filtered = moves
    
    if search_query:
        residents = st.session_state.data['residents']
        filtered = [m for m in filtered if search_query.lower() in get_name_by_id(residents, m['residentId']).lower()]
    
    if filter_status != "Todos":
        filtered = [m for m in filtered if m['status'] == filter_status]
    
    if filtered:
        df = pd.DataFrame(filtered)
        if 'residentId' in df.columns:
            df['Nome Cliente'] = df['residentId'].apply(lambda x: get_name_by_id(st.session_state.data['residents'], x))
            df['Supervisor'] = df['supervisorId'].apply(lambda x: get_name_by_id(st.session_state.data['staff'], x))
            
            df_display = df[['id', 'Nome Cliente', 'date', 'time', 'status', 'Supervisor']].copy()
            df_display.columns = ['OS #', 'Cliente', 'Data', 'Hora', 'Status', 'Supervisor']
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            st.caption(f"📊 Mostrando {len(filtered)} de {len(moves)} ordem(ns)")
    else:
        st.info("💡 Nenhuma mudança encontrada.")

# --- GESTÃO DE MUDANÇAS ---

def manage_moves():
    st.title("📦 Ordens de Serviço")
    
    moves = filter_by_scope(st.session_state.data['moves'])
    
    if not moves:
        st.info("Nenhuma OS registrada.")
        return

    df = pd.DataFrame(moves)
    
    if not df.empty and 'residentId' in df.columns:
        df['Nome Cliente'] = df['residentId'].apply(lambda x: get_name_by_id(st.session_state.data['residents'], x))
        
        edited_df = st.data_editor(
            df,
            column_config={
                "id": st.column_config.NumberColumn("OS #", disabled=True),
                "Nome Cliente": st.column_config.TextColumn("Cliente", disabled=True),
                "date": "Data",
                "time": "Hora",
                "status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["A realizar", "Realizando", "Concluído"],
                    required=True
                ),
                "metragem": st.column_config.NumberColumn("Volume (m³)", min_value=0, format="%.2f"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        if not df.equals(edited_df):
            for idx, row in edited_df.iterrows():
                move_id = row['id']
                if update_move_details(move_id, dict(row)):
                    st.session_state.data = fetch_all_data()
            st.success("Alterações salvas!")

# --- FORMULÁRIOS ---

def residents_form():
    st.title("🏠 Cadastro de Moradores")
    
    if 'resident_form_key' not in st.session_state:
        st.session_state.resident_form_key = 0
    
    with st.form(f"new_resident_{st.session_state.resident_form_key}"):
        st.subheader("📝 Dados do Cliente")
        name = st.text_input("Nome Completo *")
        c1, c2 = st.columns(2)
        selo = c1.text_input("Selo / ID")
        contact = c2.text_input("Telefone")
        
        st.subheader("📍 Origem")
        c3, c4 = st.columns([3, 1])
        orig_addr = c3.text_input("Endereço (Origem)")
        orig_num = c4.text_input("Nº")
        orig_bairro = st.text_input("Bairro (Origem)")
        
        st.subheader("🎯 Destino")
        c5, c6 = st.columns([3, 1])
        dest_addr = c5.text_input("Endereço (Destino)")
        dest_num = c6.text_input("Nº", key="dest_num")
        dest_bairro = st.text_input("Bairro (Destino)")
        
        obs = st.text_area("Observações")
        
        st.subheader("📅 Previsão")
        c7, c8 = st.columns(2)
        move_date = c7.date_input("Data da Mudança")
        move_time = c8.time_input("Hora")
        
        submit = st.form_submit_button("✅ Salvar Morador", type="primary", use_container_width=True)
        
        if submit:
            if not name:
                st.error("⚠️ Nome é obrigatório.")
            else:
                sec_id = ensure_secretary_id()
                
                new_res = {
                    'name': name, 'selo': selo, 'contact': contact,
                    'originAddress': orig_addr, 'originNumber': orig_num, 'originNeighborhood': orig_bairro,
                    'destAddress': dest_addr, 'destNumber': dest_num, 'destNeighborhood': dest_bairro,
                    'observation': obs, 'moveDate': str(move_date), 'moveTime': str(move_time),
                    'secretaryId': sec_id
                }
                if insert_resident(new_res):
                    st.session_state.data = fetch_all_data()
                    st.session_state.resident_form_key += 1
                    st.toast("🎉 Cadastro concluído!", icon="✅")
                    st.success(f"✅ **{name}** cadastrado(a) com sucesso!")
                    time.sleep(1)
                    st.rerun()

def schedule_form():
    st.title("🗓️ Agendamento de OS")
    
    scoped_residents = filter_by_scope(st.session_state.data['residents'])
    scoped_staff = filter_by_scope(st.session_state.data['staff'], key='id')
    
    if not scoped_residents:
        st.warning("Nenhum morador cadastrado. Cadastre um morador primeiro.")
        return

    with st.form("new_move"):
        res_map = {r['name']: r['id'] for r in scoped_residents}
        res_name = st.selectbox("Morador", list(res_map.keys()))
        
        c1, c2 = st.columns(2)
        m_date = c1.date_input("Data da Mudança")
        m_time = c2.time_input("Hora")
        
        metragem = st.number_input("Volume (m³)", min_value=0.0, step=0.5)
        
        st.subheader("Equipe")
        
        supervisors = [s for s in scoped_staff if s['role'] in ['SUPERVISOR', 'ADMIN']]
        coordinators = [s for s in scoped_staff if s['role'] in ['COORDINATOR', 'ADMIN']]
        drivers = [s for s in scoped_staff if s['role'] in ['DRIVER']]
        
        sup_id = None
        coord_id = None
        drv_id = None
        
        if supervisors:
            sup_name = st.selectbox("Supervisor", [s['name'] for s in supervisors])
            sup_id = next((s['id'] for s in supervisors if s['name'] == sup_name), None)
        
        if coordinators:
            coord_name = st.selectbox("Coordenador", [s['name'] for s in coordinators])
            coord_id = next((s['id'] for s in coordinators if s['name'] == coord_name), None)
        
        if drivers:
            drv_name = st.selectbox("Motorista", [s['name'] for s in drivers])
            drv_id = next((s['id'] for s in drivers if s['name'] == drv_name), None)
        
        submit = st.form_submit_button("Agendar Mudança", type="primary")
        
        if submit:
            new_move = {
                'residentId': res_map[res_name],
                'date': str(m_date),
                'time': str(m_time),
                'metragem': metragem,
                'supervisorId': sup_id,
                'coordinatorId': coord_id,
                'driverId': drv_id,
                'status': 'A realizar',
                'secretaryId': ensure_secretary_id()
            }
            
            if insert_move(new_move):
                st.session_state.data = fetch_all_data()
                st.success("✅ Mudança agendada com sucesso!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Erro ao agendar mudança.")

def staff_management():
    st.title("👥 Recursos Humanos")
    
    if 'staff_form_key' not in st.session_state:
        st.session_state.staff_form_key = 0
    
    with st.form(f"new_staff_{st.session_state.staff_form_key}"):
        st.subheader("➕ Cadastrar Novo Funcionário")
        
        name = st.text_input("Nome Completo")
        email = st.text_input("Login (Email)")
        password = st.text_input("Senha", type="password", placeholder="Deixe vazio para senha padrão: 123")
        
        role_map = {r['name']: r for r in st.session_state.data['roles'] if r['permission'] not in ['ADMIN', 'SECRETARY']}
        role_name = st.selectbox("Cargo", list(role_map.keys()))
        
        submit = st.form_submit_button("✅ Cadastrar Funcionário", type="primary", use_container_width=True)
        
        if submit:
            if name and email:
                role_permission = role_map[role_name]['permission']
                sec_id = ensure_secretary_id()
                
                if insert_staff(name, email, password or '123', role_permission, sec_id):
                    st.session_state.data = fetch_all_data()
                    st.session_state.staff_form_key += 1
                    st.toast("🎉 Cadastro concluído!", icon="✅")
                    st.success(f"✅ **{name}** cadastrado!")
                    time.sleep(1)
                    st.rerun()
    
    st.divider()
    st.subheader("📋 Funcionários Cadastrados")
    
    scoped_staff = filter_by_scope(st.session_state.data['staff'], key='id')
    
    if scoped_staff:
        for idx, row in enumerate(scoped_staff):
            role_display = ROLES.get(row.get('role', ''), row.get('role', 'N/A'))
            with st.expander(f"👤 {row['name']} - {role_display}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Email:** {row.get('email', 'N/A')}")
                    st.write(f"**Cargo:** {role_display}")
                    st.write(f"**ID:** {row['id']}")
                
                with col2:
                    if st.button(f"🗑️ Deletar", key=f"del_{row['id']}", type="secondary"):
                        if delete_staff(row['id']):
                            st.session_state.data = fetch_all_data()
                            st.success(f"✅ {row['name']} deletado!")
                            time.sleep(1)
                            st.rerun()

# --- NAVEGAÇÃO ---

if not st.session_state.user:
    login_screen()
else:
    user = st.session_state.user
    
    menu_map = {
        "Gerenciamento": {"icon": "📊", "func": dashboard},
        "Ordens de Serviço": {"icon": "📦", "func": manage_moves},
        "Moradores": {"icon": "🏠", "func": residents_form},
        "Agendamento": {"icon": "📅", "func": schedule_form},
        "Funcionários": {"icon": "👥", "func": staff_management},
    }
    
    options = ["Gerenciamento", "Ordens de Serviço"]
    can_schedule = user['role'] in ['ADMIN', 'SECRETARY', 'COORDINATOR', 'SUPERVISOR']
    
    if can_schedule:
        options.extend(["Moradores", "Agendamento"])
        
    if user['role'] in ['ADMIN', 'SECRETARY']:
        options.append("Funcionários")
    
    menu_options = [op for op in options if op in menu_map]
    
    with st.sidebar:
        try:
            st.image("Telemim_logo.png", use_container_width=True)
        except:
            st.markdown("### 🚛 TELEMIM")
        
        st.markdown("---")
        st.markdown(f"### 👤 {user['name']}")
        st.caption(f"🎯 {ROLES.get(user['role'], user['role'])}")
        st.divider()
        
        if st.button("🚪 Sair", type="primary", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    
    st.markdown("---")
    
    tab_labels = [f"{menu_map[op]['icon']} {op}" for op in menu_options]
    tabs = st.tabs(tab_labels)
    
    for i, option in enumerate(menu_options):
        with tabs[i]:
            menu_map[option]['func']()
