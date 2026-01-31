# Guía de Aprendizaje: Frontend con Next.js y React

Esta guía está diseñada para desarrolladores backend que quieren aprender desarrollo frontend moderno usando Next.js 14 y React.

## Tabla de Contenidos

1. [Conceptos Fundamentales](#1-conceptos-fundamentales)
2. [Arquitectura de Next.js](#2-arquitectura-de-nextjs)
3. [Componentes en React](#3-componentes-en-react)
4. [Hooks y Estado](#4-hooks-y-estado)
5. [Estilizado con Tailwind CSS](#5-estilizado-con-tailwind-css)
6. [Patrones Comunes](#6-patrones-comunes)
7. [Ejercicios Prácticos](#7-ejercicios-prácticos)

---

## 1. Conceptos Fundamentales

### ¿Qué es React?

React es una librería para construir interfaces de usuario. A diferencia de un framework backend que procesa requests, React:

- **Renderiza UI**: Convierte datos en elementos visuales
- **Es declarativo**: Describes QUÉ quieres ver, no CÓMO construirlo
- **Usa componentes**: Piezas reutilizables de UI

```tsx
// Componente funcional básico
function Saludo({ nombre }: { nombre: string }) {
  return <h1>Hola, {nombre}!</h1>;
}
```

### ¿Qué es Next.js?

Next.js es un framework sobre React que agrega:

| Feature | Descripción |
|---------|-------------|
| **App Router** | Sistema de routing basado en carpetas |
| **Server Components** | Componentes que renderizan en el servidor |
| **API Routes** | Endpoints backend en el mismo proyecto |
| **Optimizaciones** | Imágenes, fonts, lazy loading automático |

---

## 2. Arquitectura de Next.js

### App Router (Next.js 14+)

```
frontend/src/
├── app/                    # App Router
│   ├── layout.tsx          # Layout principal (envuelve todas las páginas)
│   ├── page.tsx            # Ruta: /
│   ├── feeds/
│   │   └── page.tsx        # Ruta: /feeds
│   └── globals.css         # Estilos globales
├── components/             # Componentes reutilizables
│   ├── NewsCard.tsx
│   └── Sidebar.tsx
└── lib/                    # Utilidades y lógica
    └── api.ts              # Cliente API
```

### Server vs Client Components

```tsx
// Server Component (default) - se ejecuta en el servidor
// No puede usar hooks ni eventos
export default function ArticlePage() {
  // Puede hacer fetch directamente
  const data = await fetch('...');
  return <div>{data.title}</div>;
}

// Client Component - se ejecuta en el browser
'use client';  // ← Esta directiva es obligatoria

export default function Counter() {
  const [count, setCount] = useState(0);  // ✓ Puede usar hooks
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

### ¿Cuándo usar cada uno?

| Usar Server Component | Usar Client Component |
|-----------------------|-----------------------|
| Fetch de datos | Interactividad (eventos) |
| Acceso a backend directo | useState, useEffect |
| SEO crítico | Animaciones |
| Contenido estático | Forms con validación |

---

## 3. Componentes en React

### Props: Comunicación Padre → Hijo

```tsx
// Props son como parámetros de función
interface NewsCardProps {
  title: string;
  summary: string;
  url: string;
}

export function NewsCard({ title, summary, url }: NewsCardProps) {
  return (
    <article>
      <h3>{title}</h3>
      <p>{summary}</p>
      <a href={url}>Leer más</a>
    </article>
  );
}

// Uso:
<NewsCard 
  title="Título del artículo"
  summary="Resumen..."
  url="/article/1"
/>
```

### Children: Composición

```tsx
// children es un prop especial
function Card({ children }: { children: React.ReactNode }) {
  return <div className="rounded-lg bg-white p-4">{children}</div>;
}

// Uso:
<Card>
  <h2>Cualquier contenido aquí</h2>
  <p>Texto, otros componentes, etc.</p>
</Card>
```

### Renderizado Condicional

```tsx
function Status({ isOnline }: { isOnline: boolean }) {
  // if/else con operador ternario
  return <span>{isOnline ? '🟢 Online' : '🔴 Offline'}</span>;
  
  // Renderizado condicional con &&
  // {isOnline && <span>🟢 Online</span>}
}
```

### Listas y Keys

```tsx
function ArticleList({ articles }: { articles: Article[] }) {
  return (
    <ul>
      {articles.map((article) => (
        // key es OBLIGATORIO para listas
        <li key={article.id}>
          <NewsCard {...article} />
        </li>
      ))}
    </ul>
  );
}
```

---

## 4. Hooks y Estado

### useState: Estado Local

```tsx
'use client';
import { useState } from 'react';

function Counter() {
  // [valor, setterFunction] = useState(valorInicial)
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>+1</button>
      <button onClick={() => setCount(prev => prev + 1)}>+1 (functional)</button>
    </div>
  );
}
```

### useEffect: Side Effects

```tsx
'use client';
import { useState, useEffect } from 'react';

function DataFetcher() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    // Esto se ejecuta DESPUÉS del render
    async function fetchData() {
      const res = await fetch('/api/data');
      const json = await res.json();
      setData(json);
      setLoading(false);
    }
    fetchData();
  }, []); // [] = ejecutar solo al montar
  
  // Dependency array:
  // [] = solo al montar
  // [x] = cuando x cambie
  // sin array = cada render (¡cuidado!)
  
  if (loading) return <p>Cargando...</p>;
  return <pre>{JSON.stringify(data)}</pre>;
}
```

### useCallback: Memorizar Funciones

```tsx
// Evita recrear funciones en cada render
const handleSubmit = useCallback(async (query: string) => {
  setLoading(true);
  await api.createFeed(query);
  setLoading(false);
}, []); // Dependencias
```

### Custom Hooks

```tsx
// Hook reutilizable para fetch
function useFetch<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  
  useEffect(() => {
    fetch(url)
      .then(res => res.json())
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [url]);
  
  return { data, loading, error };
}

// Uso:
const { data, loading, error } = useFetch<Feed[]>('/api/feeds');
```

---

## 5. Estilizado con Tailwind CSS

### Filosofía Utility-First

En lugar de CSS tradicional:

```css
/* CSS tradicional */
.card {
  padding: 1rem;
  border-radius: 0.5rem;
  background: white;
}
```

Usas clases utilitarias:

```tsx
<div className="p-4 rounded-lg bg-white">
  Contenido
</div>
```

### Clases Más Usadas

```tsx
// Spacing (p = padding, m = margin)
<div className="p-4 m-2 px-6 py-3 mt-4 mb-8">

// Flexbox
<div className="flex items-center justify-between gap-4">

// Grid
<div className="grid grid-cols-3 gap-4">

// Colors
<p className="text-white bg-purple-600 border-gray-200">

// Sizing
<div className="w-full h-64 max-w-xl min-h-screen">

// Typography
<h1 className="text-4xl font-bold text-center">

// Effects
<div className="rounded-2xl shadow-lg opacity-75">

// Responsive (sm: md: lg: xl:)
<div className="p-2 md:p-4 lg:p-8">  {/* Más padding en pantallas grandes */}

// Estados
<button className="hover:bg-blue-700 focus:ring-2 active:scale-95">
```

### Glassmorphism (usado en Briefly)

```tsx
<div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl">
  {/* Efecto vidrio translúcido */}
</div>
```

---

## 6. Patrones Comunes

### Patrón: Loading State

```tsx
function ArticleList() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);

  if (loading) {
    return <SkeletonLoader />;  // Componente placeholder
  }
  
  if (articles.length === 0) {
    return <EmptyState />;
  }
  
  return <Grid articles={articles} />;
}
```

### Patrón: Controlled Form

```tsx
function SearchForm({ onSearch }: { onSearch: (q: string) => void }) {
  const [query, setQuery] = useState('');
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();  // Prevenir reload
    onSearch(query);
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Buscar..."
      />
      <button type="submit">Buscar</button>
    </form>
  );
}
```

### Patrón: API Client

```tsx
// lib/api.ts
class ApiClient {
  private baseUrl: string;
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }
  
  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!res.ok) throw new Error(`API Error: ${res.status}`);
    return res.json();
  }
  
  async getFeeds() {
    return this.fetch<Feed[]>('/feeds');
  }
}

export const api = new ApiClient('http://localhost:8080/api/v1');
```

---

## 7. Ejercicios Prácticos

### Ejercicio 1: Componente de Tarjeta

Crea un componente `UserCard` que muestre nombre, email y avatar.

```tsx
// Tu código aquí
interface UserCardProps {
  name: string;
  email: string;
  avatarUrl?: string;
}

export function UserCard({ name, email, avatarUrl }: UserCardProps) {
  // Implementar...
}
```

### Ejercicio 2: Hook useLocalStorage

Crea un hook que persista estado en localStorage:

```tsx
function useLocalStorage<T>(key: string, initialValue: T) {
  // 1. Leer valor inicial de localStorage
  // 2. Retornar [value, setValue]
  // 3. setValue debe guardar en localStorage
}
```

### Ejercicio 3: Lista con Filtro

Crea un componente que filtre artículos por búsqueda:

```tsx
function FilterableArticleList({ articles }: { articles: Article[] }) {
  const [search, setSearch] = useState('');
  
  // Filtrar artículos que contengan el texto de búsqueda
  const filtered = // ...
  
  return (
    <div>
      <input ... />
      <ArticleList articles={filtered} />
    </div>
  );
}
```

---

## Recursos Adicionales

- [React Docs](https://react.dev) - Documentación oficial
- [Next.js Learn](https://nextjs.org/learn) - Tutorial interactivo
- [Tailwind CSS Docs](https://tailwindcss.com/docs) - Referencia de clases
- [TypeScript Handbook](https://www.typescriptlang.org/docs/) - Guía de TypeScript

---

## Próximos Pasos en Briefly

1. Estudia `frontend/src/components/NewsCard.tsx` - ejemplo de componente con props
2. Revisa `frontend/src/app/page.tsx` - conexión a API y manejo de estado
3. Modifica estilos en `globals.css` - experimenta con Tailwind
4. Crea un nuevo componente siguiendo los patrones existentes
