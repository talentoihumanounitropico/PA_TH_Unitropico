import streamlit as st
from sqlalchemy.orm import joinedload
from src.core.database import SessionLocal
from src.models.entities import Task, Activity, Evidence, Responsible, User
from datetime import datetime, timedelta
import html

def show_worker_view():
    """
    Personalized view for Workers.
    Shows only tasks assigned to the logged-in responsible.
    Allows evidence upload and descriptive observations.
    """
    st.markdown("<div class='corporate-header'>", unsafe_allow_html=True)
    st.title("👷 Mi Panel de Trabajo")
    st.write("Gestiona tus tareas asignadas, carga evidencias y reporta avances.")
    st.markdown("</div>", unsafe_allow_html=True)

    responsible_id = st.session_state.get("responsible_id")
    if not responsible_id:
        st.warning("⚠️ Tu cuenta no está vinculada a un perfil de Responsable. Contacta al Administrador.")
        return

    db = SessionLocal()
    try:
        # Get tasks assigned to this responsible
        tasks = db.query(Task).join(Task.responsibles).filter(Responsible.id == responsible_id).all()

        if not tasks:
            st.info("No tienes tareas asignadas actualmente. ¡Buen trabajo!")
            return

        # Task Classification
        now = datetime.now()
        vencidas = [t for t in tasks if t.status != "Cumplida" and t.end_date and t.end_date < now]
        proximas = [t for t in tasks if t.status != "Cumplida" and t.end_date and now <= t.end_date <= (now + timedelta(days=3))]
        cumplidas = [t for t in tasks if t.status == "Cumplida"]

        # Summary Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Tareas", len(tasks))
        c2.metric("🚫 Vencidas", len(vencidas), delta_color="inverse")
        c3.metric("⏳ Próximas", len(proximas))
        c4.metric("✅ Cumplidas", len(cumplidas))

        st.divider()

        # Group tasks by activity for better organization
        activities_map = {}
        for t in tasks:
            act = t.activity
            if act.id not in activities_map:
                activities_map[act.id] = {"obj": act, "tasks": []}
            activities_map[act.id]["tasks"].append(t)

        for act_id, data in activities_map.items():
            act = data["obj"]
            act_tasks = data["tasks"]
            
            # Header with activity progress
            st.markdown(f"### 🎯 Actividad: {act.name} (Avance: {act.progress:.1f}%)")
            st.progress(act.progress / 100)
            
            with st.expander("Ver tareas de esta actividad", expanded=True):
                for t in act_tasks:
                    # Determine card border color based on status/date
                    border_color = "#e2e8f0"
                    status_text = f"`{t.status}`"
                    if t.status == "Cumplida":
                        border_color = "#10b981" # Green
                        status_text = "✅ **Cumplida**"
                    elif t in vencidas:
                        border_color = "#ef4444" # Red
                        status_text = "🚫 **Vencida**"
                    elif t in proximas:
                        border_color = "#f59e0b" # Orange
                        status_text = "⏳ **Próxima a vencer**"

                    with st.container(border=True):
                        st.markdown(f"#### {t.name}")
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"Estado: {status_text}")
                            if t.start_date and t.end_date:
                                st.caption(f"📅 Plazo: {t.start_date.strftime('%d/%m/%y')} al {t.end_date.strftime('%d/%m/%y')}")
                        
                        with col2:
                            if t.status != "Cumplida":
                                status_opts = ["Pendiente", "En Proceso"]
                                curr_idx = status_opts.index(t.status) if t.status in status_opts else 0
                                new_status = st.selectbox("Actualizar Estado", status_opts, index=curr_idx, key=f"st_work_{t.id}")
                            else:
                                st.success("Tarea finalizada y aprobada.")

                        st.markdown("---")
                        obs = st.text_area("📝 Descripción/Observación de la ejecución", value=t.observations or "", key=f"obs_work_{t.id}", placeholder="Describe detalladamente qué hiciste en esta tarea...")
                        
                        ev_list = db.query(Evidence).filter(Evidence.task_id == t.id).all()
                        if ev_list:
                            st.caption("🔗 Evidencias Cargadas:")
                            for ev in ev_list:
                                url = ev.url if ev.url.startswith(("http://", "https://")) else f"https://{ev.url}"
                                st.markdown(f"- [Ver Evidencia]({url})")
                        
                        if t.status != "Cumplida":
                            col_ev, col_save = st.columns([3, 1])
                            with col_ev:
                                new_ev = st.text_input("Añadir nuevo enlace de evidencia (Drive, SharePoint, etc.)", key=f"ev_work_{t.id}")
                            
                            with col_save:
                                st.markdown("<br>", unsafe_allow_html=True)
                                if st.button("💾 Reportar Avance", key=f"save_work_{t.id}", use_container_width=True):
                                    t.status = new_status
                                    t.observations = obs
                                    if new_ev:
                                        db.add(Evidence(task_id=t.id, url=new_ev))
                                    
                                    if new_status == "En Proceso":
                                        t.progress = 50.0
                                    elif new_status == "Pendiente":
                                        t.progress = 0.0
                                    
                                    db.commit()
                                    st.success("✅ Avance reportado correctamente.")
                                    st.rerun()
    finally:
        db.close()
