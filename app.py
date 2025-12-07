import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import calendar
from connection import (
    fetch_all_data, init_db_structure, insert_staff, insert_resident, 
    insert_move, update_move_details, get_connection, delete_staff, 
    update_staff_details,
    # NOVAS FUNÇÕES
    insert_notification, get_user_notifications, mark_notification_read,
    get_unread_count, insert_attachment, get_attachments, 
    get_attachment_data, delete_attachment, get_report_data
)

# Imports adicionais para novas funcionalidades
try:
    from PIL import Image
    import io
    import base64
    import plotly.express as px
    import plotly.graph_objects as go
    from io import BytesIO
except ImportError:
    pass  # Será instalado via requirements.txt

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
    /* Botões primários em azul */
    .stButton>button[kind="primary"] {
        background-color: #1E88E5 !important;
        color: white !important;
        border: none !important;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #1565C0 !important;
        border: none !important;
    }
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    .logo-container {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 10px 0;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- CONSTANTES DE CARGOS ---
ROLES = {
    'ADMIN': 'Administrador',
    'SECRETARY': 'Secretária',
    'SUPERVISOR': 'Supervisor',
    'COORDINATOR': 'Coordenador',
    'DRIVER': 'Motorista'
}

# --- INICIALIZAÇÃO DO ESTADO ---
if 'data' not in st.session_state:
    conn = get_connection()
    
    if conn:
        init_db_structure(conn)
        data = fetch_all_data()
        
        if not data or not data.get('staff'):
            admin_user = {
                'name': 'Administrador',
                'email': 'admin@telemim.com',
                'password': '123',
                'role': 'ADMIN',
                'jobTitle': 'Administrador',
                'secretaryId': None
            }
            insert_staff(admin_user['name'], admin_user['email'], admin_user['password'], 
                        admin_user['role'], admin_user['jobTitle'], admin_user['secretaryId'])
            
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
    return user.get('secretaryId')  # Usar .get() para evitar KeyError

def filter_by_scope(data_list, key='secretaryId'):
    scope = get_current_scope_id()
    if scope is None: return data_list
    return [item for item in data_list if str(item.get(key)) == str(scope) or str(item.get('id')) == str(scope)]

def get_name_by_id(data_list, id_val):
    if not id_val:
        return "N/A"
    item = next((x for x in data_list if x['id'] == id_val), None)
    return item['name'] if item else "N/A"

def get_time_ago(dt):
    """Retorna tempo relativo"""
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "agora mesmo"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"há {minutes} minuto{'s' if minutes > 1 else ''}"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"há {hours} hora{'s' if hours > 1 else ''}"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"há {days} dia{'s' if days > 1 else ''}"
    else:
        return dt.strftime("%d/%m/%Y")

def ensure_secretary_id():
    """
    Garante que sempre retorne um secretaryId válido
    NUNCA retorna None!
    """
    user = st.session_state.user
    data = st.session_state.data
    
    if user['role'] == 'ADMIN':
        # Para ADMIN, tenta pegar primeira secretária
        secretaries = [s for s in data['staff'] if s['role'] == 'SECRETARY']
        if secretaries:
            return secretaries[0]['id']
        else:
            # Se não houver secretária, usa ID do próprio admin
            return user['id']
    elif user['role'] == 'SECRETARY':
        return user['id']
    else:
        # Para outros perfis, retorna secretaryId ou ID próprio
        return user.get('secretaryId') or user['id']

# --- TELA DE LOGIN ---

def login_screen():
    # Logo centralizada no topo (menor)
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
            password = st.text_input("🔑 Senha", type="password", placeholder="Digite sua senha")
            submit = st.form_submit_button("🚪 Entrar", type="primary", use_container_width=True)
            
            if submit:
                user = next((u for u in st.session_state.data['staff'] if u['email'].lower() == email.lower() and u['password'] == password), None)
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
    
    scope_id = get_current_scope_id()
    moves = filter_by_scope(st.session_state.data['moves'])
    
    # KPIs com Cards INTERATIVOS
    col1, col2, col3 = st.columns(3)
    
    # Contagem de Status
    todo = len([m for m in moves if m['status'] == 'A realizar'])
    doing = len([m for m in moves if m['status'] == 'Realizando'])
    done = len([m for m in moves if m['status'] == 'Concluído'])
    
    # Inicializa o filtro de status na sessão
    if 'dashboard_filter_status' not in st.session_state:
        st.session_state.dashboard_filter_status = "Todos"
    
    # Cards CLICÁVEIS com botões
    with col1:
        st.metric(
            label="📋 A Realizar",
            value=todo,
            delta=None
        )
        if st.button("🔍 Ver A Realizar", key="btn_todo", use_container_width=True):
            st.session_state.dashboard_filter_status = "A realizar"
            st.rerun()
    
    with col2:
        st.metric(
            label="🔄 Realizando",
            value=doing,
            delta=None
        )
        if st.button("🔍 Ver Realizando", key="btn_doing", use_container_width=True):
            st.session_state.dashboard_filter_status = "Realizando"
            st.rerun()
    
    with col3:
        st.metric(
            label="✅ Concluídas",
            value=done,
            delta=None
        )
        if st.button("🔍 Ver Concluídas", key="btn_done", use_container_width=True):
            st.session_state.dashboard_filter_status = "Concluído"
            st.rerun()
            
    st.divider()
    
    # Botão para mostrar todas
    col_clear1, col_clear2, col_clear3 = st.columns([1, 1, 1])
    with col_clear2:
        if st.session_state.dashboard_filter_status != "Todos":
            if st.button("🔄 Mostrar Todas", type="secondary", use_container_width=True):
                st.session_state.dashboard_filter_status = "Todos"
                st.rerun()
    
    # Filtros
    st.subheader("🔍 Buscar Mudanças")
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        search_query = st.text_input("Buscar por nome", "")
    
    with col_f2:
        filter_status = st.selectbox("Filtrar por Status", 
                                     ["Todos", "A realizar", "Realizando", "Concluído"],
                                     index=["Todos", "A realizar", "Realizando", "Concluído"].index(st.session_state.dashboard_filter_status))
    
    with col_f3:
        filter_date = st.date_input("Filtrar por Data", value=None)
    
    # Aplicar filtros
    filtered = moves
    
    if search_query:
        residents = st.session_state.data['residents']
        filtered = [m for m in filtered if any(search_query.lower() in get_name_by_id(residents, m['residentId']).lower())]
    
    if filter_status != "Todos":
        filtered = [m for m in filtered if m['status'] == filter_status]
    
    if filter_date:
        filtered = [m for m in filtered if str(m.get('date')) == str(filter_date)]
    
    # Exibir resultados
    if filtered:
        df = pd.DataFrame(filtered)
        
        if 'residentId' in df.columns:
            df['Nome Cliente'] = df['residentId'].apply(lambda x: get_name_by_id(st.session_state.data['residents'], x))
            df['Supervisor'] = df['supervisorId'].apply(lambda x: get_name_by_id(st.session_state.data['staff'], x))
            
            df_display = df[['id', 'Nome Cliente', 'date', 'time', 'status', 'Supervisor']].copy()
            df_display.columns = ['OS #', 'Cliente', 'Data', 'Hora', 'Status', 'Supervisor']
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            st.caption(f"📊 Mostrando {len(filtered)} de {len(moves)} ordem(ns) de serviço")
        else:
            st.warning("⚠️ Nenhuma mudança encontrada com esses filtros.")
    else:
        st.info("💡 Nenhuma mudança encontrada com esses filtros.")

# --- CALENDÁRIO VISUAL ---

def calendar_view():
    """Calendário Visual de Mudanças"""
    st.title("📅 Calendário de Mudanças")
    
    # Seletor de mês/ano
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        year = st.selectbox("Ano", range(2024, 2027), index=1)
    
    with col2:
        months = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        month = st.selectbox("Mês", range(1, 13), format_func=lambda x: months[x-1], 
                            index=datetime.now().month-1)
    
    with col3:
        view_mode = st.radio("Visualização", ["Mensal", "Lista"], horizontal=True)
    
    # Buscar mudanças do mês
    moves = filter_by_scope(st.session_state.data['moves'])
    
    # Filtrar por mês
    moves_month = []
    for m in moves:
        if m.get('date'):
            try:
                move_date = datetime.strptime(str(m['date']), '%Y-%m-%d')
                if move_date.year == year and move_date.month == month:
                    moves_month.append(m)
            except:
                pass
    
    if view_mode == "Mensal":
        render_monthly_calendar(year, month, moves_month)
    else:
        render_list_view(moves_month)
    
    # Legenda
    st.markdown("---")
    col_leg1, col_leg2, col_leg3 = st.columns(3)
    with col_leg1:
        st.markdown("🟡 **A Realizar**")
    with col_leg2:
        st.markdown("🔵 **Realizando**")
    with col_leg3:
        st.markdown("🟢 **Concluída**")

def render_monthly_calendar(year, month, moves):
    """Renderiza calendário mensal"""
    cal = calendar.monthcalendar(year, month)
    
    # Agrupar por dia
    moves_by_day = {}
    for move in moves:
        try:
            day = datetime.strptime(str(move['date']), '%Y-%m-%d').day
            if day not in moves_by_day:
                moves_by_day[day] = []
            moves_by_day[day].append(move)
        except:
            pass
    
    # Header
    weekdays = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB', 'DOM']
    cols_header = st.columns(7)
    for i, day in enumerate(weekdays):
        with cols_header[i]:
            st.markdown(f"**{day}**")
    
    # Semanas
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown("")
                else:
                    day_moves = moves_by_day.get(day, [])
                    
                    if day_moves:
                        status_counts = {}
                        for m in day_moves:
                            status = m.get('status', 'A realizar')
                            status_counts[status] = status_counts.get(status, 0) + 1
                        
                        if status_counts.get('Concluído', 0) == len(day_moves):
                            emoji = "🟢"
                        elif status_counts.get('Realizando', 0) > 0:
                            emoji = "🔵"
                        else:
                            emoji = "🟡"
                        
                        st.markdown(f"### {emoji} {day}")
                        st.caption(f"{len(day_moves)} OS")
                    else:
                        st.markdown(f"### {day}")

def render_list_view(moves):
    """Visualização em lista"""
    if not moves:
        st.info("📭 Nenhuma mudança agendada neste mês")
        return
    
    # Ordenar por data
    moves_sorted = sorted(moves, key=lambda x: x.get('date', ''), reverse=False)
    
    # Pegar residents uma vez
    all_residents = st.session_state.data.get('residents', [])
    
    st.subheader(f"📋 {len(moves_sorted)} Mudanças Agendadas")
    
    for move in moves_sorted:
        # Buscar resident
        resident = next((r for r in all_residents if r['id'] == move.get('residentId')), None)
        
        if resident:
            status_emoji = {
                'A realizar': '🟡',
                'Realizando': '🔵',
                'Concluído': '🟢'
            }
            emoji = status_emoji.get(move.get('status', 'A realizar'), '⚪')
            
            # Data formatada
            try:
                move_date = datetime.strptime(str(move['date']), '%Y-%m-%d')
                date_str = move_date.strftime('%d/%m/%Y')
            except:
                date_str = str(move.get('date', 'N/A'))
            
            with st.expander(f"{emoji} **OS #{move.get('id', '?')}** - {resident.get('name', 'N/A')} - {date_str}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**⏰ Horário:** {move.get('time', 'N/A')}")
                    st.markdown(f"**📍 Origem:** {resident.get('originAddress', 'N/A')}")
                    st.markdown(f"**📦 Volume:** {move.get('metragem', 0)} m³")
                
                with col2:
                    st.markdown(f"**📊 Status:** {move.get('status', 'N/A')}")
                    st.markdown(f"**🎯 Destino:** {resident.get('destAddress', 'N/A')}")
                    
                    # Supervisor
                    sup_id = move.get('supervisorId')
                    if sup_id:
                        sup_name = get_name_by_id(st.session_state.data.get('staff', []), sup_id)
                        st.markdown(f"**🔧 Supervisor:** {sup_name}")
                
                # Observações se tiver
                if resident.get('observation'):
                    st.markdown("---")
                    st.markdown(f"**📝 Obs:** {resident.get('observation')}")
        else:
            # Resident não encontrado
            st.warning(f"⚠️ OS #{move.get('id', '?')} - Morador não encontrado (ID: {move.get('residentId', '?')})")

# --- CENTRAL DE NOTIFICAÇÕES ---

def notifications_center():
    """Central de Notificações"""
    st.title("🔔 Central de Notificações")
    
    user_id = st.session_state.user['id']
    
    tab1, tab2 = st.tabs(["📬 Não Lidas", "📋 Todas"])
    
    with tab1:
        show_notifications(user_id, unread_only=True)
    
    with tab2:
        show_notifications(user_id, unread_only=False)

def show_notifications(user_id, unread_only=False):
    """Exibe notificações"""
    notifications = get_user_notifications(user_id, unread_only)
    
    if not notifications:
        st.info("📭 Nenhuma notificação" + (" não lida" if unread_only else ""))
        return
    
    for notif in notifications:
        icons = {'info': 'ℹ️', 'success': '✅', 'warning': '⚠️', 'error': '❌'}
        icon = icons.get(notif.get('type', 'info'), 'ℹ️')
        
        col1, col2 = st.columns([10, 2])
        
        with col1:
            if not notif.get('isread'):
                st.markdown(f"{icon} **{notif['title']}**")
            else:
                st.markdown(f"{icon} {notif['title']}")
            
            st.caption(notif['message'])
            
            if notif.get('createdat'):
                created = notif['createdat']
                if isinstance(created, str):
                    try:
                        created = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    except:
                        created = datetime.now()
                st.caption(f"🕐 {get_time_ago(created)}")
        
        with col2:
            if not notif.get('isread'):
                if st.button("✓", key=f"read_{notif['id']}", use_container_width=True):
                    mark_notification_read(notif['id'])
                    st.toast("Marcada como lida")
                    time.sleep(0.5)
                    st.rerun()
        
        st.markdown("---")

def notification_badge():
    """Badge de notificações (para sidebar)"""
    try:
        user_id = st.session_state.user['id']
        unread = get_unread_count(user_id)
        return unread
    except:
        return 0

# --- RELATÓRIOS E ANALYTICS ---

def reports_analytics_page():
    """Página de Relatórios"""
    st.title("📊 Relatórios e Analytics")
    
    # Filtros
    with st.expander("🔍 Filtros", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("Data Início", value=datetime.now() - timedelta(days=30))
        
        with col2:
            end_date = st.date_input("Data Fim", value=datetime.now())
    
    # Buscar dados
    try:
        df = get_report_data(start_date, end_date)
    except:
        df = pd.DataFrame()
    
    if df.empty:
        st.warning("Nenhum dado encontrado para o período selecionado")
        return
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de OSs", len(df))
    
    with col2:
        completed = len(df[df['status'] == 'Concluído'])
        st.metric("Concluídas", completed)
    
    with col3:
        rate = (completed / len(df) * 100) if len(df) > 0 else 0
        st.metric("Taxa Conclusão", f"{rate:.1f}%")
    
    with col4:
        pending = len(df[df['status'] == 'A realizar'])
        st.metric("Pendentes", pending)
    
    st.markdown("---")
    
    # Tentar criar gráfico
    try:
        st.subheader("📊 Distribuição por Status")
        status_counts = df['status'].value_counts()
        
        fig = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            color_discrete_sequence=['#FFC107', '#2196F3', '#4CAF50']
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.info("Gráfico não disponível (instale plotly)")
    
    # Botão de exportar
    st.markdown("---")
    if st.button("📥 Exportar para CSV", type="primary"):
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name=f"relatorio_{start_date}_{end_date}.csv",
            mime="text/csv"
        )

# --- GESTÃO DE MUDANÇAS ---

def manage_moves():
    st.title("📦 Ordens de Serviço")
    
    # Tabs: Ver OSs OU Criar nova OU Lista de Mudanças
    tab1, tab2, tab3 = st.tabs(["📋 Ver Ordens", "➕ Nova Ordem", "📅 Mudanças Agendadas"])
    
    with tab1:
        # VISUALIZAR OSs EXISTENTES
        moves = filter_by_scope(st.session_state.data['moves'])
        
        if not moves:
            st.info("💡 Nenhuma OS registrada ainda.")
            st.markdown("Clique na aba **➕ Nova Ordem** para criar a primeira!")
            return

        st.subheader("📋 Todas as Ordens de Serviço")
        
        # Filtros rápidos
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            filter_status_view = st.selectbox(
                "Filtrar por Status",
                ["Todos", "A realizar", "Realizando", "Concluído"],
                key="filter_status_moves"
            )
        
        with col_f2:
            search_client = st.text_input("🔍 Buscar cliente", placeholder="Digite o nome...")
        
        with col_f3:
            sort_by = st.selectbox("Ordenar por", ["Data (mais recente)", "Data (mais antiga)", "Cliente (A-Z)"])
        
        # Aplicar filtros
        filtered_moves = moves
        
        if filter_status_view != "Todos":
            filtered_moves = [m for m in filtered_moves if m.get('status') == filter_status_view]
        
        if search_client:
            residents = st.session_state.data['residents']
            filtered_moves = [m for m in filtered_moves 
                            if m.get('residentId') and 
                            search_client.lower() in get_name_by_id(residents, m.get('residentId')).lower()]
        
        # Ordenar
        if sort_by == "Data (mais recente)":
            filtered_moves = sorted(filtered_moves, key=lambda x: x.get('date', ''), reverse=True)
        elif sort_by == "Data (mais antiga)":
            filtered_moves = sorted(filtered_moves, key=lambda x: x.get('date', ''))
        else:  # Cliente A-Z
            residents = st.session_state.data['residents']
            filtered_moves = sorted(filtered_moves, 
                                  key=lambda x: get_name_by_id(residents, x.get('residentId')) if x.get('residentId') else 'ZZZ')
        
        st.divider()
        st.caption(f"📊 Mostrando {len(filtered_moves)} de {len(moves)} ordem(ns)")
        
        # Lista visual de OSs
        for move in filtered_moves:
            residents = st.session_state.data['residents']
            
            # Validar se move tem residentId
            if not move.get('residentId'):
                st.warning(f"⚠️ OS #{move.get('id', '?')} sem cliente vinculado")
                continue
            
            resident = next((r for r in residents if r.get('id') == move.get('residentId')), None)
            
            if not resident:
                continue
            
            # Emoji do status
            status_config = {
                'A realizar': {'emoji': '🟡', 'color': '#FFA726'},
                'Realizando': {'emoji': '🔵', 'color': '#42A5F5'},
                'Concluído': {'emoji': '🟢', 'color': '#66BB6A'}
            }
            
            status = move.get('status', 'A realizar')
            config = status_config.get(status, {'emoji': '⚪', 'color': '#999'})
            
            # Container da OS
            with st.container():
                # Cabeçalho da OS
                col_header1, col_header2, col_header3 = st.columns([3, 2, 1])
                
                with col_header1:
                    st.markdown(f"### {config['emoji']} OS #{move['id']} - {resident['name']}")
                
                with col_header2:
                    try:
                        move_date = datetime.strptime(str(move['date']), '%Y-%m-%d')
                        st.markdown(f"**📅 {move_date.strftime('%d/%m/%Y')}** às **🕐 {move.get('time', 'N/A')}**")
                    except:
                        st.markdown(f"**📅 {move.get('date', 'N/A')}** às **🕐 {move.get('time', 'N/A')}**")
                
                with col_header3:
                    st.markdown(f"**{status}**", help=f"Status atual da OS")
                
                # Detalhes e ações
                with st.expander("📋 Ver Detalhes e Editar", expanded=False):
                    col_det1, col_det2 = st.columns(2)
                    
                    with col_det1:
                        st.markdown("**📍 Endereços**")
                        st.write(f"**Origem:** {resident.get('originAddress', 'N/A')}, {resident.get('originNumber', '')}")
                        st.write(f"**Bairro:** {resident.get('originNeighborhood', 'N/A')}")
                        st.write(f"**Destino:** {resident.get('destAddress', 'N/A')}, {resident.get('destNumber', '')}")
                        st.write(f"**Bairro:** {resident.get('destNeighborhood', 'N/A')}")
                        
                        if resident.get('observation'):
                            st.markdown("**📝 Observações:**")
                            st.info(resident['observation'])
                    
                    with col_det2:
                        st.markdown("**👥 Equipe**")
                        
                        # Supervisor
                        sup_id = move.get('supervisorId')
                        if sup_id:
                            sup_name = get_name_by_id(st.session_state.data['staff'], sup_id)
                            st.write(f"🔧 **Supervisor:** {sup_name}")
                        
                        # Coordenador
                        coord_id = move.get('coordinatorId')
                        if coord_id:
                            coord_name = get_name_by_id(st.session_state.data['staff'], coord_id)
                            st.write(f"📋 **Coordenador:** {coord_name}")
                        
                        # Motorista
                        drv_id = move.get('driverId')
                        if drv_id:
                            drv_name = get_name_by_id(st.session_state.data['staff'], drv_id)
                            st.write(f"🚛 **Motorista:** {drv_name}")
                        
                        # Contato
                        if resident.get('contact'):
                            st.write(f"📞 **Contato:** {resident['contact']}")
                    
                    st.divider()
                    
                    # AÇÕES: Alterar Status e Volume
                    st.markdown("### ⚙️ Ações Rápidas")
                    
                    col_act1, col_act2, col_act3 = st.columns(3)
                    
                    with col_act1:
                        st.markdown("**📊 Alterar Status**")
                        new_status = st.selectbox(
                            "Novo status",
                            ["A realizar", "Realizando", "Concluído"],
                            index=["A realizar", "Realizando", "Concluído"].index(status),
                            key=f"status_{move['id']}",
                            label_visibility="collapsed"
                        )
                        
                        if st.button("✅ Atualizar Status", key=f"btn_status_{move['id']}", use_container_width=True):
                            if new_status != status:
                                updated_data = {
                                    'status': new_status
                                }
                                
                                # Se concluído, adicionar data/hora de conclusão
                                if new_status == "Concluído":
                                    updated_data['completionDate'] = str(datetime.now().date())
                                    updated_data['completionTime'] = str(datetime.now().time().strftime('%H:%M'))
                                
                                if update_move_details(move['id'], updated_data):
                                    st.session_state.data = fetch_all_data()
                                    st.toast(f"✅ Status alterado para: {new_status}")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao atualizar")
                            else:
                                st.info("Status não foi alterado")
                    
                    with col_act2:
                        st.markdown("**📦 Volume (m³)**")
                        current_volume = move.get('metragem', 0.0)
                        new_volume = st.number_input(
                            "Volume",
                            min_value=0.0,
                            step=0.5,
                            value=float(current_volume) if current_volume else 0.0,
                            key=f"volume_{move['id']}",
                            label_visibility="collapsed"
                        )
                        
                        if st.button("✅ Atualizar Volume", key=f"btn_volume_{move['id']}", use_container_width=True):
                            if new_volume != current_volume:
                                if update_move_details(move['id'], {'metragem': new_volume}):
                                    st.session_state.data = fetch_all_data()
                                    st.toast(f"✅ Volume atualizado: {new_volume} m³")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao atualizar")
                            else:
                                st.info("Volume não foi alterado")
                    
                    with col_act3:
                        st.markdown("**📅 Reagendar**")
                        new_date = st.date_input(
                            "Nova data",
                            value=datetime.strptime(str(move['date']), '%Y-%m-%d').date() if move.get('date') else datetime.now().date(),
                            key=f"date_{move['id']}",
                            label_visibility="collapsed"
                        )
                        
                        if st.button("✅ Reagendar", key=f"btn_date_{move['id']}", use_container_width=True):
                            if str(new_date) != str(move.get('date')):
                                if update_move_details(move['id'], {'date': str(new_date)}):
                                    st.session_state.data = fetch_all_data()
                                    st.toast(f"✅ Reagendado para: {new_date.strftime('%d/%m/%Y')}")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao atualizar")
                            else:
                                st.info("Data não foi alterada")
                
                st.markdown("---")
    
    with tab2:
        # CRIAR NOVA OS
        st.subheader("➕ Criar Nova Ordem de Serviço")
        
        scoped_residents = filter_by_scope(st.session_state.data['residents'])
        scoped_staff = filter_by_scope(st.session_state.data['staff'], key='id')
        
        if not scoped_residents:
            st.warning("⚠️ Nenhum morador cadastrado nesta base.")
            st.info("💡 Cadastre um morador primeiro na aba **🏠 Moradores**")
            return
        
        # Inicializar contador de formulários
        if 'manage_moves_form_key' not in st.session_state:
            st.session_state.manage_moves_form_key = 0

        with st.form(f"create_move_{st.session_state.manage_moves_form_key}"):
            st.markdown("#### 📋 Informações da OS")
            
            res_map = {r['name']: r['id'] for r in scoped_residents}
            res_name = st.selectbox("👤 Cliente *", list(res_map.keys()), 
                                    help="Selecione o morador/cliente desta mudança")
            
            st.divider()
            
            c1, c2 = st.columns(2)
            m_date = c1.date_input("📅 Data da Mudança *", help="Data prevista")
            m_time = c2.time_input("🕐 Hora *", help="Horário previsto")
            
            metragem = st.number_input("📦 Volume (m³)", 
                                       min_value=0.0, 
                                       step=0.5, 
                                       value=0.0,
                                       help="Volume estimado em metros cúbicos")
            
            st.divider()
            st.markdown("#### 👥 Equipe (Opcional)")
            
            supervisors = [s for s in scoped_staff if s['role'] in ['SUPERVISOR', 'ADMIN']]
            coordinators = [s for s in scoped_staff if s['role'] in ['COORDINATOR', 'ADMIN']]
            drivers = [s for s in scoped_staff if s['role'] in ['DRIVER']]
            
            sup_id = None
            coord_id = None
            drv_id = None
            
            col_sup, col_coord, col_drv = st.columns(3)
            
            with col_sup:
                if supervisors:
                    sup_options = ["Nenhum"] + [s['name'] for s in supervisors]
                    sup_name = st.selectbox("🔧 Supervisor", sup_options)
                    if sup_name != "Nenhum":
                        sup_id = next((s['id'] for s in supervisors if s['name'] == sup_name), None)
                else:
                    st.info("💡 Sem supervisor")
            
            with col_coord:
                if coordinators:
                    coord_options = ["Nenhum"] + [s['name'] for s in coordinators]
                    coord_name = st.selectbox("📋 Coordenador", coord_options)
                    if coord_name != "Nenhum":
                        coord_id = next((s['id'] for s in coordinators if s['name'] == coord_name), None)
                else:
                    st.info("💡 Sem coordenador")
            
            with col_drv:
                if drivers:
                    drv_options = ["Nenhum"] + [s['name'] for s in drivers]
                    drv_name = st.selectbox("🚛 Motorista", drv_options)
                    if drv_name != "Nenhum":
                        drv_id = next((s['id'] for s in drivers if s['name'] == drv_name), None)
                else:
                    st.info("💡 Sem motorista")
            
            st.divider()
            submit = st.form_submit_button("✅ Criar Ordem de Serviço", 
                                           type="primary", 
                                           use_container_width=True)
            
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
                    st.session_state.manage_moves_form_key += 1
                    
                    st.toast("🎉 OS criada com sucesso!", icon="✅")
                    st.success(f"""
                    ✅ **Ordem de Serviço criada com sucesso!**
                    
                    👤 Cliente: {res_name}
                    📅 Data: {m_date.strftime('%d/%m/%Y')}
                    🕐 Hora: {m_time.strftime('%H:%M')}
                    📦 Volume: {metragem} m³
                    📊 Status: A realizar
                    """)
                    
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("❌ Erro ao criar OS. Tente novamente.")
    
    with tab3:
        # LISTA DE MUDANÇAS AGENDADAS
        st.subheader("📅 Mudanças Agendadas")
        
        moves = filter_by_scope(st.session_state.data['moves'])
        
        if not moves:
            st.info("💡 Nenhuma mudança agendada.")
            return
        
        # Filtros
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            filter_status_agenda = st.selectbox(
                "Status",
                ["Todos", "A realizar", "Realizando", "Concluído"],
                key="filter_agenda_status"
            )
        
        with col_f2:
            filter_date_from = st.date_input(
                "De (Data)",
                value=None,
                key="filter_date_from"
            )
        
        with col_f3:
            filter_date_to = st.date_input(
                "Até (Data)",
                value=None,
                key="filter_date_to"
            )
        
        # Aplicar filtros
        filtered = moves
        
        if filter_status_agenda != "Todos":
            filtered = [m for m in filtered if m.get('status') == filter_status_agenda]
        
        if filter_date_from:
            filtered = [m for m in filtered if m.get('date') and str(m['date']) >= str(filter_date_from)]
        
        if filter_date_to:
            filtered = [m for m in filtered if m.get('date') and str(m['date']) <= str(filter_date_to)]
        
        # Ordenar por data
        filtered = sorted(filtered, key=lambda x: x.get('date', ''), reverse=False)
        
        st.caption(f"📊 {len(filtered)} mudança(s) agendada(s)")
        st.divider()
        
        # Agrupar por data
        moves_by_date = {}
        for move in filtered:
            date_str = move.get('date', 'Sem data')
            if date_str not in moves_by_date:
                moves_by_date[date_str] = []
            moves_by_date[date_str].append(move)
        
        # Mostrar por data
        for date_str, moves_list in moves_by_date.items():
            # Formatar data
            try:
                date_obj = datetime.strptime(str(date_str), '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d/%m/%Y - %A')
                
                # Verificar se é hoje
                if date_obj.date() == datetime.now().date():
                    formatted_date += " 🔥 HOJE"
                elif date_obj.date() < datetime.now().date():
                    formatted_date += " ⚠️ ATRASADA"
            except:
                formatted_date = str(date_str)
            
            st.markdown(f"### 📅 {formatted_date}")
            st.caption(f"{len(moves_list)} mudança(s) neste dia")
            
            # Listar mudanças deste dia
            for move in moves_list:
                residents = st.session_state.data['residents']
                resident = next((r for r in residents if r.get('id') == move.get('residentId')), None)
                
                if not resident:
                    continue
                
                # Status
                status_emoji = {
                    'A realizar': '🟡',
                    'Realizando': '🔵',
                    'Concluído': '🟢'
                }
                emoji = status_emoji.get(move.get('status', 'A realizar'), '⚪')
                
                # Card da mudança
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        st.markdown(f"{emoji} **{resident.get('name', 'N/A')}**")
                        if resident.get('contact'):
                            st.caption(f"📞 {resident['contact']}")
                    
                    with col2:
                        st.write(f"🕐 **{move.get('time', 'N/A')}**")
                        st.caption(f"OS #{move.get('id', '?')}")
                    
                    with col3:
                        st.write(f"📦 **{move.get('metragem', 0)} m³**")
                        st.caption(f"{move.get('status', 'N/A')}")
                    
                    with col4:
                        if st.button("👁️", key=f"view_agenda_{move['id']}", help="Ver detalhes"):
                            st.session_state[f"show_details_{move['id']}"] = not st.session_state.get(f"show_details_{move['id']}", False)
                            st.rerun()
                    
                    # Detalhes (se expandido)
                    if st.session_state.get(f"show_details_{move['id']}", False):
                        st.markdown("---")
                        
                        col_det1, col_det2 = st.columns(2)
                        
                        with col_det1:
                            st.markdown("**📍 Endereços:**")
                            st.write(f"**Origem:** {resident.get('originAddress', 'N/A')}, {resident.get('originNumber', '')}")
                            st.write(f"Bairro: {resident.get('originNeighborhood', 'N/A')}")
                            st.write(f"**Destino:** {resident.get('destAddress', 'N/A')}, {resident.get('destNumber', '')}")
                            st.write(f"Bairro: {resident.get('destNeighborhood', 'N/A')}")
                        
                        with col_det2:
                            st.markdown("**👥 Equipe:**")
                            
                            sup_id = move.get('supervisorId')
                            if sup_id:
                                sup_name = get_name_by_id(st.session_state.data['staff'], sup_id)
                                st.write(f"🔧 Supervisor: {sup_name}")
                            
                            coord_id = move.get('coordinatorId')
                            if coord_id:
                                coord_name = get_name_by_id(st.session_state.data['staff'], coord_id)
                                st.write(f"📋 Coordenador: {coord_name}")
                            
                            drv_id = move.get('driverId')
                            if drv_id:
                                drv_name = get_name_by_id(st.session_state.data['staff'], drv_id)
                                st.write(f"🚛 Motorista: {drv_name}")
                        
                        if resident.get('observation'):
                            st.markdown("**📝 Observações:**")
                            st.info(resident['observation'])
                    
                    st.markdown("---")
            
            st.divider()

# --- FORMULÁRIOS ---

def residents_form():
    st.title("🏠 Gestão de Moradores")
    
    # Tabs: Cadastrar novo OU Ver/Editar existentes
    tab1, tab2 = st.tabs(["➕ Cadastrar Novo", "📋 Ver e Editar"])
    
    with tab1:
        # CADASTRAR NOVO MORADOR
        st.subheader("➕ Novo Morador")
        
        # Inicializar contador de cadastros
        if 'resident_form_key' not in st.session_state:
            st.session_state.resident_form_key = 0
        
        with st.form(f"new_resident_{st.session_state.resident_form_key}"):
            st.markdown("#### 📝 Dados do Cliente")
            name = st.text_input("Nome Completo *", placeholder="Digite o nome completo...")
            c1, c2 = st.columns(2)
            selo = c1.text_input("Selo / ID", placeholder="Ex: A123")
            contact = c2.text_input("Telefone / Contato", placeholder="(00) 00000-0000")
            
            st.markdown("#### 📍 Origem")
            c3, c4 = st.columns([3, 1])
            orig_addr = c3.text_input("Endereço (Origem)", placeholder="Rua, Avenida...")
            orig_num = c4.text_input("Nº (Origem)", placeholder="123")
            orig_bairro = st.text_input("Bairro (Origem)", placeholder="Nome do bairro")
            
            st.markdown("#### 🎯 Destino")
            c5, c6 = st.columns([3, 1])
            dest_addr = c5.text_input("Endereço (Destino)", placeholder="Rua, Avenida...")
            dest_num = c6.text_input("Nº (Destino)", placeholder="456")
            dest_bairro = st.text_input("Bairro (Destino)", placeholder="Nome do bairro")
            
            obs = st.text_area("Observações", placeholder="Informações adicionais...")
            
            st.markdown("#### 📅 Previsão")
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
                if sec_options:
                    selected_sec_name = st.selectbox("Vincular à Secretária", list(sec_options.keys()))
                    if selected_sec_name: 
                        sec_id = sec_options[selected_sec_name]

            submit = st.form_submit_button("✅ Salvar Morador", type="primary", use_container_width=True)
            
            if submit:
                if not name:
                    st.error("⚠️ Nome é obrigatório.")
                else:
                    # Garantir secretaryId válido
                    if sec_id is None:
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
                        
                        st.toast("🎉 Morador cadastrado!", icon="✅")
                        st.success(f"✅ **{name}** cadastrado(a) com sucesso!\n\n📍 Origem: {orig_addr or 'N/A'}\n🎯 Destino: {dest_addr or 'N/A'}")
                        
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Erro ao cadastrar morador.")
    
    with tab2:
        # VER E EDITAR MORADORES EXISTENTES
        st.subheader("📋 Moradores Cadastrados")
        
        residents = filter_by_scope(st.session_state.data['residents'])
        
        if not residents:
            st.info("💡 Nenhum morador cadastrado ainda.")
            return
        
        # Filtro de busca
        search_resident = st.text_input("🔍 Buscar morador", placeholder="Digite o nome...")
        
        # Filtrar
        if search_resident:
            residents = [r for r in residents if search_resident.lower() in r.get('name', '').lower()]
        
        st.caption(f"📊 Mostrando {len(residents)} morador(es)")
        st.divider()
        
        # Listar moradores
        for resident in residents:
            with st.container():
                col_header1, col_header2 = st.columns([3, 1])
                
                with col_header1:
                    st.markdown(f"### 👤 {resident.get('name', 'Sem nome')}")
                    if resident.get('contact'):
                        st.caption(f"📞 {resident['contact']}")
                
                with col_header2:
                    if resident.get('selo'):
                        st.markdown(f"**ID:** {resident['selo']}")
                
                with st.expander("📋 Ver Detalhes e Editar", expanded=False):
                    # Detalhes atuais
                    col_det1, col_det2 = st.columns(2)
                    
                    with col_det1:
                        st.markdown("**📍 Endereços**")
                        st.write(f"**Origem:**")
                        st.write(f"  {resident.get('originAddress', 'N/A')}, {resident.get('originNumber', '')}")
                        st.write(f"  {resident.get('originNeighborhood', 'N/A')}")
                        st.write(f"**Destino:**")
                        st.write(f"  {resident.get('destAddress', 'N/A')}, {resident.get('destNumber', '')}")
                        st.write(f"  {resident.get('destNeighborhood', 'N/A')}")
                    
                    with col_det2:
                        st.markdown("**📅 Previsão de Mudança**")
                        if resident.get('moveDate'):
                            try:
                                move_dt = datetime.strptime(str(resident['moveDate']), '%Y-%m-%d')
                                st.write(f"📅 {move_dt.strftime('%d/%m/%Y')}")
                            except:
                                st.write(f"📅 {resident.get('moveDate', 'N/A')}")
                        
                        if resident.get('moveTime'):
                            st.write(f"🕐 {resident['moveTime']}")
                        
                        if resident.get('observation'):
                            st.markdown("**📝 Observações:**")
                            st.info(resident['observation'])
                    
                    st.divider()
                    
                    # AÇÕES: Editar e Excluir
                    st.markdown("### ⚙️ Ações")
                    
                    col_act1, col_act2 = st.columns([3, 1])
                    
                    with col_act1:
                        # Formulário de edição rápida
                        with st.form(f"edit_resident_{resident['id']}"):
                            st.markdown("**✏️ Editar Informações**")
                            
                            col_e1, col_e2 = st.columns(2)
                            
                            new_name = col_e1.text_input("Nome", value=resident.get('name', ''))
                            new_contact = col_e2.text_input("Telefone", value=resident.get('contact', ''))
                            
                            new_obs = st.text_area("Observações", value=resident.get('observation', ''))
                            
                            if st.form_submit_button("✅ Salvar Alterações", use_container_width=True):
                                # Atualizar no banco (precisa criar função update_resident)
                                updated_data = {
                                    'name': new_name,
                                    'contact': new_contact,
                                    'observation': new_obs
                                }
                                
                                # Por enquanto, usar connection para update
                                try:
                                    conn = get_connection()
                                    if conn:
                                        cur = conn.cursor()
                                        cur.execute("""
                                            UPDATE residents 
                                            SET name = %s, contact = %s, observation = %s
                                            WHERE id = %s
                                        """, (new_name, new_contact, new_obs, resident['id']))
                                        conn.commit()
                                        cur.close()
                                        conn.close()
                                        
                                        st.session_state.data = fetch_all_data()
                                        st.toast(f"✅ {new_name} atualizado!")
                                        time.sleep(0.5)
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erro ao atualizar: {str(e)}")
                    
                    with col_act2:
                        st.markdown("**🗑️ Excluir**")
                        st.caption("⚠️ Ação irreversível!")
                        
                        # Verificar se tem OSs vinculadas ANTES do botão
                        moves_vinculadas = [m for m in st.session_state.data['moves'] if m.get('residentId') == resident['id']]
                        
                        if moves_vinculadas:
                            # TEM OSs - mostrar bloqueio
                            st.error(f"❌ Não pode excluir")
                            st.caption(f"{len(moves_vinculadas)} OS(s) vinculada(s)")
                            
                            # Botão desabilitado
                            st.button("🗑️ Excluir Morador", 
                                     key=f"delete_{resident['id']}", 
                                     type="secondary", 
                                     use_container_width=True,
                                     disabled=True,
                                     help="Exclua as OSs vinculadas primeiro")
                            
                            # Mostrar as OSs vinculadas
                            with st.expander("📋 Ver OSs vinculadas"):
                                for move in moves_vinculadas:
                                    try:
                                        move_date = datetime.strptime(str(move.get('date')), '%Y-%m-%d')
                                        date_str = move_date.strftime('%d/%m/%Y')
                                    except:
                                        date_str = str(move.get('date', 'N/A'))
                                    
                                    st.write(f"• OS #{move.get('id')} - {date_str} - Status: {move.get('status', 'N/A')}")
                        else:
                            # NÃO TEM OSs - pode excluir
                            if st.button("🗑️ Excluir Morador", 
                                        key=f"delete_{resident['id']}", 
                                        type="secondary", 
                                        use_container_width=True):
                                st.session_state[f"confirm_delete_{resident['id']}"] = True
                                st.rerun()
                        
                        # Confirmação (só aparece se não tem OSs vinculadas)
                        if st.session_state.get(f"confirm_delete_{resident['id']}", False):
                            st.warning("⚠️ Tem certeza?")
                            col_conf1, col_conf2 = st.columns(2)
                            
                            with col_conf1:
                                if st.button("✅ Sim", key=f"yes_{resident['id']}", use_container_width=True):
                                    try:
                                        conn = get_connection()
                                        if conn:
                                            cur = conn.cursor()
                                            cur.execute("DELETE FROM residents WHERE id = %s", (resident['id'],))
                                            conn.commit()
                                            cur.close()
                                            conn.close()
                                            
                                            # Limpar confirmação
                                            del st.session_state[f"confirm_delete_{resident['id']}"]
                                            
                                            st.session_state.data = fetch_all_data()
                                            st.toast(f"🗑️ {resident.get('name', 'Morador')} excluído!")
                                            time.sleep(0.5)
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao excluir: {str(e)}")
                            
                            with col_conf2:
                                if st.button("❌ Não", key=f"no_{resident['id']}", use_container_width=True):
                                    del st.session_state[f"confirm_delete_{resident['id']}"]
                                    st.rerun()
                
                st.markdown("---")

def schedule_form():
    st.title("🗓️ Agendamento de OS")
    
    scoped_residents = filter_by_scope(st.session_state.data['residents'])
    scoped_staff = filter_by_scope(st.session_state.data['staff'], key='id')
    
    if not scoped_residents:
        st.warning("⚠️ Nenhum morador cadastrado nesta base.")
        st.info("💡 Cadastre um morador primeiro na aba **🏠 Moradores**")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("➕ Ir para Cadastro", type="primary", use_container_width=True):
                st.info("👆 Clique na aba '🏠 Moradores' no menu acima")
        return
    
    # Inicializar contador de formulários
    if 'schedule_form_key' not in st.session_state:
        st.session_state.schedule_form_key = 0

    with st.form(f"new_move_{st.session_state.schedule_form_key}"):
        st.subheader("📋 Informações da Mudança")
        
        res_map = {r['name']: r['id'] for r in scoped_residents}
        res_name = st.selectbox("👤 Morador *", list(res_map.keys()), 
                                help="Selecione o morador desta mudança")
        
        st.divider()
        
        c1, c2 = st.columns(2)
        m_date = c1.date_input("📅 Data da Mudança *", help="Data prevista para a mudança")
        m_time = c2.time_input("🕐 Hora *", help="Horário previsto")
        
        metragem = st.number_input("📦 Volume (m³)", 
                                   min_value=0.0, 
                                   step=0.5, 
                                   value=0.0,
                                   help="Volume estimado da mudança")
        
        st.divider()
        st.subheader("👥 Equipe (Opcional)")
        
        supervisors = [s for s in scoped_staff if s['role'] in ['SUPERVISOR', 'ADMIN']]
        coordinators = [s for s in scoped_staff if s['role'] in ['COORDINATOR', 'ADMIN']]
        drivers = [s for s in scoped_staff if s['role'] in ['DRIVER']]
        
        sup_id = None
        coord_id = None
        drv_id = None
        
        if supervisors:
            sup_options = ["Nenhum"] + [s['name'] for s in supervisors]
            sup_name = st.selectbox("🔧 Supervisor", sup_options)
            if sup_name != "Nenhum":
                sup_id = next((s['id'] for s in supervisors if s['name'] == sup_name), None)
        else:
            st.info("💡 Nenhum supervisor cadastrado")
        
        if coordinators:
            coord_options = ["Nenhum"] + [s['name'] for s in coordinators]
            coord_name = st.selectbox("📋 Coordenador", coord_options)
            if coord_name != "Nenhum":
                coord_id = next((s['id'] for s in coordinators if s['name'] == coord_name), None)
        else:
            st.info("💡 Nenhum coordenador cadastrado")
        
        if drivers:
            drv_options = ["Nenhum"] + [s['name'] for s in drivers]
            drv_name = st.selectbox("🚛 Motorista", drv_options)
            if drv_name != "Nenhum":
                drv_id = next((s['id'] for s in drivers if s['name'] == drv_name), None)
        else:
            st.info("💡 Nenhum motorista cadastrado")
        
        st.divider()
        submit = st.form_submit_button("✅ Agendar Mudança", 
                                       type="primary", 
                                       use_container_width=True)
        
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
                st.session_state.schedule_form_key += 1
                
                st.toast("🎉 OS agendada com sucesso!", icon="✅")
                st.success(f"""
                ✅ **Mudança agendada com sucesso!**
                
                👤 Cliente: {res_name}
                📅 Data: {m_date.strftime('%d/%m/%Y')}
                🕐 Hora: {m_time.strftime('%H:%M')}
                📦 Volume: {metragem} m³
                """)
                
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("❌ Erro ao agendar mudança. Tente novamente.")

def staff_management():
    st.title("👥 Recursos Humanos")
    
    # Inicializar contador de cadastros na sessão
    if 'staff_form_key' not in st.session_state:
        st.session_state.staff_form_key = 0
    
    # Formulário de cadastro com key dinâmica para reset
    with st.form(f"new_staff_{st.session_state.staff_form_key}"):
        st.subheader("➕ Cadastrar Novo Funcionário")
        
        name = st.text_input("Nome Completo", placeholder="Digite o nome completo...")
        email = st.text_input("Login (Email)", placeholder="exemplo@telemim.com")
        password = st.text_input("Senha", type="password", placeholder="Deixe vazio para senha padrão: 123")
        
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

        submit = st.form_submit_button("✅ Cadastrar Funcionário", type="primary", use_container_width=True)
        
        if submit:
            if name and email:
                role_permission = role_map[role_name]['permission']
                if insert_staff(name, email, password or '123', role_permission, role_name, sec_id):
                    # Atualizar dados
                    st.session_state.data = fetch_all_data()
                    
                    # Incrementar key do formulário para resetá-lo
                    st.session_state.staff_form_key += 1
                    
                    # Notificação toast
                    st.toast("🎉 Cadastro concluído com sucesso!", icon="✅")
                    
                    # Mensagem de sucesso adicional
                    st.success(f"✅ **{name}** cadastrado(a) com sucesso!\\n\\n📧 Login: `{email}`\\n🔑 Senha: `{password or '123'}`")
                    
                    # Aguardar um pouco para mostrar a mensagem
                    time.sleep(1)
                    
                    # Recarregar para limpar o formulário
                    st.rerun()
                else:
                    st.error("❌ Erro ao cadastrar funcionário no banco de dados.")
            elif not name:
                st.error("⚠️ Nome é obrigatório")
            elif not email:
                st.error("⚠️ Email é obrigatório")
    
    st.divider()
    
    # Lista de funcionários cadastrados
    st.subheader("📋 Funcionários Cadastrados")
    
    scoped_staff = filter_by_scope(st.session_state.data['staff'], key='id')
    
    if scoped_staff:
        df = pd.DataFrame(scoped_staff)
        available_cols = df.columns.tolist()
        preferred_cols = ['id', 'name', 'email', 'role']
        display_cols = [col for col in preferred_cols if col in available_cols]
        
        if display_cols:
            if 'role' in df.columns:
                df['role_display'] = df['role'].apply(lambda x: ROLES.get(x, x))
            
            for idx, row in df.iterrows():
                with st.expander(f"👤 {row['name']} - {row.get('role_display', row.get('role', 'N/A'))}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        with st.form(f"edit_staff_{row['id']}_{idx}"):
                            st.write("**Editar Informações:**")
                            
                            new_name = st.text_input("Nome", value=row.get('name', ''))
                            new_email = st.text_input("Email", value=row.get('email', ''))
                            
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
                                index=role_index
                            )
                            
                            col_btn1, col_btn2 = st.columns(2)
                            
                            with col_btn1:
                                save_btn = st.form_submit_button("💾 Salvar", type="primary", use_container_width=True)
                            
                            if save_btn:
                                new_role = next((key for key, value in ROLES.items() if value == new_role_display), current_role)
                                
                                if update_staff_details(row['id'], new_name, '', new_email, new_role):
                                    st.toast(f"✅ {new_name} atualizado!", icon="💾")
                                    st.success(f"✅ **{new_name}** atualizado com sucesso!")
                                    st.session_state.data = fetch_all_data()
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao atualizar")
                    
                    with col2:
                        st.write("**Ações:**")
                        st.write("")
                        
                        if st.button(f"🗑️ Deletar", key=f"del_{row['id']}", type="secondary", use_container_width=True):
                            # Verificar se tem OSs vinculadas como supervisor, coordenador ou motorista
                            moves_supervisor = [m for m in st.session_state.data['moves'] if m.get('supervisorId') == row['id']]
                            moves_coordinator = [m for m in st.session_state.data['moves'] if m.get('coordinatorId') == row['id']]
                            moves_driver = [m for m in st.session_state.data['moves'] if m.get('driverId') == row['id']]
                            
                            total_moves = len(moves_supervisor) + len(moves_coordinator) + len(moves_driver)
                            
                            if total_moves > 0:
                                st.error(f"❌ Não é possível excluir!")
                                st.warning(f"⚠️ Este funcionário está vinculado a **{total_moves} OS(s)**.")
                                st.info("💡 **Solução:** Altere ou exclua as OSs vinculadas primeiro.")
                                
                                # Mostrar detalhes
                                with st.expander("📋 Ver OSs vinculadas"):
                                    if moves_supervisor:
                                        st.write(f"**Como Supervisor:** {len(moves_supervisor)} OS(s)")
                                    if moves_coordinator:
                                        st.write(f"**Como Coordenador:** {len(moves_coordinator)} OS(s)")
                                    if moves_driver:
                                        st.write(f"**Como Motorista:** {len(moves_driver)} OS(s)")
                            else:
                                st.session_state[f'confirm_delete_{row["id"]}'] = True
                                st.rerun()
                        
                        if st.session_state.get(f'confirm_delete_{row["id"]}', False):
                            st.warning("⚠️ Confirmar exclusão?")
                            col_yes, col_no = st.columns(2)
                            
                            with col_yes:
                                if st.button("Sim", key=f"yes_{row['id']}", use_container_width=True):
                                    if delete_staff(row['id']):
                                        st.toast(f"🗑️ {row['name']} deletado!", icon="✅")
                                        st.success(f"✅ **{row['name']}** deletado com sucesso!")
                                        st.session_state.data = fetch_all_data()
                                        if f'confirm_delete_{row["id"]}' in st.session_state:
                                            del st.session_state[f'confirm_delete_{row["id"]}']
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("❌ Erro ao deletar")
                            
                            with col_no:
                                if st.button("Não", key=f"no_{row['id']}", use_container_width=True):
                                    if f'confirm_delete_{row["id"]}' in st.session_state:
                                        del st.session_state[f'confirm_delete_{row["id"]}']
                                    st.rerun()
                        
                        st.caption(f"ID: {row['id']}")
            
            st.caption(f"📊 Total: {len(scoped_staff)} funcionário(s)")
        else:
            st.error("Nenhuma coluna válida para exibir.")
    else:
        st.info("💡 Nenhum funcionário cadastrado no seu escopo ainda.")

def manage_secretaries():
    st.title("🏢 Gestão de Secretarias")
    
    # Inicializar contador
    if 'secretary_form_key' not in st.session_state:
        st.session_state.secretary_form_key = 0
    
    # Formulário de cadastro
    st.subheader("➕ Cadastrar Nova Secretaria")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        name = st.text_input("Nome da Secretaria / Base", 
                            placeholder="Ex: Matriz, Filial Sul...",
                            key=f"sec_name_{st.session_state.secretary_form_key}")
    
    with col2:
        st.write("")
        st.write("")
        if st.button("✅ Criar Base", type="primary", use_container_width=True):
            if name:
                login = name.lower().replace(" ", "") + "@telemim.com"
                if insert_staff(name, login, '123', 'SECRETARY', 'Secretária', None, name):
                    st.session_state.data = fetch_all_data()
                    st.session_state.secretary_form_key += 1
                    
                    st.toast("🎉 Secretaria criada com sucesso!", icon="✅")
                    st.success(f"✅ **{name}** criada com sucesso!\\n\\n📧 Login: `{login}`\\n🔑 Senha: `123`")
                    
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Erro ao cadastrar Secretária no banco de dados.")
            else:
                st.error("⚠️ Nome da Secretaria / Base é obrigatório.")
    
    st.divider()
    
    # Lista de secretarias cadastradas
    st.subheader("📋 Secretarias Cadastradas")
    
    secretaries = [s for s in st.session_state.data['staff'] if s['role'] == 'SECRETARY']
    
    if secretaries:
        df = pd.DataFrame(secretaries)
        available_cols = df.columns.tolist()
        preferred_cols = ['id', 'name', 'branchName', 'email']
        display_cols = [col for col in preferred_cols if col in available_cols]
        
        if display_cols:
            df_display = df[display_cols].copy()
            
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
            
            st.dataframe(
                df_display,
                column_config=column_config,
                hide_index=True,
                use_container_width=True
            )
            
            st.caption(f"📊 Total de secretarias: {len(secretaries)}")
        else:
            st.warning("Dados incompletos na tabela de secretarias.")
    else:
        st.info("💡 Nenhuma secretaria cadastrada ainda.")

def manage_roles():
    st.title("🛡️ Gestão de Cargos")
    
    st.info("Cargos padrão do sistema. Para adicionar novos cargos, contate o administrador.")
    
    if st.button("Adicionar Novo Cargo (Admin)", type="secondary"):
        name = st.text_input("Nome do Cargo")
        perm = st.selectbox("Permissão", list(ROLES.keys()))
        
        if st.button("Criar"):
            if name:
                perm_key = next(key for key, value in ROLES.items() if value == perm)
                st.session_state.data['roles'].append({'id': int(time.time()), 'name': name, 'permission': perm_key})
                st.success("Cargo criado.")
            
    st.table(pd.DataFrame(st.session_state.data['roles']))

def reports_page():
    """Página de relatórios simples (legacy)"""
    st.title("📈 Relatórios")
    st.info("Use o menu 'Relatórios' para acessar analytics avançados")

# --- NAVEGAÇÃO PRINCIPAL ---

if not st.session_state.user:
    login_screen()
else:
    user = st.session_state.user
    
    # Mapeamento de Opções com Ícones
    menu_map = {
        "Gerenciamento": {"icon": "📊", "func": dashboard},
        "Ordens de Serviço": {"icon": "📦", "func": manage_moves},
        "Calendário": {"icon": "📅", "func": calendar_view},
        "Notificações": {"icon": "🔔", "func": notifications_center},
        "Moradores": {"icon": "🏠", "func": residents_form},
        "Agendamento": {"icon": "📅", "func": schedule_form},
        "Funcionários": {"icon": "👥", "func": staff_management},
        "Secretarias": {"icon": "🏢", "func": manage_secretaries},
        "Cargos": {"icon": "🛡️", "func": manage_roles},
        "Relatórios": {"icon": "📈", "func": reports_analytics_page},
    }
    
    # Regras de Menu Dinâmico
    options = ["Gerenciamento", "Ordens de Serviço", "Calendário", "Notificações"]
    can_schedule = user['role'] in ['ADMIN', 'SECRETARY', 'COORDINATOR', 'SUPERVISOR']
    
    if can_schedule:
        options.extend(["Moradores", "Agendamento"])
        
    if user['role'] == 'ADMIN':
        options.extend(["Funcionários", "Cargos", "Secretarias", "Relatórios"])
    elif user['role'] == 'SECRETARY':
        options.extend(["Funcionários", "Relatórios"])
        
    # Criação da Lista de Opções para o Menu
    menu_options = [op for op in options if op in menu_map]
    
    # Sidebar com logo e usuário
    with st.sidebar:
        # Logo pequena
        try:
            st.image("Telemim_logo.png", use_container_width=True)
        except:
            st.markdown("### 🚛 TELEMIM")
        
        st.markdown("---")
        
        st.markdown(f"### 👤 {user['name']}")
        st.caption(f"🎯 {user.get('jobTitle', ROLES.get(user['role'], user['role']))}")
        
        # Badge de notificações
        unread = notification_badge()
        if unread > 0:
            st.warning(f"🔔 {unread} notificação(ões) não lida(s)")
        
        st.divider()
        
        if st.button("🚪 Sair", type="primary", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    
    # Menu horizontal no topo
    st.markdown("---")
    
    # Criar abas com ícones e nomes
    tab_labels = [f"{menu_map[op]['icon']} {op}" for op in menu_options]
    tabs = st.tabs(tab_labels)
    
    # Renderizar cada aba
    for i, option in enumerate(menu_options):
        with tabs[i]:
            menu_map[option]['func']()
