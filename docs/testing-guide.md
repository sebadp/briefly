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

### Crear Feed con Lenguaje Natural
```bash
curl -X POST http://localhost:8080/api/v1/feeds/from-natural-language \
  -H "Content-Type: application/json" \
  -d '{"query": "Noticias de tecnología e inteligencia artificial"}'
```

### Listar Feeds
```bash
curl http://localhost:8080/api/v1/feeds
```

### Ver Documentación Interactiva
```bash
open http://localhost:8080/docs
```

---

## 5. Probar Agentes de IA

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
    article = await scraper.scrape_article('https://techcrunch.com')
    print(f'Title: {article.title}')
    print(f'Summary: {article.summary[:200]}...')
    await scraper.close()

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

## 6. Probar Frontend

### En el navegador: http://localhost:3000

**Verificar:**
- ✓ Indicador de conexión (verde = conectado)
- ✓ Input de lenguaje natural
- ✓ Tabs de feeds creados
- ✓ Grid de artículos

**Flujo completo:**
1. Escribir: "Noticias de startups y venture capital"
2. Click "Crear Feed"
3. Ver mensaje de éxito
4. Navegar a `/feeds` para ver gestión

---

## 7. Verificar Bases de Datos

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

## 10. Próximos Pasos

- [ ] Agregar tests automatizados
- [ ] CI/CD con GitHub Actions
- [ ] Deploy a AWS: `cd infra && cdk deploy --all`
- [ ] Agregar autenticación de usuarios
