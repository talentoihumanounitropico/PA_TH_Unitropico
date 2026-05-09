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
            joinedload(Activity.tasks).joinedload(Task.responsibles)
        ).filter(Activity.strategic_item_id == item.id).order_by(Activity.id).all()
        
        for i, act in enumerate(activities, 1):
            # Usamos una versión en el key para forzar el cierre al actualizar
            act_ver = st.session_state.get(f"v_act_{act.id}", 0)
            with st.expander(f"🎯 {i}. Actividad: {act.name} (Peso: {act.weight:.1f}% | Avance: {format_progress_color(act.progress)})", expanded=False, key=f"exp_act_{act.id}_{act_ver}"):
                
                tasks = sorted(act.tasks, key=lambda x: x.id)
                if not tasks:
                    st.info("Sin tareas vinculadas.")
                    continue

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
                                    st.error("Falta evidencia.")
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
                                
                                # Lógica de Auto-Retraer: Incrementar versión de los keys
                                st.session_state[f"v_act_{act.id}"] = act_ver + 1
                                st.session_state[f"v_task_{t.id}"] = task_ver + 1
                                st.session_state.success_msg = f"✅ Tarea '{t.name}' actualizada correctamente."
                                st.rerun()

                        st.divider()
                        st.caption("🔗 Evidencias")
                        for ev in ev_list:
                            url = ev.url if ev.url.startswith(("http://", "https://")) else f"https://{ev.url}"
                            st.link_button("🔗 Ver Evidencia", url)
                        
                        with st.popover("➕ Vincular"):
                            link = st.text_input("URL", key=f"l_sup_{t.id}")
                            if st.button("Vincular", key=f"b_sup_{t.id}"):
                                if link:
                                    db.add(Evidence(task_id=t.id, url=link))
                                    db.commit()
                                    st.rerun()
    finally:
        db.close()
