# HKS-Spatial

Image analysis and transformation system for dementia-friendly home design using RAG + Vision LLM and automated image editing.

## Directory Structure

```
HKS-Spatial/
├── backend/                      # Node.js/Express backend server
│   ├── middleware/               # Express middleware
│   ├── models/                   # Database models
│   ├── routes/                   # API routes
│   ├── server.js                 # Main server file
│   ├── package.json              # Node.js dependencies
│   └── old.env                   # Backend environment variables
│
├── Spatial-Design-Studio-Frontend/  # React frontend application
│   └── frontend/
│       ├── src/                  # React source code
│       ├── public/               # Static assets
│       ├── package.json          # Frontend dependencies
│       └── vite.config.ts        # Vite configuration
│
├── coordinator/                  # Service management
│   ├── config.py                 # Configuration
│   ├── service_manager.py        # Service lifecycle
│   └── main.py                   # CLI for manual control
│
├── RAG-Langchain/               # Image analysis service (submodule)
│   ├── .venv/                   # Virtual environment
│   ├── requirements.txt         # Dependencies
│   ├── api_server.py            # FastAPI wrapper
│   └── dementia_pipeline.py     # Core analysis logic
│
├── picture-generation-verbose-api-module/  # Image transformation service (submodule)
│   ├── myenv/                   # Virtual environment
│   ├── requirements.txt         # Dependencies
│   ├── transform_image.py       # Core transformation logic
│   └── interior-segment-labeler/ # Image segmentation
│
├── .env                          # Environment variables (API keys)
├── .env.example                  # Template for .env
├── requirements.txt              # Coordinator dependencies
├── package.json                  # Root package.json (monorepo)
├── setup.bat                     # Windows setup script
├── setup.sh                      # Unix/Mac setup script
└── analyze_and_transform_image.py # Main workflow script
```

## Setup

### 1. Clone the repositary with submodules

```bash
git clone --recursive https://github.com/Birthright00/HKS-Spatial.git
```

### 2. Run Setup Script

**Windows**:
```bash
./setup.bat
```

**Unix/Mac**:
```bash
chmod +x setup.sh
./setup.sh
```

This will:
- Create virtual environments for coordinator and both submodules
- Install all Python dependencies (CPU version of PyTorch by default)
- Create `.env` file from template

**Note**: The setup script currently handles Python backend services only. Frontend setup is separate (see step 3 below).

**Note on GPU Support**: The setup installs CPU-only PyTorch by default for maximum compatibility. For GPU acceleration, manually install the CUDA version after setup:
```bash
cd picture-generation-verbose-api-module
source myenv/bin/activate  # or myenv\Scripts\activate on Windows
pip install torch==2.6.0+cu124 torchvision==0.21.0+cu124 --extra-index-url https://download.pytorch.org/whl/cu124
```
The code automatically uses GPU if available at runtime.

### 3. Install Node.js Dependencies

**Prerequisites**: Ensure Node.js and npm are installed on your system. Download from [nodejs.org](https://nodejs.org/).

Install all Node.js dependencies (root, backend, and frontend) with a single command:

```bash
npm run install-all
```

This will:
- Install root dependencies (concurrently, axios)
- Install backend dependencies (Express, MongoDB, etc.)
- Install frontend dependencies (React 19, Vite, TypeScript, Tailwind CSS, React Router)

**Alternative**: Install only specific parts:
```bash
npm install                    # Root only
npm run install-backend        # Backend only
npm run install-frontend       # Frontend only
```

Configure backend environment variables in `backend/old.env` if needed.

### 4. Configure API Keys

The project uses multiple API keys for different services. You'll need to configure them in the appropriate environment files:

#### Python Services (`.env` in root directory)

Edit `.env` in the root directory and add your API keys:

```env
# OpenAI API (used by RAG-Langchain)
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic API (optional, for Claude models in RAG)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Nanobanana API (used by picture-generation-verbose-api-module)
NANOBANANA_API_KEY=your_nanobanana_api_key_here

# ElevenLabs API (optional, for text-to-speech)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

Required API keys:
- **OPENAI_API_KEY**: For RAG analysis using OpenAI's Vision API
- **NANOBANANA_API_KEY**: For image transformation/editing
- **ELEVENLABS_API_KEY**: For text-to-speech features (optional)

#### MongoDB Configuration (Backend)

If using the Node.js backend server, configure MongoDB settings in the same root `.env` file:

```env
# MongoDB Configuration
MONGODB_USERNAME=your_mongodb_username
MONGODB_PASSWORD=your_mongodb_password
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database_name
DATABASE_NAME=spatial_design_studio

# Backend Server Configuration
PORT=8000
BACKEND_HOST=0.0.0.0
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
JWT_SECRET=your_super_secret_key_that_is_long_and_random
```

## Updates

To update the code in the submodules recursively:

```bash
git submodule update --recursive
```

## Usage

### Running the Web Application (Frontend + Backend)

**Run both frontend and backend together** (recommended):

```bash
npm run dev
```

This will start:
- **Frontend** at `http://localhost:5173` (React/Vite dev server)
- **Backend** at `http://localhost:3000` (Express server)

**Run separately**:
```bash
npm run frontend    # Frontend only
npm run backend     # Backend only
```

**Build frontend for production**:
```bash
cd Spatial-Design-Studio-Frontend/frontend
npm run build
cd ../..
```

### Running Python Services

The project includes Python-based microservices. Activate the Python virtual environment first:

**Windows**:
```bash
venv\Scripts\activate
```

**Unix/Mac**:
```bash
source venv/bin/activate
```

#### Service Control

**Start all Python services**:
```bash
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

**Restart services**:
```bash
python -m coordinator.main restart
```

### Image Analysis Workflow (Python Services)

Analyze and transform an image using the Python microservices:

```bash
# Windows
venv\Scripts\python analyze_and_transform_image.py room.jpg

# Unix/Mac
source venv/bin/activate
python analyze_and_transform_image.py room.jpg
```

**Options**:
```bash
# Specify output directory
python analyze_and_transform_image.py room.jpg --output-dir results/

# Keep services running after completion
python analyze_and_transform_image.py room.jpg --keep-services
```

**What happens**:
1. Starts microservices (RAG on port 8001, Picture-Generation on port 8002)
2. Analyzes image for dementia safety issues → Returns JSON recommendations
3. Transforms image based on recommendations → Returns edited image
4. Saves results to `output/` directory:
   - `{image}_analysis_{timestamp}.txt` - Text analysis
   - `{image}_analysis_{timestamp}.json` - JSON recommendations
   - `{image}_transformed_{timestamp}.jpg` - Transformed image
5. Stops services automatically

### API Endpoints

Python microservices:

Once services are running, you can call them directly:

**RAG Analysis (Port 8001)**:
```bash
curl -X POST http://127.0.0.1:8001/analyze \
  -F "file=@room.jpg"
```

**Picture Transformation (Port 8002)**:
```bash
curl -X POST http://127.0.0.1:8002/transform \
  -F "file=@room.jpg" \
  -F "analysis_json={\"issues\": [...]}"
```

## Troubleshooting

**Services won't start**:
- Verify virtual environments exist: `ls RAG-Langchain/.venv` and `ls picture-generation-verbose-api-module/myenv`
- Check API keys in `.env`
- Run setup script again

**GPU acceleration**:
To enable GPU support after setup:
```bash
cd picture-generation-verbose-api-module
source myenv/bin/activate  # or myenv\Scripts\activate on Windows
pip uninstall torch torchvision
pip install torch==2.6.0+cu124 torchvision==0.21.0+cu124 --extra-index-url https://download.pytorch.org/whl/cu124
```

**Port conflicts**:
- Change ports in `.env`:
  ```env
  RAG_SERVICE_PORT=8011
  IMAGE_GEN_SERVICE_PORT=8012
  ```

**Line ending issues on Unix/Mac** (setup.sh fails):
```bash
dos2unix setup.sh
# or
sed -i 's/\r$//' setup.sh
```

## Architecture Notes

- Each submodule runs in its own isolated virtual environment
- Services communicate via FastAPI REST APIs
- Coordinator manages service lifecycle and health checks
- All API keys stored in single `.env` file in root directory
- **Default CPU installation** for maximum compatibility across all systems
- Code automatically uses GPU if available at runtime (when CUDA version is manually installed)
- Interior segmentation model loads to appropriate device at runtime
