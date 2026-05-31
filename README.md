# MoonCARE

**Companion for Your Menstrual Emotional Well-being**

MoonCARE is an intelligent emotional health app designed specifically for women. Through natural conversations, it understands your premenstrual state, provides warm emotional support, and offers gentle health guidance.

---

## Features

### 1. AI Emotional Chat
**Description**: An intelligent conversational engine based on a multi-Agent routing system that perceives your emotional state and provides personalized emotional companionship.

**Benefits**: Get understanding and response anytime you open the app. AI not only acknowledges emotional expressions but also naturally learns about your physical state and life circumstances.

**Use Cases**:
- When experiencing premenstrual mood swings or irritability
- When you want to talk but don't want to burden others
- When you need emotional support late at night

---

### 2. Premenstrual State Awareness
**Description**: Collects signals related to Premenstrual Syndrome (PMS) through natural conversation and generates a for-reference-only cycle state summary.

**Benefits**: Without any "tests" or "questionnaires", the system naturally understands your state through conversation and generates a reviewable summary, helping you better understand your emotional cycles.

**Use Cases**:
- Want to understand your premenstrual syndrome patterns
- Want to know if recent mood dips are related to your cycle
- Need a clearer understanding of your current state

---

### 3. Menstrual Cycle Tracking
**Description**: Record and predict menstrual cycles, tracking different phases such as menstruation, ovulation, and luteal phase.

**Benefits**: Stop manual calculations. Smart predictions help you prepare in advance. Intuitive phase display lets you know which physiological period you're currently in, helping you arrange life and work accordingly.

**Use Cases**:
- Record menstruation dates
- Predict next period
- Understand which cycle phase you're in

---

### 4. Mood Diary
**Description**: Daily mood tracking with text and emotion tags, recording physical symptoms and life events.

**Benefits**: Through continuous recording, discover patterns and triggers of your emotional changes. When reviewing historical diaries, see the trajectory of your emotional起伏.

**Use Cases**:
- Review today's emotions before bed
- Record physical symptoms (headache, abdominal pain)
- Tag life events that affect emotions

---

### 5. Music Therapy
**Description**: Recommends suitable music playlists based on your emotional state and cycle phase.

**Benefits**: No need to struggle with choices - the system recommends appropriate therapeutic music based on your state. Get suitable musical support when feeling down.

**Use Cases**:
- When relaxing before bed
- Wanting comfort during menstruation
- Needing stress relief when work pressure builds

---

### 6. Breathing Guide
**Description**: Structured breathing exercises to help relieve anxiety and physical tension.

**Benefits**: Relieve immediate physical tension and emotional anxiety through scientific breathing rhythms. A readily available quick relaxation tool.

**Use Cases**:
- When feeling anxious or tense
- Wanting relief from menstrual cramps
- Wanting to relax and fall asleep before bed

---

### 7. Mood Waves
**Description**: Visualized emotional and cycle fluctuation curves, displaying trends in your physical and mental state.

**Benefits**: See your emotional cycle patterns intuitively, better planning important schedules and life rhythms.

**Use Cases**:
- Review a week/month's emotional changes
- Analyze the relationship between cycle and emotions
- Choose the best time for important matters

---

### 8. Profile Center
**Description**: Personal profile management, app settings, and data management.

**Benefits**: Manage your account information, set notification preferences, export or delete personal data, and protect privacy.

**Use Cases**:
- Change nickname and avatar
- Set reminder notifications
- Export or delete personal data

---

## Technical Architecture

### Tech Stack

| Layer | Technology | Description |
|-------|------------|-------------|
| Frontend | Vue 3, Composition API, Pinia, Axios, Vite | Responsive mobile interface |
| Backend | FastAPI, SQLAlchemy, Pydantic | High-performance Python API |
| Database | SQLite (local) / PostgreSQL (production) | Data persistence |
| AI | Multi-Agent routing, LLM Service | Intelligent conversation and emotion understanding |
| Deployment | Docker, Docker Compose | Containerized deployment |

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │  Home   │  │  Chat   │  │  Cycle  │  │  Diary  │       │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘       │
│       │            │            │            │              │
│  ┌────┴────────────┴────────────┴────────────┴────┐        │
│  │              Vue 3 + Pinia State                 │        │
│  └─────────────────────┬───────────────────────────┘        │
└────────────────────────┼──────────────────────────────────────┘
                         │ HTTP / WebSocket
┌────────────────────────┼──────────────────────────────────────┐
│                        │           Backend                    │
│  ┌─────────────────────┴───────────────────────────┐        │
│  │              FastAPI REST / WebSocket            │        │
│  └───┬─────────┬─────────┬─────────┬─────────┬───┘        │
│      │         │         │         │         │              │
│  ┌───┴───┐ ┌───┴───┐ ┌───┴───┐ ┌───┴───┐ ┌───┴───┐        │
│  │Percept│ │Router │ │Support│ │Knowl- │ │Inter- │        │
│  │ionAgent│ │      │ │tAgent │ │edgeAgent│ │vention│        │
│  └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ │Agent  │         │
│      │         │         │         │      │       │         │
│      └─────────┴────┬────┴─────────┴──────┴───────┘         │
│                     │                                       │
│  ┌──────────────────┴────────────────────────────────┐      │
│  │            LLM Service / Fallback                  │      │
│  └──────────────────┬────────────────────────────────┘      │
│                     │                                       │
│  ┌──────────────────┴────────────────────────────────┐      │
│  │         SQLAlchemy + Database Session             │      │
│  └──────────────────┬────────────────────────────────┘      │
└──────────────────────┼───────────────────────────────────────┘
                       │
              ┌────────┴────────┐
              │  SQLite/PostgreSQL│
              └──────────────────┘
```

### Data Flow

```
User Input → PerceptionAgent (Risk Detection) → Router (Intent Routing)
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
              Crisis/High          Support           Knowledge
               → Intervention      → SupportAgent    → KnowledgeAgent
                    │                    │                    │
                    └────────────────────┴────────────────────┘
                                         │
                                   LLM Service
                                         │
                           ┌─────────────┴─────────────┐
                           │                           │
                      Normal Reply              Timeout Fallback
                           │                           │
                      Return to User           Return Safe Fallback
```

---

## Quick Start

### Requirements

| Tool | Version |
|------|---------|
| Python | 3.10+ |
| Node.js | 20+ |
| npm | 10+ |
| Docker (optional) | 24+ |

### Local Development

**Method 1: One-command Setup**

```bash
# After cloning, run from project root
npm run setup    # Install dependencies, copy env files
npm run dev      # Start both frontend and backend
```

**Method 2: Manual Start**

```bash
# Terminal 1: Start backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2: Start frontend
cd frontend
npm install
npm run dev
```

After startup, access:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

### Docker Deployment

**1. Prepare Environment File**

```bash
cp .env.example .env
```

Edit `.env` and configure required fields:

```env
# Database password (required)
DB_PASSWORD=your_strong_password

# JWT secret (required)
SECRET_KEY=your_long_random_secret_key

# AI Provider config (at least one required)
NVIDIA_API_KEY=your_nvidia_api_key
# or
ZAI_API_KEY=your_zai_api_key
# or
OPENAI_API_KEY=your_openai_api_key
```

**2. Build and Start**

```bash
# Build image
docker compose build

# Start services
docker compose up -d
```

**3. Verify Services**

```bash
# Check service status
docker compose ps

# View app logs
docker compose logs -f app

# Check health
curl http://localhost:8000/healthz
```

**4. Stop Services**

```bash
docker compose down
```

To clean data:

```bash
docker compose down -v
```

---

## Configuration Guide

### Frontend Environment Variables

Create `frontend/.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API URL | http://localhost:8000/api/v1 |

### Backend Environment Variables

Create `backend/.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | sqlite:///./healthai.db |
| `SECRET_KEY` | JWT signing key | - (required) |
| `DEBUG` | Debug mode | true |
| `LLM_PROVIDER` | AI Provider | nvidia |

### AI Provider Configuration

| Provider | Required Variables | Description |
|----------|-------------------|-------------|
| NVIDIA | `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, `NVIDIA_MODEL_NAME` | NVIDIA NIM |
| Z.AI (GLM) | `ZAI_API_KEY`, `ZAI_BASE_URL`, `ZAI_MODEL_NAME` | Zhipu GLM series |
| OpenAI | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `MODEL_NAME` | OpenAI compatible |
| vLLM | `VLLM_BASE_URL`, `VLLM_API_KEY`, `VLLM_MODEL_NAME` | Local vLLM server |
| Accelerated | `ACCELERATED_LLM_BASE_URL`, `ACCELERATED_LLM_API_KEY`, `ACCELERATED_LLM_MODEL_NAME` | Accelerated inference |

### LLM Timeout Configuration

| Variable | Description | Default (seconds) |
|----------|-------------|-------------------|
| `LLM_REQUEST_TIMEOUT_SECONDS` | Total request timeout | 45 |
| `LLM_CONNECT_TIMEOUT_SECONDS` | Connection timeout | 10 |
| `CHAT_AGENT_REPLY_TIMEOUT_SECONDS` | Agent reply timeout | 45 |

---

## Privacy & Security

### Data Statement
- Chat logs, diaries, and cycle data are stored only on your self-deployed server or locally
- All user data is stored locally by default and is not uploaded to any third party
- Production-grade security policies are enforced when `DEBUG=false`

### Crisis Intervention
- Built-in crisis keyword detection
- Immediate safety intervention when high-risk expressions like suicide or self-harm are detected
- Provides national mental health helpline and other resources

### Security Recommendations
- Always set strong passwords and JWT keys for production
- Never commit `.env` files to version control
- Regularly update AI Provider API keys

---

## Usage Notes

**1. Purpose & Identity**
- MoonCARE is an emotional companion tool, not a medical service
- Cannot replace doctor diagnosis, treatment, or advice

**2. Data Accuracy**
- Cycle predictions are based on historical data; individual differences may cause deviations
- AI responses are based on statistical patterns and cannot guarantee complete accuracy

**3. Emergencies**
- For urgent psychological crises, please call the mental health helpline or seek medical attention
- AI companionship cannot replace professional mental health services

**4. User Responsibility**
- Please ensure shared content complies with local laws and regulations
- Protect your account credentials and password security

---

## AI-Related Questions

**Q: AI responses are slow or timing out. What should I do?**
A: Check your network connection and AI Provider status. You can adjust `LLM_REQUEST_TIMEOUT_SECONDS` in `.env`. Persistent timeouts may indicate API rate limits or server-side issues.

**Q: How do I switch to a different AI model?**
A: Modify `LLM_PROVIDER` and corresponding API Key in the backend `.env`. Supported providers: NVIDIA, Z.AI (GLM), OpenAI, vLLM, Accelerated.

**Q: Can I run AI models locally?**
A: Yes. Deploy local models through vLLM or other OpenAI-compatible inference services. Configure `VLLM_BASE_URL` and `VLLM_MODEL_NAME` in `.env`. vLLM on Windows requires GPU support.

**Q: AI response quality is inconsistent. What can I do?**
A: Try: 1) Switch AI Provider; 2) Adjust timeout configuration; 3) Ensure API Key quota is sufficient; 4) Check prompt configuration.

**Q: Can I use it offline?**
A: Current version requires network connection for AI services. Fully offline mode is planned.

---

## Local Test Account

Local development mode (`DEBUG=true`) provides a test account:

| Email | Password |
|-------|----------|
| test@mooncare.local | test123456 |

**Note**: Set `DEBUG=false` in production environments.

---

## FAQ

**Q: How do I change the port?**
A: For local development, modify ports in `package.json`; for Docker deployment, modify `APP_PORT` in `.env`.

**Q: How do I reset the database?**
A: Delete `backend/healthai.db` (SQLite) or run database migration rollback (PostgreSQL).

**Q: Frontend build failed. What should I do?**
A: Check Node.js version (needs 20+), clear cache `rm -rf node_modules package-lock.json && npm install`.

**Q: Database connection fails during Docker deployment?**
A: Ensure `DB_PASSWORD` is set in `.env` and the postgres service in `docker-compose.yml` is ready. Wait for healthcheck to pass before accessing the app.

---

## License

This project is for learning and personal use only. For commercial use, please contact the developer.

---

## Contact

- Issue Reports: https://github.com/your-repo/issues
- Product Inquiries: contact@mooncare.example