# LegalLens

LegalLens es una plataforma avanzada de análisis de contratos impulsada por Inteligencia Artificial. El sistema permite a los usuarios subir documentos legales en formato PDF y obtener de forma instantánea un análisis detallado que incluye puntos clave, cláusulas potencialmente abusivas (red flags) y una evaluación de riesgo total.

La arquitectura del proyecto es híbrida, utilizando **Google Gemini 1.5 Flash** como motor principal de análisis y **Ollama (Llama 3.2)** como motor local de respaldo (fallback), garantizando así la disponibilidad del servicio en todo momento.

## Características Principales

- **Análisis Inteligente**: Extracción automática de entidades (nombres, DNI, fechas, importes).
- **Detección de Riesgos**: Identificación de cláusulas abusivas o sospechosas.
- **Motor Híbrido**: Integración con Google Gemini y fallback automático a modelos locales con Ollama.
- **Visor Integrado**: Visualización del PDF original en paralelo con el informe de la IA.
- **Arquitectura Robusta**: Despliegue mediante contenedores Docker con Nginx como proxy inverso.

## Requisitos Previos

- **Docker**:
  - **Linux**: Docker y Docker Compose instalados.
  - **Windows**: [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y funcionando (se recomienda usar WSL2).
- **API Key**: Una clave de API de Google AI Studio (opcional, para usar Gemini). Puedes obtenerla en [Google AI Studio](https://aistudio.google.com/).

## Configuración e Instalación

Sigue estos pasos para poner en marcha el proyecto:

### 1. Clonar el repositorio
```bash
git clone https://github.com/sergiorg03/LegalLens.git
cd LegalLens
```

### 2. Configurar variables de entorno
Crea un archivo llamado `.env` en la raíz del proyecto. 

**En Windows (PowerShell):**
```powershell
New-Item .env
```
**En Linux (Bash):**
```bash
nano .env
```

**Contenido del archivo .env:**
```env
# Google Gemini (Motor Principal) - Recomendable si pagas alguna clave de Gemini  
GOOGLE_API_KEY=tu_clave_de_api_aqui

# Ollama (Motor Local / Fallback)
OLLAMA_MODEL=llama3:8b
```

### 3. Desplegar con Docker
Ejecuta el siguiente comando en tu terminal (CMD, PowerShell o Bash):

```bash
docker compose up -d --build
```

### 4. Ejecutar Migraciones
Una vez que los contenedores estén activos, prepara la base de datos de Django:

```bash
docker compose exec backend python backend/manage.py migrate
```

### 5. Comprobar el estado de los servicios
```bash
docker compose ps
```

## Uso del Sistema

1. Accede a **http://localhost** en tu navegador.
2. Si no tienes cuenta, utilice el apartado de **Registro** para crear un usuario.
3. Tras iniciar sesión, podrá subir un contrato en PDF desde el botón **Subir**.
4. El sistema procesará el documento y mostrará el informe detallado de forma automática.

## Estructura del Proyecto

- `backend/`: Aplicación principal en Django (gestión de usuarios, base de datos y archivos).
- `ai_engine/`: Microservicio en FastAPI que orquesta las llamadas a Gemini y Ollama.
- `nginx/`: Configuración del servidor web y proxy.
- `dataset/`: Ejemplos de contratos para pruebas de análisis.

---
*Documentación técnica del proyecto LegalLens.*
