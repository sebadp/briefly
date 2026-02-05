# Arquitectura de Base de Datos Híbrida

Briefly utiliza una arquitectura híbrida optimizada para el rendimiento y la integridad de los datos, combinando las fortalezas de las bases de datos relacionales (SQL) y NoSQL.

## Resumen

- **PostgreSQL**: Actúa como **Source of Truth** (Fuente de Verdad). Almacena relaciones críticas, configuración de usuarios y metadatos estructurados.
- **DynamoDB**: Actúa como **Read Cache** (Caché de Lectura) y almacenamiento de contenido masivo (artículos scrapeados).

```mermaid
graph TB
    subgraph "PostgreSQL - Integridad & Relaciones"
        D[Dashboards]
        S[Sources]
        DS[DashboardSources (Link Table)]
        A_pg[Articles Metadata (Compact)]
    end
    
    subgraph "DynamoDB - Velocidad & Volumen"
        A_dyn[Articles Content (Full HTML/Text)]
    end
    
    D --> DS --> S --> A_pg
    A_pg -.->|"cache sync"| A_dyn
```

## Por qué Híbrido?

1.  **Integridad Relacional**: Necesitamos gestión compleja de relaciones (un Source puede estar en muchos Dashboards). PostgreSQL es excelente para esto.
2.  **Velocidad de Lectura**: Un Dashboard puede cargar 50+ artículos. DynamoDB permite obtenerlos en una sola query por `Partition Key` (Feed ID) en milisegundos, sin joins costosos.
3.  **Flexibilidad de Esquema**: El contenido scrapeado de los artículos varía mucho. NoSQL es ideal para guardar estos blobs de datos heterogéneos.

## Flujo de Datos

### 1. Creación de Dashboard (Postgres)
Cuando un usuario crea un Dashboard:
1. Se guarda en la tabla `dashboards` de PostgreSQL.
2. Se asocian las fuentes en `dashboard_sources`.

### 2. Scraping & Escritura (Dual-Write)
El `ArticleService` maneja la escritura para garantizar consistencia:
1. **Postgres**: Se guarda el `Article` (título, url, fecha) para deduplicación y búsquedas relacionales.
2. **DynamoDB**: Se guarda el objeto completo (incluyendo el contenido scrapeado extenso) con un TTL.

### 3. Lectura de Artículos (DynamoDB First)
Cuando el usuario abre un Dashboard:
1. Backend hace una **Query a DynamoDB** usando `pk=FEED#{id}`.
2. Esto retorna todos los artículos listos para renderizar.
3. **Fallback**: Si DynamoDB falla, el sistema podría reconstruir los datos desde Postgres (aunque sin el contenido completo scrapeado, solo metadatos).

## Estructura de DynamoDB

- **Tabla**: `briefly-articles`
- **PK**: `FEED#{dashboard_id}`
- **SK**: `ARTICLE#{timestamp}#{article_id}`

Esta estructura optimiza la query más frecuente: "Dame las noticias más recientes de este dashboard".
