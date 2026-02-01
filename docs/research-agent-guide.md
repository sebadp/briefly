# Research Agent Guide & Best Practices 🧠

Esta guía explica cómo funciona el **Research Agent** actual de Briefly y propone una hoja de ruta de mejoras basada en las mejores prácticas de la industria para agentes autónomos en 2024.

---

## 1. ¿Cómo funciona el Agente Actual?

El agente actual (`backend/app/agents/research_agent.py`) sigue un patrón **"Plan-then-Act" lineal**. Es efectivo para tareas simples pero tiene limitaciones para investigaciones complejas.

### Flujo de Ejecución (Pipeline Lineal)

1.  **Planificación (Heurística)**:
    *   Recibe un `topic`.
    """
    Agent that performs deep research to find news sources for a topic.
    Designed for streaming output of its thought process.
    Implements ReAct pattern with Validation Step.
    """
    *   *Limitación: No usa un LLM para "pensar" creativamente sobre qué buscar, solo llena huecos.*

2.  **Búsqueda (Search)**:
    *   Ejecuta las queries en Google/Tavily.
    *   Agrega resultados a una lista de candidatos, eliminando duplicados por dominio.
    *   *Limitación: No evalúa la calidad del resultado antes de abrirlo, solo confía en el título.*

3.  **Validación y Filtrado (Filter)**:
    *   Toma los primeros 8 candidatos.
    *   Intenta scrapear 3 artículos de la home de cada uno.
    *   Si encuentra artículos -> **Válido**. Si no -> **Descartado**.
    *   *Limitación: Si el sitio tiene un anti-bot fuerte o estructura compleja, se descarta aunque sea una fuente excelente.*

4.  **Resultado**:
    *   Devuelve la lista de fuentes validadas.

---

## 2. Mejores Prácticas en la Industria (2024)

Basado en la investigación de arquitecturas de agentes autónomos (AutoGPT, BabyAGI, LangChain):

### A. Patrones de Razonamiento
*   **ReAct (Reason + Act)**: En lugar de un plan fijo, el agente debería:
    1.  **Pensar**: "¿Qué información me falta para completar este briefing?"
    2.  **Actuar**: Ejecutar una herramienta (buscar, leer, navegar).
    3.  **Observar**: Analizar el resultado.
    4.  **Repetir**: Decidir el siguiente paso basado en la observación.
*   **Reflection**: El agente debe criticar su propio trabajo. "¿Esta fuente es realmente fiable o es clickbait? ¿Necesito buscar una segunda opinión?"

### B. Uso de Herramientas (Tool Use)
El agente no debería ser solo un script. Debería tener acceso a una "caja de herramientas":
*   `search_web(query)`
*   `read_page(url)`
*   `check_rss_feed(url)`
*   `validate_credibility(text)`

### D. Tendencias 2025 (The Agentic Era)
*   **Multi-Agent Systems (MAS)**: La colaboración entre agentes especializados es el estándar. Un "Manager Agent" orquesta a agentes investigadores, escritores y validadores.
*   **Agentic Mesh**: Arquitectura distribuida y modular donde los agentes son pequeños, especializados y se comunican entre sí.
*   **Explainable AI (XAI)**: Los agentes deben explicar *por qué* tomaron una decisión (ej: "¿Por qué descartaste esta fuente?").
*   **Human-in-the-Loop**: Para decisiones críticas, el agente propone y el humano aprueba.
*   **LLM-as-a-Judge**: Usar un LLM potente (ej: GPT-4o, Claude 3.5 Sonnet) para evaluar la calidad del output de agentes más pequeños y rápidos.

---

## 3. Propuesta de Mejoras (Roadmap)

### Nivel 1: Optimizaciones Inmediatas (Quick Wins) ⚡
1.  **Generación de Queries con LLM**:
    *   Reemplazar la lista fija de f-strings por una llamada a Gemini/Claude.
    *   *Prompt*: "Genera 3 queries de búsqueda avanzadas para encontrar fuentes de noticias profundas sobre '{topic}'. Evita sitios genéricos."
2.  **Validación de Frecuencia y Relevancia**:
    *   **Frecuencia**: Verificar que la fuente tenga al menos **1-2 artículos por mes** en los últimos 3 meses. Esto asegura que la fuente esté activa.
    *   **Relevancia (Post-Research)**: Al finalizar, usar un LLM para leer los títulos/resúmenes scrapeados y asignar un **Relevance Score (1-10)** respecto al topic original. Filtrar fuentes con score < 7.
3.  **Detección de RSS**:
    *   Muchos sitios de noticias tienen feeds RSS ocultos. Detectarlos garantiza actualizaciones más fiables que el scraping visual.

### Nivel 2: Arquitectura Agéntica (Medium Term) 🛠️
4.  **Implementar Patrón ReAct**:
    *   Permitir que el agente decida si necesita más búsquedas. "Encontré 2 fuentes, pero el usuario pidió 5. Voy a buscar términos relacionados."
5.  **Parallelization**:
    *   La validación actual es secuencial (lenta). Usar `asyncio.gather` para validar 5 sitios en paralelo.

### Nivel 3: Agente Autónomo Avanzado (Long Term) 🚀
6.  **Reflection Step**:
    *   Antes de entregar el briefing, el agente hace un loop de auto-crítica: "He seleccionado estas 5 fuentes. ¿Son demasiado similares? ¿Hay sesgo? Voy a reemplazar una por una fuente de opinión contraria."
7.  **Memory System (PostgreSQL)**:
    *   Crear una tabla `SourceReputation`. Si el agente valida "The Veritas" hoy, guardarlo como fuente confiable globalmente para futuras búsquedas.

---

## 4. Ejemplo de Flujo Mejorado (Nivel 2)

```mermaid
graph TD
    A[Input: "Crypto Trends"] --> B{LLM: Plan Queries}
    B --> C[Query 1: "Top crypto news sites"]
    B --> D[Query 2: "DeFi analysis blogs"]
    C & D --> E[Search Tools (Parallel)]
    E --> F[Raw Candidates List]
    F --> G{LLM Filter: Are these relevant?}
    G -- Yes --> H[Scraper Agents (Parallel)]
    G -- No --> I[Discard]
    H --> J{Quality Check: Good content?}
    J -- Good --> K[Add to Briefing]
    J -- Bad --> L[Discard]
    K --> M[Final Briefing]
```
