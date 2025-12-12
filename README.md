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
└── analyze_and_transform_image.py # Image Transform testing script
```

## Setup

### Note: Please Install Python 3.12 before running the setup process 

https://www.python.org/downloads/release/python-3120/

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

### 3. Configure API Keys

The project uses multiple API keys for different services. You'll need to configure them in the appropriate environment files:

#### Python Services (`.env` in root directory)

Edit `.env` in the root directory and add your API keys:

```env
# OpenAI API (used by RAG-Langchain)
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic API (optional, for Claude models in RAG)
VITE_OPENROUTER_API_KEY=your_vite_api_key_here

# Nanobanana API (used by picture-generation-verbose-api-module)
NANOBANANA_API_KEY=your_nanobanana_api_key_here

# ElevenLabs API (optional, for text-to-speech)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

Required API keys:
- **OPENAI_API_KEY**: For RAG analysis using OpenAI's Vision API
- **NANOBANANA_API_KEY**: For image transformation/editing
- **ELEVENLABS_API_KEY**: For text-to-speech features
- **VITE_OPENROUTER_API_KEY**: For Memory Bot Features 

#### MongoDB Setup & Configuration (Backend)

To Setup MongoDB: 
1. Create Account at https://www.mongodb.com/cloud/atlas/register

2. Create a cluster. 
   - Choose Shared Free Tier. 
   - Choose a region (e.g., Singapore AWS ap-southeast-1). 
   - Name your cluster (e.g., Dementia-Cluster)

3. Creating a Database User.
   - Go to Database Access -> Add New Database User
   - Choose a username and password
   - Set Role -> Read and write to any database
   - Save the user

4. Configure network access.
   - In Network Access, click on Add IP Address
   - Select option of: Allow Access From Anywhere (0.0.0.0/0) -> This is solely for development
   - Change it once going to production.

5. Get connection string to put into .env
   - Database -> Connect -> Drivers
   - Select Node.js
   - Copy generated URL, which should look like the follow:
   mongodb+srv://<username>:<password>@<cluster-id>.mongodb.net/<database>
   (Replace placeholders with actual credentials)

6. Create Environment Variables (As seen below.)

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
JWT_SECRET=jwt_secret_key
```

## Ngrok Tunneling Setup (Optional)

For remote access to your local development environment (e.g., testing on mobile devices over the internet), you can use ngrok to create a secure tunnel.

### Prerequisites

1. Install ngrok from [ngrok.com](https://ngrok.com/download)
2. Sign up for a free ngrok account and get your auth token

### Setup Steps

1. **Authenticate ngrok** (one-time setup):
   ```bash
   ngrok authtoken YOUR_AUTH_TOKEN
   ```

2. **Start ngrok tunnel** to expose your frontend:
   ```bash
   ngrok http 5173
   ```

   This will provide a public URL like: `https://abc123.ngrok-free.app`

3. **Access your application**:
   - The ngrok URL will tunnel to your local Vite dev server (port 5173)
   - Share the ngrok URL to access from any device
   - The Vite config is already set up to allow ngrok hosts (see `vite.config.ts`)

### Notes

- The frontend Vite configuration already includes ngrok in `allowedHosts`
- Free ngrok accounts have session limits and may show a warning page
- Those limits may cause the image generation service to stall or lag 
- For production deployments, consider using a proper hosting service

## Updates

To update the code in the submodules recursively (only if code is updated):

1. Change code source in source control to main/master

2. Run this command
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
- **Frontend** Frontend Server
- **Backend**  Backend Server

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

**Exclude Specific Services**
```bash
python -m coordinator.main start --exclude {Service name} # verbose, product_search, rag, detection, image_gen
```

## Known issues with services that could not be resolved

Due to external circumstances, there are some issues that could not be resolved during the prototyping process

### WebSocket issues in Memory Bot interface

Sometimes, when running the application and entering the Memory Bot interface for the first time, a WebSocket connection error would occur, resulting in no voice-over playing.

**Solution** 

Exit the Memory Bot interface and enter the interface again. The WebSocket connection should be established and the voice-over should play again.

### DuckDuckGo search API issues

Sometimes, the DuckDuckGo Search API may experience issues with returning search responses, resulting in the Product Search feature not returning results consistently. At the time of development, the team is not sure of the cause of this issue, but a similar incident with searches timing out have been reported here: https://github.com/serpapi/public-roadmap/issues/2795 

**Solutions**

1. Disable the Product Search Service if it causes the loading screen to hang. The Service Coordinator allows for specific services to be disabled, without disrupting other services.

```bash
python -m coordinator.main start --exclude product_search
```

2. Explore other Search APIs, such as Google Search API and SerpAPI. The Microservices architecture allows for the Search Service Module to be updated without affecting the other functionalities of the application.

## Image Analysis Workflow (Python Services)

Analyze and transform an image using the Python microservices (used for testing image generation):

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
