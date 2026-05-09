import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy.orm import joinedload
from src.core.database import SessionLocal
from src.models.entities import Task, Responsible, Activity, StrategicItem, Policy, PlanMacro
import pandas as pd
import html

def show_reports_view():
    """
    Personal Productivity Dashboard.
    Analyzes institutional efficiency per responsible person using ranking and sunburst charts.
    """
    # --- High-End Visual Configuration ---
    COLORS = {
        "primary": "#00594e",
        "secondary": "#b5a160",
        "accent": "#1e293b",
        "success": "#10b981",
        "pending": "#94a3b8",
        "process": "#3b82f6"
    }
    
    st.markdown("<div class='corporate-header'>", unsafe_allow_html=True)
    st.title("📈 Dashboard de Seguimiento Personal")
    st.write("Análisis de alta precisión sobre la productividad institucional")
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
            joinedload(Responsible.tasks).joinedload(Task.activity)
            .joinedload(Activity.strategic_item).joinedload(StrategicItem.policy)
            .joinedload(Policy.plan_macro)
        ).all()

        if not responsibles:
            st.info("No hay responsables registrados.")
            return

        # Transformación de datos FILTRADA POR AÑO
        res_list = []
        task_list = []
        for r in responsibles:
            # Filtrar solo tareas que pertenezcan al año seleccionado
            year_tasks = [t for t in r.tasks if t.activity.strategic_item.policy.plan_macro.year == sel_year]
            
            t_count = len(year_tasks)
            if t_count == 0: continue # No mostrar si no tiene tareas en este año
            
            avg_eff = sum(t.progress for t in year_tasks) / t_count
            res_list.append({
                "Nombre": r.name,
                "Cargo": r.role,
                "Total": t_count,
                "Eficiencia": avg_eff,
                "Cumplidas": sum(1 for t in year_tasks if t.status == "Cumplida"),
                "Proceso": sum(1 for t in year_tasks if t.status == "En Proceso"),
                "Pendientes": sum(1 for t in year_tasks if t.status == "Pendiente")
            })
            for t in year_tasks:
                task_list.append({
                    "Responsable": r.name, 
                    "Estado": t.status, 
                    "Avance": t.progress, 
                    "Tarea": t.name,
                    "Peso": t.weight
                })

        if not res_list:
            st.warning(f"No se registran tareas asignadas para el año {sel_year}.")
            return

        df_res = pd.DataFrame(res_list)
        df_tasks = pd.DataFrame(task_list)

        # 1. KPIs Ejecutivos
        st.markdown("<br>", unsafe_allow_html=True)
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Talento Humano", len(df_res))
        kpi2.metric("Eficiencia Institucional", f"{df_res['Eficiencia'].mean():.1f}%")
        kpi3.metric("Operaciones en Curso", df_res['Total'].sum())
        
        best_idx = df_res['Eficiencia'].idxmax()
        kpi4.metric("Líder de Gestión", df_res.loc[best_idx]['Nombre'].split()[-1], delta="TOP")

        st.divider()

        # 2. Bloque de Visualización Principal
        col_viz_1, col_viz_2 = st.columns([1.6, 1])
        
        with col_viz_1:
            df_res_sorted = df_res.sort_values("Eficiencia", ascending=True)
            fig_rank = px.bar(
                df_res_sorted, x="Eficiencia", y="Nombre",
                orientation='h', title="🏆 Ranking de Cumplimiento Institucional",
                color="Eficiencia",
                color_continuous_scale=[[0, '#f1f5f9'], [0.5, '#b5a160'], [1, '#00594e']],
                template="plotly_white"
            )
            fig_rank.update_traces(texttemplate='%{x:.1f}%', textposition='outside')
            fig_rank.update_layout(showlegend=False, xaxis=dict(range=[0, 110]), height=400)
            st.plotly_chart(fig_rank, use_container_width=True)

        with col_viz_2:
            fig_sun = px.sunburst(
                df_tasks, path=['Estado', 'Responsable'], values='Avance',
                title="🎯 Arquitectura de Operación",
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
        selected_name = st.selectbox("Seleccione el responsable", df_res['Nombre'].tolist())
        
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
            audit_tasks = df_tasks[df_tasks['Responsable'] == selected_name]
            st.dataframe(audit_tasks[['Tarea', 'Estado', 'Avance']], hide_index=True, use_container_width=True)

    finally:
        db.close()
