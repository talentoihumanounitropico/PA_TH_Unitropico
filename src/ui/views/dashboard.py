import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy.orm import joinedload
from src.core.database import SessionLocal
from src.models.entities import PlanMacro, Policy, StrategicItem, Activity, Task
from src.services.calculations import CalculationService
import pandas as pd
from datetime import datetime

def show_executive_dashboard():
    """
    Renders the Executive Dashboard with high-level Business Intelligence metrics.
    Uses interactive Plotly charts for policy compliance and strategic networking.
    """
    # --- High-End Visual Configuration ---
    COLORS = {
        "primary": "#00594e",
        "secondary": "#b5a160",
        "neutral": "#64748b",
        "success": "#10b981",
        "warning": "#f59e0b",
        "danger": "#ef4444"
    }
    
    st.markdown("<div class='corporate-header'>", unsafe_allow_html=True)
    st.title("🏛️ Tablero de Control Estratégico TH")
    st.write("Seguimiento Integral: Gestión Macro, Políticas y Programas")
    st.markdown("</div>", unsafe_allow_html=True)
    
    db = SessionLocal()
    try:
        # Carga completa para análisis multinivel
        macros = db.query(PlanMacro).options(
            joinedload(PlanMacro.policies).joinedload(Policy.strategic_items)
        ).all()
        
        if not macros: return st.info("No hay datos registrados para análisis.")

        # --- FILTROS DE FÁCIL ACCESO ---
        st.markdown("### 📊 Filtros de Consulta")
        with st.container(border=True):
            f1, f2, f3, f4 = st.columns(4)
            all_years = sorted(list(set([m.year for m in macros] + [datetime.now().year])))
            sel_year = f1.selectbox("📅 Año", all_years, index=all_years.index(datetime.now().year) if datetime.now().year in all_years else 0)
            sel_semester = f2.selectbox("🌓 Semestre", ["Todos", "Semestre A", "Semestre B"])
            sel_quarter = f3.selectbox("📊 Trimestre", ["Todos", "T1", "T2", "T3", "T4"])
            months_names = ["Todos", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            sel_month = f4.selectbox("📆 Mes", months_names)

        macro = next((m for m in macros if m.year == sel_year), macros[0])

        # Recolección de datos filtrados
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
                                "Programa/Plan": si.name,
                                "Avance": t.progress,
                                "Estado": t.status,
                                "Fecha": t.end_date
                            })
        
        df_f = pd.DataFrame(tasks_data)

        # --- SECCIÓN 1: GESTIÓN MACRO (NIVEL 5) ---
        st.markdown(f"## 🏢 {macro.name}")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Avance Plan Macro", f"{macro.progress:.1f}%")
        k2.metric("Cumplimiento Periodo", f"{df_f['Avance'].mean() if not df_f.empty else 0:.1f}%")
        k3.metric("Tareas Activas", len(df_f))
        k4.metric("Políticas en Curso", len(macro.policies))

        st.divider()

        # --- SECCIÓN 2: POLÍTICAS Y PROGRAMAS (NIVELES 4 Y 3) ---
        col_left, col_right = st.columns([1, 1.2])

        with col_left:
            # Velocímetro Principal: Gestión Institucional
            _, color = CalculationService.get_semaforo(macro.progress)
            fig_macro = go.Figure(go.Indicator(
                mode = "gauge+number", value = macro.progress,
                number={'suffix': "%", 'valueformat': ".1f"},
                title = {'text': "Avance Consolidado TH", 'font': {'size': 18, 'color': COLORS["primary"]}},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': color},
                    'steps': [
                        {'range': [0, 60], 'color': "#fee2e2"},
                        {'range': [60, 80], 'color': "#fef3c7"},
                        {'range': [80, 100], 'color': "#d1fae5"}
                    ]
                }
            ))
            fig_macro.update_layout(height=350, margin=dict(l=30, r=30, t=50, b=20), template="plotly_white")
            st.plotly_chart(fig_macro, use_container_width=True)

        with col_right:
            # Avance por Política (Horizontal Bar - Fácil de entender)
            pol_list = [{"Nombre": p.name, "Avance": p.progress} for p in macro.policies]
            df_pol = pd.DataFrame(pol_list).sort_values("Avance", ascending=True)
            
            fig_pol = px.bar(
                df_pol, x='Avance', y='Nombre', orientation='h',
                title="Cumplimiento por Política Institucional",
                color='Avance',
                color_continuous_scale=[[0, '#ef4444'], [0.5, '#f59e0b'], [1, '#10b981']],
                template="plotly_white"
            )
            fig_pol.update_traces(texttemplate='%{x:.1f}%', textposition='outside')
            fig_pol.update_layout(showlegend=False, xaxis=dict(range=[0, 110]), yaxis=dict(title=""))
            st.plotly_chart(fig_pol, use_container_width=True)

        st.divider()

        # --- SECCIÓN 3: DESGLOSE DE PROGRAMAS Y PLANES ---
        st.subheader("🧩 Desglose Estratégico (Políticas > Programas > Planes)")
        
        # Gráfico Sunburst: Lo más fácil para ver jerarquías
        if not df_f.empty:
            fig_sun = px.sunburst(
                df_f, path=['Política', 'Programa/Plan'], values='Avance',
                title="Mapa de Programas y Planes por Política",
                color='Avance',
                color_continuous_scale='RdYlGn',
                template="plotly_white",
                hover_data={'Avance': ':.1f'}
            )
            fig_sun.update_traces(
                texttemplate="<b>%{label}</b>",
                hovertemplate="<b>%{label}</b><br>Avance: %{color:.1f}%<extra></extra>"
            )
            fig_sun.update_layout(margin=dict(t=40, l=0, r=0, b=0), height=500)
            st.plotly_chart(fig_sun, use_container_width=True)
        else:
            st.info("No hay datos suficientes para el desglose detallado en este periodo.")

        # --- SECCIÓN 4: TENDENCIA TEMPORAL ---
        if not df_f.empty:
            st.subheader("📈 Evolución de la Gestión")
            df_f['Mes'] = df_f['Fecha'].dt.strftime('%b %Y')
            df_trend = df_f.groupby('Mes')['Avance'].mean().reset_index()
            
            fig_trend = px.line(
                df_trend, x='Mes', y='Avance', markers=True, text='Avance',
                title="Tendencia de Avance del Periodo",
                template="plotly_white"
            )
            fig_trend.update_traces(line_color=COLORS["primary"], line_width=4, texttemplate='%{y:.1f}%', textposition='top center')
            fig_trend.update_layout(yaxis=dict(range=[0, 115]))
            st.plotly_chart(fig_trend, use_container_width=True)

    finally:
        db.close()
