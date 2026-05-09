import streamlit as st
from src.core.database import engine, Base, SessionLocal
from src.services.auth import AuthService
from src.models.entities import User
from src.ui.views.admin import show_admin_view
from src.ui.views.dashboard import show_executive_dashboard
from src.ui.views.supervisor import show_supervisor_view
from src.ui.views.alerts import show_alerts_view
from src.ui.views.reports import show_reports_view
from src.ui.views.mosaico import show_mosaico_view
from src.ui.views.export_reports import show_export_reports_view
from src.ui.views.public_landing import show_public_landing
import os
from PIL import Image

# Initialize database schema
Base.metadata.create_all(bind=engine)

# Seed initial responsibles if they don't exist
def seed_responsibles():
    from src.models.entities import Responsible
    db = SessionLocal()
    if db.query(Responsible).count() == 0:
        initial_res = [
            Responsible(name="Ing. Claudia Morales", role="Coordinadora de Talento Humano", department="Talento Humano"),
            Responsible(name="Dr. Ricardo Serna", role="Director Administrativo", department="Dirección Administrativa"),
            Responsible(name="Lic. Sonia Pinzón", role="Analista de Nómina", department="Talento Humano")
        ]
        db.add_all(initial_res)
        db.commit()
    db.close()

seed_responsibles()

# Page configuration with Institutional Identity
favicon_path = "assets/images/favicon.png"
page_icon = "🏛️"
if os.path.exists(favicon_path):
    page_icon = Image.open(favicon_path)

st.set_page_config(
    page_title="Plataforma TH | Unitrópico",
    page_icon=page_icon,
    layout="wide"
)

# Initialize authentication session
AuthService.init_session()

# Load corporate CSS
@st.cache_data
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            return f"<style>{f.read()}</style>"
    return ""

style_html = local_css("assets/style.css")
st.markdown(style_html, unsafe_allow_html=True)

def main():
    """
    Main entry point for the Streamlit application.
    Orchestrates authentication flow and high-level view routing.
    """
    if not AuthService.is_authenticated():
        render_sidebar_login()
        show_public_landing()
    else:
        show_app()

def render_sidebar_login():
    """
    Renders the secure login portal in the sidebar.
    """
    with st.sidebar:
        logo_path = "assets/images/logo.png"
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
            
        st.markdown("<div class='auth-sidebar'>", unsafe_allow_html=True)
        st.markdown("<h3 class='auth-sidebar-title'>🔐 Acceso Seguro</h3>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 0.85rem; color: #64748b;'>Portal exclusivo para personal operativo.</p>", unsafe_allow_html=True)
        
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        
        if st.button("Ingresar al Portal", use_container_width=True):
            db = SessionLocal()
            if AuthService.login(db, username, password):
                st.toast("✅ Bienvenido")
                st.rerun()
            else:
                st.error("Credenciales inválidas")
            db.close()
        st.markdown("</div>", unsafe_allow_html=True)

def show_app():
    """
    Renders the main application shell with structured navigation and role-based access.
    """
    user_role = st.session_state.get('role')
    user_name = st.session_state.get('username')

    with st.sidebar:
        logo_path = "assets/images/logo.png"
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
            
        st.markdown(f"### 👤 {user_name}")
        st.caption(f"Rol: **{user_role}**")
        st.divider()
        
    # --- Structured Navigation ---
    if 'choice' not in st.session_state:
        st.session_state.choice = "🏠 Dashboard"

    with st.sidebar:
        st.markdown("### 📊 INTELIGENCIA")
        if st.button("🏠 Dashboard Institucional", use_container_width=True):
            st.session_state.choice = "🏠 Dashboard"
        if st.button("📈 Dashboard Personal", use_container_width=True):
            st.session_state.choice = "📈 Dashboard Personal"
        if st.button("🧩 Mosaico TH", use_container_width=True):
            st.session_state.choice = "🧩 Mosaico TH"
        if st.button("📄 Reportes TH (Exportar)", use_container_width=True):
            st.session_state.choice = "📄 Reportes TH"
        
        st.divider()
        
        if user_role == "Admin":
            st.markdown("### ⚙️ ADMINISTRACIÓN")
            if st.button("⚙️ Configuración Admin", use_container_width=True):
                st.session_state.choice = "⚙️ Configuración Admin"
            st.divider()

        st.markdown("### 🧐 SEGUIMIENTO")
        if st.button("🧐 Gestión de tareas", use_container_width=True):
            st.session_state.choice = "🧐 Gestión de tareas"
        if st.button("🚨 Centro de Alertas", use_container_width=True):
            st.session_state.choice = "🚨 Tareas Críticas"

        # --- Sidebar Progress Indicator ---
        st.divider()
        st.markdown("### 🏛️ Avance de Gestión TH")
        db = SessionLocal()
        try:
            from src.models.entities import PlanMacro, Policy
            from sqlalchemy.orm import joinedload
            macro = db.query(PlanMacro).options(joinedload(PlanMacro.policies)).first()
            if macro:
                st.metric("Consolidado Total", f"{macro.progress:.1f}%")
                for pol in macro.policies:
                    st.caption(f"{pol.name}")
                    st.progress(pol.progress / 100)
            else:
                st.info("Sin plan configurado.")
        finally:
            db.close()

        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            AuthService.logout()

    # --- View Rendering (Scoped inside show_app) ---
    choice = st.session_state.choice

    if choice == "🏠 Dashboard":
        show_executive_dashboard()
    elif choice == "📈 Dashboard Personal":
        show_reports_view()
    elif choice == "🧩 Mosaico TH":
        show_mosaico_view()
    elif choice == "📄 Reportes TH":
        show_export_reports_view()
    elif choice == "⚙️ Configuración Admin" and user_role == "Admin": show_admin_view()
    elif choice == "🧐 Gestión de tareas":
        show_supervisor_view()
    elif choice == "🚨 Tareas Críticas":
        show_alerts_view()

if __name__ == "__main__":
    main()
