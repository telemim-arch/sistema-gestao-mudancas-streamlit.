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
                        
                        # Botão clicável no dia
                        if st.button(f"{emoji} **{day}**", 
                                   key=f"day_{day}_{month}_{year}",
                                   use_container_width=True,
                                   help=f"{len(day_moves)} mudança(s) - Clique para detalhes"):
                            st.session_state['selected_day'] = day
                            st.session_state['selected_month'] = month
                            st.session_state['selected_year'] = year
                            st.session_state['selected_moves'] = day_moves
                            st.rerun()
                        
                        st.caption(f"{len(day_moves)} OS", unsafe_allow_html=False)
                    else:
                        st.markdown(f"### {day}")
    
    # Mostrar detalhes do dia selecionado
    if (st.session_state.get('selected_day') and 
        st.session_state.get('selected_month') == month and
        st.session_state.get('selected_year') == year and
        st.session_state.get('selected_moves')):
        
        st.markdown("---")
        st.subheader(f"📋 Mudanças do dia {st.session_state['selected_day']}/{month}/{year}")
        
        if st.button("❌ Fechar Detalhes"):
            del st.session_state['selected_day']
            del st.session_state['selected_moves']
            st.rerun()
        
        for move in st.session_state['selected_moves']:
            # Buscar resident (ambos formatos)
            resident = next((r for r in st.session_state.data['residents'] 
                           if r['id'] == move.get('residentId') 
                           or r['id'] == move.get('residentid')), None)
            
            if resident:
                status_color = {
                    'A realizar': '🟡',
                    'Realizando': '🔵',
                    'Concluído': '🟢'
                }
                emoji = status_color.get(move.get('status'), '⚪')
                
                with st.expander(f"{emoji} {move.get('time', 'N/A')} - {resident['name']} - OS #{move['id']}", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**Status:** {move.get('status', 'N/A')}")
                        st.write(f"**Hora:** {move.get('time', 'N/A')}")
                        st.write(f"**Volume:** {move.get('metragem', 0)} m³")
                    
                    with col2:
                        origin = resident.get('originAddress', 'N/A')
                        if resident.get('originNumber'):
                            origin += f", {resident['originNumber']}"
                        st.write(f"**Origem:** {origin}")
                        
                        dest = resident.get('destAddress', 'N/A')
                        if resident.get('destNumber'):
                            dest += f", {resident['destNumber']}"
                        st.write(f"**Destino:** {dest}")
                    
                    with col3:
                        st.write(f"**Contato:** {resident.get('contact', 'N/A')}")
                        
                        # Equipe
                        staff_data = st.session_state.data.get('staff', [])
                        if move.get('supervisorId') or move.get('supervisorid'):
                            sup_id = move.get('supervisorId') or move.get('supervisorid')
                            sup = next((s for s in staff_data if s['id'] == sup_id), None)
                            if sup:
                                st.write(f"**Supervisor:** {sup['name']}")
                        
                        if move.get('driverId') or move.get('driverid'):
                            drv_id = move.get('driverId') or move.get('driverid')
                            drv = next((s for s in staff_data if s['id'] == drv_id), None)
                            if drv:
                                st.write(f"**Motorista:** {drv['name']}")

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
        # Buscar resident (ambos formatos de ID)
        resident = next((r for r in all_residents if r['id'] == move.get('residentId') 
                        or r['id'] == move.get('residentid')), None)
        
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
    st.title("📦 Ordens de Serviço e Agendamento")
    
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
            resident_id = move.get('residentId') or move.get('residentid')
            
            if not resident_id:
                # OS sem cliente - mostrar card de erro
                st.error(f"⚠️ **OS #{move.get('id', '?')} SEM CLIENTE VINCULADO**")
                
                col_warn1, col_warn2 = st.columns([3, 1])
                
                with col_warn1:
                    st.caption(f"📅 Data: {move.get('date', 'N/A')} • 🕐 Hora: {move.get('time', 'N/A')} • Status: {move.get('status', 'N/A')}")
                    st.caption("💡 Esta OS foi criada sem vincular um cliente. Execute o SQL de limpeza no Supabase para remover.")
                
                with col_warn2:
                    if st.button("📋 Ver SQL", key=f"sql_orphan_{move['id']}", use_container_width=True):
                        st.code(f"DELETE FROM moves WHERE id = {move['id']};", language="sql")
                
                st.divider()
                continue
            
            # Buscar cliente
            resident = next((r for r in residents if r.get('id') == resident_id), None)
            
            if not resident:
                st.warning(f"⚠️ OS #{move.get('id', '?')} vinculada ao cliente ID {resident_id}, mas cliente não encontrado no banco.")
                st.caption("💡 Cliente pode ter sido excluído. Execute SQL para limpar: `DELETE FROM moves WHERE id = {move['id']};`")
                st.divider()
                continue
            
            # Configuração de cores por status
            status_config = {
                'A realizar': {
                    'emoji': '🟡',
                    'color': '#FFA726',
                    'bg': 'linear-gradient(135deg, #FFF9C4 0%, #FFFFFF 100%)',
                    'border': '#FFA726'
                },
                'Realizando': {
                    'emoji': '🔵',
                    'color': '#42A5F5',
                    'bg': 'linear-gradient(135deg, #E3F2FD 0%, #FFFFFF 100%)',
                    'border': '#42A5F5'
                },
                'Concluído': {
                    'emoji': '🟢',
                    'color': '#66BB6A',
                    'bg': 'linear-gradient(135deg, #E8F5E9 0%, #FFFFFF 100%)',
                    'border': '#66BB6A'
                }
            }
            
            status = move.get('status', 'A realizar')
            config = status_config.get(status, {
                'emoji': '⚪',
                'color': '#999',
                'bg': '#F5F5F5',
                'border': '#999'
            })
            
            # CARD MODERNO
            st.markdown(f"""
            <div style="
                background: {config['bg']};
                border-left: 8px solid {config['border']};
                border-radius: 15px;
                padding: 25px;
                margin-bottom: 20px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                transition: all 0.3s ease;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h2 style="margin: 0; color: #333; font-size: 24px;">
                        {config['emoji']} OS #{move['id']} - {resident['name']}
                    </h2>
                    <div style="background: {config['color']}; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 14px;">
                        {status.upper()}
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 15px;">
                    <div>
                        <span style="color: #666; font-size: 13px;">📅 Data</span><br>
                        <span style="color: #333; font-weight: bold; font-size: 16px;">{datetime.strptime(str(move['date']), '%Y-%m-%d').strftime('%d/%m/%Y') if move.get('date') else 'N/A'}</span>
                    </div>
                    <div>
                        <span style="color: #666; font-size: 13px;">🕐 Horário</span><br>
                        <span style="color: #333; font-weight: bold; font-size: 16px;">{move.get('time', 'N/A')}</span>
                    </div>
                    <div>
                        <span style="color: #666; font-size: 13px;">📦 Volume</span><br>
                        <span style="color: #333; font-weight: bold; font-size: 16px;">{move.get('metragem', 0)} m³</span>
                    </div>
                    <div>
                        <span style="color: #666; font-size: 13px;">📞 Contato</span><br>
                        <span style="color: #333; font-weight: bold; font-size: 16px;">{resident.get('contact', 'Sem contato')}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # BARRA DE AÇÕES RÁPIDAS
            col_act1, col_act2, col_act3, col_act4, col_act5 = st.columns(5)
            
            with col_act1:
                # Edição Rápida de Status
                if st.button("📊 Status", key=f"quick_status_{move['id']}", use_container_width=True, help="Alterar status rapidamente"):
                    st.session_state[f"edit_status_{move['id']}"] = not st.session_state.get(f"edit_status_{move['id']}", False)
                    st.rerun()
            
            with col_act2:
                # Edição Rápida de Volume
                if st.button("📦 Volume", key=f"quick_volume_{move['id']}", use_container_width=True, help="Alterar volume"):
                    st.session_state[f"edit_volume_{move['id']}"] = not st.session_state.get(f"edit_volume_{move['id']}", False)
                    st.rerun()
            
            with col_act3:
                # Ver Detalhes Completos
                if st.button("📋 Detalhes", key=f"details_{move['id']}", use_container_width=True, help="Ver detalhes completos"):
                    st.session_state[f"show_details_{move['id']}"] = not st.session_state.get(f"show_details_{move['id']}", False)
                    st.rerun()
            
            with col_act4:
                # Compartilhar (copiar info)
                if st.button("📤 Compartilhar", key=f"share_{move['id']}", use_container_width=True, help="Copiar informações"):
                    share_text = f"""
📦 MUDANÇA TELEMIM

👤 Cliente: {resident['name']}
📅 Data: {datetime.strptime(str(move['date']), '%Y-%m-%d').strftime('%d/%m/%Y') if move.get('date') else 'N/A'}
🕐 Horário: {move.get('time', 'N/A')}
📦 Volume: {move.get('metragem', 0)} m³
📞 Contato: {resident.get('contact', 'Sem contato')}

📍 Origem: {resident.get('originAddress', 'N/A')}, {resident.get('originNumber', '')} - {resident.get('originNeighborhood', 'N/A')}
📍 Destino: {resident.get('destAddress', 'N/A')}, {resident.get('destNumber', '')} - {resident.get('destNeighborhood', 'N/A')}

Status: {status}
OS #{move['id']}
                    """.strip()
                    st.code(share_text, language=None)
                    st.toast("✅ Informações prontas para copiar!", icon="📋")
            
            with col_act5:
                # Excluir OS (com confirmação)
                if st.button("🗑️ Excluir", key=f"delete_{move['id']}", use_container_width=True, type="secondary", help="Excluir esta OS"):
                    st.session_state[f"confirm_delete_{move['id']}"] = True
                    st.rerun()
            
            # MODAL DE EDIÇÃO DE STATUS
            if st.session_state.get(f"edit_status_{move['id']}", False):
                with st.container():
                    st.markdown("---")
                    st.markdown(f"### 📊 Alterar Status - OS #{move['id']}")
                    
                    col_s1, col_s2, col_s3 = st.columns([2, 2, 1])
                    
                    with col_s1:
                        new_status = st.selectbox(
                            "Novo Status",
                            ["A realizar", "Realizando", "Concluído"],
                            index=["A realizar", "Realizando", "Concluído"].index(status),
                            key=f"new_status_{move['id']}"
                        )
                    
                    with col_s2:
                        if st.button("✅ Confirmar", key=f"confirm_status_{move['id']}", type="primary", use_container_width=True):
                            if new_status != status:
                                updated_data = {'status': new_status}
                                if new_status == "Concluído":
                                    updated_data['completionDate'] = str(datetime.now().date())
                                    updated_data['completionTime'] = str(datetime.now().time().strftime('%H:%M'))
                                
                                if update_move_details(move['id'], updated_data):
                                    st.session_state.data = fetch_all_data()
                                    st.session_state[f"edit_status_{move['id']}"] = False
                                    st.toast(f"✅ Status atualizado: {new_status}")
                                    time.sleep(0.5)
                                    st.rerun()
                    
                    with col_s3:
                        if st.button("❌ Cancelar", key=f"cancel_status_{move['id']}", use_container_width=True):
                            st.session_state[f"edit_status_{move['id']}"] = False
                            st.rerun()
                    
                    st.markdown("---")
            
            # MODAL DE EDIÇÃO DE VOLUME
            if st.session_state.get(f"edit_volume_{move['id']}", False):
                with st.container():
                    st.markdown("---")
                    st.markdown(f"### 📦 Alterar Volume - OS #{move['id']}")
                    
                    col_v1, col_v2, col_v3 = st.columns([2, 2, 1])
                    
                    with col_v1:
                        current_volume = move.get('metragem', 0.0)
                        new_volume = st.number_input(
                            "Novo Volume (m³)",
                            min_value=0.0,
                            step=0.5,
                            value=float(current_volume) if current_volume else 0.0,
                            key=f"new_volume_{move['id']}"
                        )
                    
                    with col_v2:
                        if st.button("✅ Confirmar", key=f"confirm_volume_{move['id']}", type="primary", use_container_width=True):
                            if new_volume != current_volume:
                                if update_move_details(move['id'], {'metragem': new_volume}):
                                    st.session_state.data = fetch_all_data()
                                    st.session_state[f"edit_volume_{move['id']}"] = False
                                    st.toast(f"✅ Volume atualizado: {new_volume} m³")
                                    time.sleep(0.5)
                                    st.rerun()
                    
                    with col_v3:
                        if st.button("❌ Cancelar", key=f"cancel_volume_{move['id']}", use_container_width=True):
                            st.session_state[f"edit_volume_{move['id']}"] = False
                            st.rerun()
                    
                    st.markdown("---")
            
            # DETALHES COMPLETOS
            if st.session_state.get(f"show_details_{move['id']}", False):
                with st.expander("📋 DETALHES COMPLETOS", expanded=True):
                    col_det1, col_det2, col_det3 = st.columns(3)
                    
                    with col_det1:
                        st.markdown("### 📍 Endereços")
                        st.markdown(f"""
                        **Origem:**  
                        {resident.get('originAddress', 'N/A')}, {resident.get('originNumber', '')}  
                        Bairro: {resident.get('originNeighborhood', 'N/A')}
                        
                        **Destino:**  
                        {resident.get('destAddress', 'N/A')}, {resident.get('destNumber', '')}  
                        Bairro: {resident.get('destNeighborhood', 'N/A')}
                        """)
                        
                        if resident.get('observation'):
                            st.markdown("**📝 Observações:**")
                            st.info(resident['observation'])
                    
                    with col_det2:
                        st.markdown("### 👥 Equipe Designada")
                        
                        staff_data = st.session_state.data.get('staff', [])
                        
                        sup_id = move.get('supervisorId')
                        if sup_id:
                            sup = next((s for s in staff_data if s['id'] == sup_id), None)
                            if sup:
                                st.markdown(f"🔧 **Supervisor:** {sup['name']}")
                        else:
                            st.caption("🔧 Supervisor: Não definido")
                        
                        coord_id = move.get('coordinatorId')
                        if coord_id:
                            coord = next((s for s in staff_data if s['id'] == coord_id), None)
                            if coord:
                                st.markdown(f"📋 **Coordenador:** {coord['name']}")
                        else:
                            st.caption("📋 Coordenador: Não definido")
                        
                        drv_id = move.get('driverId')
                        if drv_id:
                            drv = next((s for s in staff_data if s['id'] == drv_id), None)
                            if drv:
                                st.markdown(f"🚛 **Motorista:** {drv['name']}")
                        else:
                            st.caption("🚛 Motorista: Não definido")
                    
                    with col_det3:
                        st.markdown("### ⚙️ Ações Avançadas")
                        
                        # Reagendar
                        st.markdown("**📅 Reagendar**")
                        new_date = st.date_input(
                            "Nova data",
                            value=datetime.strptime(str(move['date']), '%Y-%m-%d').date() if move.get('date') else datetime.now().date(),
                            key=f"resch_date_{move['id']}",
                            label_visibility="collapsed"
                        )
                        
                        if st.button("📅 Reagendar", key=f"btn_resch_{move['id']}", use_container_width=True):
                            if str(new_date) != str(move.get('date')):
                                if update_move_details(move['id'], {'date': str(new_date)}):
                                    st.session_state.data = fetch_all_data()
                                    st.toast(f"✅ Reagendado: {new_date.strftime('%d/%m/%Y')}")
                                    time.sleep(0.5)
                                    st.rerun()
                        
                        st.divider()
                        
                        # Atribuir Equipe
                        if st.button("👥 Atribuir Equipe", key=f"assign_{move['id']}", use_container_width=True):
                            st.session_state[f"assign_team_{move['id']}"] = True
                            st.rerun()
                    
                    # Formulário de atribuição de equipe
                    if st.session_state.get(f"assign_team_{move['id']}", False):
                        st.markdown("---")
                        st.markdown("### 👥 Atribuir Equipe")
                        
                        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
                        
                        staff_data = st.session_state.data.get('staff', [])
                        
                        with col_t1:
                            supervisors = [s for s in staff_data if s.get('role') == 'SUPERVISOR']
                            sup_options = {"(Nenhum)": None}
                            for s in supervisors:
                                sup_options[s['name']] = s['id']
                            
                            selected_sup = st.selectbox("🔧 Supervisor", list(sup_options.keys()), key=f"sel_sup_{move['id']}")
                        
                        with col_t2:
                            coordinators = [s for s in staff_data if s.get('role') == 'COORDINATOR']
                            coord_options = {"(Nenhum)": None}
                            for c in coordinators:
                                coord_options[c['name']] = c['id']
                            
                            selected_coord = st.selectbox("📋 Coordenador", list(coord_options.keys()), key=f"sel_coord_{move['id']}")
                        
                        with col_t3:
                            drivers = [s for s in staff_data if s.get('role') == 'DRIVER']
                            drv_options = {"(Nenhum)": None}
                            for d in drivers:
                                drv_options[d['name']] = d['id']
                            
                            selected_drv = st.selectbox("🚛 Motorista", list(drv_options.keys()), key=f"sel_drv_{move['id']}")
                        
                        with col_t4:
                            if st.button("✅ Salvar Equipe", key=f"save_team_{move['id']}", type="primary", use_container_width=True):
                                team_update = {
                                    'supervisorId': sup_options[selected_sup],
                                    'coordinatorId': coord_options[selected_coord],
                                    'driverId': drv_options[selected_drv]
                                }
                                
                                if update_move_details(move['id'], team_update):
                                    st.session_state.data = fetch_all_data()
                                    st.session_state[f"assign_team_{move['id']}"] = False
                                    st.toast("✅ Equipe atualizada!")
                                    time.sleep(0.5)
                                    st.rerun()
            
            # CONFIRMAÇÃO DE EXCLUSÃO
            if st.session_state.get(f"confirm_delete_{move['id']}", False):
                st.warning(f"⚠️ **Confirmar exclusão da OS #{move['id']}?**")
                st.caption("Esta ação não pode ser desfeita!")
                
                col_d1, col_d2 = st.columns(2)
                
                with col_d1:
                    if st.button("✅ SIM, EXCLUIR", key=f"yes_delete_{move['id']}", type="primary", use_container_width=True):
                        # Aqui você implementaria a exclusão
                        st.error("❌ Função de exclusão não implementada. Execute SQL no Supabase: `DELETE FROM moves WHERE id = " + str(move['id']) + ";`")
                        st.session_state[f"confirm_delete_{move['id']}"] = False
                
                with col_d2:
                    if st.button("❌ Cancelar", key=f"no_delete_{move['id']}", use_container_width=True):
                        st.session_state[f"confirm_delete_{move['id']}"] = False
                        st.rerun()
            
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
        # LISTA DE MUDANÇAS AGENDADAS - INTERFACE INTUITIVA
        st.subheader("📅 Agenda de Mudanças")
        
        moves = filter_by_scope(st.session_state.data['moves'])
        
        if not moves:
            st.info("💡 Nenhuma mudança agendada.")
            return
        
        # Filtros compactos
        col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1])
        
        with col_f1:
            filter_status_agenda = st.selectbox(
                "📊 Status",
                ["Todos", "A realizar", "Realizando", "Concluído"],
                key="filter_agenda_status"
            )
        
        with col_f2:
            filter_date_from = st.date_input(
                "📅 De",
                value=None,
                key="filter_date_from"
            )
        
        with col_f3:
            filter_date_to = st.date_input(
                "📅 Até",
                value=None,
                key="filter_date_to"
            )
        
        with col_f4:
            st.write("")
            st.write("")
            if st.button("🔄", help="Limpar filtros", use_container_width=True):
                st.session_state.filter_agenda_status = "Todos"
                st.rerun()
        
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
                
                # Verificar se é hoje, amanhã ou atrasada
                today = datetime.now().date()
                days_diff = (date_obj.date() - today).days
                
                if days_diff == 0:
                    formatted_date += " 🔥 **HOJE**"
                    date_color = "#FF5722"
                elif days_diff == 1:
                    formatted_date += " ⭐ **AMANHÃ**"
                    date_color = "#FF9800"
                elif days_diff < 0:
                    formatted_date += f" ⚠️ **ATRASADA** ({abs(days_diff)} dia{'s' if abs(days_diff) > 1 else ''})"
                    date_color = "#F44336"
                else:
                    date_color = "#2196F3"
            except:
                formatted_date = str(date_str)
                date_color = "#999"
            
            # Cabeçalho da data
            st.markdown(f"### 📅 {formatted_date}")
            st.caption(f"{len(moves_list)} mudança(s)")
            
            # Listar mudanças deste dia
            for move in moves_list:
                residents = st.session_state.data['residents']
                resident = next((r for r in residents if r.get('id') == move.get('residentId')), None)
                
                if not resident:
                    continue
                
                # Card visual da mudança
                with st.container():
                    # Definir cor de fundo baseado no status
                    status = move.get('status', 'A realizar')
                    if status == 'Concluído':
                        bg_color = "#E8F5E9"
                        border_color = "#4CAF50"
                        emoji = "🟢"
                    elif status == 'Realizando':
                        bg_color = "#E3F2FD"
                        border_color = "#2196F3"
                        emoji = "🔵"
                    else:
                        bg_color = "#FFF9C4"
                        border_color = "#FFC107"
                        emoji = "🟡"
                    
                    # HTML Card customizado
                    st.markdown(f"""
                    <div style="background-color: {bg_color}; 
                                border-left: 5px solid {border_color}; 
                                padding: 15px; 
                                border-radius: 5px; 
                                margin-bottom: 10px;">
                        <h4 style="margin: 0; color: #333;">{emoji} {resident.get('name', 'N/A')}</h4>
                        <p style="margin: 5px 0; color: #666;">
                            🕐 {move.get('time', 'N/A')} • 
                            📦 {move.get('metragem', 0)} m³ • 
                            📋 OS #{move.get('id', '?')}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Ações rápidas em colunas
                    col_act1, col_act2, col_act3, col_act4 = st.columns([2, 2, 2, 1])
                    
                    with col_act1:
                        # Alterar status rapidamente
                        status_options = ["A realizar", "Realizando", "Concluído"]
                        current_index = status_options.index(status) if status in status_options else 0
                        
                        new_status = st.selectbox(
                            "Status",
                            status_options,
                            index=current_index,
                            key=f"status_quick_{move['id']}",
                            label_visibility="collapsed"
                        )
                        
                        if new_status != status:
                            if st.button("✅ Atualizar", key=f"update_status_{move['id']}", use_container_width=True):
                                updated = {'status': new_status}
                                if new_status == "Concluído":
                                    updated['completionDate'] = str(datetime.now().date())
                                    updated['completionTime'] = str(datetime.now().time().strftime('%H:%M'))
                                
                                if update_move_details(move['id'], updated):
                                    st.session_state.data = fetch_all_data()
                                    st.toast(f"✅ Status: {new_status}")
                                    time.sleep(0.3)
                                    st.rerun()
                    
                    with col_act2:
                        if resident.get('contact'):
                            st.write(f"📞 {resident['contact']}")
                        else:
                            st.write("📞 Sem contato")
                    
                    with col_act3:
                        # Mostrar equipe resumida
                        team_parts = []
                        if move.get('supervisorId'):
                            sup = get_name_by_id(st.session_state.data['staff'], move['supervisorId'])
                            if sup != "N/A":
                                team_parts.append(f"👷 {sup.split()[0]}")
                        if move.get('driverId'):
                            drv = get_name_by_id(st.session_state.data['staff'], move['driverId'])
                            if drv != "N/A":
                                team_parts.append(f"🚛 {drv.split()[0]}")
                        
                        if team_parts:
                            st.caption(" • ".join(team_parts))
                        else:
                            st.caption("⚠️ Sem equipe")
                    
                    with col_act4:
                        # Botão de expandir detalhes
                        if st.button("📋", key=f"details_{move['id']}", help="Ver detalhes completos"):
                            st.session_state[f"show_full_{move['id']}"] = not st.session_state.get(f"show_full_{move['id']}", False)
                            st.rerun()
                    
                    # Detalhes completos (expandível)
                    if st.session_state.get(f"show_full_{move['id']}", False):
                        st.markdown("---")
                        
                        col_det1, col_det2 = st.columns(2)
                        
                        with col_det1:
                            st.markdown("**📍 Endereços:**")
                            st.write(f"**Origem:** {resident.get('originAddress', 'N/A')}, {resident.get('originNumber', '')}")
                            st.caption(f"Bairro: {resident.get('originNeighborhood', 'N/A')}")
                            st.write(f"**Destino:** {resident.get('destAddress', 'N/A')}, {resident.get('destNumber', '')}")
                            st.caption(f"Bairro: {resident.get('destNeighborhood', 'N/A')}")
                        
                        with col_det2:
                            st.markdown("**👥 Equipe Completa:**")
                            
                            sup_id = move.get('supervisorId')
                            if sup_id:
                                st.write(f"🔧 **Supervisor:** {get_name_by_id(st.session_state.data['staff'], sup_id)}")
                            
                            coord_id = move.get('coordinatorId')
                            if coord_id:
                                st.write(f"📋 **Coordenador:** {get_name_by_id(st.session_state.data['staff'], coord_id)}")
                            
                            drv_id = move.get('driverId')
                            if drv_id:
                                st.write(f"🚛 **Motorista:** {get_name_by_id(st.session_state.data['staff'], drv_id)}")
                            
                            if not any([sup_id, coord_id, drv_id]):
                                st.warning("⚠️ Nenhuma equipe atribuída")
                        
                        if resident.get('observation'):
                            st.markdown("**📝 Observações:**")
                            st.info(resident['observation'])
                    
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
                        # Recarregar dados para pegar o ID do morador recém-criado
                        st.session_state.data = fetch_all_data()
                        
                        # Buscar o morador recém-criado (último inserido)
                        all_residents = st.session_state.data['residents']
                        new_resident = max(all_residents, key=lambda x: x.get('id', 0))
                        
                        # CRIAR OS AUTOMATICAMENTE
                        auto_os = {
                            'residentId': new_resident['id'],
                            'date': str(move_date),
                            'time': str(move_time),
                            'metragem': 0.0,
                            'supervisorId': None,
                            'coordinatorId': None,
                            'driverId': None,
                            'status': 'A realizar',
                            'secretaryId': sec_id
                        }
                        
                        # Inserir OS
                        os_criada = insert_move(auto_os)
                        
                        # Recarregar novamente para pegar a OS
                        st.session_state.data = fetch_all_data()
                        st.session_state.resident_form_key += 1
                        
                        if os_criada:
                            st.toast("🎉 Morador + OS criados!", icon="✅")
                            st.success(f"""
                            ✅ **{name}** cadastrado(a) com sucesso!
                            
                            📍 Origem: {orig_addr or 'N/A'}
                            🎯 Destino: {dest_addr or 'N/A'}
                            
                            📦 **OS criada automaticamente!**
                            📅 Data: {move_date.strftime('%d/%m/%Y')}
                            🕐 Hora: {move_time.strftime('%H:%M')}
                            """)
                        else:
                            st.toast("🎉 Morador cadastrado!", icon="✅")
                            st.warning(f"✅ **{name}** cadastrado(a)!\n\n⚠️ Erro ao criar OS automaticamente.\n💡 Crie a OS manualmente em 'Agendamento'.")
                        
                        time.sleep(1.5)
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
                        
                        # Verificar se tem OSs vinculadas ANTES do botão (ambos formatos)
                        moves_vinculadas = [m for m in st.session_state.data['moves'] 
                                          if m.get('residentId') == resident['id'] 
                                          or m.get('residentid') == resident['id']]
                        
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
                                if st.button("✅ Sim", key=f"yes_res_{resident['id']}", use_container_width=True):
                                    try:
                                        conn = get_connection()
                                        if conn:
                                            cur = conn.cursor()
                                            cur.execute("DELETE FROM residents WHERE id = %s", (resident['id'],))
                                            conn.commit()
                                            cur.close()
                                            conn.close()
                                            
                                            # Limpar confirmação antes de rerun
                                            if f"confirm_delete_{resident['id']}" in st.session_state:
                                                del st.session_state[f"confirm_delete_{resident['id']}"]
                                            
                                            st.session_state.data = fetch_all_data()
                                            st.toast(f"🗑️ {resident.get('name', 'Morador')} excluído!")
                                            time.sleep(0.5)
                                            st.rerun()
                                        else:
                                            st.error("❌ Erro de conexão")
                                    except Exception as e:
                                        st.error(f"❌ Erro ao excluir: {str(e)}")
                            
                            with col_conf2:
                                if st.button("❌ Não", key=f"no_res_{resident['id']}", use_container_width=True):
                                    if f"confirm_delete_{resident['id']}" in st.session_state:
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
        
        # Cargos fixos do sistema
        user = st.session_state.user
        
        if user['role'] == 'ADMIN':
            # Admin pode criar qualquer cargo
            cargos_disponiveis = {
                "Coordenador": "COORDINATOR",
                "Supervisor": "SUPERVISOR",
                "Motorista": "DRIVER",
                "Secretária": "SECRETARY"
            }
        else:
            # Secretária só pode criar Coordenador, Supervisor e Motorista
            cargos_disponiveis = {
                "Coordenador": "COORDINATOR",
                "Supervisor": "SUPERVISOR",
                "Motorista": "DRIVER"
            }
        
        role_name = st.selectbox("Cargo", list(cargos_disponiveis.keys()))
        role_permission = cargos_disponiveis[role_name]
        
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
                                if st.button("Sim", key=f"yes_staff_{row['id']}_{idx}", use_container_width=True):
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
                                if st.button("Não", key=f"no_staff_{row['id']}_{idx}", use_container_width=True):
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
    
    st.markdown("""
    ### Cargos do Sistema Telemim Mudanças
    
    Os cargos abaixo são padrão do sistema e não podem ser editados ou removidos.
    Cada funcionário deve ser cadastrado com um destes cargos.
    """)
    
    # Cargos fixos do sistema
    cargos_fixos = [
        {
            "Cargo": "📋 Coordenador",
            "Permissão": "COORDINATOR",
            "Descrição": "Coordena equipes e operações de mudança",
            "Acesso": "Visualizar e gerenciar OSs, atribuir equipes"
        },
        {
            "Cargo": "🔧 Supervisor", 
            "Permissão": "SUPERVISOR",
            "Descrição": "Supervisiona execução das mudanças",
            "Acesso": "Executar OSs, atualizar status, ver equipe"
        },
        {
            "Cargo": "🚛 Motorista",
            "Permissão": "DRIVER", 
            "Descrição": "Realiza o transporte das mudanças",
            "Acesso": "Visualizar suas OSs designadas"
        },
        {
            "Cargo": "📝 Secretária",
            "Permissão": "SECRETARY",
            "Descrição": "Gerencia cadastros e agendamentos",
            "Acesso": "Cadastrar clientes, agendar mudanças, gerenciar funcionários"
        },
        {
            "Cargo": "👑 Administrador",
            "Permissão": "ADMIN",
            "Descrição": "Acesso total ao sistema",
            "Acesso": "Todas as funcionalidades, gestão completa"
        }
    ]
    
    # Mostrar em cards
    for cargo in cargos_fixos:
        with st.expander(f"{cargo['Cargo']} - {cargo['Permissão']}", expanded=False):
            st.markdown(f"**Descrição:** {cargo['Descrição']}")
            st.markdown(f"**Acessos:** {cargo['Acesso']}")
            
            # Contar quantos funcionários tem este cargo
            staff = st.session_state.data.get('staff', [])
            count = len([s for s in staff if s.get('role') == cargo['Permissão']])
            
            if count > 0:
                st.success(f"✅ {count} funcionário(s) com este cargo")
            else:
                st.info(f"ℹ️ Nenhum funcionário com este cargo")
    
    st.divider()
    
    # Resumo
    st.subheader("📊 Resumo por Cargo")
    
    staff = st.session_state.data.get('staff', [])
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        coord_count = len([s for s in staff if s.get('role') == 'COORDINATOR'])
        st.metric("📋 Coordenadores", coord_count)
    
    with col2:
        sup_count = len([s for s in staff if s.get('role') == 'SUPERVISOR'])
        st.metric("🔧 Supervisores", sup_count)
    
    with col3:
        drv_count = len([s for s in staff if s.get('role') == 'DRIVER'])
        st.metric("🚛 Motoristas", drv_count)
    
    with col4:
        sec_count = len([s for s in staff if s.get('role') == 'SECRETARY'])
        st.metric("📝 Secretárias", sec_count)
    
    with col5:
        admin_count = len([s for s in staff if s.get('role') == 'ADMIN'])
        st.metric("👑 Admins", admin_count)
    
    st.divider()
    
    st.info("""
    💡 **Como usar:**
    
    1. Vá em **👥 Funcionários**
    2. Cadastre novo funcionário
    3. Selecione um dos cargos acima
    4. O funcionário terá as permissões do cargo automaticamente
    
    ⚠️ **Importante:** Os cargos são fixos e não podem ser alterados para manter a integridade do sistema.
    """)

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
        "Moradores": {"icon": "🏠", "func": residents_form},
        "Funcionários": {"icon": "👥", "func": staff_management},
        "Secretarias": {"icon": "🏢", "func": manage_secretaries},
        "Cargos": {"icon": "🛡️", "func": manage_roles},
        "Relatórios": {"icon": "📈", "func": reports_analytics_page},
    }
    
    # Regras de Menu Dinâmico
    options = ["Gerenciamento", "Ordens de Serviço", "Calendário"]
    can_schedule = user['role'] in ['ADMIN', 'SECRETARY', 'COORDINATOR', 'SUPERVISOR']
    
    if can_schedule:
        options.extend(["Moradores"])
        
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
