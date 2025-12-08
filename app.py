with tab2:
        # ============================================
        # TAB 2: AGENDAR NOVA OS
        # ============================================
        st.subheader("➕ Agendar Nova Mudança")
        
        scoped_residents = filter_by_scope(st.session_state.data['residents'])
        scoped_staff = filter_by_scope(st.session_state.data['staff'], key='id')
        
        if not scoped_residents:
            st.warning("⚠️ Nenhum morador cadastrado nesta base.")
            st.info("💡 Cadastre um morador primeiro na aba **🏠 Moradores**")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("➕ Ir para Moradores", type="primary", use_container_width=True):
                    st.info("👆 Clique na aba '🏠 Moradores' no menu acima")
        else:
            # Inicializar contador
            if 'schedule_form_key' not in st.session_state:
                st.session_state.schedule_form_key = 0

            with st.form(f"new_move_schedule_{st.session_state.schedule_form_key}"):
                st.markdown("#### 📋 Informações da Mudança")
                
                res_map = {r['name']: r['id'] for r in scoped_residents}
                res_name = st.selectbox("👤 Morador *", list(res_map.keys()), 
                                        help="Selecione o morador desta mudança")
                
                st.divider()
                
                c1, c2 = st.columns(2)
                m_date = c1.date_input("📅 Data da Mudança *", help="Data prevista")
                m_time = c2.time_input("🕐 Hora *", help="Horário previsto")
                
                metragem = st.number_input("📦 Volume (m³)", 
                                           min_value=0.0, 
                                           step=0.5, 
                                           value=0.0,
                                           help="Volume estimado")
                
                st.divider()
                st.markdown("#### 👥 Equipe (Opcional)")
                
                supervisors = [s for s in scoped_staff if s['role'] in ['SUPERVISOR', 'ADMIN']]
                coordinators = [s for s in scoped_staff if s['role'] in ['COORDINATOR', 'ADMIN']]
                drivers = [s for s in scoped_staff if s['role'] in ['DRIVER']]
                
                sup_id = None
                coord_id = None
                drv_id = None
                
                col_eq1, col_eq2, col_eq3 = st.columns(3)
                
                with col_eq1:
                    if supervisors:
                        sup_options = ["Nenhum"] + [s['name'] for s in supervisors]
                        sup_name = st.selectbox("🔧 Supervisor", sup_options)
                        if sup_name != "Nenhum":
                            sup_id = next((s['id'] for s in supervisors if s['name'] == sup_name), None)
                    else:
                        st.info("💡 Nenhum supervisor")
                
                with col_eq2:
                    if coordinators:
                        coord_options = ["Nenhum"] + [s['name'] for s in coordinators]
                        coord_name = st.selectbox("📋 Coordenador", coord_options)
                        if coord_name != "Nenhum":
                            coord_id = next((s['id'] for s in coordinators if s['name'] == coord_name), None)
                    else:
                        st.info("💡 Nenhum coordenador")
                
                with col_eq3:
                    if drivers:
                        drv_options = ["Nenhum"] + [s['name'] for s in drivers]
                        drv_name = st.selectbox("🚛 Motorista", drv_options)
                        if drv_name != "Nenhum":
                            drv_id = next((s['id'] for s in drivers if s['name'] == drv_name), None)
                    else:
                        st.info("💡 Nenhum motorista")
                
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
                        
                        st.toast("🎉 OS agendada!", icon="✅")
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
                        st.error("❌ Erro ao agendar mudança.")
