import streamlit as st
import pandas as pd
from datetime import datetime
import time
from connection import fetch_all_data, init_db_structure, insert_staff, insert_resident, insert_move, update_move_details, get_connection

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
        # Inicializa a estrutura do DB se for a primeira vez
        init_db_structure(conn)
        
        # Tenta buscar dados. Se não houver, insere os dados iniciais.
        data = fetch_all_data()
        
        # Verifica se a tabela staff está vazia e insere dados iniciais se necessário
        if not data['staff']:
            st.info("Banco de dados vazio. Inserindo dados iniciais de demonstração...")
            
            # Dados iniciais hardcoded (usados apenas para a primeira inicialização)
            initial_staff = [
                {'name': 'Admin Geral', 'email': 'admin@telemim.com', 'password': '123', 'role': 'ADMIN', 'jobTitle': 'Administrador', 'secretaryId': None, 'branchName': None},
                {'name': 'Ana Secretária', 'email': 'ana@telemim.com', 'password': '123', 'role': 'SECRETARY', 'jobTitle': 'Secretária', 'secretaryId': None, 'branchName': 'Matriz'},
            ]
            
            # Inserção de Staff (Admin e Secretária)
            for s in initial_staff:
                insert_staff(s['name'], s['email'], s['password'], s['role'], s['jobTitle'], s['secretaryId'], s['branchName'])
            
            # Re-fetch para obter os IDs reais
            data = fetch_all_data()
            
            # Mapeamento de IDs
            staff_map = {s['name']: s['id'] for s in data['staff']}
            ana_id = staff_map.get('Ana Secretária')
            
            # Inserção de Staff (Motorista e Supervisor) que dependem da Secretária
            if ana_id:
                initial_staff_linked = [
                    {'name': 'Carlos Motorista', 'email': 'carlos@telemim.com', 'password': '123', 'role': 'DRIVER', 'jobTitle': 'Motorista', 'secretaryId': ana_id, 'branchName': None},
                    {'name': 'Maria Supervisora', 'email': 'maria@telemim.com', 'password': '123', 'role': 'SUPERVISOR', 'jobTitle': 'Supervisor', 'secretaryId': ana_id, 'branchName': None}
                ]
                for s in initial_staff_linked:
                    insert_staff(s['name'], s['email'], s['password'], s['role'], s['jobTitle'], s['secretaryId'], s['branchName'])
            
            # Re-fetch para obter os IDs reais atualizados
            data = fetch_all_data()
            staff_map = {s['name']: s['id'] for s in data['staff']}
            ana_id = staff_map.get('Ana Secretária')
            carlos_id = staff_map.get('Carlos Motorista')
            maria_id = staff_map.get('Maria Supervisora')
            
            # Inserção de Residentes (depende do ID da Secretária)
            if ana_id:
                initial_resident = {
                    'name': 'João Silva', 'selo': 'A101', 'contact': '1199999999', 
                    'originAddress': 'Rua A, 100', 'destAddress': 'Rua B, 200', 'observation': 'Piano de cauda', 
                    'moveDate': '2023-12-01', 'moveTime': '08:00', 'secretaryId': ana_id,
                    'originNumber': 'S/N', 'originNeighborhood': 'Centro',
                    'destNumber': 'S/N', 'destNeighborhood': 'Bairro Novo'
                }
                insert_resident(initial_resident)
                
                # Re-fetch para obter o ID do residente
                data = fetch_all_data()
                resident_map = {r['name']: r['id'] for r in data['residents']}
                joao_id = resident_map.get('João Silva')
                
                # Inserção de Moves (depende dos IDs de Resident, Supervisor, Driver)
                if joao_id and carlos_id and maria_id:
                    initial_move = {
                        'residentId': joao_id, 'date': '2023-12-01', 'time': '08:00', 'metragem': 15.0, 
                        'supervisorId': maria_id, 'coordinatorId': None, 'driverId': carlos_id, 
                        'status': 'A realizar', 'secretaryId': ana_id, 'completionDate': None, 'completionTime': None
                    }
                    insert_move(initial_move)
            
            # Re-fetch final para carregar todos os dados no session state
            data = fetch_all_data()
            
        # Adiciona a lista de roles hardcoded (não está no DB)
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
        st.session_state.data = {'staff': [], 'residents': [], 'moves': [], 'roles': []} # Dados vazios para evitar erro

if 'user' not in st.session_state:
    st.session_state.user = None

# --- FUNÇÕES AUXILIARES ---

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

# --- TELA DE LOGIN ---
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

# --- TELAS DO SISTEMA ---

def dashboard():
    st.title("📊 Painel de Controle")
    
    scope_id = get_current_scope_id()
    moves = filter_by_scope(st.session_state.data['moves'])
    
    # KPIs
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
        
    # Cards Interativos (Usando st.button com HTML/CSS para simular cards)
    with col1:
        if st.button(f"**A Realizar**\n\n# {todo}", key="kpi_todo", use_container_width=True):
            set_filter("A realizar")
    with col2:
        if st.button(f"**Realizando**\n\n# {doing}", key="kpi_doing", use_container_width=True):
            set_filter("Realizando")
    with col3:
        if st.button(f"**Concluídas**\n\n# {done}", key="kpi_done", use_container_width=True):
            set_filter("Concluído")
            
    st.divider()
    
    # Filtros
    st.subheader("🔎 Buscar Mudanças")
    c1, c2, c3 = st.columns(3)
    f_name = c1.text_input("Nome do Cliente")
    
    # O filtro de status agora usa o valor da sessão (que pode ter sido alterado pelos cards)
    f_status = c2.selectbox("Status", ["Todos", "A realizar", "Realizando", "Concluído"], 
                            index=["Todos", "A realizar", "Realizando", "Concluído"].index(st.session_state.dashboard_filter_status),
                            key="status_selectbox")
    
    # Atualiza o filtro da sessão se o selectbox for alterado manualmente
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

    # Exibir Tabela Simplificada
    if filtered:
        df = pd.DataFrame(filtered)
        
        # Verifica se o DataFrame tem colunas antes de tentar acessá-las
        if 'residentId' in df.columns:
            df['Cliente'] = df['residentId'].apply(lambda x: get_name_by_id(st.session_state.data['residents'], x))
            df_display = df[['id', 'date', 'Cliente', 'status', 'metragem']]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            # Isso só deve acontecer se filtered for uma lista de dicionários vazios, o que é um caso limite
            st.warning("Nenhuma mudança encontrada com esses filtros.")
    else:
        st.warning("Nenhuma mudança encontrada com esses filtros.")

def manage_moves():
    st.title("📦 Ordens de Serviço")
    
    moves = filter_by_scope(st.session_state.data['moves'])
    
    if not moves:
        st.info("Nenhuma OS registrada.")
        return

    # Convert to DataFrame for editing
    df = pd.DataFrame(moves)
    
    # Helper columns for display
    df['Nome Cliente'] = df['residentId'].apply(lambda x: get_name_by_id(st.session_state.data['residents'], x))
    df['Supervisor'] = df['supervisorId'].apply(lambda x: get_name_by_id(st.session_state.data['staff'], x))
    
    # Edit Mode
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
    
    # Save changes back to database
    if not df.equals(edited_df):
        success = True
        for index, row in edited_df.iterrows():
            # Apenas atualiza se houver mudança real na linha (Streamlit não indica qual linha mudou)
            original_row = df.loc[index]
            
            # Verifica se a linha foi modificada (comparando colunas editáveis)
            editable_cols = ['date', 'time', 'status', 'metragem', 'completionDate', 'completionTime']
            modified = any(original_row[col] != row[col] for col in editable_cols)
            
            if modified:
                # Converte data e hora para string ou None
                completion_date = str(row['completionDate']) if pd.notna(row['completionDate']) else None
                completion_time = str(row['completionTime']) if pd.notna(row['completionTime']) else None
                
                # Usando a função update_move_details que criamos no connection.py
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
            # Re-fetch para atualizar o session state com os dados do DB
            st.session_state.data = fetch_all_data()
            st.success("Alterações salvas automaticamente no banco de dados!")

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
        
        # Admin select secretary logic
        user = st.session_state.user
        sec_id = get_current_scope_id()
        
        # Admin select secretary logic
        user = st.session_state.user
        sec_id = get_current_scope_id()
        
        if user['role'] == 'ADMIN':
            secretaries = [s for s in st.session_state.data['staff'] if s['role'] == 'SECRETARY']
            
            # Corrigindo o KeyError: Usar o nome da secretária se branchName for None
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
                # O campo 'id' é gerado automaticamente pelo DB
                new_res = {
                    'name': name, 'selo': selo, 'contact': contact,
                    'originAddress': orig_addr, 'originNumber': orig_num, 'originNeighborhood': orig_bairro,
                    'destAddress': dest_addr, 'destNumber': dest_num, 'destNeighborhood': dest_bairro,
                    'observation': obs, 'moveDate': str(move_date), 'moveTime': str(move_time),
                    'secretaryId': sec_id
                }
                if insert_resident(new_res):
                    # Atualiza o session state após a inserção no DB
                    st.session_state.data = fetch_all_data()
                    st.success("Morador cadastrado com sucesso!")
                else:
                    st.error("Erro ao cadastrar morador no banco de dados.")

def schedule_form():
    st.title("🗓️ Agendamento de OS")
    
    # Filter lists by scope
    scoped_residents = filter_by_scope(st.session_state.data['residents'])
    scoped_staff = filter_by_scope(st.session_state.data['staff'])
    
    if not scoped_residents:
        st.warning("Nenhum morador cadastrado nesta base. Cadastre um morador primeiro.")
        return

    with st.form("new_move"):
        # Resident Select
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
        
        submit = st.form_submit_button("Confirmar Agendamento")
        
        if submit:
            if not res_name or not sup_name or not drive_name:
                st.error("Selecione o Morador, Supervisor e Motorista.")
            else:
                resident_id = res_map[res_name]
                supervisor_id = sup_map[sup_name]
                driver_id = drive_map.get(drive_name)
                coordinator_id = coord_map.get(coord_name)
                sec_id = get_current_scope_id()
                
                new_move = {
                    'residentId': resident_id, 'date': str(date), 'time': str(time_val),
                    'metragem': 0.0, # Metragem inicial é 0.0, será atualizada no manage_moves
                    'supervisorId': supervisor_id, 'coordinatorId': coordinator_id,
                    'driverId': driver_id, 'status': 'A realizar', 'secretaryId': sec_id,
                    'completionDate': None, 'completionTime': None
                }
                if insert_move(new_move):
                    # Atualiza o session state após a inserção no DB
                    st.session_state.data = fetch_all_data()
                    st.success("Ordem de Serviço agendada com sucesso!")
                else:
                    st.error("Erro ao agendar Ordem de Serviço no banco de dados.")

def staff_management():
    st.title("👥 Recursos Humanos")
    
    # Removendo st.tabs para evitar problemas de renderização de formulário
    with st.form("new_staff"):
            name = st.text_input("Nome Completo")
            email = st.text_input("Login (Email)")
            password = st.text_input("Senha", type="password")
            
            # Role Select
            role_map = {r['name']: r for r in st.session_state.data['roles'] if r['permission'] not in ['ADMIN', 'SECRETARY']}
            role_name = st.selectbox("Cargo", list(role_map.keys()))
            
            # Admin Linking
            user = st.session_state.user
            sec_id = None
            if user['role'] == 'ADMIN':
                secs = [s for s in st.session_state.data['staff'] if s['role'] == 'SECRETARY']
                sec_map = {s['branchName']: s['id'] for s in secs}
                sec_name = st.selectbox("Vincular à Secretária", list(sec_map.keys()))
                if sec_name: sec_id = sec_map[sec_name]
            else:
                sec_id = user['id'] # Self link for secretary

            submit = st.form_submit_button("Cadastrar Funcionário")
            
            if submit:
                if name:
                    role_permission = role_map[role_name]['permission']
                    if insert_staff(name, email, password or '123', role_permission, role_name, sec_id):
                        # Atualiza o session state após a inserção no DB
                        st.session_state.data = fetch_all_data()
                        st.success("Usuário criado!")
                    else:
                        st.error("Erro ao cadastrar funcionário no banco de dados.")
                else:
                    st.error("Nome obrigatório")

    st.subheader("Equipe Cadastrada")
    scoped_staff = filter_by_scope(st.session_state.data['staff'])
    df = pd.DataFrame(scoped_staff)
    if not df.empty:
        # Hide password for security visual
        df_display = df[['name', 'jobTitle', 'email', 'role']]
        st.dataframe(df_display, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhum funcionário encontrado.")

def manage_secretaries():
    st.title("🏢 Gestão de Secretarias")
    
    with st.form("new_sec"):
        name = st.text_input("Nome da Secretaria / Base")
        submit = st.form_submit_button("Criar Base")
        
        if submit and name:
            login = name.lower().replace(" ", "") + "@telemim.com"
            # Para Secretária, o secretaryId é o próprio ID (auto-referência)
            # Como o ID é gerado pelo DB, vamos inserir sem o ID e depois atualizar o session state
            if insert_staff(name, login, '123', 'SECRETARY', 'Secretária', None, name):
                # Re-fetch para obter o ID gerado e atualizar o session state
                st.session_state.data = fetch_all_data()
                
                # Encontrar o ID da secretária recém-criada para atualizar o secretaryId (self-reference)
                new_sec = next((s for s in st.session_state.data['staff'] if s['email'] == login), None)
                if new_sec and new_sec['secretaryId'] is None:
                    # ATENÇÃO: A função insert_staff não permite UPDATE. 
                    # Para simplificar, vamos aceitar que o secretaryId da Secretária seja NULL por enquanto,
                    # e o escopo será tratado pelo `filter_by_scope` que verifica `item.get('id') == str(scope)`.
                    # Em um sistema real, seria necessário um UPDATE SQL para self-reference.
                    st.success(f"Criado! Login automático: {login} / Senha: 123. (Lembre-se de configurar o secretaryId no DB se necessário para escopo)")
                else:
                    st.success(f"Criado! Login automático: {login} / Senha: 123.")
            else:
                st.error("Erro ao cadastrar Secretária no banco de dados.")

def manage_roles():
    st.title("🛡️ Cargos")
    
    with st.form("new_role"):
        name = st.text_input("Nome do Cargo")
        perm = st.selectbox("Permissão do Sistema", list(ROLES.values()))
        submit = st.form_submit_button("Salvar Cargo")
        
        if submit and name:
            # Find key by value
            perm_key = next(key for key, value in ROLES.items() if value == perm)
            st.session_state.data['roles'].append({'id': int(time.time()), 'name': name, 'permission': perm_key})
            st.success("Cargo criado.")
            
    st.table(pd.DataFrame(st.session_state.data['roles']))

# --- NAVEGAÇÃO PRINCIPAL ---

if not st.session_state.user:
    login_screen()
else:
    user = st.session_state.user
    
    # Mapeamento de Opções e Ícones
    menu_map = {
        "Gerenciamento": {"icon": "house", "func": dashboard},
        "Ordens de Serviço": {"icon": "box-seam", "func": manage_moves},
        "Moradores": {"icon": "person-vcard", "func": residents_form},
        "Agendamento": {"icon": "calendar-check", "func": schedule_form},
        "Funcionários": {"icon": "people", "func": staff_management},
        "Secretarias": {"icon": "building", "func": manage_secretaries},
        "Cargos": {"icon": "shield-lock", "func": manage_roles},
    }
    
    # Regras de Menu Dinâmico
    options = ["Gerenciamento", "Ordens de Serviço"]
    can_schedule = user['role'] in ['ADMIN', 'SECRETARY', 'COORDINATOR', 'SUPERVISOR']
    
    if can_schedule:
        options.extend(["Moradores", "Agendamento"])
        
    if user['role'] == 'ADMIN':
        options.extend(["Funcionários", "Cargos", "Secretarias"])
    elif user['role'] == 'SECRETARY':
        options.extend(["Funcionários"]) # Secretária manages her own staff
        
    # Criação da Lista de Opções para o Menu Topo (st.selectbox)
    menu_options = [op for op in options if op in menu_map]
    
    # Renderiza o menu no topo
    choice = st.selectbox("Navegação", menu_options, label_visibility="collapsed")
    
    # Sidebar de Usuário
    with st.sidebar:
        st.title(f"Olá, {user['name']}")
        st.caption(f"Cargo: {user.get('jobTitle', 'N/A')}")
        
        if st.button("Sair", type="primary"):
            st.session_state.user = None
            st.rerun()
            
        st.divider()

    # Router
    if choice == "Gerenciamento":
        dashboard()
    elif choice == "Ordens de Serviço":
        manage_moves()
    elif choice == "Moradores":
        residents_form()
    elif choice == "Agendamento":
        schedule_form()
    elif choice == "Funcionários":
        staff_management()
    elif choice == "Secretarias":
        manage_secretaries()
    elif choice == "Cargos":
        manage_roles()

