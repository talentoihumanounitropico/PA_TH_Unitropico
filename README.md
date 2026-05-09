# 🏛️ Sistema Integral de Seguimiento Estratégico de Talento Humano - Unitrópico

![Versión](https://img.shields.io/badge/Versi%C3%B3n-2.1.0--Estable-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

## 📝 Descripción
Plataforma avanzada de **Business Intelligence** y gestión operativa diseñada específicamente para la **Universidad Internacional del Trópico Americano (Unitrópico)**. El sistema facilita el monitoreo riguroso del **Plan Estratégico de Talento Humano**, permitiendo una trazabilidad total desde los objetivos macro hasta las tareas individuales de cada funcionario.

## 🚀 Características Principales

### 📊 Inteligencia y Visualización
- **Dashboard Ejecutivo**: Radares de cumplimiento institucional, mapas de red de interdependencia y análisis de tendencia temporal.
- **Mosaico TH**: Explorador jerárquico interactivo que permite visualizar la estructura de la entidad en 360°.
- **Alertas Críticas**: Sistema inteligente de detección de cuellos de botella y tareas vencidas.

### 👷 Gestión Operativa y Control
- **Portal del Trabajador**: Interfaz simplificada para que el personal reporte avances y cargue evidencias de cumplimiento.
- **Sistema de Evidencias**: Soporte para URLs de evidencia y campo de observaciones obligatorias para garantizar la integridad de los reportes.
- **Clonación Estratégica**: Herramienta de alta eficiencia para duplicar estructuras organizacionales para nuevos periodos fiscales.

## 👥 Roles y Niveles de Acceso

El sistema implementa un modelo de **Control de Acceso Basado en Roles (RBAC)**:

| Rol | Descripción | Funcionalidades Clave |
| :--- | :--- | :--- |
| **Admin** | Administrador de Sistema | Configuración estratégica, gestión de usuarios, auditoría total y clonación de planes. |
| **Supervisor** | Gestor Operativo | Supervisión de cumplimiento, validación de evidencias y gestión de alertas. |
| **Worker** | Personal Operativo | Reporte de cumplimiento de tareas asignadas, carga de evidencias y seguimiento personal. |

## 🛡️ Arquitectura de Seguridad
La plataforma ha sido blindada siguiendo los estándares de **OWASP Top 10**:

- **Sanitización XSS**: Barreras contra inyección de scripts en todos los campos de entrada.
- **Protección CSRF/CORS**: Configuración de servidor para prevenir ataques de falsificación y accesos no autorizados.
- **Defensa Anti-Bots**: Retardo algorítmico en login y ofuscación del DOM para prevenir extracción automatizada (Scraping).
- **Criptografía Bcrypt**: Hasheo de contraseñas con salting aleatorio.

> [!NOTE]
> Para más detalles técnicos sobre la seguridad, consulte el documento: [SECURITY_ARCHITECTURE.md](file:///c:/Users/carlo/OneDrive/Documentos/PA_TH/PA_TH_Unitropico/SECURITY_ARCHITECTURE.md)

## 🛠️ Tecnologías Utilizadas
- **Core**: Python 3.12
- **UI Framework**: Streamlit
- **Persistence**: SQLAlchemy (SQLite / PostgreSQL)
- **Data Analysis**: Pandas & NumPy
- **Visuals**: Plotly Premium & CSS Institucional

## 📂 Estructura del Proyecto
```text
PA_TH_Unitropico/
├── appth.py                # Punto de entrada y orquestador de rutas
├── src/
│   ├── core/               # Motor de base de datos y configuración
│   ├── models/             # Esquemas de datos (Plan, Tareas, Usuarios)
│   ├── services/           # Lógica: Cálculos, Autenticación, Seguridad
│   └── ui/
│       └── views/          # Módulos de interfaz (Admin, Supervisor, Worker)
├── assets/                 # Branding: CSS dinámico, Imágenes institucionales
├── data/                   # Almacenamiento local persistente
└── docs/                   # Guías de despliegue y seguridad
```

## 🔧 Instalación y Despliegue
Para detalles sobre el entorno de producción y requerimientos técnicos, vea la [GUIA_DESPLIEGUE.md](file:///c:/Users/carlo/OneDrive/Documentos/PA_TH/PA_TH_Unitropico/GUIA_DESPLIEGUE.md).

---
**Desarrollado para la Excelencia en la Gestión de Talento Humano - Unitrópico 🏛️**
