# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CapiAgentes is a multi-agent financial analysis system with a mixed architecture approach:
- **Backend**: Python 3.10+ with FastAPI, LangGraph orchestration, and hexagonal architecture
- **Frontend**: Next.js 15 with App Router, React 19, TypeScript, and Tailwind CSS
- **Real-time**: WebSocket + REST API fallback with structured JSON responses
- **Multi-Agent System**: LangGraph-based orchestrator coordinating specialized financial agents
- **Database**: PostgreSQL with SQLAlchemy (async) and SQLite for LangGraph checkpoints
- **Deployment**: Docker Compose with health checks and volume persistence

## Critical Architecture Notes

### Backend Structure (Clean IA-Ready Architecture)
CapiAgentes follows ARCHITECTURE.md canonical structure for AI development:
```
src/                          # Product code (hexagonal architecture)
├── domain/                   # Business entities and contracts
│   ├── contracts/           # Intent, AgentTask, processing contracts
│   ├── entities/           # Financial domain entities
│   ├── repositories/       # Repository interfaces
│   └── services/           # Domain services
├── application/            # Use cases and application logic
│   ├── conversation/       # Unified conversation state management
│   ├── nlp/               # Intent classification
│   └── use_cases/         # Financial analysis use cases
├── infrastructure/         # External adapters
│   ├── repositories/       # Repository implementations
│   ├── providers/          # Dependency injection providers
│   └── llm/               # LLM reasoning integration
├── presentation/          # External interfaces (FastAPI, WebSocket)
├── core/                  # Configuration, logging, exceptions
└── tests/                 # All tests (unit, integration, contracts)

ia_workspace/                # AI dynamic interaction space
├── orquestador/            # ÚNICO orchestrator pipeline
├── agentes/               # Isolated agent directories
│   ├── summary/           # Financial summary agent
│   ├── branch/            # Branch analysis agent
│   ├── anomaly/           # Anomaly detection agent
│   └── capi_gus_fallback/ # Conversation fallback agent
└── data/                  # Manipulable data (CSV, JSON, cache)
```

**CRITICAL**: AI must use ia_workspace for agent interaction. src/ contains product architecture only.

### Frontend Routes
```
/                    → Redirects to /pages/home
/pages/home         → Home page with navigation cards
/pages/map          → Interactive map with chat
/dashboard          → Executive dashboard
/workspace          → AI workspace
```

## Essential Commands

### Quick Start (Recommended)
```powershell
# Windows - ONE COMMAND PER USE CASE
.\docker-commands.ps1 start     # Start complete system
.\docker-commands.ps1 stop      # Stop everything
.\docker-commands.ps1 restart   # Restart (keeps data)
.\docker-commands.ps1 rebuild   # Rebuild from scratch
.\docker-commands.ps1 logs      # View real-time logs
.\docker-commands.ps1 status    # Check service health
.\docker-commands.ps1 clean     # Clean everything (removes data)

# Linux/Mac
./docker-commands.sh start      # Start complete system
./docker-commands.sh stop       # Stop everything
./docker-commands.sh restart    # Restart (keeps data)
./docker-commands.sh rebuild    # Rebuild from scratch
./docker-commands.sh logs       # View real-time logs
./docker-commands.sh status     # Check service health
./docker-commands.sh clean      # Clean everything (removes data)
```

### Advanced Docker Management (Optional)
```powershell
# Professional deployment with profiles
./docker.ps1 -Action prod -Profile all         # Full production stack
./docker.ps1 -Action dev -Follow               # Development with live logs
./docker.ps1 -Action monitor                   # Start monitoring stack
./docker.ps1 -Action backup                    # Create data backup
./docker.ps1 -Action health                    # Comprehensive health check
```

### Manual Development (Advanced Users)
```bash
# Backend (Terminal 1)
cd Backend
python src/api/main.py    # NOT python main.py or presentation/main.py

# Frontend (Terminal 2)
cd Frontend
npm run dev
```

### Testing
```bash
# Backend tests
cd Backend
pytest tests/ -v
pytest tests/test_summary_agent.py -v  # Specific test
python -m pytest tests/test_structured_metrics_integration.py -v  # Integration test

# Frontend tests
cd Frontend
npm test
```

### Linting & Type Checking
```bash
# Backend
cd Backend
black src/ --check
flake8 src/
mypy src/

# Frontend
cd Frontend
npm run lint
npx tsc --noEmit
```

## Key API Endpoints

### Health & Status
- `GET /api/health` - Basic health check
- `GET /api/status` - Service status with details
- `GET /api/test` - Test endpoint with data status

### Core Functionality
- `POST /api/command` - Execute orchestrator commands (LangGraph runtime)
- `POST /api/ingest` - Data ingestion (auto-loads from data/)
- `WS /ws` - WebSocket for real-time chat with state updates

### Dynamic Agent Management
- `POST /api/agents/register/{agent_name}` - Register agent dynamically
- `POST /api/agents/unregister/{agent_name}` - Unregister agent
- `GET /api/agents/status` - List agent registry status
- `POST /api/graph/refresh` - Rebuild dynamic graph

### Workspace & Files
- `GET /api/files` - List available data files
- `GET /api/workspace/*` - Workspace operations

### Balance Management (Saldos)
- `GET /api/saldos/sucursales` - List all branch balances
- `GET /api/saldos/sucursales/{sucursal_id}` - Get specific branch balance
- `GET /api/saldos/dispositivos` - List device balances

### Backend Control (Frontend API Routes)
- `POST /api/backend/start` - Start backend server
- `POST /api/backend/stop` - Stop backend server
- `GET /api/backend/status` - Check backend status
- `POST /api/backend/kill` - Force kill backend process

## Multi-Agent System Architecture

### Unified LangGraph Orchestrator
Created via `Backend/src/presentation/orchestrator_factory.py` - OrchestratorFactory
- **LangGraph-based orchestration** with graph workflow execution
- **Complete node coverage**: Summary, Branch, Anomaly, and Capi Gus nodes
- **Real data integration**: Uses FileDataRepository and FinancialAnalysisService
- **Domain-driven architecture**: Eliminates hardcoded data, uses repository patterns
- **Hybrid agent integration**: Bridge pattern connects existing agents with LangGraph nodes
- Intent classification and conditional routing via RouterNode
- Response envelope building with workflow stage tracking
- Conversation state management and hash-based deduplication
- WebSocket and REST endpoint integration in `main.py`
- Production-ready architecture with real data validation

### Specialized Agents
- **SummaryAgent**: Financial summaries and total metrics
- **BranchAgent**: Branch-specific performance analysis
- **AnomalyAgent**: Financial irregularity detection
- **Capi Gus (Conversación)**: Greetings, conversation, and unknown intent handling
- **CapiDatabNode**: Database queries and balance operations with semantic planning
- **CapiDesktopNode**: File operations and desktop integration
- **CapiNoticiasNode**: News analysis and external content processing (optional dependency)

### Unified Architecture
- **Single orchestrator**: Clean, unified system with LangGraph runtime
- **Dynamic agent registration**: Runtime agent loading via DynamicGraphManager
- **Checkpoint persistence**: SQLite-based workflow state persistence
- **Production ready**: Streamlined codebase with monitoring and health checks

### Key Architecture Patterns

#### Dependency Injection
- **RepositoryProvider**: Singleton pattern for managing repository instances
- **Test-friendly**: Easy mocking via constructor injection
- **Thread-safe**: Uses threading locks for singleton access

#### Conversation Management
- **ConversationStateManager**: Unified conversation state with TTL cleanup
- **Anti-repetition**: Hash-based duplicate detection for queries and summaries
- **Session persistence**: Automatic cleanup of expired sessions

#### Structured Data Response
- **ResponseEnvelope**: Consistent response format with metadata
- **Structured metrics**: Eliminates fragile text parsing in frontend
- **Trace ID propagation**: Full request traceability through @with_trace decorator

#### LLM Integration
- **CompositeLLMReasoner**: Multi-strategy reasoning (FAQ → LLM → Enhanced stub)
- **AdvancedReasoner**: Semantic intent classification with multi-step plan generation
- **Fault tolerant**: Graceful degradation when OpenAI API unavailable
- **Pattern matching**: Fast FAQ responses for common queries

#### State Management
- **GraphState**: Immutable state with type safety and JSON serialization
- **StateMutator**: Utility methods for state updates (merge_dict, update_field, append_to_list)
- **WorkflowStatus**: Comprehensive workflow tracking (INITIALIZED, PROCESSING, COMPLETED, FAILED, PAUSED)
- **Real-time updates**: WebSocket state snapshots and node transition broadcasting

### LangGraph Workflow Architecture
```
User Query → StartNode → IntentNode → ReActNode → ReasoningNode → SupervisorNode → RouterNode → [SummaryNode|BranchNode|AnomalyNode|Capi GusNode|CapiDatabNode|CapiDesktopNode|CapiNoticiasNode] → HumanGateNode → AssembleNode → FinalizeNode
```

#### Advanced Multi-Agent Architecture
- **ReActNode**: Implements ReAct (Reasoning + Acting) pattern for iterative problem solving
- **ReasoningNode**: Advanced deliberation using `AdvancedReasoner` for multi-step planning
- **SupervisorNode**: Coordinates parallel agent execution and manages task queues
- **HumanGateNode**: Human-in-the-loop approval gate with interrupt capabilities
- **Dynamic Graph Builder**: Runtime agent registration and graph reconstruction

### Data Flow
1. CSV/Excel files → `Backend/ia_workspace/data/` directory (auto-loaded on startup)
2. Query → LangGraph Runtime → Intent Detection → Conditional Routing
3. Specialized Node → FileDataRepository → FinancialAnalysisService → Domain Validation
4. Node Processing → AssembleNode → ResponseEnvelope → WebSocket/REST → Frontend
5. Frontend → Structured metrics consumption (no text parsing)

**Critical**: The system now uses real data from CSV files via FileDataRepository, eliminating previous hardcoded sample data fallbacks.

## Frontend Architecture

### Component Structure
```
Frontend/src/app/
├── pages/              # Page components
│   ├── home/          # Landing page
│   └── map/           # Interactive map with chat
├── dashboard/          # Executive dashboard
├── components/         # Shared components
│   ├── Chat/          # ChatBox component
│   ├── Dashboard/     # Dashboard components
│   └── [Header, Footer, NavBar, etc.]
└── utils/orchestrator/ # Backend client
```

### Key Frontend Files
- `src/app/utils/orchestrator/client.ts` - Backend API client
- `src/app/components/Chat/ChatBox.tsx` - Main chat interface
- `src/app/dashboard/page.tsx` - Dashboard implementation
- `src/app/services/saldosService.ts` - Balance data service for branch operations
- `src/app/services/dashboardService.ts` - Dashboard data aggregation service

## Configuration

### Backend Environment (.env)
```env
OPENAI_API_KEY=sk-...       # Optional for LLM reasoning (uses FAQ fallback if missing)
SECRET_KEY=...               # 32+ char secret for sessions
LOG_LEVEL=INFO              # Logging level (DEBUG, INFO, WARNING, ERROR)
ENVIRONMENT=development     # Environment (development, production)
STRUCTURED_LOGS=false       # Enable JSON structured logging with trace_id
```

### Frontend Environment (.env.local)
```env
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=...     # For map functionality
NEXT_TELEMETRY_DISABLED=1               # Disable Next.js telemetry
NODE_ENV=development                    # Or production
```

## Common Issues & Solutions

### Backend Won't Start
- Check Python version (3.10+) with `python --version`
- Ensure running from correct directory and file: `cd Backend && python src/api/main.py` (NOT `python main.py`)
- Missing dependencies: `pip install -r requirements.txt` from Backend directory
- Path issues: Backend entry point includes UTF-8 encoding setup and path management
- OpenAI API key missing: System will work with FAQ fallback, but log warnings
- Import errors: Ensure PYTHONPATH includes Backend/src or use `python -m` syntax

### Agent/Orchestrator Issues
- **Import errors**: Ensure Python path includes Backend/src directory
- **Repository not found**: Check `RepositoryProvider` singleton initialization
- **No agents registered**: Verify agent registry in orchestrator initialization
- **Conversation state issues**: Check `ConversationStateManager` TTL and cleanup

### Test Failures
- **Import path errors**: Run tests from Backend directory with `python -m pytest`
- **Mock repository issues**: Use `repo_provider` parameter in Orchestrator constructor
- **Trace ID missing**: Ensure `@with_trace` decorator on test functions
- **Parity test tolerance**: Adjust tolerance ratio in `tests/utils/parity.py`

### Frontend Issues
- **API connection failed**: Verify backend running on port 8000
- **Structured metrics missing**: Check ResponseEnvelope.data.metrics format
- **WebSocket disconnect**: System automatically falls back to REST
- **Dashboard parsing errors**: Ensure backend returns structured metrics

### Data Processing Issues
- **No data loaded**: Place CSV files in `Backend/ia_workspace/data/` directory
- **File format unsupported**: Use CSV, Excel (.xlsx), or Parquet formats
- **Auto-ingestion failed**: Check file permissions and format validity

## Data Processing

### Supported Formats
- CSV files (primary)
- Excel (.xlsx)
- Parquet files

### Data Location
- Place files in `Backend/ia_workspace/data/` directory - they're auto-loaded on startup
- Auto-ingestion handles multiple file formats via FileDataRepository
- Real-time domain validation rejects invalid records (e.g., zero amounts)
- Data loading supports both individual and bulk file processing
- Docker volume persistence: `Backend/ia_workspace:/app/ia_workspace`

### Sample Queries
- "Analiza los datos financieros"
- "Detectar anomalías en las transacciones"
- "Mostrar resumen de ingresos"
- "Rendimiento por sucursal"
- "¿Cuál es el saldo de la sucursal 001?"
- "Mostrar balances de todas las sucursales"
- "Estado de dispositivos por sucursal"

## Desktop Integration

### CapiLauncher.exe
- Windows executable built with PyInstaller from `launcher/` directory
- Provides desktop integration for launching the platform
- Build with: `launcher/scripts/Build Launcher.bat`
- Generated executable appears in repository root

## Testing Strategy

### Backend Tests Structure
```
Backend/tests/
├── test_orchestrator.py              # Main orchestrator tests
├── test_*_agent.py                   # Individual agent tests
├── test_structured_metrics_integration.py  # Metrics integration
├── test_conversation_state*.py      # Conversation management
├── test_trace_id_propagation.py     # Logging and traceability
├── test_repository_provider*.py     # Repository DI tests
└── utils/parity.py                   # Test utilities for comparisons
```

### Key Test Categories
- **Agent Tests**: Individual agent functionality (`test_*_agent.py`)
- **Integration Tests**: End-to-end workflow testing (`test_*_integration.py`)  
- **Repository Tests**: Data layer and dependency injection (`test_repository_*`)
- **Conversation Tests**: Session management and state persistence
- **Trace Tests**: Logging and request correlation (`test_trace_id_propagation.py`)

### Test Utilities
- **Parity Testing**: `tests/utils/parity.py` provides tolerance-based comparison functions
- **Mock Repositories**: Easy dependency injection for testing
- **Response Envelope Validation**: Structured testing of API responses

### Frontend Test Commands
```bash
cd Frontend
npm test          # Run all tests via Vitest
npm run dev       # Development with Turbopack (Next.js 15)
npm run build     # Production build check
npm run lint      # ESLint checking
npx tsc --noEmit  # TypeScript type checking
```

### LangGraph Testing
```bash
# Backend - Test individual nodes
cd Backend
pytest tests/test_reasoning_node.py -v     # Test ReasoningNode
pytest tests/test_react_node.py -v         # Test ReActNode
pytest tests/test_supervisor_node.py -v    # Test SupervisorNode
pytest tests/test_dynamic_graph*.py -v     # Test dynamic graph management

# Integration testing
pytest tests/test_langgraph_integration.py -v  # Full workflow integration
pytest tests/test_reasoning_system.py -v       # Advanced reasoning system
```

## Performance Considerations

- WebSocket preferred over REST for real-time updates
- Orchestrator caches data in memory after initial load
- Frontend uses React 19 with Turbopack for fast dev builds
- Backend runs single worker in dev, can scale in production

## Deployment Notes

- Docker Compose configured for production deployment
- Backend healthcheck may take 30s to pass initially
- Frontend build includes all environment variables at build time
- PostgreSQL data persisted at `postgres_data:/var/lib/postgresql/data/pgdata`
- Backend workspace persisted at `Backend/ia_workspace:/app/ia_workspace`
- Desktop integration via mounted volume: `C:/Users/lucas/OneDrive/Desktop:/app/user_desktop:ro`

## Repository Structure

### Key Directories
```
CAPI/
├── Backend/                  # Python FastAPI backend
│   ├── src/                 # Clean architecture source code
│   ├── ia_workspace/        # AI agents and data workspace
│   ├── tests/               # Test suite
│   ├── logs/                # Application logs
│   └── Dockerfile           # Backend container config
├── Frontend/                # Next.js React frontend
│   ├── src/app/            # App Router pages and components
│   ├── public/             # Static assets
│   └── Dockerfile          # Frontend container config
├── docs/                   # Project documentation
├── launcher/               # Desktop launcher source
├── observability/          # Elastic stack for monitoring
└── docker-compose.yml      # Main deployment configuration
```

### Important Files
- `docker-commands.ps1/.sh` - Unified Docker orchestration scripts
- `.env.example` - Environment variable template
- `AGENTS.md` - Agent system documentation
- `README.md` - Quick start guide

## Key Technology Decisions

### Backend Stack
- **FastAPI**: High-performance async API framework
- **LangGraph**: Multi-agent workflow orchestration
- **Pydantic**: Data validation and serialization
- **SQLAlchemy**: Database ORM with async support
- **pytest**: Testing framework with async support

### Frontend Stack
- **Next.js 15**: React framework with App Router
- **React 19**: Latest React with server components
- **TypeScript**: Type safety and better DX
- **Tailwind CSS**: Utility-first CSS framework
- **Leaflet**: Interactive maps via react-leaflet
- **Recharts**: Data visualization library
- **Vitest**: Fast unit testing framework