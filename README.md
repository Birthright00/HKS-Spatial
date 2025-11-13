# HKS-Spatial

Image analysis and transformation system for dementia-friendly home design using RAG + Vision LLM and automated image editing.

## Directory Structure

```
HKS-Spatial/
├── .env                          # Environment variables (API keys)
├── .env.example                  # Template for .env
├── requirements.txt              # Coordinator dependencies
├── setup.bat                     # Windows setup script
├── setup.sh                      # Unix/Mac setup script
├── analyze_and_transform_image.py # Main workflow script
│
├── coordinator/                  # Service management
│   ├── config.py                 # Configuration
│   ├── service_manager.py        # Service lifecycle
│   └── main.py                   # CLI for manual control
│
├── RAG-Langchain/               # Image analysis service
│   ├── .venv/                   # Virtual environment
│   ├── requirements.txt         # Dependencies
│   ├── api_server.py            # FastAPI wrapper
│   └── dementia_pipeline.py     # Core analysis logic
│
└── picture-generation-verbose-api-module/  # Image transformation service
    ├── myenv/                   # Virtual environment
    ├── requirements.txt         # Dependencies
    ├── api_server.py            # FastAPI wrapper
    └── transform_image.py       # Core transformation logic
```

## Setup

### 1. Clone the repositary with submodules

```bash
git clone --recursive https://github.com/Birthright00/HKS-Spatial.git
```

### 1. Run Setup Script

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
- Install all dependencies (CPU version of PyTorch by default)
- Create `.env` file from template

**Note on GPU Support**: The setup installs CPU-only PyTorch by default for maximum compatibility. For GPU acceleration, manually install the CUDA version after setup:
```bash
cd picture-generation-verbose-api-module
source myenv/bin/activate  # or myenv\Scripts\activate on Windows
pip install torch==2.6.0+cu124 torchvision==0.21.0+cu124 --extra-index-url https://download.pytorch.org/whl/cu124
```
The code automatically uses GPU if available at runtime.

### 2. Configure API Keys

Edit `.env` and add your API keys:

```env
OPENAI_API_KEY=your_openai_key_here
NANOBANANA_API_KEY=your_nanobanana_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
```

## Usage

### Complete Workflow (Recommended)

Analyze and transform an image in one command:

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

### Manual Service Control (Advanced)

**Start services**:
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

### API Endpoints

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

**File encoding errors on Mac/Linux** (UnicodeDecodeError during pip install):
```bash
# Fix UTF-16 encoded requirements.txt files
cd RAG-Langchain
iconv -f UTF-16LE -t UTF-8 requirements.txt > requirements_utf8.txt
mv requirements_utf8.txt requirements.txt
cd ..

# Or reset from git if cloned from repository
git checkout RAG-Langchain/requirements.txt
```

## Architecture Notes

- Each submodule runs in its own isolated virtual environment
- Services communicate via FastAPI REST APIs
- Coordinator manages service lifecycle and health checks
- All API keys stored in single `.env` file in root directory
- **Default CPU installation** for maximum compatibility across all systems
- Code automatically uses GPU if available at runtime (when CUDA version is manually installed)
- Interior segmentation model loads to appropriate device at runtime
