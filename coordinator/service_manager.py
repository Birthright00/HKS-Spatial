"""
Microservice Manager for HKS-Spatial
====================================
Manages startup, health checks, and communication with submodule microservices.
"""

import subprocess
import time
import requests
from pathlib import Path
from typing import Dict, Optional
import logging
from enum import Enum

from .config import ServiceConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status enum"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    UNHEALTHY = "unhealthy"


class SubmoduleService:
    """Represents a single submodule microservice"""

    def __init__(
        self,
        name: str,
        path: Path,
        script: str,
        host: str,
        port: int,
        venv_path: Optional[Path] = None
    ):
        self.name = name
        self.path = path
        self.script = script
        self.host = host
        self.port = port
        self.venv_path = venv_path or (path / "venv")
        self.process: Optional[subprocess.Popen] = None
        self.status = ServiceStatus.STOPPED

    @property
    def url(self) -> str:
        """Get service URL"""
        return f"http://{self.host}:{self.port}"

    @property
    def health_url(self) -> str:
        """Get health check URL"""
        return f"{self.url}/health"

    def get_python_executable(self) -> Path:
        """Get path to Python executable in venv"""
        if self.venv_path.exists():
            # Windows
            python_exe = self.venv_path / "Scripts" / "python.exe"
            if python_exe.exists():
                return python_exe
            # Unix
            python_exe = self.venv_path / "bin" / "python"
            if python_exe.exists():
                return python_exe

        raise FileNotFoundError(
            f"Virtual environment not found at {self.venv_path}. "
            f"Please run setup script first."
        )

    def start(self) -> bool:
        """Start the service"""
        if self.status == ServiceStatus.RUNNING:
            logger.warning(f"{self.name} is already running")
            return True

        try:
            logger.info(f"Starting {self.name} service...")
            self.status = ServiceStatus.STARTING

            python_exe = self.get_python_executable()
            script_path = self.path / self.script

            if not script_path.exists():
                raise FileNotFoundError(f"Script not found: {script_path}")

            # Start the service process
            self.process = subprocess.Popen(
                [str(python_exe), str(script_path)],
                cwd=str(self.path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for service to be ready
            # Services now use lazy loading, so startup should be fast
            max_retries = 60  # 1 minute (generous for slow systems)
            for i in range(max_retries):
                if self.check_health():
                    self.status = ServiceStatus.RUNNING
                    logger.info(f"✓ {self.name} service started successfully on {self.url}")
                    return True

                # Show progress every 10 seconds
                if (i + 1) % 10 == 0:
                    logger.info(f"  Still waiting for {self.name}... ({i + 1}s)")

                time.sleep(1)

            self.status = ServiceStatus.ERROR
            logger.error(f"✗ {self.name} service failed to start within {max_retries} seconds")

            # Print stderr for debugging
            if self.process and self.process.stderr:
                stderr_output = self.process.stderr.read()
                if stderr_output:
                    logger.error(f"  Service error output: {stderr_output[:500]}")

            return False

        except Exception as e:
            self.status = ServiceStatus.ERROR
            logger.error(f"✗ Failed to start {self.name}: {e}")
            return False

    def stop(self) -> bool:
        """Stop the service"""
        if self.process is None:
            return True

        try:
            logger.info(f"Stopping {self.name} service...")
            self.process.terminate()
            self.process.wait(timeout=10)
            self.status = ServiceStatus.STOPPED
            logger.info(f"✓ {self.name} service stopped")
            return True

        except subprocess.TimeoutExpired:
            logger.warning(f"Force killing {self.name} service...")
            self.process.kill()
            self.status = ServiceStatus.STOPPED
            return True

        except Exception as e:
            logger.error(f"✗ Failed to stop {self.name}: {e}")
            return False

    def check_health(self) -> bool:
        """Check if service is healthy"""
        try:
            response = requests.get(self.health_url, timeout=2)
            is_healthy = response.status_code == 200

            if is_healthy:
                self.status = ServiceStatus.RUNNING
            else:
                self.status = ServiceStatus.UNHEALTHY

            return is_healthy

        except requests.exceptions.RequestException:
            if self.status == ServiceStatus.RUNNING:
                self.status = ServiceStatus.UNHEALTHY
            return False

    def restart(self) -> bool:
        """Restart the service"""
        logger.info(f"Restarting {self.name} service...")
        self.stop()
        time.sleep(2)
        return self.start()


class ServiceManager:
    """Manages all microservices"""

    def __init__(self):
        self.services: Dict[str, SubmoduleService] = {}
        self._initialize_services()

    def _initialize_services(self):
        """Initialize service configurations"""

        # RAG-Langchain service (uses .venv)
        self.services["rag"] = SubmoduleService(
            name="RAG-Langchain",
            path=ServiceConfig.RAG_LANGCHAIN_PATH,
            script="api_server.py",
            host=ServiceConfig.RAG_SERVICE_HOST,
            port=ServiceConfig.RAG_SERVICE_PORT,
            venv_path=ServiceConfig.RAG_LANGCHAIN_PATH / ".venv"
        )

        # Note: Picture generation runs as direct subprocess (not a service)
        # The transform_image.py script is called directly by analyze_and_transform_image.py
        # No api_server.py needed for picture-generation

    def start_all(self) -> bool:
        """Start all services"""
        logger.info("Starting all services...")

        success = True
        for service in self.services.values():
            if not service.start():
                success = False

        return success

    def stop_all(self):
        """Stop all services"""
        logger.info("Stopping all services...")

        for service in self.services.values():
            service.stop()

    def restart_all(self) -> bool:
        """Restart all services"""
        logger.info("Restarting all services...")
        self.stop_all()
        time.sleep(2)
        return self.start_all()

    def get_service(self, name: str) -> Optional[SubmoduleService]:
        """Get a service by name"""
        return self.services.get(name)

    def health_check_all(self) -> Dict[str, bool]:
        """Check health of all services"""
        return {
            name: service.check_health()
            for name, service in self.services.items()
        }

    def get_status(self) -> Dict[str, Dict]:
        """Get status of all services"""
        return {
            name: {
                "status": service.status.value,
                "url": service.url,
                "healthy": service.check_health()
            }
            for name, service in self.services.items()
        }


# Note: Convenience functions removed
# - call_rag_service: Now called directly in analyze_and_transform_image.py
# - call_image_gen_service: No longer needed - transform_image.py is called as subprocess
