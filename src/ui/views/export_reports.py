import streamlit as st
import calendar
from datetime import datetime, date
from src.core.database import SessionLocal
from src.services.word_exporter import WordExporterService

def show_export_reports_view():
    """
    Renders the UI for filtering and exporting Word reports.
    """
    st.markdown("<div class='corporate-header'>", unsafe_allow_html=True)
    st.title("📄 Reportes TH (Exportación a Word)")
    st.write("Genere informes ejecutivos filtrados por periodo temporal.")
    st.markdown("</div>", unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader("Filtros de Exportación")
        
        c1, c2 = st.columns(2)
        with c1:
            current_year = datetime.now().year
            years = list(range(2024, 2036))
            selected_year = st.selectbox("Año", years, index=years.index(current_year) if current_year in years else 0)
            
        with c2:
            filter_type = st.selectbox("Tipo de Filtro", ["Año Completo", "Semestre", "Trimestre", "Mes"])
            
        # Dynamic second filter
        start_dt = None
        end_dt = None
        filter_label = ""
        
        if filter_type == "Año Completo":
            start_dt = datetime(selected_year, 1, 1)
            end_dt = datetime(selected_year, 12, 31, 23, 59, 59)
            filter_label = f"Año {selected_year}"
            
        elif filter_type == "Semestre":
            sem = st.selectbox("Seleccione el Semestre", ["Semestre 1 (Ene-Jun)", "Semestre 2 (Jul-Dic)"])
            if "1" in sem:
                start_dt = datetime(selected_year, 1, 1)
                end_dt = datetime(selected_year, 6, 30, 23, 59, 59)
                filter_label = f"Primer Semestre {selected_year}"
            else:
                start_dt = datetime(selected_year, 7, 1)
                end_dt = datetime(selected_year, 12, 31, 23, 59, 59)
                filter_label = f"Segundo Semestre {selected_year}"
                
        elif filter_type == "Trimestre":
            trim = st.selectbox("Seleccione el Trimestre", ["Q1 (Ene-Mar)", "Q2 (Abr-Jun)", "Q3 (Jul-Sep)", "Q4 (Oct-Dic)"])
            if "Q1" in trim:
                start_dt = datetime(selected_year, 1, 1)
                end_dt = datetime(selected_year, 3, 31, 23, 59, 59)
            elif "Q2" in trim:
                start_dt = datetime(selected_year, 4, 1)
                end_dt = datetime(selected_year, 6, 30, 23, 59, 59)
            elif "Q3" in trim:
                start_dt = datetime(selected_year, 7, 1)
                end_dt = datetime(selected_year, 9, 30, 23, 59, 59)
            else:
                start_dt = datetime(selected_year, 10, 1)
                end_dt = datetime(selected_year, 12, 31, 23, 59, 59)
            filter_label = f"Trimestre {trim.split(' ')[0]} del {selected_year}"
            
        elif filter_type == "Mes":
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_str = st.selectbox("Seleccione el Mes", meses)
            mes_idx = meses.index(mes_str) + 1
            
            # Find the last day of the selected month
            last_day = calendar.monthrange(selected_year, mes_idx)[1]
            
            start_dt = datetime(selected_year, mes_idx, 1)
            end_dt = datetime(selected_year, mes_idx, last_day, 23, 59, 59)
            filter_label = f"Mes de {mes_str} del {selected_year}"

        st.info(f"📅 Rango seleccionado: {start_dt.strftime('%d/%m/%Y')} al {end_dt.strftime('%d/%m/%Y')}")

        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("⚙️ Procesar Datos para Reporte", use_container_width=True, type="primary"):
            with st.spinner("Generando documento, analizando gráficos y jerarquías... Esto puede tomar unos segundos."):
                db = SessionLocal()
                try:
                    bio = WordExporterService.generate_report(db, start_dt, end_dt, filter_label)
                    
                    st.success("✅ Reporte generado exitosamente.")
                    
                    filename = f"reporte_TH_{filter_label.replace(' ', '_')}.docx"
                    
                    st.download_button(
                        label="📥 Descargar Reporte en Word",
                        data=bio,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Ocurrió un error al generar el reporte: {str(e)}")
                finally:
                    db.close()
