import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy.orm import joinedload
from src.core.database import SessionLocal
from src.models.entities import PlanMacro, Policy, StrategicItem, Activity, Task
import pandas as pd
from datetime import datetime

def show_public_landing():
    """
    Renders the Advanced Public Dashboard with filters and multiple sections.
    """
    st.markdown("""
        <div class="hero-banner">
            <h1 class="hero-title">Gestión Estratégica Institucional</h1>
            <p class="hero-subtitle">Transparencia y avance en la ejecución del Plan Estratégico de Talento Humano en Unitrópico. Conoce cómo estamos construyendo una mejor institución.</p>
        </div>
    """, unsafe_allow_html=True)

    db = SessionLocal()
    try:
        # 1. Extracción profunda de datos
        macros = db.query(PlanMacro).options(
            joinedload(PlanMacro.policies).joinedload(Policy.strategic_items).joinedload(StrategicItem.activities).joinedload(Activity.tasks)
        ).all()
        
        if not macros:
            st.info("No hay datos consolidados disponibles en este momento.")
            return

        # 2. Panel de Filtros Interactivos
        st.markdown("<div class='filter-container'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: var(--primary-color); margin-bottom: 1rem;'>🔎 Explorador Estratégico</h4>", unsafe_allow_html=True)
        f1, f2, f3, f4 = st.columns(4)
        
        all_years = sorted(list(set([m.year for m in macros] + [datetime.now().year])))
        current_year = datetime.now().year
        sel_year = f1.selectbox("📅 Año Vigencia", all_years, index=all_years.index(current_year) if current_year in all_years else 0)
        
        sel_semester = f2.selectbox("🌓 Semestre", ["Todos", "Semestre A", "Semestre B"])
        sel_quarter = f3.selectbox("📊 Trimestre", ["Todos", "T1", "T2", "T3", "T4"])
        months_names = ["Todos", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        sel_month = f4.selectbox("📆 Mes", months_names)
        st.markdown("</div>", unsafe_allow_html=True)

        # 3. Procesamiento y Filtrado de Datos
        macro = next((m for m in macros if m.year == sel_year), macros[-1])
        
        tasks_data = []
        
        for pol in macro.policies:
            for si in pol.strategic_items:
                for act in si.activities:
                    for t in act.tasks:
                        if not t.end_date: continue
                        match = True
                        if sel_semester == "Semestre A" and not (1 <= t.end_date.month <= 6): match = False
                        if sel_semester == "Semestre B" and not (7 <= t.end_date.month <= 12): match = False
                        if sel_quarter != "Todos" and f"T{(t.end_date.month-1)//3+1}" != sel_quarter: match = False
                        if sel_month != "Todos" and months_names[t.end_date.month] != sel_month: match = False
                        
                        if match:
                            tasks_data.append({
                                "Política": pol.name,
                                "Programa": si.name,
                                "Avance": t.progress,
                                "Fecha": t.end_date
                            })
                            
        df_f = pd.DataFrame(tasks_data)
        
        # Recalcular métricas macro basadas en los filtros
        if df_f.empty:
            filtered_macro_progress = 0
            filtered_tasks_count = 0
        else:
            filtered_macro_progress = df_f['Avance'].mean()
            filtered_tasks_count = len(df_f)

        # SECCIÓN A: RESUMEN DE IMPACTO
        st.markdown("<h2 class='section-title'>📊 Resumen de Impacto</h2>", unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
                <div class="glass-card" style="text-align: center; padding: 1.5rem;">
                    <div class="glass-metric" style="font-size: 2.5rem;">{macro.progress:.1f}%</div>
                    <div class="glass-label" style="font-size: 0.95rem;">Avance Plan Macro</div>
                </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
                <div class="glass-card" style="text-align: center; padding: 1.5rem;">
                    <div class="glass-metric" style="font-size: 2.5rem;">{filtered_macro_progress:.1f}%</div>
                    <div class="glass-label" style="font-size: 0.95rem;">Cumplimiento Periodo</div>
                </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
                <div class="glass-card" style="text-align: center; padding: 1.5rem;">
                    <div class="glass-metric" style="font-size: 2.5rem;">{len(macro.policies)}</div>
                    <div class="glass-label" style="font-size: 0.95rem;">Políticas Activas</div>
                </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
                <div class="glass-card" style="text-align: center; padding: 1.5rem;">
                    <div class="glass-metric" style="font-size: 2.5rem;">{filtered_tasks_count}</div>
                    <div class="glass-label" style="font-size: 0.95rem;">Hitos Activos</div>
                </div>
            """, unsafe_allow_html=True)

        # Velocímetro
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = macro.progress,
            number={'suffix': "%", 'valueformat': ".1f"},
            title = {'text': "Avance Institucional Consolidado", 'font': {'size': 20, 'color': '#00594e'}},
            gauge = {
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "#00594e"},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 40], 'color': '#fee2e2'},
                    {'range': [40, 75], 'color': '#fef3c7'},
                    {'range': [75, 100], 'color': '#d1fae5'}
                ],
            }
        ))
        fig_gauge.update_layout(height=350, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "#1e293b", 'family': "Outfit"})
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 3rem 0; border: none; height: 1px; background-color: #e2e8f0;'/>", unsafe_allow_html=True)

        if not df_f.empty:
            # SECCIÓN B: DISTRIBUCIÓN ESTRATÉGICA
            st.markdown("<h2 class='section-title'>🧩 Distribución Estratégica</h2>", unsafe_allow_html=True)
            col_b1, col_b2 = st.columns([1.2, 1])
            
            with col_b1:
                st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                # Agregar peso unitario para calcular áreas
                df_f['Peso'] = 1 
                
                fig_tree = px.treemap(
                    df_f, 
                    path=[px.Constant("Visión Global"), 'Política', 'Programa'], 
                    values='Peso',
                    color='Avance',
                    color_continuous_scale=[[0, '#fee2e2'], [0.5, '#fef3c7'], [1, '#d1fae5']], # Colores pastel semáforo
                    title="Mapa de Calor Estratégico (Tamaño = Volumen de Tareas)"
                )
                
                # Diseño ejecutivo con texto enriquecido
                fig_tree.update_traces(
                    texttemplate="<span style='font-size:14px; font-weight:bold;'>%{label}</span><br>Avance: %{color:.1f}%",
                    hovertemplate="<b>%{label}</b><br>Avance Promedio: %{color:.1f}%<br>Total Hitos: %{value}<extra></extra>",
                    marker=dict(line=dict(color='#ffffff', width=2))
                )
                
                fig_tree.update_layout(
                    margin=dict(t=40, l=10, r=10, b=10), 
                    height=450, 
                    paper_bgcolor="rgba(0,0,0,0)", 
                    font={'family': "Outfit", 'color': '#1e293b'}
                )
                st.plotly_chart(fig_tree, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col_b2:
                st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                # Avance real jerárquico por política (igual al dashboard interno)
                pol_list = [{"Nombre": p.name, "Avance": p.progress} for p in macro.policies]
                df_pol = pd.DataFrame(pol_list).sort_values("Avance", ascending=True)
                fig_bar = px.bar(
                    df_pol, x='Avance', y='Nombre', orientation='h',
                    title="Cumplimiento por Política Institucional",
                    color='Avance',
                    color_continuous_scale=[[0, '#ef4444'], [0.5, '#f59e0b'], [1, '#10b981']]
                )
                fig_bar.update_traces(texttemplate='%{x:.1f}%', textposition='outside')
                fig_bar.update_layout(showlegend=False, xaxis=dict(range=[0, 110]), yaxis=dict(title=""), height=450, paper_bgcolor="rgba(0,0,0,0)", font={'family': "Outfit"})
                st.plotly_chart(fig_bar, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<hr style='margin: 3rem 0; border: none; height: 1px; background-color: #e2e8f0;'/>", unsafe_allow_html=True)

            # SECCIÓN C: TENDENCIA TEMPORAL
            st.markdown("<h2 class='section-title'>📈 Línea de Tiempo y Tendencia</h2>", unsafe_allow_html=True)
            st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
            df_f['Mes_Año'] = df_f['Fecha'].dt.strftime('%Y-%m')
            df_trend = df_f.groupby('Mes_Año')['Avance'].mean().reset_index()
            # Sort chronologically
            df_trend = df_trend.sort_values('Mes_Año')
            
            fig_trend = px.line(
                df_trend, x='Mes_Año', y='Avance', markers=True, text='Avance',
                title="Evolución de Avance en el Periodo Seleccionado",
            )
            fig_trend.update_traces(line_color="#b5a160", line_width=4, marker=dict(size=10, color="#00594e"), texttemplate='%{y:.1f}%', textposition='top center')
            fig_trend.update_layout(xaxis_title="Mes", yaxis_title="Avance Promedio (%)", yaxis=dict(range=[0, 115]), height=400, paper_bgcolor="rgba(0,0,0,0)", font={'family': "Outfit"})
            st.plotly_chart(fig_trend, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("⚠️ No se encontraron hitos estratégicos para el periodo y filtros seleccionados. Intenta ampliar tu búsqueda.")

        st.markdown("""
            <div style="text-align: center; margin-top: 3rem; color: #64748b; font-size: 0.9rem;">
                © 2026 Unitrópico - Sistema Integral de Seguimiento Estratégico de Talento Humano.<br>
                Información de acceso público. Para detalles operativos, inicie sesión.
            </div>
        """, unsafe_allow_html=True)

    finally:
        db.close()
