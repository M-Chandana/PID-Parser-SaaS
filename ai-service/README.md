# PID Parser AI Microservice Wrapper

This service provides a FastAPI wrapper for the P&ID detection and parsing logic.

## Current Milestone: B1
- [x] FastAPI Service Structure
- [x] Health Check Endpoint (`/health`)
- [x] Parsing Wrapper Endpoint (`/parse`)
- [x] Pydantic Response Schemas
- [x] Pipeline Logic Stubs (Ready for giza-pidparser integration)
- [x] Dockerization
- [x] AI Capability Parity Matrix

## Project Structure
```
ai-service/
├── app/
│   ├── main.py           # API endpoints
│   ├── schemas/          # Data models
│   │   └── parser.py     # Response schema
│   └── services/         # Core logic
│       └── parser_engine.py # Pipeline implementation
├── Dockerfile            # Container config
├── requirements.txt      # Python dependencies
├── .env.example          # Environment template
└── PARITY_MATRIX.md      # AI capability tracking
```

## Running the Service

### Prerequisites
- Python 3.11+
- Docker (Optional)

### Local Setup
1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`.
Documentation: `http://localhost:8000/docs`.

### Docker
```bash
docker build -t pid-parser-ai .
docker run -p 8000:8000 pid-parser-ai
```
