# Briefly 🗞️⚡

> AI-powered personalized news feeds using natural language

**Briefly** te permite crear feeds de noticias personalizados describiendo en lenguaje natural qué temas te interesan. El sistema usa IA para encontrar fuentes relevantes, scrapear artículos y presentarlos en un formato limpio y moderno.

![Dashboard Preview](docs/assets/dashboard_preview.png)

---

## 🏗️ Arquitectura

```
briefly/
├── backend/          # FastAPI + Strands + Claude SDK
├── frontend/         # Next.js 14 + TypeScript + Tailwind
├── infra/            # AWS CDK (Python)
└── docs/             # Documentación técnica
```

### Tech Stack

| Componente | Tecnología |
|------------|-----------|
| **Backend** | FastAPI, Python 3.11+, SQLModel |
| **AI/LLM** | Strands Agents, Claude SDK (Anthropic) |
| **DB Relacional** | PostgreSQL |
| **DB NoSQL** | DynamoDB |
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| **Infra** | AWS CDK, ECS Fargate, RDS, Amplify |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- AWS CLI (para deploy)
- Anthropic API Key

### Development Setup

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/briefly.git
cd briefly

# 2. Start databases
docker-compose up -d postgres dynamodb-local

# 3. Setup backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # Add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload

# 4. Setup frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) 🎉

---

## 📁 Repository Structure

### `/backend`
FastAPI application with:
- REST API for feeds, sources, and articles
- Strands agent for natural language interpretation
- Claude-powered web scraper
- PostgreSQL + DynamoDB data layer

[→ Backend README](backend/README.md)

### `/frontend`
Next.js 14 application with:
- Modern dashboard UI
- Natural language feed creation
- Responsive news card grid
- Real-time updates

[→ Frontend README](frontend/README.md)

### `/infra`
AWS CDK infrastructure:
- RDS PostgreSQL
- DynamoDB tables
- ECS Fargate services
- Amplify hosting

[→ Infrastructure README](infra/README.md)

### `/docs`
Technical documentation:
- [Claude Scraping Guide](docs/claude-scraping-guide.md)
- [NL Interpretation Guide](docs/nl-interpretation-guide.md)

---

## 🔑 Key Features

- **🗣️ Natural Language Input**: Describe your interests, get a curated feed
- **🤖 AI-Powered Scraping**: Claude extracts structured content from any news site
- **📰 Clean UI**: Modern, responsive news cards with glassmorphism design
- **⚡ Fast Refresh**: Configurable refresh intervals per feed
- **🌐 Multi-source**: Combine multiple websites into a single feed
- **🔒 Personal**: Your feeds, your sources, your data

---

## 🛠️ Development

### Running Tests

```bash
# Backend tests
cd backend && pytest -v

# Frontend tests
cd frontend && npm test

# E2E tests
cd frontend && npm run test:e2e
```

### Code Quality

```bash
# Backend
cd backend
ruff check .
ruff format .
mypy .

# Frontend
cd frontend
npm run lint
npm run typecheck
```

---

## 📦 Deployment

### AWS Deployment

```bash
cd infra
pip install -r requirements.txt
cdk bootstrap  # First time only
cdk deploy --all
```

See [Infrastructure Guide](infra/README.md) for detailed deployment instructions.

---

## 🗺️ Roadmap

- [ ] MVP Backend (feeds, sources, scraping)
- [ ] MVP Frontend (dashboard, news cards)
- [ ] AI Integration (Strands + Claude)
- [ ] AWS Deployment
- [ ] RSS/Atom feed support
- [ ] Email digest feature
- [ ] Mobile app (React Native)

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) first.

---

<p align="center">
  Built with ❤️ using <a href="https://fastapi.tiangolo.com/">FastAPI</a>, <a href="https://nextjs.org/">Next.js</a>, and <a href="https://www.anthropic.com/">Claude</a>
</p>
