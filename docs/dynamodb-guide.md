# Guía Completa de DynamoDB para Briefly

Esta guía cubre todo lo necesario para trabajar con DynamoDB Local en el contexto del proyecto Briefly, desde la administración básica hasta consultas avanzadas con Python.

---

## 1. Conceptos Básicos

DynamoDB es una base de datos NoSQL clave-valor. A diferencia de SQL, no tiene esquemas rígidos (excepto para la clave primaria) y está optimizada para escalabilidad masiva.

### Estructura en Briefly
En `briefly`, usamos un **Single Table Design** simplificado:

- **Tabla**: `briefly-articles`
- **Partition Key (PK)**: `pk`
  - Identifica el Feed.
  - Formato: `FEED#{feed_id}`
- **Sort Key (SK)**: `sk`
  - Identifica el Artículo y permite ordenamiento por fecha.
  - Formato: `ARTICLE#{scraped_at_iso}#{article_id}`

Esta estructura nos permite hacer la consulta más importante eficientemente: *"Dame los últimos artículos de este feed"*.

---

## 2. Acceso a DynamoDB Local

Actualmente tienes DynamoDB corriendo en local vía Docker.

### DynamoDB Admin UI
Tienes una interfaz visual disponible en tu navegador:
- **URL**: [http://localhost:8001](http://localhost:8001)

Desde aquí puedes:
1. Ver todas las tablas.
2. Hacer clic en `briefly-articles` para ver los ítems.
3. Usar la caja de búsqueda para filtrar por Partition Key.

### Verificación desde Terminal
Puedes verificar que la base de datos responde:
```bash
# Listar tabla
curl -s http://localhost:8000/
# Nota: La API es JSON, curl directo fallará sin headers correctos, mejor usar AWS CLI o Python.
```

---

## 3. Consultas con AWS CLI (Opcional)

Si tienes `aws-cli` instalado, puedes interactuar directamente (usando credenciales dummy):

```bash
export AWS_ACCESS_KEY_ID=local
export AWS_SECRET_ACCESS_KEY=local
export AWS_DEFAULT_REGION=us-east-1

# Listar tablas
aws dynamodb list-tables --endpoint-url http://localhost:8000

# Escanear todos los datos (útil en dev, prohibido en prod)
aws dynamodb scan --table-name briefly-articles --endpoint-url http://localhost:8000
```

---

## 4. Consultas con Python (`boto3`)

Esta es la forma recomendada de interactuar. Puedes usar este script como plantilla (`scripts/debug_dynamo.py`):

```python
import boto3
from boto3.dynamodb.conditions import Key
import json
from decimal import Decimal

# Helper para imprimir JSON con decimales
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

# 1. Conectar a DynamoDB Local
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='us-east-1',
    aws_access_key_id='local',
    aws_secret_access_key='local'
)

table = dynamodb.Table('briefly-articles')

def scan_all_articles():
    """Trae TODOS los artículos (Scan)"""
    print(f"📦 Escaneando tabla {table.name}...")
    response = table.scan()
    items = response.get('Items', [])
    print(f"Total ítems: {len(items)}")
    for item in items[:5]: # Muestra los primeros 5
        print(json.dumps(item, cls=DecimalEncoder, indent=2))

def query_by_feed(feed_id):
    """Consulta eficiente por Feed (Query)"""
    pk_value = f"FEED#{feed_id}"
    print(f"\n🔍 Buscando artículos para: {pk_value}")
    
    response = table.query(
        KeyConditionExpression=Key('pk').eq(pk_value),
        ScanIndexForward=False, # True = Ascendente, False = Descendente (más nuevo primero)
        Limit=10
    )
    
    items = response.get('Items', [])
    print(f"Encontrados: {len(items)}")
    for item in items:
        print(f"- {item.get('title')} ({item.get('sk')})")

if __name__ == "__main__":
    scan_all_articles()
    
    # Ejemplo con un ID real (cópialo del scan)
    # query_by_feed("feed-uuid-here")
```

### Ejecutar el script
```bash
cd backend
source .venv/bin/activate
python scripts/debug_dynamo.py
```

---

## 5. Operaciones Comunes en Código (`app/db/dynamodb.py`)

Si necesitas modificar cómo interactúa la app:

### Insertar (PutItem)
```python
item = {
    "pk": {"S": f"FEED#{feed_id}"},
    "sk": {"S": f"ARTICLE#{now}#{uuid}"},
    "title": {"S": "Título Artículo"},
    # Atributo TTL para borrado automático
    "ttl": {"N": str(timestamp + 30_days)}
}
await client.put_item(TableName=TABLE_NAME, Item=item)
```
*Nota: Usamos el cliente de bajo nivel (`client.put_item`) que requiere especificar tipos (`{"S": ...}`). `boto3.resource` (usado en el script de debug) infiere tipos automáticamente.*

### Consultar (Query)
```python
response = await client.query(
    TableName=TABLE_NAME,
    KeyConditionExpression="pk = :pk",
    ExpressionAttributeValues={":pk": {"S": f"FEED#{feed_id}"}},
    ScanIndexForward=False  # Para obtener los más recientes primero
)
```

---

## 6. Solución de Problemas Comunes

### "ResourceNotFoundException"
- La tabla no existe.
- Solución: Reinicia el backend (el código de inicialización crea la tabla) o corre el script de setup.

### "Connection Refused"
- El contenedor Docker no está corriendo o el puerto 8000 está bloqueado.
- Solución: `docker-compose up -d dynamodb-local`

### Datos desaparecen al reiniciar
- Actualmente DynamoDB Local corre con `-inMemory` para evitar problemas de permisos de volumen.
- Esto es normal en esta configuración. Para persistencia real, habría que arreglar el volumen de Docker.
