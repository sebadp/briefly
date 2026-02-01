# Guía de Testing - Briefly MVP

Esta guía cubre todo el proyecto: backend, frontend, bases de datos, y los agentes de IA.

---

## 1. Prerrequisitos

```bash
# Verificar que Docker esté corriendo
docker ps
# Esperado: briefly-postgres, briefly-dynamodb, briefly-dynamodb-admin

# Si no están corriendo:
cd backend && docker-compose up -d
```

---

## 2. Configuración de Ambiente

### Backend (.env)
```bash
# Copiar ejemplo y configurar
cp backend/.env.example backend/.env

# Editar backend/.env con tus API keys:
LLM_PROVIDER=gemini          # o "anthropic"
GEMINI_API_KEY=tu-key-aqui   # Para Gemini
ANTHROPIC_API_KEY=           # Para Claude (opcional)

# Search APIs (para Research Agent)
TAVILY_API_KEY=tu-key        # Opción preferida
GOOGLE_SEARCH_API_KEY=       # Fallback
GOOGLE_SEARCH_ENGINE_ID=     # Fallback
```

### Verificar configuración
```bash
cd backend
source .venv/bin/activate
python -c "from app.config import get_settings; s = get_settings(); print(f'Provider: {s.llm_provider}')"
```

---

## 3. Iniciar Servicios

### Terminal 1 - Backend (puerto 8080)
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8080
```

### Terminal 2 - Frontend (puerto 3000)
```bash
cd frontend
npm run dev
```

---

## 4. Probar Backend API

### Health Check
```bash
curl http://localhost:8080/health
# → {"status":"healthy","app":"Briefly"}
```

### Crear Briefing con Lenguaje Natural
```bash
curl -X POST http://localhost:8080/api/v1/briefings \
  -H "Content-Type: application/json" \
  -d '{"topic": "Noticias de tecnología e inteligencia artificial", "name": "AI News"}'
```

### Listar Briefings
```bash
curl http://localhost:8080/api/v1/briefings
```

### Ver Documentación Interactiva
```bash
open http://localhost:8080/docs
```

---

## 5. Probar Multi-Article Scraping

### Vía API (cURL)
```bash
# Scrapear 5 artículos de TechCrunch
curl -X POST "http://localhost:8080/api/v1/sources/add-and-scrape-multiple?url=https://techcrunch.com&name=TechCrunch&article_count=5"
```

### Vía Frontend
1. Ir a http://localhost:3000/explore
2. Pegar URL: `https://techcrunch.com`
3. Seleccionar "5 artículos" en el dropdown
4. Click "Scrape"
5. Ver tarjetas de artículos agrupados por fuente

---

## 6. Probar Agentes de IA

### Probar Gemini Scraper
```bash
cd backend
source .venv/bin/activate
python -c "
import asyncio
from app.agents import get_scraper_agent

async def test():
    scraper = get_scraper_agent()
    print(f'Using: {type(scraper).__name__}')
    articles = await scraper.scrape_multiple_from_homepage('https://techcrunch.com', limit=3)
    for a in articles:
        print(f'- {a.title}')
    await scraper.close()

asyncio.run(test())
"
```

### Probar Search Service
```bash
python -c "
import asyncio
from app.services.search_service import SearchService

async def test():
    ss = SearchService()
    results = await ss.search('AI news websites', num_results=5)
    for r in results:
        print(f'{r["source"]}: {r["title"]}')
    await ss.close()

asyncio.run(test())
"
```

### Cambiar entre Claude y Gemini
```bash
# En backend/.env:
LLM_PROVIDER=gemini   # Usa GeminiScraperAgent
LLM_PROVIDER=anthropic  # Usa ScraperAgent (Claude)
```

---

## 7. Probar Research Agent & Briefings

### Vía Frontend (Recomendado)
1. Ir a http://localhost:3000
2. Escribir tema o click en quick topic (Tech, Startups, etc.)
3. Observar el terminal en tiempo real:
   - 🧠 Generando queries
   - 🌐 Buscando en Google/Tavily
   - 🕵️ Validando fuentes
   - ✨ Resultados encontrados
4. Click "Crear Briefing" al finalizar
5. Ver briefing con fuentes agrupadas

### Vía API (Stream SSE)
```bash
# Stream de research en tiempo real
curl -N "http://localhost:8080/api/v1/research/stream?topic=crypto%20news"
```

### Listar Dashboards
```bash
curl http://localhost:8080/api/v1/dashboards
```

---

## 8. Probar Frontend

### En el navegador: http://localhost:3000

**Verificar:**
- ✓ Indicador de conexión (verde = conectado)
- ✓ Input de lenguaje natural
- ✓ Tabs de feeds creados
- ✓ Grid de artículos
- ✓ **Nuevo**: Página de Sources con selector de cantidad
- ✓ **Nuevo**: Página de Dashboards con Research Agent

**Flujo completo:**
1. Escribir: "Noticias de startups y venture capital"
2. Click "Crear Feed"
3. Ver mensaje de éxito
4. Navegar a `/feeds` para ver gestión
5. **Nuevo**: Navegar a `/dashboards/new` para probar Research Agent

---

## 9. Verificar Bases de Datos

### PostgreSQL
```bash
docker exec -it briefly-postgres psql -U briefly -d briefly

# Ver tablas
\dt

# Ver feeds creados
SELECT id, name, natural_language_query FROM feeds;

# Salir
\q
```

### DynamoDB Admin
```bash
open http://localhost:8001
# Ver tabla: briefly-articles
```

---

## 8. Estructura de Archivos Clave

```
briefly/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── feed_agent.py      # Strands - NL interpretation
│   │   │   ├── scraper_agent.py   # Claude scraper
│   │   │   └── gemini_scraper.py  # Gemini scraper
│   │   ├── api/v1/                # REST endpoints
│   │   ├── db/                    # PostgreSQL + DynamoDB
│   │   └── config.py              # Settings
│   ├── .env                       # API keys (NO commitear)
│   └── .env.example               # Template
├── frontend/
│   ├── src/app/page.tsx           # Dashboard
│   ├── src/lib/api.ts             # API client
│   └── src/components/            # UI components
├── infra/                         # AWS CDK
└── docs/                          # Guías
```

---

## 9. Troubleshooting

| Problema | Solución |
|----------|----------|
| "Backend desconectado" en frontend | Verificar que backend corra en puerto **8080** |
| "Failed to fetch" | CORS o backend no corriendo |
| "Gemini API error" | Verificar `GEMINI_API_KEY` en `.env` |
| Imágenes no cargan | Reiniciar frontend (Next.js image config) |

---

## 10. CI/CD y Code Review

El proyecto incluye un pipeline automatizado en GitHub Actions.

### Pipeline de Calidad (`ci.yml`)
Se ejecuta en cada `push` y `pull_request`.
- **Tests**: `pytest`
- **Linting**: `ruff check` y `ruff format`
- **Typing**: `mypy`

### AI Code Reviewer (`ai-review.yml`)
Se ejecuta automáticamente al abrir un **Pull Request**.
1. El script `scripts/ai_reviewer.py` analiza el diff.
2. Gemini 2.0 busca bugs y mejoras.
3. El agente comenta directamente en el PR.

**Para probar el AI Reviewer localmente:**
```bash
export GEMINI_API_KEY=tu-api-key
export GITHUB_TOKEN=tu-github-token # Opcional si solo quieres ver el output en consola
# Nota: El script normal espera entorno de GitHub Actions, pero puedes ver la lógica en backend/scripts/ai_reviewer.py
```

---

## 11. Próximos Pasos

- [x] CI/CD con GitHub Actions
- [ ] Deploy a AWS: `cd infra && cdk deploy --all`
- [ ] Agregar autenticación de usuarios
