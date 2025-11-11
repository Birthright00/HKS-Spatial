# HKS-Spatial Microservices Architecture

## Overview

This repository uses a **microservices architecture** to manage multiple submodules with conflicting dependencies. Each submodule runs in its own isolated virtual environment as an independent service, coordinated by a central service manager.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     HKS-Spatial Root                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Coordinator (Central venv)                   │  │
│  │  - Manages service lifecycle                         │  │
│  │  - Health monitoring                                 │  │
│  │  - API routing                                       │  │
│  │  - Shared .env configuration                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│          ┌────────────────┴────────────────┐               │
│          │                                 │               │
│          ▼                                 ▼               │
│  ┌──────────────────┐            ┌──────────────────┐     │
│  │  RAG-Langchain   │            │ Picture Gen      │     │
│  │  Service         │            │ Service          │     │
│  │  (Port 8001)     │            │ (Port 8002)      │     │
│  │                  │            │                  │     │
│  │  Own venv:       │            │  Own venv:       │     │
│  │  - langchain     │            │  - torch         │     │
│  │  - openai        │            │  - torchvision   │     │
│  │  - chromadb      │            │  - opencv        │     │
│  │  - spacy         │            │  - transformers  │     │
│  │  - gradio        │            │  - google-genai  │     │
│  └──────────────────┘            └──────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Coordinator ([coordinator/](coordinator/))
The central service manager that:
- Starts/stops services in their respective venvs
- Health checks and monitoring
- Routes requests to appropriate services
- Manages shared configuration from `.env`

**Dependencies**: Minimal (requests, fastapi, python-dotenv)

### 2. RAG-Langchain Service ([RAG-Langchain/](RAG-Langchain/))
Dementia home safety image analysis using RAG + Vision LLM.

**API Endpoints**:
- `POST /analyze/image` - Analyze uploaded image
- `POST /analyze/base64` - Analyze base64 image
- `POST /rag/query` - Query RAG system
- `GET /health` - Health check

**Dependencies**: ~200 packages including langchain, openai, chromadb

### 3. Picture Generation Service ([picture-generation-verbose-api-module/](picture-generation-verbose-api-module/))
Image generation and editing using Nanobanana/Gemini API.

**API Endpoints**:
- `POST /generate/edit` - Edit uploaded image
- `POST /generate/edit-base64` - Edit base64 image
- `GET /health` - Health check

**Dependencies**: PyTorch, computer vision libraries

## Benefits of This Architecture

### 1. Dependency Isolation
Each submodule maintains its own virtual environment:
- No dependency conflicts between torch and langchain
- Independent version management
- Can update one service without affecting others

### 2. Robustness
- Services can restart independently
- Failure in one service doesn't crash others
- Health monitoring for all services
- Graceful degradation

### 3. Scalability
- Services can be moved to different machines
- Can scale individual services based on load
- Easy to add new services

### 4. Development Flexibility
- Work on one service without affecting others
- Clear API contracts between services
- Easier testing and debugging
- Hot reload individual services

### 5. Unified Configuration
- Single `.env` file for all API keys
- Consistent configuration across services
- Easy environment management

## Directory Structure

```
HKS-Spatial/
├── .env                          # Shared environment variables
├── .env.example                  # Template for .env
├── .gitignore                    # Git ignore patterns
├── requirements.txt              # Coordinator dependencies
├── setup.bat                     # Windows setup script
├── setup.sh                      # Unix/Mac setup script
├── README.md                     # This file
│
├── coordinator/                  # Central coordinator
│   ├── __init__.py
│   ├── config.py                 # Shared configuration
│   ├── service_manager.py        # Service management
│   └── main.py                   # CLI entry point
│
├── RAG-Langchain/               # Submodule
│   ├── venv/                    # Its own virtual environment
│   ├── requirements.txt         # Its dependencies
│   ├── api_server.py            # FastAPI service wrapper
│   ├── dementia_pipeline.py     # Core functionality
│   └── ...
│
├── picture-generation-verbose-api-module/  # Submodule
│   ├── venv/                    # Its own virtual environment
│   ├── requirements.txt         # Its dependencies
│   ├── api_server.py            # FastAPI service wrapper
│   ├── nanobanana_edit.py       # Core functionality
│   └── ...
│
└── Spatial-Design-Studio-Frontend/  # Frontend submodule
    └── ...
```

## Quick Start

### 1. Initial Setup

**Windows**:
```bash
setup.bat
```

**Unix/Mac**:
```bash
chmod +x setup.sh
./setup.sh
```

This script will:
1. Create coordinator venv
2. Create RAG-Langchain venv
3. Create picture-generation venv
4. Install all dependencies
5. Create `.env` from template

### 2. Configure Environment Variables

Edit `.env` and add your API keys:

```env
OPENAI_API_KEY=your_key_here
NANOBANANA_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
```

### 3. Run Complete Workflow (Recommended)

**Analyze and transform an image in one command**:

```bash
# Windows
venv\Scripts\python analyze_and_transform_image.py room.jpg

# Unix/Mac
source venv/bin/activate
python analyze_and_transform_image.py room.jpg
```

This will:
1. Start microservices automatically
2. Analyze image with RAG (dementia_pipeline.py)
3. Transform image based on analysis (transform_image.py)
4. Save results to `./output/` directory
5. Stop services automatically

**With custom output directory**:
```bash
python analyze_and_transform_image.py room.jpg --output-dir results/
```

### 4. Manual Service Management (Advanced)

If you need finer control over services:

**Start all services**:
```bash
# Windows
venv\Scripts\python -m coordinator.main start

# Unix/Mac
source venv/bin/activate
python -m coordinator.main start
```

**Check status**:
```bash
python -m coordinator.main status
```

**Stop services**:
```bash
python -m coordinator.main stop
```

## Main Workflow

### Complete Pipeline: Analyze + Transform

The main use case is to analyze an image and apply transformations:

```bash
python analyze_and_transform_image.py room_photo.jpg --output-dir results/
```

**What happens**:
1. **Services start**: RAG-Langchain (port 8001) and Picture-Generation (port 8002)
2. **Analysis**: `dementia_pipeline.py` analyzes the image using RAG + GPT-4o Vision
   - Returns detailed text analysis
   - Extracts JSON with structured recommendations
3. **Transformation**: `transform_image.py` applies each recommendation sequentially
   - Segments each item to be changed
   - Uses Nanobanana/Gemini API to edit the image
   - Returns final transformed image
4. **Results saved**:
   - `{image}_analysis_{timestamp}.txt` - Full text analysis
   - `{image}_analysis_{timestamp}.json` - Structured JSON
   - `{image}_transformed_{timestamp}.jpg` - Edited image
5. **Services stop** automatically

### Individual Services (Advanced)

If you need to call services separately:

#### Analyze Only

```bash
# Start services
python -m coordinator.main start

# Analyze an image (returns JSON)
curl -X POST http://127.0.0.1:8001/analyze \
  -F "file=@room.jpg"

# Stop services
python -m coordinator.main stop
```

#### Transform Only (with existing JSON)

```bash
# Requires services running
curl -X POST http://127.0.0.1:8002/transform \
  -F "file=@room.jpg" \
  -F "analysis_json=@analysis.json"
```

## API Reference

### RAG Service (Port 8001)

Wraps [dementia_pipeline.py](RAG-Langchain/dementia_pipeline.py)

#### POST /analyze
Analyze uploaded image for dementia safety issues.

**Request**:
- Form data with `file` (image file)

**Response**:
```json
{
  "success": true,
  "analysis_text": "Full text analysis with markdown...",
  "analysis_json": {
    "room_type": "...",
    "analysis_summary": {...},
    "issues": [...]
  }
}
```

#### GET /health
Check service health.

### Picture Generation Service (Port 8002)

Wraps [transform_image.py](picture-generation-verbose-api-module/transform_image.py)

#### POST /transform
Transform image based on JSON recommendations.

**Request**:
- Form data with `file` (original image)
- `analysis_json` (JSON string with issues array)

**Response**:
```json
{
  "success": true,
  "transformed_image_path": "/tmp/transform/transformed_xxx.jpg"
}
```

#### GET /download/{filename}
Download transformed image file.

#### GET /health
Check service health.

## Maintenance

### Update Submodule Dependencies

To update dependencies for a specific submodule:

```bash
# For RAG-Langchain
cd RAG-Langchain
venv\Scripts\activate  # or source venv/bin/activate
pip install --upgrade package_name
pip freeze > requirements.txt
deactivate
cd ..
```

### Add New Service

1. Add submodule with its own `requirements.txt`
2. Create `api_server.py` in the submodule
3. Add service configuration to [coordinator/config.py](coordinator/config.py)
4. Add service to [coordinator/service_manager.py](coordinator/service_manager.py)
5. Update setup scripts

### Troubleshooting

**Service won't start**:
- Check if venv exists: `ls RAG-Langchain/venv`
- Verify API keys in `.env`
- Check logs in service output

**Port conflicts**:
- Change ports in `.env`:
  ```env
  RAG_SERVICE_PORT=8011
  IMAGE_GEN_SERVICE_PORT=8012
  ```

**Import errors**:
- Ensure you're using the correct venv
- Reinstall dependencies: `pip install -r requirements.txt`

## Best Practices

1. **Always use the coordinator** to start services (don't run services directly)
2. **Keep .env in root** - never commit it to git
3. **Update requirements.txt** when adding packages to a service
4. **Check service health** before making API calls
5. **Use setup scripts** for new environments
6. **Monitor service logs** for debugging

## Future Enhancements

- [ ] Docker containerization for easier deployment
- [ ] Service auto-restart on failure
- [ ] Load balancing for multiple service instances
- [ ] Centralized logging system
- [ ] API gateway with authentication
- [ ] Service discovery mechanism
- [ ] Prometheus metrics export
- [ ] Frontend integration

## Contributing

When adding new functionality:

1. Determine if it belongs in an existing service or needs a new one
2. Keep services focused and single-purpose
3. Document API endpoints in this file
4. Update setup scripts if adding dependencies
5. Test service startup and health checks

## License

MIT License
