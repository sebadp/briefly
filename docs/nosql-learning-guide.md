# Guía de Aprendizaje: NoSQL con DynamoDB

Esta guía está diseñada para desarrolladores acostumbrados a bases de datos relacionales (PostgreSQL, MySQL) que quieren aprender DynamoDB y patrones NoSQL.

## Tabla de Contenidos

1. [SQL vs NoSQL: Cambio de Mentalidad](#1-sql-vs-nosql-cambio-de-mentalidad)
2. [Conceptos Clave de DynamoDB](#2-conceptos-clave-de-dynamodb)
3. [Diseño de Single-Table](#3-diseño-de-single-table)
4. [Operaciones CRUD](#4-operaciones-crud)
5. [Patrones de Acceso](#5-patrones-de-acceso)
6. [Uso con Python (aioboto3)](#6-uso-con-python-aioboto3)
7. [Ejercicios Prácticos](#7-ejercicios-prácticos)

---

## 1. SQL vs NoSQL: Cambio de Mentalidad

### La Gran Diferencia

| SQL (PostgreSQL) | NoSQL (DynamoDB) |
|------------------|------------------|
| Diseñas tablas primero, queries después | Diseñas queries primero, tablas después |
| Normalización (evitar duplicación) | Desnormalización (duplicar para optimizar) |
| JOINs para relacionar datos | Pre-computar relaciones en el diseño |
| Schema estricto | Schema flexible por item |
| Escala vertical (servidor más grande) | Escala horizontal (más particiones) |

### Cuándo Usar Cada Uno

```
┌─────────────────────────────────────────────────────────────┐
│                      USA SQL CUANDO:                         │
├─────────────────────────────────────────────────────────────┤
│ • Queries complejos y ad-hoc (analytics, reporting)         │
│ • Relaciones muchos-a-muchos frecuentes                     │
│ • Transacciones ACID críticas                               │
│ • Schema muy estructurado y estable                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     USA NOSQL CUANDO:                        │
├─────────────────────────────────────────────────────────────┤
│ • Patrones de acceso conocidos y predecibles                │
│ • Escala masiva (millones de requests/segundo)              │
│ • Latencia ultra-baja requerida                             │
│ • Datos semi-estructurados o variables                      │
│ • Casos key-value o document-based                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Conceptos Clave de DynamoDB

### Partition Key (PK)

La **partition key** determina en qué partición física se guarda el item.

```
PK = "FEED#abc123"  →  Partición A
PK = "FEED#xyz789"  →  Partición B
```

**Reglas:**
- Debe distribuir datos uniformemente
- Queries SIEMPRE deben especificar PK
- Alta cardinalidad = mejor distribución

### Sort Key (SK)

La **sort key** ordena items dentro de una partición.

```
PK = "FEED#abc123", SK = "ARTICLE#2024-01-01#0001"
PK = "FEED#abc123", SK = "ARTICLE#2024-01-02#0002"
PK = "FEED#abc123", SK = "META#info"
```

**Permite:**
- Range queries (`SK BETWEEN`, `SK BEGINS_WITH`)
- Ordenamiento automático
- Múltiples tipos de items en la misma partición

### Anatomía de un Item

```json
{
  "PK": "FEED#123",           // Partition Key (requerido)
  "SK": "ARTICLE#2024-01-15", // Sort Key (opcional)
  "title": "Breaking News",   // Atributos
  "summary": "...",
  "url": "https://...",
  "GSI1PK": "SOURCE#techcrunch", // Para index secundario
  "GSI1SK": "2024-01-15"
}
```

---

## 3. Diseño de Single-Table

### ¿Qué es Single-Table Design?

En lugar de múltiples tablas como en SQL:

```
# SQL: múltiples tablas
users, feeds, sources, articles, comments
```

En DynamoDB usas **una sola tabla** para todo:

```
# DynamoDB: una tabla con PK/SK strategy
briefly-articles
  ├── PK="USER#1"        SK="PROFILE"       -> datos del usuario
  ├── PK="USER#1"        SK="FEED#abc"      -> feed del usuario
  ├── PK="FEED#abc"      SK="CONFIG"        -> configuración del feed
  ├── PK="FEED#abc"      SK="ARTICLE#001"   -> artículo
  └── PK="FEED#abc"      SK="ARTICLE#002"   -> artículo
```

### Ejemplo: Diseño para Briefly

```python
# Patrón de keys para Briefly
{
    # Feed metadata
    "PK": "FEED#<feed_id>",
    "SK": "META",
    "name": "Tech News",
    "query": "noticias de tecnología",
    
    # Artículos del feed
    "PK": "FEED#<feed_id>",
    "SK": "ARTICLE#<timestamp>#<article_id>",
    "title": "...",
    "summary": "...",
    
    # Para buscar por fuente (GSI)
    "GSI1PK": "SOURCE#<source_url>",
    "GSI1SK": "<timestamp>",
}
```

### Global Secondary Index (GSI)

Un GSI permite queries con otra PK/SK:

```
Tabla Principal:
  PK = FEED#123, SK = ARTICLE#001 → Query: "artículos de un feed"

GSI1:
  GSI1PK = SOURCE#techcrunch, GSI1SK = 2024-01-15 → Query: "artículos de una fuente"
```

---

## 4. Operaciones CRUD

### PutItem (Create/Update)

```python
import aioboto3

session = aioboto3.Session()
async with session.resource('dynamodb', endpoint_url='http://localhost:8000') as dynamodb:
    table = await dynamodb.Table('briefly-articles')
    
    await table.put_item(Item={
        'PK': f'FEED#{feed_id}',
        'SK': f'ARTICLE#{timestamp}#{article_id}',
        'title': 'Breaking News',
        'summary': 'Something happened...',
        'url': 'https://example.com/article',
        'source_name': 'TechCrunch',
        'created_at': '2024-01-15T10:30:00Z',
    })
```

### GetItem (Read por PK+SK)

```python
response = await table.get_item(Key={
    'PK': f'FEED#{feed_id}',
    'SK': f'ARTICLE#{article_id}',
})
item = response.get('Item')
```

### Query (Múltiples items por PK)

```python
from boto3.dynamodb.conditions import Key

# Todos los artículos de un feed
response = await table.query(
    KeyConditionExpression=Key('PK').eq(f'FEED#{feed_id}') & Key('SK').begins_with('ARTICLE#')
)
articles = response['Items']

# Con ordenamiento descendente (más recientes primero)
response = await table.query(
    KeyConditionExpression=Key('PK').eq(f'FEED#{feed_id}'),
    ScanIndexForward=False,  # DESC
    Limit=20,
)
```

### DeleteItem

```python
await table.delete_item(Key={
    'PK': f'FEED#{feed_id}',
    'SK': f'ARTICLE#{article_id}',
})
```

### Scan (Evitar en producción)

```python
# ⚠️ SCAN lee TODA la tabla - muy costoso
response = await table.scan()  # No recomendado
```

---

## 5. Patrones de Acceso

### Diseño Basado en Queries

**Paso 1:** Listar todos los queries que necesitas

```
1. Obtener artículos de un feed     → PK = FEED#id
2. Obtener artículo específico      → PK = FEED#id, SK = ARTICLE#id
3. Artículos por fuente             → GSI: PK = SOURCE#url
4. Artículos recientes (global)     → GSI: PK = "ARTICLES", SK = timestamp
```

**Paso 2:** Diseñar PK/SK para soportar esos queries

```python
# Item structure
{
    "PK": "FEED#123",           # Para queries 1 y 2
    "SK": "ARTICLE#2024-01-15#abc",
    
    "GSI1PK": "SOURCE#techcrunch.com",  # Para query 3
    "GSI1SK": "2024-01-15",
    
    "GSI2PK": "ARTICLES",       # Para query 4
    "GSI2SK": "2024-01-15T10:30:00Z",
}
```

### Anti-patrones

```python
# ❌ MAL: User ID como Sort Key
"PK": "ARTICLE", "SK": "user123"  # No puedes buscar por rango

# ✓ BIEN: Timestamp como Sort Key
"PK": "FEED#123", "SK": "2024-01-15#article_id"  # Permite range queries

# ❌ MAL: Hot partition
"PK": "ALL_USERS"  # Todos los requests van a una partición

# ✓ BIEN: Distribuir carga
"PK": "USER#<user_id>"  # Distribuye entre particiones
```

---

## 6. Uso con Python (aioboto3)

### Cliente Asíncrono

```python
# app/db/dynamodb.py - Implementación en Briefly
import aioboto3
from app.config import get_settings

class DynamoDBClient:
    def __init__(self):
        self.settings = get_settings()
        self.session = aioboto3.Session()
        self.table_name = self.settings.dynamodb_table_name
    
    async def _get_table(self):
        async with self.session.resource(
            'dynamodb',
            endpoint_url=self.settings.dynamodb_endpoint_url,
            region_name=self.settings.aws_region,
        ) as dynamodb:
            return await dynamodb.Table(self.table_name)
```

### Crear Tabla

```python
async def create_table_if_not_exists(self):
    async with self.session.client('dynamodb', ...) as client:
        try:
            await client.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {'AttributeName': 'PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'SK', 'KeyType': 'RANGE'},
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'PK', 'AttributeType': 'S'},
                    {'AttributeName': 'SK', 'AttributeType': 'S'},
                ],
                BillingMode='PAY_PER_REQUEST',  # On-demand pricing
            )
        except client.exceptions.ResourceInUseException:
            pass  # Table already exists
```

### Operaciones de Alto Nivel

```python
async def put_article(self, feed_id: str, article_id: str, **data):
    table = await self._get_table()
    await table.put_item(Item={
        'PK': f'FEED#{feed_id}',
        'SK': f'ARTICLE#{datetime.now().isoformat()}#{article_id}',
        **data,
    })

async def get_articles_by_feed(self, feed_id: str, limit: int = 20):
    table = await self._get_table()
    response = await table.query(
        KeyConditionExpression=Key('PK').eq(f'FEED#{feed_id}'),
        ScanIndexForward=False,  # Más recientes primero
        Limit=limit,
    )
    return response['Items']
```

---

## 7. Ejercicios Prácticos

### Ejercicio 1: Diseñar Keys para un Blog

Requirimientos:
- Listar posts de un usuario
- Listar comentarios de un post
- Listar posts por categoría

¿Qué PK/SK y GSIs usarías?

### Ejercicio 2: Implementar Paginación

```python
async def get_articles_paginated(self, feed_id: str, page_size: int, last_key: dict = None):
    # Implementar paginación con ExclusiveStartKey
    pass
```

### Ejercicio 3: Agregar GSI por Fecha

Modifica el diseño de Briefly para poder buscar:
- Todos los artículos de hoy (global)
- Artículos de la última semana por fuente

---

## Comparación Rápida

```python
# SQL (PostgreSQL)
SELECT * FROM articles 
WHERE feed_id = '123' 
ORDER BY created_at DESC 
LIMIT 20;

# DynamoDB
response = await table.query(
    KeyConditionExpression=Key('PK').eq('FEED#123'),
    ScanIndexForward=False,
    Limit=20,
)
```

---

## Recursos Adicionales

- [AWS DynamoDB Guide](https://docs.aws.amazon.com/dynamodb/) - Documentación oficial
- [DynamoDB Book](https://dynamodbbook.com/) - Guía definitiva de Alex DeBrie
- [Single-Table Design](https://www.alexdebrie.com/posts/dynamodb-single-table/) - Artículo esencial
- [DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html) - Para desarrollo

---

## Próximos Pasos en Briefly

1. Estudia `backend/app/db/dynamodb.py` - cliente implementado
2. Usa DynamoDB Admin UI en `http://localhost:8001` para explorar datos
3. Agrega un GSI para buscar por fuente
4. Implementa paginación en `get_articles_by_feed`
