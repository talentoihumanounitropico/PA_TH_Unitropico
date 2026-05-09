import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy.orm import joinedload
from src.core.database import SessionLocal
from src.models.entities import Task, Responsible, Activity, StrategicItem, Policy, PlanMacro
import pandas as pd
import html

# --- High-End Visual Configuration ---
COLORS = {
    "primary": "#00594e",
    "secondary": "#b5a160",
    "accent": "#1e293b",
    "success": "#10b981",
    "pending": "#94a3b8",
    "process": "#3b82f6"
}

def render_tab_content(df_res, df_items, role_label, item_label):
    if df_res.empty:
        st.warning(f"No hay datos registrados para {role_label} en este periodo.")
        return
        
    # 1. KPIs Ejecutivos
    st.markdown("<br>", unsafe_allow_html=True)
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric(f"Total {role_label}", len(df_res))
    kpi2.metric("Eficiencia Institucional", f"{df_res['Eficiencia'].mean():.1f}%")
    kpi3.metric(f"{item_label}s a cargo", df_res['Total'].sum())
    
    best_idx = df_res['Eficiencia'].idxmax()
    kpi4.metric(f"Líder de {role_label}", df_res.loc[best_idx]['Nombre'].split()[-1], delta="TOP")

    st.divider()

    # 2. Bloque de Visualización Principal
    col_viz_1, col_viz_2 = st.columns([1.6, 1])
    
    with col_viz_1:
        df_res_sorted = df_res.sort_values("Eficiencia", ascending=True)
        fig_rank = px.bar(
            df_res_sorted, x="Eficiencia", y="Nombre",
            orientation='h', title=f"🏆 Ranking de Eficiencia - {role_label}",
            color="Eficiencia",
            color_continuous_scale=[[0, '#f1f5f9'], [0.5, '#b5a160'], [1, '#00594e']],
            template="plotly_white"
        )
        fig_rank.update_traces(texttemplate='%{x:.1f}%', textposition='outside')
        fig_rank.update_layout(showlegend=False, xaxis=dict(range=[0, 110]), height=400)
        st.plotly_chart(fig_rank, use_container_width=True)

    with col_viz_2:
        fig_sun = px.sunburst(
            df_items, path=['Estado', 'Responsable'], values='Avance',
            title=f"🎯 Arquitectura de {item_label}s",
            color='Estado',
            color_discrete_map={"Cumplida": COLORS["primary"], "En Proceso": COLORS["secondary"], "Pendiente": COLORS["pending"]},
            template="plotly_white"
        )
        fig_sun.update_traces(
            texttemplate="<b>%{label}</b>",
            hovertemplate="<b>%{label}</b><br>Suma de Avances: %{value:.1f}%<extra></extra>"
        )
        fig_sun.update_layout(height=400)
        st.plotly_chart(fig_sun, use_container_width=True)

    st.divider()

    # 3. Ficha de Auditoría Individual
    st.subheader("🔍 Auditoría de Gestión Individual")
    selected_name = st.selectbox("Seleccione el responsable", df_res['Nombre'].tolist(), key=f"sel_{role_label}")
    
    res_row = df_res[df_res['Nombre'] == selected_name].iloc[0]
    col_aud_1, col_aud_2 = st.columns([1, 2])
    
    with col_aud_1:
        st.markdown(f"""
        <div style='background: white; padding: 25px; border-radius: 20px; border-top: 8px solid {COLORS["primary"]}; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);'>
            <h2 style='margin:0; color: {COLORS["accent"]};'>{html.escape(selected_name)}</h2>
            <p style='color: #64748b;'>{html.escape(res_row['Cargo'])}</p>
            <hr style='border: 0.5px solid #f1f5f9;'>
            <div style='display: flex; justify-content: space-between; margin-bottom: 5px;'><span>Cumplidas:</span><b>{res_row['Cumplidas']}</b></div>
            <div style='display: flex; justify-content: space-between; margin-bottom: 5px;'><span>En Proceso:</span><b>{res_row['Proceso']}</b></div>
            <div style='display: flex; justify-content: space-between; margin-bottom: 15px;'><span>Pendientes:</span><b>{res_row['Pendientes']}</b></div>
            <div style='text-align: center;'>
                <p style='margin:0; font-size: 0.8rem; color: #64748b;'>EFICIENCIA</p>
                <h1 style='margin:0; color: {COLORS["primary"]};'>{res_row['Eficiencia']:.1f}%</h1>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_aud_2:
        audit_items = df_items[df_items['Responsable'] == selected_name]
        st.dataframe(audit_items[[item_label, 'Estado', 'Avance']], hide_index=True, use_container_width=True)


def show_reports_view():
    """
    Personal Productivity Dashboard.
    Analyzes institutional efficiency per responsible person using ranking and sunburst charts.
    """
    st.markdown("<div class='corporate-header'>", unsafe_allow_html=True)
    st.title("📈 Dashboard de Seguimiento Personal")
    st.write("Análisis de alta precisión sobre la productividad institucional dividida por roles")
    st.markdown("</div>", unsafe_allow_html=True)
    
    db = SessionLocal()
    try:
        # 0. FILTRO DE AÑO (Para soporte multi-clonación)
        macros = db.query(PlanMacro).all()
        if not macros:
            st.info("No hay planes registrados para análisis.")
            return
            
        all_years = sorted(list(set([m.year for m in macros])))
        sel_year = st.selectbox("📅 Seleccione Año de Gestión", all_years, index=len(all_years)-1)

        # Carga optimizada
        responsibles = db.query(Responsible).options(
            joinedload(Responsible.tasks).joinedload(Task.activity).joinedload(Activity.strategic_item).joinedload(StrategicItem.policy).joinedload(Policy.plan_macro),
            joinedload(Responsible.supervised_activities).joinedload(Activity.strategic_item).joinedload(StrategicItem.policy).joinedload(Policy.plan_macro)
        ).all()

        if not responsibles:
            st.info("No hay responsables registrados.")
            return

        res_workers = []
        tasks_list = []
        
        res_supervisors = []
        acts_list = []

        def get_act_status(prog):
            if prog >= 99.9: return "Cumplida"
            if prog > 0.0: return "En Proceso"
            return "Pendiente"

        for r in responsibles:
            # Procesamiento de Operativos (Workers)
            year_tasks = [
                t for t in r.tasks 
                if getattr(getattr(getattr(getattr(t, 'activity', None), 'strategic_item', None), 'policy', None), 'plan_macro', None) is not None 
                and t.activity.strategic_item.policy.plan_macro.year == sel_year
            ]
            
            if year_tasks:
                t_count = len(year_tasks)
                avg_eff = sum(t.progress for t in year_tasks) / t_count
                res_workers.append({
                    "Nombre": r.name,
                    "Cargo": r.role,
                    "Total": t_count,
                    "Eficiencia": avg_eff,
                    "Cumplidas": sum(1 for t in year_tasks if t.status == "Cumplida"),
                    "Proceso": sum(1 for t in year_tasks if t.status == "En Proceso"),
                    "Pendientes": sum(1 for t in year_tasks if t.status == "Pendiente")
                })
                for t in year_tasks:
                    tasks_list.append({"Responsable": r.name, "Estado": t.status, "Avance": t.progress, "Tarea": t.name, "Peso": t.weight})

            # Procesamiento de Tácticos (Supervisores)
            year_acts = [
                a for a in r.supervised_activities 
                if getattr(getattr(getattr(a, 'strategic_item', None), 'policy', None), 'plan_macro', None) is not None 
                and a.strategic_item.policy.plan_macro.year == sel_year
            ]
            
            if year_acts:
                a_count = len(year_acts)
                avg_eff = sum(a.progress for a in year_acts) / a_count
                res_supervisors.append({
                    "Nombre": r.name,
                    "Cargo": r.role,
                    "Total": a_count,
                    "Eficiencia": avg_eff,
                    "Cumplidas": sum(1 for a in year_acts if get_act_status(a.progress) == "Cumplida"),
                    "Proceso": sum(1 for a in year_acts if get_act_status(a.progress) == "En Proceso"),
                    "Pendientes": sum(1 for a in year_acts if get_act_status(a.progress) == "Pendiente")
                })
                for a in year_acts:
                    acts_list.append({"Responsable": r.name, "Estado": get_act_status(a.progress), "Avance": a.progress, "Actividad": a.name, "Peso": a.weight})

        df_res_w = pd.DataFrame(res_workers)
        df_t = pd.DataFrame(tasks_list)
        
        df_res_s = pd.DataFrame(res_supervisors)
        df_a = pd.DataFrame(acts_list)

        tab1, tab2 = st.tabs(["🧑‍💻 Gestión Operativa (Workers)", "👨‍💼 Gestión Táctica (Supervisores)"])
        
        with tab1:
            render_tab_content(df_res_w, df_t, "Operativos", "Tarea")
            
        with tab2:
            render_tab_content(df_res_s, df_a, "Supervisores", "Actividad")

    finally:
        db.close()
