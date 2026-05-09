import streamlit as st
from sqlalchemy.orm import joinedload
from src.core.database import SessionLocal
from src.models.entities import PlanMacro, Policy, StrategicItem, Activity, Task, Evidence
from src.services.calculations import CalculationService
from datetime import datetime
import html

def format_progress_color(progress):
    if progress < 1.0: return f":red[**{progress:.1f}%**]"
    elif progress < 99.9: return f":orange[**{progress:.1f}%**]"
    else: return f":green[**{progress:.1f}%**]"

def show_supervisor_view():
    """
    Operational management view for Supervisors.
    Enables task tracking, evidence upload, and progress reporting with forced validation.
    """
    st.markdown("<div class='corporate-header'>", unsafe_allow_html=True)
    st.title("🧐 Gestión de tareas")
    st.write("Control operativo con validación de evidencias y observaciones")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Mostrar mensaje de éxito persistente tras rerun
    if "success_msg" in st.session_state:
        st.success(st.session_state.success_msg)
        del st.session_state.success_msg

    db = SessionLocal()
    try:
        user_role = st.session_state.get('role')
        res_id = st.session_state.get('responsible_id')
        
        if user_role == "Supervisor" and res_id:
            # Calcular trabajadores a cargo globalmente
            all_supervised_acts = db.query(Activity).filter(Activity.supervisors.any(id=res_id)).all()
            all_managed_workers = set()
            for a in all_supervised_acts:
                for t in a.tasks:
                    for r in t.responsibles:
                        if r.id != res_id:
                            all_managed_workers.add(r.id)
            
            st.metric("👥 Trabajadores a cargo (Total Institucional)", len(all_managed_workers))
            st.divider()

        macros = db.query(PlanMacro).order_by(PlanMacro.id).all()
        if not macros: return st.info("Sin planes configurados.")
        
        m_id = st.selectbox("Gestión Macro", options=[m.id for m in macros], format_func=lambda x: next(m.name for m in macros if m.id == x))
        macro = db.query(PlanMacro).filter(PlanMacro.id == m_id).first()
        
        pol_id = st.selectbox("Política", options=[p.id for p in macro.policies], format_func=lambda x: f"{next(p.name for p in macro.policies if p.id == x)} ({next(p.progress for p in macro.policies if p.id == x):.1f}%)")
        policy = db.query(Policy).filter(Policy.id == pol_id).first()
        
        si_id = st.selectbox("Plan / Programa", options=[si.id for si in policy.strategic_items], format_func=lambda x: f"{next(si.name for si in policy.strategic_items if si.id == x)} ({next(si.progress for si in policy.strategic_items if si.id == x):.1f}%)")
        item = db.query(StrategicItem).filter(StrategicItem.id == si_id).first()

        st.divider()
        st.subheader(f"Seguimiento: {item.name}")
        
        activities = db.query(Activity).options(
            joinedload(Activity.tasks).joinedload(Task.responsibles),
            joinedload(Activity.supervisors),
            joinedload(Activity.evidences)
        ).filter(Activity.strategic_item_id == item.id).order_by(Activity.id).all()
        
        # Filtrado por rol
        filtered_activities = []
        for act in activities:
            if user_role == "Admin":
                filtered_activities.append(act)
            else:
                is_supervisor = any(sup.id == res_id for sup in act.supervisors)
                is_worker = any(any(r.id == res_id for r in t.responsibles) for t in act.tasks)
                if is_supervisor or is_worker:
                    filtered_activities.append(act)
        
        activities = filtered_activities
        
        # --- Filtrado por Trabajador ---
        available_workers = {}
        for act in activities:
            for t in act.tasks:
                for r in t.responsibles:
                    available_workers[r.id] = r
                    
        selected_worker_id = "Todos"
        if available_workers:
            worker_opts = ["Todos"] + list(available_workers.keys())
            selected_worker_id = st.selectbox(
                "Filtrar por Trabajador (Opcional)", 
                options=worker_opts, 
                format_func=lambda x: "Todos los Trabajadores" if x == "Todos" else available_workers[x].name
            )
            
        display_tasks = {}
        activities_to_show = []
        for act in activities:
            tasks = sorted(act.tasks, key=lambda x: x.id)
            if selected_worker_id != "Todos":
                tasks = [t for t in tasks if any(r.id == selected_worker_id for r in t.responsibles)]
            
            # Mostrar la actividad si tiene tareas para este worker, o si estamos viendo "Todos"
            if tasks or selected_worker_id == "Todos":
                activities_to_show.append(act)
                display_tasks[act.id] = tasks
        
        if not activities_to_show:
            st.info("No tienes actividades/tareas asignadas bajo este filtro.")
            
        for i, act in enumerate(activities_to_show, 1):
            # Usamos una versión en el key para forzar el cierre al actualizar
            act_ver = st.session_state.get(f"v_act_{act.id}", 0)
            
            # Verificar evidencia de actividad
            has_act_ev = any(e.activity_id == act.id for e in act.evidences)
            ev_badge = ""
            if act.progress >= 99.9:
                if has_act_ev:
                    ev_badge = " | ✅ Actividad terminada a completitud"
                else:
                    ev_badge = " | 🔴 Actividad terminada sin informe consolidado"
                    
            with st.expander(f"🎯 {i}. Actividad: {act.name} (Peso: {act.weight:.1f}% | Avance: {format_progress_color(act.progress)}){ev_badge}", expanded=False, key=f"exp_act_{act.id}_{act_ver}"):
                
                tasks = display_tasks[act.id]
                if not tasks:
                    st.info("Sin tareas vinculadas.")
                else:
                    for j, t in enumerate(tasks, 1):
                        task_ver = st.session_state.get(f"v_task_{t.id}", 0)
                        with st.expander(f"{i}.{j} {t.name} (Peso: {t.weight:.1f}% | Avance: {format_progress_color(t.progress)})", key=f"exp_t_{t.id}_{task_ver}"):
                            ev_list = db.query(Evidence).filter(Evidence.task_id == t.id).all()
                            has_evidence = len(ev_list) > 0
                            
                            c1, c2 = st.columns([1, 1])
                            with c1: 
                                if t.responsibles:
                                    res_badges = " ".join([f"<span class='badge' style='background-color:#f1f5f9; color:#475569; border:1px solid #cbd5e1;'>{html.escape(r.name)}</span>" for r in t.responsibles])
                                    st.markdown(res_badges, unsafe_allow_html=True)
                                if t.start_date and t.end_date:
                                    st.caption(f"📅 {t.start_date.strftime('%d/%m/%y')} - {t.end_date.strftime('%d/%m/%y')}")
                            
                            with c2:
                                status_opts = ["Pendiente", "En Proceso", "Cumplida"]
                                curr_idx = status_opts.index(t.status) if t.status in status_opts else 0
                                new_status = st.selectbox("Estado", status_opts, index=curr_idx, key=f"st_sup_{t.id}")
                            
                            st.markdown("---")
                            obs = st.text_area("📝 Observaciones", value=t.observations or "", key=f"obs_sup_{t.id}")
                            
                            if st.button("💾 Guardar", key=f"save_sup_{t.id}"):
                                can_save = True
                                if new_status == "Cumplida":
                                    if not has_evidence: 
                                        st.error("Falta evidencia en la tarea (debe ser cargada por el Worker).")
                                        can_save = False
                                    elif not obs or len(obs.strip()) < 5: 
                                        st.error("Observaciones requeridas.")
                                        can_save = False
                                
                                if can_save:
                                    t.status = new_status
                                    t.progress = 100.0 if new_status == "Cumplida" else (50.0 if new_status == "En Proceso" else 0.0)
                                    t.observations = obs
                                    if new_status == "Cumplida": t.fulfillment_date = datetime.now()
                                    
                                    db.add(t)
                                    db.commit()
                                    CalculationService.update_all_levels(db, t.id)
                                    
                                    st.session_state[f"v_act_{act.id}"] = act_ver + 1
                                    st.session_state[f"v_task_{t.id}"] = task_ver + 1
                                    st.session_state.success_msg = f"✅ Tarea '{t.name}' actualizada correctamente."
                                    st.rerun()

                            st.divider()
                            st.caption("🔗 Evidencias (Cargadas por Worker)")
                            if not ev_list:
                                st.info("Sin evidencias cargadas en esta tarea.")
                            else:
                                for ev in ev_list:
                                    url = ev.url if ev.url.startswith(("http://", "https://")) else f"https://{ev.url}"
                                    st.link_button(f"🔗 Ver Evidencia: {ev.description or 'Tarea'}", url)

                # --- Activity-Level General Evidence (Supervisor Role) ---
                st.markdown("---")
                st.markdown("#### 📂 Evidencia General de la Actividad")
                act_ev_list = db.query(Evidence).filter(Evidence.activity_id == act.id).all()
                
                if act_ev_list:
                    for aev in act_ev_list:
                        aurl = aev.url if aev.url.startswith(("http://", "https://")) else f"https://{aev.url}"
                        st.link_button(f"📄 Informe/Evidencia General: {aev.description or 'Actividad'}", aurl, type="primary")
                
                with st.expander("➕ Cargar Evidencia de Actividad (Reporte Final / Informe)"):
                    c_ev1, c_ev2 = st.columns([2, 1])
                    with c_ev1:
                        act_link = st.text_input("Enlace (Drive, SharePoint, PDF)", key=f"act_l_{act.id}")
                    with c_ev2:
                        act_desc = st.text_input("Descripción", placeholder="Ej: Informe Final", key=f"act_d_{act.id}")
                    
                    if st.button("💾 Guardar Evidencia de Actividad", key=f"act_b_{act.id}"):
                        if act_link:
                            db.add(Evidence(activity_id=act.id, url=act_link, description=act_desc))
                            db.commit()
                            st.session_state.success_msg = "✅ Evidencia general de la actividad guardada."
                            st.rerun()
                        else:
                            st.error("Ingresa un enlace válido.")
    finally:
        db.close()
