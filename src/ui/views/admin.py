import streamlit as st
from sqlalchemy.orm import joinedload
from src.core.database import SessionLocal
from src.models.entities import PlanMacro, Policy, StrategicItem, Activity, Task, Responsible, User
from src.services.auth import AuthService
import pandas as pd
from datetime import datetime
import html

def format_progress_color(progress):
    if progress < 1.0: return f":red[**{progress:.1f}%**]"
    elif progress < 99.9: return f":orange[**{progress:.1f}%**]"
    else: return f":green[**{progress:.1f}%**]"

# Helper to get siblings
def get_siblings_weights(db, obj):
    if isinstance(obj, Policy): return [p.weight for p in db.query(Policy).filter(Policy.plan_macro_id == obj.plan_macro_id, Policy.id != obj.id).all()]
    if isinstance(obj, StrategicItem): return [s.weight for s in db.query(StrategicItem).filter(StrategicItem.policy_id == obj.policy_id, StrategicItem.id != obj.id).all()]
    if isinstance(obj, Activity): return [a.weight for a in db.query(Activity).filter(Activity.strategic_item_id == obj.strategic_item_id, Activity.id != obj.id).all()]
    if isinstance(obj, Task): return [t.weight for t in db.query(Task).filter(Task.activity_id == obj.activity_id, Task.id != obj.id).all()]
    return []

def weight_manager_ui(siblings_weights, entity_name, key_prefix, default_weight=None):
    current_total = sum(siblings_weights)
    remaining = max(0.0, 100.0 - current_total)
    num_existing = len(siblings_weights)
    
    st.markdown("##### ⚖️ Asignación de Peso")
    mode = st.radio("Distribución de Peso", ["Manual", "Automática"], horizontal=True, key=f"{key_prefix}_mode")
    
    assigned_weight = 0.0
    is_valid = False
    
    if mode == "Automática":
        new_weight = 100.0 / (num_existing + 1)
        st.info(f"💡 El sistema asignará automáticamente **{new_weight:.1f}%** a todos los {num_existing + 1} elementos.")
        assigned_weight = new_weight
        is_valid = True
    else:
        init_val = default_weight if default_weight is not None else min(20.0, remaining)
        assigned_weight = st.number_input("Peso (%)", min_value=0.0, max_value=100.0, value=float(init_val), step=1.0, key=f"{key_prefix}_weight")
        projected = current_total + assigned_weight
        
        if projected > 100.001:
            st.error(f"🔴 **Excede 100%:** Suma proyectada {projected:.1f}%")
            is_valid = False
        elif projected >= 90.0:
            st.warning(f"🟡 **Acumulado:** {projected:.1f}% (Queda {max(0.0, 100.0 - projected):.1f}%)")
            is_valid = True
        else:
            st.success(f"🟢 **Acumulado:** {projected:.1f}% (Queda {max(0.0, 100.0 - projected):.1f}%)")
            is_valid = True
            
        st.progress(min(projected / 100.0, 1.0))
        
    return mode, assigned_weight, is_valid

def auto_distribute_weights(db, siblings, new_item=None):
    items = siblings + ([new_item] if new_item else [])
    if not items: return
    w = 100.0 / len(items)
    for i in items: i.weight = w
def show_admin_view():
    """
    Main Administration interface for managing the 5-level institutional hierarchy.
    Allows CRUD operations on Plans, Policies, Programs, Activities, and Responsibles.
    """
    st.markdown("<div class='corporate-header'>", unsafe_allow_html=True)
    st.title("⚙️ Configuración de Estructura Institucional")
    st.write("Administración jerárquica y cronograma institucional")
    st.markdown("</div>", unsafe_allow_html=True)
    
    db = SessionLocal()
    try:
        t1, t2, t3, t4, t5 = st.tabs(["🏛️ Gestión Macro", "📂 Planes y Programas", "✅ Operación", "👥 Responsables", "🛠️ Continuidad"])
        
        with t1: manage_macro_level(db)
        with t2: manage_strategic_level(db)
        with t3: manage_operational_level(db)
        with t4: manage_responsibles_level(db)
        with t5: manage_tools_level(db)
            
    finally:
        db.close()

@st.dialog("Eliminar")
def confirm_delete(db, obj, label):
    st.warning(f"¿Eliminar {label}: {obj.name}?")
    if st.button("Confirmar", type="primary"):
        db.delete(obj)
        db.commit()
        st.rerun()

@st.dialog("Editar")
def edit_dialog(db, obj, label):
    new_name = st.text_input("Nombre", value=obj.name)
    is_valid = True
    new_weight = getattr(obj, 'weight', None)
    
    if hasattr(obj, 'weight'):
        siblings_weights = get_siblings_weights(db, obj)
        current_total = sum(siblings_weights)
        
        new_weight = st.number_input("Peso (%)", min_value=0.0, max_value=100.0, value=float(obj.weight), step=1.0)
        projected = current_total + new_weight
        
        if projected > 100.001:
            st.error(f"🔴 **Excede 100%:** Suma proyectada {projected:.1f}%")
            is_valid = False
        elif projected >= 90.0:
            st.warning(f"🟡 **Acumulado:** {projected:.1f}% (Queda {max(0.0, 100.0 - projected):.1f}%)")
        else:
            st.success(f"🟢 **Acumulado:** {projected:.1f}% (Queda {max(0.0, 100.0 - projected):.1f}%)")
        st.progress(min(projected / 100.0, 1.0))

    new_status, new_progress, new_start, new_end = None, None, None, None
    selected_res = []
    
    if isinstance(obj, Task):
        col_s1, col_s2 = st.columns(2)
        status_opts = ["Pendiente", "En Proceso", "Cumplida"]
        new_status = col_s1.selectbox("Estado", status_opts, index=status_opts.index(obj.status) if obj.status in status_opts else 0)
        new_progress = col_s2.number_input("Avance (%)", value=float(obj.progress), min_value=0.0, max_value=100.0)
        
        col1, col2 = st.columns(2)
        new_start = col1.date_input("Fecha Inicio", value=obj.start_date or datetime.now())
        new_end = col2.date_input("Fecha Fin", value=obj.end_date or datetime.now())
        
        all_res = db.query(Responsible).all()
        res_map = {r.id: r for r in all_res}
        current_ids = [r.id for r in obj.responsibles]
        selected_ids = st.multiselect(
            "Responsables (Workers) Asignados", 
            options=list(res_map.keys()), 
            default=current_ids,
            format_func=lambda x: f"{res_map[x].name} ({res_map[x].role})"
        )
        selected_res = [res_map[rid] for rid in selected_ids]
        
    elif isinstance(obj, Activity):
        all_res = db.query(Responsible).all()
        res_map = {r.id: r for r in all_res}
        current_ids = [r.id for r in getattr(obj, 'supervisors', [])]
        selected_ids = st.multiselect(
            "Supervisores Asignados a la Actividad", 
            options=list(res_map.keys()), 
            default=current_ids,
            format_func=lambda x: f"{res_map[x].name} ({res_map[x].role})"
        )
        selected_res = [res_map[rid] for rid in selected_ids]

    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Guardar", disabled=not is_valid, use_container_width=True, type="primary"):
        try:
            obj.name = new_name
            if hasattr(obj, 'weight'): obj.weight = new_weight
            
            if isinstance(obj, Task):
                obj.status = new_status
                obj.progress = new_progress
                obj.start_date = new_start
                obj.end_date = new_end
                obj.target_date = new_end
                obj.responsibles = selected_res
                obj.responsible_name = ", ".join([r.name for r in selected_res])
            elif isinstance(obj, Activity):
                obj.supervisors = selected_res
                
            db.add(obj) 

            db.commit()
            
            from src.services.calculations import CalculationService
            if isinstance(obj, Task):
                CalculationService.update_all_levels(db, obj.id)
            else:
                CalculationService.recalculate_all(db)
            
            st.toast("✅ Cambios guardados")
            st.rerun()
        except Exception as e:
            db.rollback()
            st.error(f"Error al guardar: {str(e)}")

def _render_item(db, obj, label, prefix=""):
    c1, c2, c3 = st.columns([4, 0.5, 0.5])
    name_display = f"**{prefix} {obj.name}**"
    if hasattr(obj, 'type'): name_display += f" ({obj.type})"
    if hasattr(obj, 'weight'): name_display += f" - {obj.weight}%"
    
    # Mostrar fechas solo para tareas
    if isinstance(obj, Task) and obj.end_date:
        name_display += f" | 🗓️ {obj.start_date.strftime('%d/%m') if obj.start_date else '?'} al {obj.end_date.strftime('%d/%m/%y')}"
    
    c1.markdown(name_display)
    if c2.button("✏️", key=f"e_{obj.id}_{label}_{obj.__tablename__}_{prefix}"): edit_dialog(db, obj, label)
    if c3.button("🗑️", key=f"d_{obj.id}_{label}_{obj.__tablename__}_{prefix}"): confirm_delete(db, obj, label)

def manage_macro_level(db):
    st.subheader("1. Gestión Macro y Políticas")
    with st.expander("➕ Nuevo Plan Macro"):
        with st.form("n_m"):
            name = st.text_input("Nombre (Ej: Gestión TH)")
            st.markdown("<div class='btn-activity'>", unsafe_allow_html=True)
            if st.form_submit_button("Crear"):
                db.add(PlanMacro(name=name, year=2026, objective=""))
                db.commit()
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    
    macros = db.query(PlanMacro).options(joinedload(PlanMacro.policies)).order_by(PlanMacro.year.desc(), PlanMacro.id).all()
    for i, m in enumerate(macros, 1):
        with st.expander(f"📁 {i}. {m.name} ({m.year})", expanded=(i==1)):
            _render_item(db, m, "Macro", prefix="Gestión:")
            st.markdown("---")
            for j, pol in enumerate(m.policies, 1):
                with st.container(): _render_item(db, pol, "Política", prefix=f"{i}.{j}.")
            with st.popover("➕ Política"):
                p_name = st.text_input("Nombre Política", key=f"p_n_{m.id}")
                s_weights = [p.weight for p in m.policies]
                mode, p_weight, is_valid = weight_manager_ui(s_weights, "Política", f"p_w_{m.id}")
                
                st.markdown("<div class='btn-activity'>", unsafe_allow_html=True)
                if st.button("Añadir", disabled=not is_valid, key=f"btn_p_{m.id}"):
                    new_pol = Policy(name=p_name, weight=p_weight, plan_macro_id=m.id)
                    db.add(new_pol)
                    if mode == "Automática": auto_distribute_weights(db, list(m.policies), new_pol)
                    db.commit()
                    from src.services.calculations import CalculationService
                    CalculationService.recalculate_all(db)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

def manage_strategic_level(db):
    st.subheader("2. Planes y Programas")
    
    macros = db.query(PlanMacro).order_by(PlanMacro.year.desc(), PlanMacro.id).all()
    if not macros: return st.info("Sin planes macro configurados.")
    
    m_id = st.selectbox("1. Gestión Macro", options=[m.id for m in macros], format_func=lambda x: next(m.name for m in macros if m.id == x), key="m_st")
    macro = db.query(PlanMacro).filter(PlanMacro.id == m_id).first()
    
    if not macro.policies: return st.info("Cree políticas primero en esta gestión.")
    
    pol_id = st.selectbox("2. Seleccione Política", options=[p.id for p in macro.policies], format_func=lambda x: next(p.name for p in macro.policies if p.id == x), key="p_st")
    pol = db.query(Policy).filter(Policy.id == pol_id).first()
    
    st.write(f"**Elementos de: {pol.name}**")
    items = sorted(pol.strategic_items, key=lambda x: x.id)
    for i, item in enumerate(items, 1):
        with st.container(border=True):
            _render_item(db, item, "Estratégico", prefix=f"{i}.")

    with st.popover("➕ Crear Plan o Programa", use_container_width=True):
        type = st.radio("Tipo", ["Plan", "Programa"], key=f"si_type_{pol.id}")
        name = st.text_input(f"Nombre {type}", key=f"si_name_{pol.id}")
        
        s_weights = [si.weight for si in pol.strategic_items]
        mode, weight, is_valid = weight_manager_ui(s_weights, type, f"si_w_{pol.id}")
        
        if st.button("Guardar", disabled=not is_valid, key=f"btn_si_{pol.id}"):
            new_si = StrategicItem(name=name, type=type, weight=weight, policy_id=pol.id)
            db.add(new_si)
            if mode == "Automática": auto_distribute_weights(db, list(pol.strategic_items), new_si)
            db.commit()
            from src.services.calculations import CalculationService
            CalculationService.recalculate_all(db)
            st.rerun()

def manage_operational_level(db):
    st.subheader("3. Operación (Cronograma de Tareas)")
    
    macros = db.query(PlanMacro).order_by(PlanMacro.year.desc(), PlanMacro.id).all()
    if not macros: return st.info("Sin planes configurados.")
    
    m_id = st.selectbox("1. Gestión Macro", options=[m.id for m in macros], format_func=lambda x: next(m.name for m in macros if m.id == x), key="m_op")
    macro = db.query(PlanMacro).filter(PlanMacro.id == m_id).first()
    
    if not macro.policies: return st.info("Cree políticas primero.")
    
    pol_id = st.selectbox("2. Política", options=[p.id for p in macro.policies], format_func=lambda x: f"{next(p.name for p in macro.policies if p.id == x)} ({next(p.progress for p in macro.policies if p.id == x):.1f}%)", key="p_op")
    policy = db.query(Policy).filter(Policy.id == pol_id).first()
    
    if not policy.strategic_items: return st.info("Cree Planes o Programas primero en esta política.")
    
    si_id = st.selectbox("3. Plan / Programa", options=[si.id for si in policy.strategic_items], format_func=lambda x: f"{next(si.name for si in policy.strategic_items if si.id == x)} ({next(si.progress for si in policy.strategic_items if si.id == x):.1f}%)", key="si_op")
    item = db.query(StrategicItem).options(
        joinedload(StrategicItem.activities).joinedload(Activity.tasks).joinedload(Task.responsibles)
    ).filter(StrategicItem.id == si_id).first()
    
    activities = sorted(item.activities, key=lambda x: x.id)
    for i, act in enumerate(activities, 1):
        with st.expander(f"🎯 {i}. Actividad: {act.name} (Peso: {act.weight:.1f}% | Avance: {format_progress_color(act.progress)})", expanded=True):
            _render_item(db, act, "Actividad", prefix=f"{i}.")
            
            tasks = sorted(act.tasks, key=lambda x: x.id)
            for j, t in enumerate(tasks, 1):
                with st.expander(f"{i}.{j} {t.name} (Peso: {t.weight:.1f}% | Avance: {format_progress_color(t.progress)})"):
                    # Mostrar responsables de forma limpia (sin etiqueta de campo)
                    if t.responsibles:
                        res_html = " ".join([f"<span class='badge' style='background-color:#f1f5f9; color:#475569; border:1px solid #cbd5e1;'>{html.escape(r.name)}</span>" for r in t.responsibles])
                        st.markdown(res_html, unsafe_allow_html=True)
                    else:
                        st.caption("Sin responsables asignados")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_t1, col_t2 = st.columns([5, 1])
                    if col_t1.button("✏️ Editar Tarea", key=f"e_{t.id}_T", use_container_width=True): edit_dialog(db, t, "Tarea")
                    if col_t2.button("🗑️", key=f"d_{t.id}_T", use_container_width=True): confirm_delete(db, t, "Tarea")
            
            with st.popover("➕ Añadir Tarea con Cronograma", use_container_width=True):
                t_name = st.text_input("Descripción Tarea", key=f"n_t_{act.id}")
                
                s_weights = [t.weight for t in act.tasks]
                mode, t_weight, is_valid = weight_manager_ui(s_weights, "Tarea", f"wm_t_{act.id}")
                
                col_d1, col_d2 = st.columns(2)
                t_start = col_d1.date_input("Fecha Inicio", value=datetime.now(), key=f"ds_t_{act.id}")
                t_end = col_d2.date_input("Fecha Fin", value=datetime.now(), key=f"de_t_{act.id}")
                
                # Selección de Responsables
                all_res = db.query(Responsible).all()
                res_map = {r.id: r for r in all_res}
                selected_res_ids = st.multiselect(
                    "Seleccionar Responsables", 
                    options=list(res_map.keys()),
                    format_func=lambda x: f"{res_map[x].name} ({res_map[x].role})",
                    key=f"res_t_{act.id}"
                )
                
                if st.button("Vincular Tarea", disabled=not is_valid, key=f"btn_t_{act.id}"):
                    new_task = Task(
                        name=t_name, 
                        weight=t_weight, 
                        activity_id=act.id, 
                        start_date=t_start, 
                        end_date=t_end, 
                        target_date=t_end,
                        responsible_name=", ".join([res_map[rid].name for rid in selected_res_ids])
                    )
                    new_task.responsibles = [res_map[rid] for rid in selected_res_ids]
                    db.add(new_task)
                    if mode == "Automática": auto_distribute_weights(db, list(act.tasks), new_task)
                    db.commit()
                    from src.services.calculations import CalculationService
                    CalculationService.recalculate_all(db)
                    st.toast("✅ Tarea vinculada exitosamente")
                    st.rerun()

    st.markdown("<div class='btn-activity'>", unsafe_allow_html=True)
    with st.popover("➕ Nueva Actividad", use_container_width=True):
        name = st.text_input("Actividad", key=f"n_act_{item.id}")
        
        s_weights = [a.weight for a in item.activities]
        mode, weight, is_valid = weight_manager_ui(s_weights, "Actividad", f"wm_act_{item.id}")
        
        all_res = db.query(Responsible).all()
        res_map = {r.id: r for r in all_res}
        selected_res_ids = st.multiselect(
            "Seleccionar Supervisores", 
            options=list(res_map.keys()),
            format_func=lambda x: f"{res_map[x].name} ({res_map[x].role})",
            key=f"res_act_{item.id}"
        )
        
        if st.button("Crear", disabled=not is_valid, key=f"btn_act_{item.id}"):
            new_act = Activity(name=name, weight=weight, strategic_item_id=item.id)
            new_act.supervisors = [res_map[rid] for rid in selected_res_ids]
            db.add(new_act)
            if mode == "Automática": auto_distribute_weights(db, list(item.activities), new_act)
            db.commit()
            from src.services.calculations import CalculationService
            CalculationService.recalculate_all(db)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def manage_responsibles_level(db):
    st.subheader("👥 Gestión de Responsables Institucionales")
    
    with st.expander("➕ Nuevo Responsable", expanded=False):
        with st.form("n_res"):
            col1, col2 = st.columns(2)
            name = col1.text_input("Nombre Completo")
            role = col2.text_input("Cargo/Rol")
            dept = st.text_input("Departamento/Área")
            if st.form_submit_button("Registrar Responsable"):
                if name and role:
                    db.add(Responsible(name=name, role=role, department=dept))
                    db.commit()
                    st.success(f"✅ {name} registrado.")
                    st.rerun()
                else:
                    st.error("Nombre y Cargo son obligatorios.")

    responsibles = db.query(Responsible).order_by(Responsible.name).all()
    if not responsibles:
        st.info("No hay responsables registrados.")
        return

    for res in responsibles:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([4, 0.5, 0.5, 0.5])
            
            # Check if linked user exists
            user_linked = db.query(User).filter(User.responsible_id == res.id).first()
            user_info = f" | 🔐 {user_linked.username} ({user_linked.role})" if user_linked else " | 🔓 Sin acceso"
            
            c1.markdown(f"**{res.name}** - {res.role} ({res.department}){user_info}")
            
            if c2.button("🔑", key=f"k_res_{res.id}", help="Gestionar Credenciales"):
                manage_credentials_dialog(db, res)
            if c3.button("✏️", key=f"e_res_{res.id}"):
                edit_responsible_dialog(db, res)
            if c4.button("🗑️", key=f"d_res_{res.id}"):
                confirm_delete(db, res, "Responsable")

@st.dialog("Gestionar Credenciales")
def manage_credentials_dialog(db, res):
    user = db.query(User).filter(User.responsible_id == res.id).first()
    
    if user:
        st.write(f"Usuario vinculado: **{user.username}**")
        st.write(f"Rol actual: **{user.role}**")
        
        new_role = st.selectbox("Cambiar Rol de Permisos", ["Admin", "Supervisor", "Worker"], index=["Admin", "Supervisor", "Worker"].index(user.role))
        new_pass = st.text_input("Cambiar Contraseña", type="password", placeholder="Dejar en blanco para no cambiar")
        
        if st.button("Actualizar Usuario", use_container_width=True):
            user.role = new_role
            if new_pass:
                user.password_hash = AuthService.hash_password(new_pass)
            db.commit()
            st.success("Usuario actualizado correctamente.")
            st.rerun()
            
        if st.button("⚠️ Eliminar Acceso", type="primary", use_container_width=True):
            db.delete(user)
            db.commit()
            st.rerun()
    else:
        st.info("Este responsable no tiene cuenta de acceso al sistema.")
        with st.form("f_new_user"):
            u_name = st.text_input("Usuario (Login)")
            u_email = st.text_input("Email")
            u_pass = st.text_input("Contraseña", type="password")
            u_role = st.selectbox("Rol de Permisos", ["Admin", "Supervisor", "Worker"], index=2)
            
            if st.form_submit_button("Crear Cuenta de Acceso", use_container_width=True):
                if u_name and u_pass:
                    # Check if username exists
                    existing = db.query(User).filter(User.username == u_name).first()
                    if existing:
                        st.error("El nombre de usuario ya está en uso.")
                    else:
                        new_user = User(
                            username=u_name,
                            email=u_email,
                            password_hash=AuthService.hash_password(u_pass),
                            role=u_role,
                            responsible_id=res.id
                        )
                        db.add(new_user)
                        db.commit()
                        st.success(f"Cuenta para {res.name} creada como {u_role}.")
                        st.rerun()
                else:
                    st.error("Usuario y Contraseña son requeridos.")

@st.dialog("Editar Responsable")
def edit_responsible_dialog(db, res):
    with st.form("f_edit_res"):
        res.name = st.text_input("Nombre", value=res.name)
        res.role = st.text_input("Cargo", value=res.role)
        res.department = st.text_input("Departamento", value=res.department)
        if st.form_submit_button("Guardar Cambios"):
            db.commit()
            st.rerun()

def manage_tools_level(db):
    st.subheader("🛠️ Herramientas de Continuidad Estratégica")
    st.write("Duplica toda la estructura institucional para un nuevo año fiscal.")
    
    macros = db.query(PlanMacro).all()
    if not macros:
        st.info("No hay planes registrados para clonar.")
        return

    # Usar mapa de IDs para evitar DetachedInstanceError
    macro_map = {m.id: m for m in macros}
    
    with st.container(border=True):
        src_id = st.selectbox("Plan Origen (Fuente)", options=list(macro_map.keys()), format_func=lambda x: f"{macro_map[x].name} ({macro_map[x].year})")
        src_macro = db.query(PlanMacro).filter(PlanMacro.id == src_id).options(joinedload(PlanMacro.policies)).first()
        
        new_year = st.number_input("Año Destino", value=src_macro.year + 1)
        new_name = st.text_input("Nombre del Nuevo Plan", value=f"{src_macro.name} {new_year}")
        
        if st.button("🚀 Iniciar Clonación Estratégica", use_container_width=True):
            with st.spinner("Clonando estructura multinivel..."):
                tasks_to_bind = []
                try:
                    # 1. Macro (Ensure objective is not None)
                    new_macro = PlanMacro(
                        name=new_name, 
                        year=new_year, 
                        objective=src_macro.objective or ""
                    )
                    
                    # 2. Políticas
                    for p_src in src_macro.policies:
                        p_new = Policy(name=p_src.name, weight=p_src.weight)
                        new_macro.policies.append(p_new)
                        
                        # 3. Items
                        for si_src in p_src.strategic_items:
                            si_new = StrategicItem(name=si_src.name, type=si_src.type, weight=si_src.weight)
                            p_new.strategic_items.append(si_new)
                            
                            # 4. Actividades
                            for act_src in si_src.activities:
                                act_new = Activity(name=act_src.name, weight=act_src.weight)
                                si_new.activities.append(act_new)
                                
                                # 5. Tareas
                                for t_src in act_src.tasks:
                                    # Safe date shifting (handling Feb 29 if necessary)
                                    n_start, n_end = None, None
                                    try:
                                        if t_src.start_date: n_start = t_src.start_date.replace(year=new_year)
                                        if t_src.end_date: n_end = t_src.end_date.replace(year=new_year)
                                    except ValueError:
                                        # Fallback for leap year issues (Feb 29 -> Feb 28)
                                        if t_src.start_date: n_start = t_src.start_date.replace(year=new_year, day=28)
                                        if t_src.end_date: n_end = t_src.end_date.replace(year=new_year, day=28)
                                    
                                    t_new = Task(
                                        name=t_src.name, weight=t_src.weight,
                                        status="Pendiente", progress=0.0,
                                        start_date=n_start, end_date=n_end, target_date=n_end,
                                        responsible_name=t_src.responsible_name
                                    )
                                    act_new.tasks.append(t_new)
                                    # Store mapping to apply responsibles safely after flush
                                    tasks_to_bind.append((t_new, list({r for r in t_src.responsibles})))
                    
                    db.add(new_macro)
                    db.flush() # Forces IDs to be generated without committing
                    
                    # Safe many-to-many binding after IDs exist
                    for t_new, responsibles in tasks_to_bind:
                        t_new.responsibles = responsibles
                        
                    db.commit()
                    st.balloons()
                    st.success(f"✅ ¡Estructura '{new_name}' creada exitosamente para el año {new_year}!")
                    st.info("Nota: Todas las tareas han sido reiniciadas a estado 'Pendiente' con 0% de avance.")
                    st.rerun()
                except Exception as e:
                    db.rollback()
                    st.error(f"Error de Integridad: {str(e)}")
