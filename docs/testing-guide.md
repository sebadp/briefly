# Guía de Testing - Briefly MVP

Esta guía te ayudará a probar todo el proyecto creado en esta sesión.

## Estructura de Ramas (Trunk-Based Development)

Usamos **Trunk-Based Development**, el approach más usado por equipos profesionales (Google, Netflix, Amazon):

```
main ─────────────────────────────────────────────▶
  └── feat/initial-mvp (rama actual)
```

**Principios:**
- `main` siempre está deployable
- Ramas cortas (< 2 días)
- Commits pequeños y frecuentes
- Feature flags para código no terminado

---

## 1. Verificar Infraestructura

```bash
# Ver que Docker está corriendo
docker ps
# Esperado:
# briefly-postgres        (puerto 5432)
# briefly-dynamodb        (puerto 8000)
# briefly-dynamodb-admin  (puerto 8001)

# Si no están corriendo:
cd backend && docker-compose up -d
```

---

## 2. Probar Backend

### Terminal 1 - Iniciar servidor
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

### Terminal 2 - Probar endpoints
```bash
# Health check
curl http://localhost:8000/health
# → {"status":"healthy","app":"Briefly"}

# Crear feed con lenguaje natural
curl -X POST http://localhost:8000/api/v1/feeds/from-natural-language \
  -H "Content-Type: application/json" \
  -d '{"query": "Noticias de tecnología en español"}'

# Listar feeds
curl http://localhost:8000/api/v1/feeds

# Ver documentación interactiva
open http://localhost:8000/docs
```

---

## 3. Probar Frontend

### Terminal 3 - Iniciar Next.js
```bash
cd frontend
npm run dev
```

### En el navegador
1. Abrir http://localhost:3000
2. Verificar:
   - ✓ Sidebar con navegación
   - ✓ Input de lenguaje natural
   - ✓ Grid de noticias (mock data)
   - ✓ Theme dark con glassmorphism

3. Probar crear feed:
   - Escribir "Noticias de IA y startups"
   - Click "Crear Feed"
   - Ver mensaje de éxito

---

## 4. Verificar Base de Datos

### PostgreSQL
```bash
# Conectar a PostgreSQL
docker exec -it briefly-postgres psql -U briefly -d briefly

# Ver tablas
\dt
# → users, feeds, sources, alembic_version

# Ver estructura
\d+ feeds

# Salir
\q
```

### DynamoDB Admin
1. Abrir http://localhost:8001
2. Ver tabla `briefly-articles` (se crea al primer scrape)

---

## 5. Flujo Completo

1. **Crear feed**: POST `/api/v1/feeds/from-natural-language`
2. **Agregar source**: POST `/api/v1/sources`
3. **Scrape**: POST `/api/v1/articles/scrape`
4. **Ver artículos**: GET `/api/v1/articles?feed_id=...`

---

## 6. Git Workflow (Trunk-Based)

```bash
# Ver rama actual
git branch
# → * feat/initial-mvp

# Ver commits
git log --oneline -5

# Cuando termines de probar, mergear a main:
git checkout main
git merge feat/initial-mvp
git push origin main

# Crear nueva rama para siguiente feature:
git checkout -b feat/next-feature
```

---

## 7. Próximos Pasos

- [ ] Conectar frontend al backend real (quitar mock data)
- [ ] Probar scraping con Claude (requiere `ANTHROPIC_API_KEY`)
- [ ] Agregar autenticación de usuarios
- [ ] Deploy a AWS
