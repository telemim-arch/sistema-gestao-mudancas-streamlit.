import streamlit as st
import pandas as pd
from datetime import datetime
import time
from connection import fetch_all_data, init_db_structure, insert_staff, insert_resident, insert_move, update_move_details, get_connection, delete_staff

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Telemim Mudanças", page_icon="🚛", layout="wide")

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
    }
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# --- CONSTANTES DE CARGOS ---
ROLES = {
    'ADMIN': 'Administrador',
    'SECRETARY': 'Secretária',
    'SUPERVISOR': 'Supervisor',
    'COORDINATOR': 'Coordenador',
    'DRIVER': 'Motorista',
    'HELPER': 'Ajudante'
}

# --- INICIALIZAÇÃO DO BANCO DE DADOS E DADOS (SESSION STATE) ---
if 'data' not in st.session_state:
    conn = get_connection()
    if conn:
        init_db_structure(conn)
        data = fetch_all_data()
        
        if not data['staff']:
            st.info("Banco de dados vazio. Inserindo dados iniciais de demonstração...")
            
            initial_staff = [
                {'name': 'Admin Geral', 'email': 'admin@telemim.com', 'password': '123', 'role': 'ADMIN', 'jobTitle': 'Administrador', 'secretaryId': None, 'branchName': None},
                {'name': 'Ana Secretária', 'email': 'ana@telemim.com', 'password': '123', 'role': 'SECRETARY', 'jobTitle': 'Secretária', 'secretaryId': None, 'branchName': 'Matriz'},
            ]
            
            for s in initial_staff:
                insert_staff(s['name'], s['email'], s['password'], s['role'], s['jobTitle'], s['secretaryId'], s['branchName'])
            
            data = fetch_all_data()
            staff_map = {s['name']: s['id'] for s in data['staff']}
            ana_id = staff_map.get('Ana Secretária')
            
            if ana_id:
                initial_staff_linked = [
                    {'name': 'Carlos Motorista', 'email': 'carlos@telemim.com', 'password': '123', 'role': 'DRIVER', 'jobTitle': 'Motorista', 'secretaryId': ana_id, 'branchName': None},
                    {'name': 'Maria Supervisora', 'email': 'maria@telemim.com', 'password': '123', 'role': 'SUPERVISOR', 'jobTitle': 'Supervisor', 'secretaryId': ana_id, 'branchName': None}
                ]
                for s in initial_staff_linked:
                    insert_staff(s['name'], s['email'], s['password'], s['role'], s['jobTitle'], s['secretaryId'], s['branchName'])
            
            data = fetch_all_data()
            staff_map = {s['name']: s['id'] for s in data['staff']}
            ana_id = staff_map.get('Ana Secretária')
            carlos_id = staff_map.get('Carlos Motorista')
            maria_id = staff_map.get('Maria Supervisora')
            
            if ana_id:
                initial_resident = {
                    'name': 'João Silva', 'selo': 'A101', 'contact': '1199999999', 
                    'originAddress': 'Rua A, 100', 'destAddress': 'Rua B, 200', 'observation': 'Piano de cauda', 
                    'moveDate': '2023-12-01', 'moveTime': '08:00', 'secretaryId': ana_id,
                    'originNumber': 'S/N', 'originNeighborhood': 'Centro',
                    'destNumber': 'S/N', 'destNeighborhood': 'Bairro Novo'
                }
                insert_resident(initial_resident)
                
                data = fetch_all_data()
                resident_map = {r['name']: r['id'] for r in data['residents']}
                joao_id = resident_map.get('João Silva')
                
                if joao_id and carlos_id and maria_id:
                    initial_move = {
                        'residentId': joao_id, 'date': '2023-12-01', 'time': '08:00', 'metragem': 15.0, 
                        'supervisorId': maria_id, 'coordinatorId': None, 'driverId': carlos_id, 
                        'status': 'A realizar', 'secretaryId': ana_id, 'completionDate': None, 'completionTime': None
                    }
                    insert_move(initial_move)
            
            data = fetch_all_data()
            
        data['roles'] = [
            {'id': 1, 'name': 'Administrador', 'permission': 'ADMIN'},
            {'id': 2, 'name': 'Secretária', 'permission': 'SECRETARY'},
            {'id': 3, 'name': 'Supervisor', 'permission': 'SUPERVISOR'},
            {'id': 4, 'name': 'Coordenador', 'permission': 'COORDINATOR'},
            {'id': 5, 'name': 'Motorista', 'permission': 'DRIVER'}
        ]
        
        st.session_state.data = data
    else:
        st.error("Não foi possível conectar ao banco de dados. Verifique suas credenciais em .streamlit/secrets.toml.")
        st.session_state.data = {'staff': [], 'residents': [], 'moves': [], 'roles': []}

if 'user' not in st.session_state:
    st.session_state.user = None

def get_current_scope_id():
    user = st.session_state.user
    if not user: return None
    if user['role'] == 'ADMIN': return None
    if user['role'] == 'SECRETARY': return user['id']
    return user['secretaryId']

def filter_by_scope(data_list, key='secretaryId'):
    scope = get_current_scope_id()
    if scope is None: return data_list
    return [item for item in data_list if str(item.get(key)) == str(scope) or str(item.get('id')) == str(scope)]

def get_name_by_id(data_list, id_val):
    item = next((x for x in data_list if str(x['id']) == str(id_val)), None)
    return item['name'] if item else 'N/A'

def login_screen():
    st.markdown("<h1 style='text-align: center; color: #2563eb;'>🚛 TELEMIM</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Sistema de Gestão de Mudanças</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar")
            
            if submit:
                user = next((u for u in st.session_state.data['staff'] if u['email'].lower() == email.lower() and u['password'] == password), None)
                if user:
                    st.session_state.user = user
                    st.success(f"Bem-vindo, {user['name']}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
        
        st.info("Teste: admin@telemim.com / 123")

def dashboard():
    st.title("📊 Painel de Controle")
    
    scope_id = get_current_scope_id()
    moves = filter_by_scope(st.session_state.data['moves'])
    
    # KPIs com Cards Melhorados
    col1, col2, col3 = st.columns(3)
    
    # Contagem de Status
    todo = len([m for m in moves if m['status'] == 'A realizar'])
    doing = len([m for m in moves if m['status'] == 'Realizando'])
    done = len([m for m in moves if m['status'] == 'Concluído'])
    
    # Inicializa o filtro de status na sessão
    if 'dashboard_filter_status' not in st.session_state:
        st.session_state.dashboard_filter_status = "Todos"
        
    # Função para mudar o filtro ao clicar no card
    def set_filter(status):
        st.session_state.dashboard_filter_status = status
        
    # Cards com métricas usando st.metric (corrigido)
    with col1:
        st.metric(
            label="📋 A Realizar",
            value=todo,
            delta=None
        )
        if st.button("Ver Detalhes", key="btn_todo", use_container_width=True):
            set_filter("A realizar")
    
    with col2:
        st.metric(
            label="🔄 Realizando",
            value=doing,
            delta=None
        )
        if st.button("Ver Detalhes", key="btn_doing", use_container_width=True):
            set_filter("Realizando")
    
    with col3:
        st.metric(
            label="✅ Concluídas",
            value=done,
            delta=None
        )
        if st.button("Ver Detalhes", key="btn_done", use_container_width=True):
            set_filter("Concluído")
            
    st.divider()
    
    # Filtros
    st.subheader("🔎 Buscar Mudanças")
    c1, c2, c3 = st.columns(3)
    f_name = c1.text_input("Nome do Cliente", placeholder="Digite o nome...")
    
    # O filtro de status agora usa o valor da sessão
    f_status = c2.selectbox(
        "Status", 
        ["Todos", "A realizar", "Realizando", "Concluído"], 
        index=["Todos", "A realizar", "Realizando", "Concluído"].index(st.session_state.dashboard_filter_status),
        key="status_selectbox"
    )
    
    # Atualiza o filtro da sessão se o selectbox for alterado
    if f_status != st.session_state.dashboard_filter_status:
        st.session_state.dashboard_filter_status = f_status
        
    f_date = c3.date_input("Data", value=None)
    
    # Aplicar Filtros
    filtered = moves
    if st.session_state.dashboard_filter_status != "Todos":
        filtered = [m for m in filtered if m['status'] == st.session_state.dashboard_filter_status]
    if f_date:
        filtered = [m for m in filtered if m['date'] == str(f_date)]
    if f_name:
        filtered = [m for m in filtered if f_name.lower() in get_name_by_id(st.session_state.data['residents'], m['residentId']).lower()]

    # Exibir Tabela
    if filtered:
        df = pd.DataFrame(filtered)
        if 'residentId' in df.columns:
            df['Cliente'] = df['residentId'].apply(lambda x: get_name_by_id(st.session_state.data['residents'], x))
            df_display = df[['id', 'date', 'Cliente', 'status', 'metragem']]
            
            # Renomear colunas
            df_display.columns = ['OS #', 'Data', 'Cliente', 'Status', 'Volume (m³)']
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            st.caption(f"📊 Mostrando {len(filtered)} de {len(moves)} ordem(ns) de serviço")
        else:
            st.warning("⚠️ Nenhuma mudança encontrada com esses filtros.")
    else:
        st.info("💡 Nenhuma mudança encontrada com esses filtros.")


def manage_moves():
    st.title("📦 Ordens de Serviço")
    
    moves = filter_by_scope(st.session_state.data['moves'])
    
    if not moves:
        st.info("Nenhuma OS registrada.")
        return

    df = pd.DataFrame(moves)
    
    if not df.empty and 'residentId' in df.columns:
        df['Nome Cliente'] = df['residentId'].apply(lambda x: get_name_by_id(st.session_state.data['residents'], x))
        df['Supervisor'] = df['supervisorId'].apply(lambda x: get_name_by_id(st.session_state.data['staff'], x))
        
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
                "completionDate": st.column_config.DateColumn("Data Fim"),
                "completionTime": st.column_config.TimeColumn("Hora Fim"),
            },
            hide_index=True,
            disabled=["residentId", "secretaryId", "driverId", "coordinatorId", "Supervisor"],
            use_container_width=True
        )
        
        if not df.equals(edited_df):
            success = True
            for index, row in edited_df.iterrows():
                original_row = df.loc[index]
                editable_cols = ['date', 'time', 'status', 'metragem', 'completionDate', 'completionTime']
                modified = any(original_row[col] != row[col] for col in editable_cols)
                
                if modified:
                    completion_date = str(row['completionDate']) if pd.notna(row['completionDate']) else None
                    completion_time = str(row['completionTime']) if pd.notna(row['completionTime']) else None
                    
                    if not update_move_details(
                        move_id=row['id'],
                        metragem=row['metragem'],
                        status=row['status'],
                        completionDate=completion_date,
                        completionTime=completion_time
                    ):
                        success = False
                        st.error(f"Erro ao atualizar OS #{row['id']} no banco de dados.")
                        break
            
            if success:
                st.session_state.data = fetch_all_data()
                st.success("Alterações salvas automaticamente no banco de dados!")
    else:
        st.info("Nenhuma Ordem de Serviço encontrada.")

def residents_form():
    st.title("🏠 Cadastro de Moradores")
    
    with st.form("new_resident"):
        st.subheader("Dados do Cliente")
        name = st.text_input("Nome Completo *")
        c1, c2 = st.columns(2)
        selo = c1.text_input("Selo / ID")
        contact = c2.text_input("Telefone / Contato")
        
        st.subheader("Origem")
        c3, c4 = st.columns([3, 1])
        orig_addr = c3.text_input("Endereço (Origem)")
        orig_num = c4.text_input("Nº (Origem)")
        orig_bairro = st.text_input("Bairro (Origem)")
        
        st.subheader("Destino")
        c5, c6 = st.columns([3, 1])
        dest_addr = c5.text_input("Endereço (Destino)")
        dest_num = c6.text_input("Nº (Destino)")
        dest_bairro = st.text_input("Bairro (Destino)")
        
        obs = st.text_area("Observações")
        
        st.subheader("Previsão")
        c7, c8 = st.columns(2)
        move_date = c7.date_input("Data da Mudança")
        move_time = c8.time_input("Hora")
        
        user = st.session_state.user
        sec_id = get_current_scope_id()
        
        if user['role'] == 'ADMIN':
            secretaries = [s for s in st.session_state.data['staff'] if s['role'] == 'SECRETARY']
            sec_options = {}
            for s in secretaries:
                key = s.get('branchName') or s['name']
                sec_options[key] = s['id']
            selected_sec_name = st.selectbox("Vincular à Secretária", list(sec_options.keys()))
            if selected_sec_name: sec_id = sec_options[selected_sec_name]

        submit = st.form_submit_button("Salvar Morador")
        
        if submit:
            if not name:
                st.error("Nome é obrigatório.")
            else:
                new_res = {
                    'name': name, 'selo': selo, 'contact': contact,
                    'originAddress': orig_addr, 'originNumber': orig_num, 'originNeighborhood': orig_bairro,
                    'destAddress': dest_addr, 'destNumber': dest_num, 'destNeighborhood': dest_bairro,
                    'observation': obs, 'moveDate': str(move_date), 'moveTime': str(move_time),
                    'secretaryId': sec_id
                }
                if insert_resident(new_res):
                    st.session_state.data = fetch_all_data()
                    st.success("Morador cadastrado com sucesso!")
                else:
                    st.error("Erro ao cadastrar morador no banco de dados.")

def schedule_form():
    st.title("🗓️ Agendamento de OS")
    
    scoped_residents = filter_by_scope(st.session_state.data['residents'])
    scoped_staff = filter_by_scope(st.session_state.data['staff'], key='id')
    
    if not scoped_residents:
        st.warning("Nenhum morador cadastrado nesta base. Cadastre um morador primeiro.")
        return

    with st.form("new_move"):
        res_map = {r['name']: r['id'] for r in scoped_residents}
        res_name = st.selectbox("Morador", list(res_map.keys()))
        
        c1, c2 = st.columns(2)
        date = c1.date_input("Data")
        time_val = c2.time_input("Hora")
        
        st.subheader("Equipe")
        supervisors = [s for s in scoped_staff if s['role'] == 'SUPERVISOR']
        coordinators = [s for s in scoped_staff if s['role'] == 'COORDINATOR']
        drivers = [s for s in scoped_staff if s['role'] == 'DRIVER']
        
        sup_map = {s['name']: s['id'] for s in supervisors}
        coord_map = {s['name']: s['id'] for s in coordinators}
        drive_map = {s['name']: s['id'] for s in drivers}
        
        sup_name = st.selectbox("Supervisor (Obrigatório)", list(sup_map.keys()) if sup_map else [])
        coord_name = st.selectbox("Coordenador", ["Nenhum"] + list(coord_map.keys()))
        drive_name = st.selectbox("Motorista", ["Nenhum"] + list(drive_map.keys()))
        
        user = st.session_state.user
        sec_id = get_current_scope_id()
        
        if user['role'] == 'ADMIN':
            secretaries = [s for s in st.session_state.data['staff'] if s['role'] == 'SECRETARY']
            sec_options = {}
            for s in secretaries:
                key = s.get('branchName') or s['name']
                sec_options[key] = s['id']
            selected_sec_name = st.selectbox("Vincular à Secretária (Admin)", list(sec_options.keys()))
            if selected_sec_name: sec_id = sec_options[selected_sec_name]
            
        if sec_id is None:
            st.error("Erro: O ID da Secretária não foi definido. O Admin deve selecionar uma Secretária.")
            
        submit = st.form_submit_button("Confirmar Agendamento")
        
        if submit:
            if not res_name or not sup_name:
                st.error("Selecione o Morador e o Supervisor.")
            else:
                resident_id = res_map[res_name]
                supervisor_id = sup_map[sup_name]
                driver_id = drive_map.get(drive_name)
                coordinator_id = coord_map.get(coord_name)
                
                new_move = {
                    'residentId': resident_id, 'date': str(date), 'time': str(time_val),
                    'metragem': 0.0,
                    'supervisorId': supervisor_id, 'coordinatorId': coordinator_id,
                    'driverId': driver_id, 'status': 'A realizar', 'secretaryId': sec_id,
                }
                
                if insert_move(new_move):
                    st.session_state.data = fetch_all_data()
                    st.success("Ordem de Serviço agendada com sucesso!")
                else:
                    st.error("Erro ao agendar Ordem de Serviço no banco de dados.")

def staff_management():
    st.title("👥 Recursos Humanos")
    
    # Formulário de cadastro
    with st.form("new_staff"):
        st.subheader("➕ Cadastrar Novo Funcionário")
        
        name = st.text_input("Nome Completo")
        email = st.text_input("Login (Email)")
        password = st.text_input("Senha", type="password")
        
        role_map = {r['name']: r for r in st.session_state.data['roles'] if r['permission'] not in ['ADMIN', 'SECRETARY']}
        role_name = st.selectbox("Cargo", list(role_map.keys()))
        
        user = st.session_state.user
        sec_id = None
        if user['role'] == 'ADMIN':
            secs = [s for s in st.session_state.data['staff'] if s['role'] == 'SECRETARY']
            sec_options = {}
            for s in secs:
                key = s.get('branchName') or s['name']
                sec_options[key] = s['id']
            if sec_options:
                sec_name = st.selectbox("Vincular à Secretária", list(sec_options.keys()))
                if sec_name: 
                    sec_id = sec_options[sec_name]
        else:
            sec_id = user['id']

        submit = st.form_submit_button("Cadastrar Funcionário", type="primary")
        
        if submit:
            if name:
                role_permission = role_map[role_name]['permission']
                if insert_staff(name, email, password or '123', role_permission, role_name, sec_id):
                    st.session_state.data = fetch_all_data()
                    st.success("✅ Usuário criado!")
                    st.rerun()
                else:
                    st.error("❌ Erro ao cadastrar funcionário no banco de dados.")
            else:
                st.error("⚠️ Nome obrigatório")
    
    st.divider()
    
    # Lista de funcionários cadastrados
    st.subheader("📋 Funcionários Cadastrados")
    
    scoped_staff = filter_by_scope(st.session_state.data['staff'], key='id')
    
    if scoped_staff:
        # Criar DataFrame
        df = pd.DataFrame(scoped_staff)
        
        # Colunas disponíveis
        available_cols = df.columns.tolist()
        preferred_cols = ['id', 'name', 'email', 'role']
        display_cols = [col for col in preferred_cols if col in available_cols]
        
        if display_cols:
            # Mapear roles para nomes legíveis
            if 'role' in df.columns:
                df['role_display'] = df['role'].apply(lambda x: ROLES.get(x, x))
            
            # Exibir cada funcionário como um card expansível
            for idx, row in df.iterrows():
                with st.expander(f"👤 {row['name']} - {row.get('role_display', row.get('role', 'N/A'))}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        # Formulário de edição
                        with st.form(f"edit_staff_{row['id']}"):
                            st.write("**Editar Informações:**")
                            
                            new_name = st.text_input("Nome", value=row.get('name', ''), key=f"name_{row['id']}")
                            new_email = st.text_input("Email", value=row.get('email', ''), key=f"email_{row['id']}")
                            
                            current_role = row.get('role', '')
                            current_role_display = ROLES.get(current_role, current_role)
                            role_options = list(ROLES.values())
                            
                            try:
                                role_index = role_options.index(current_role_display)
                            except ValueError:
                                role_index = 0
                            
                            new_role_display = st.selectbox(
                                "Permissão", 
                                role_options, 
                                index=role_index,
                                key=f"role_{row['id']}"
                            )
                            
                            col_btn1, col_btn2 = st.columns(2)
                            
                            with col_btn1:
                                save_btn = st.form_submit_button("💾 Salvar", type="primary", use_container_width=True)
                            
                            if save_btn:
                                new_role = next((key for key, value in ROLES.items() if value == new_role_display), current_role)
                                
                                if update_staff_details(row['id'], new_name, '', new_email, new_role):
                                    st.success(f"✅ {new_name} atualizado!")
                                    st.session_state.data = fetch_all_data()
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao atualizar")
                    
                    with col2:
                        st.write("**Ações:**")
                        st.write("")
                        
                        # Botão de deletar
                        if st.button(f"🗑️ Deletar", key=f"del_{row['id']}", type="secondary", use_container_width=True):
                            st.session_state[f'confirm_delete_{row["id"]}'] = True
                            st.rerun()
                        
                        # Confirmação de exclusão
                        if st.session_state.get(f'confirm_delete_{row["id"]}', False):
                            st.warning("⚠️ Confirmar exclusão?")
                            col_yes, col_no = st.columns(2)
                            
                            with col_yes:
                                if st.button("Sim", key=f"yes_{row['id']}", use_container_width=True):
                                    # Importar a função delete_staff
                                    from connection import delete_staff
                                    if delete_staff(row['id']):
                                        st.success(f"✅ {row['name']} deletado!")
                                        st.session_state.data = fetch_all_data()
                                        if f'confirm_delete_{row["id"]}' in st.session_state:
                                            del st.session_state[f'confirm_delete_{row["id"]}']
                                        st.rerun()
                                    else:
                                        st.error("❌ Erro ao deletar")
                            
                            with col_no:
                                if st.button("Não", key=f"no_{row['id']}", use_container_width=True):
                                    if f'confirm_delete_{row["id"]}' in st.session_state:
                                        del st.session_state[f'confirm_delete_{row["id"]}']
                                    st.rerun()
                        
                        # Info do ID
                        st.caption(f"ID: {row['id']}")
            
            st.caption(f"📊 Total: {len(scoped_staff)} funcionário(s)")
        else:
            st.error("Nenhuma coluna válida para exibir.")
    else:
        st.info("💡 Nenhum funcionário cadastrado no seu escopo ainda.")


def manage_secretaries():
    st.title("🏢 Gestão de Secretarias")
    
    # Formulário de cadastro
    st.subheader("Cadastrar Nova Secretaria")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        name = st.text_input("Nome da Secretaria / Base")
    
    with col2:
        st.write("")  # Espaçamento
        st.write("")  # Espaçamento
        if st.button("Criar Base", type="primary", use_container_width=True):
            if name:
                login = name.lower().replace(" ", "") + "@telemim.com"
                if insert_staff(name, login, '123', 'SECRETARY', 'Secretária', None, name):
                    st.session_state.data = fetch_all_data()
                    new_sec = next((s for s in st.session_state.data['staff'] if s['email'] == login), None)
                    if new_sec:
                        st.success(f"✅ Criado! Login: {login} | Senha: 123")
                        st.rerun()
                    else:
                        st.success(f"✅ Criado! Login: {login} | Senha: 123")
                else:
                    st.error("Erro ao cadastrar Secretária no banco de dados.")
            else:
                st.error("Nome da Secretaria / Base é obrigatório.")
    
    st.divider()
    
    # Lista de secretarias cadastradas
    st.subheader("Secretarias Cadastradas")
    
    # Filtrar apenas secretárias
    secretaries = [s for s in st.session_state.data['staff'] if s['role'] == 'SECRETARY']
    
    if secretaries:
        # Criar DataFrame
        df = pd.DataFrame(secretaries)
        
        # Colunas disponíveis
        available_cols = df.columns.tolist()
        
        # Colunas que queremos exibir
        preferred_cols = ['id', 'name', 'branchName', 'email']
        display_cols = [col for col in preferred_cols if col in available_cols]
        
        if display_cols:
            df_display = df[display_cols].copy()
            
            # Renomear colunas para exibição
            rename_map = {
                'id': 'ID',
                'name': 'Nome',
                'branchName': 'Base',
                'email': 'Login'
            }
            
            # Configuração de colunas
            column_config = {}
            for col in display_cols:
                if col == 'id':
                    column_config[col] = st.column_config.NumberColumn("ID", disabled=True)
                elif col == 'name':
                    column_config[col] = st.column_config.TextColumn("Nome", disabled=True)
                elif col == 'branchName':
                    column_config[col] = st.column_config.TextColumn("Base", disabled=True)
                elif col == 'email':
                    column_config[col] = st.column_config.TextColumn("Login", disabled=True)
            
            # Exibir tabela (apenas leitura)
            st.dataframe(
                df_display,
                column_config=column_config,
                hide_index=True,
                use_container_width=True
            )
            
            # Estatísticas
            st.caption(f"📊 Total de secretarias: {len(secretaries)}")
        else:
            st.warning("Dados incompletos na tabela de secretarias.")
    else:
        st.info("Nenhuma secretaria cadastrada ainda.")


def reports_page():
    st.title("📈 Relatórios e Análises")
    st.info("Funcionalidade em desenvolvimento. Aqui você poderá gerar relatórios de OS, desempenho da equipe e exportar dados.")

def manage_roles():
    st.title("🛡️ Cargos")
    
    with st.form("new_role"):
        name = st.text_input("Nome do Cargo")
        perm = st.selectbox("Permissão do Sistema", list(ROLES.values()))
        submit = st.form_submit_button("Salvar Cargo")
        
        if submit:
            if name:
                perm_key = next(key for key, value in ROLES.items() if value == perm)
                st.session_state.data['roles'].append({'id': int(time.time()), 'name': name, 'permission': perm_key})
                st.success("Cargo criado.")
            
    st.table(pd.DataFrame(st.session_state.data['roles']))

# SUBSTITUIR A SEÇÃO DE NAVEGAÇÃO PRINCIPAL NO FINAL DO ARQUIVO

if not st.session_state.user:
    login_screen()
else:
    user = st.session_state.user
    
    # Mapeamento de Opções com Ícones e Emojis
    menu_map = {
        "Gerenciamento": {"icon": "📊", "func": dashboard},
        "Ordens de Serviço": {"icon": "📦", "func": manage_moves},
        "Moradores": {"icon": "🏠", "func": residents_form},
        "Agendamento": {"icon": "📅", "func": schedule_form},
        "Funcionários": {"icon": "👥", "func": staff_management},
        "Secretarias": {"icon": "🏢", "func": manage_secretaries},
        "Cargos": {"icon": "🛡️", "func": manage_roles},
        "Relatórios": {"icon": "📈", "func": reports_page},
    }
    
    # Regras de Menu Dinâmico
    options = ["Gerenciamento", "Ordens de Serviço"]
    can_schedule = user['role'] in ['ADMIN', 'SECRETARY', 'COORDINATOR', 'SUPERVISOR']
    
    if can_schedule:
        options.extend(["Moradores", "Agendamento"])
        
    if user['role'] == 'ADMIN':
        options.extend(["Funcionários", "Cargos", "Secretarias", "Relatórios"])
    elif user['role'] == 'SECRETARY':
        options.extend(["Funcionários"])
        
    # Criação da Lista de Opções para o Menu
    menu_options = [op for op in options if op in menu_map]
    
    # Sidebar de Usuário com ícones
    with st.sidebar:
        st.markdown(f"### 👤 {user['name']}")
        st.caption(f"🎯 Cargo: {user.get('jobTitle', user['role'])}")
        
        st.divider()
        
        # Menu de navegação na sidebar
        st.markdown("### 📑 Menu")
        
        for option in menu_options:
            icon = menu_map[option]['icon']
            if st.button(f"{icon} {option}", key=f"menu_{option}", use_container_width=True):
                st.session_state['current_page'] = option
        
        st.divider()
        
        if st.button("🚪 Sair", type="primary", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    
    # Renderizar página selecionada
    current_page = st.session_state.get('current_page', 'Gerenciamento')
    
    # Garantir que a página atual está nas opções disponíveis
    if current_page not in menu_options:
        current_page = menu_options[0]
        st.session_state['current_page'] = current_page
    
    # Executar função da página
    menu_map[current_page]['func']()
