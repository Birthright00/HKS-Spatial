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
import signal
import sys

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
                # Check if process has crashed
                if self.process.poll() is not None:
                    self.status = ServiceStatus.ERROR
                    logger.error(f"✗ {self.name} process exited unexpectedly (exit code: {self.process.returncode})")

                    # Print stderr for debugging
                    if self.process.stderr:
                        stderr_output = self.process.stderr.read()
                        if stderr_output:
                            logger.error(f"  Service error output: {stderr_output[:500]}")

                    self._cleanup_failed_process()
                    return False

                if self.check_health():
                    self.status = ServiceStatus.RUNNING
                    logger.info(f"✓ {self.name} service started successfully on {self.url}")
                    return True

                # Show progress every 10 seconds
                if (i + 1) % 10 == 0:
                    logger.info(f"  Still waiting for {self.name}... ({i + 1}s)")

                time.sleep(1)

            # Timeout reached
            self.status = ServiceStatus.ERROR
            logger.error(f"✗ {self.name} service failed to start within {max_retries} seconds")

            # Print stderr for debugging
            if self.process and self.process.stderr:
                stderr_output = self.process.stderr.read()
                if stderr_output:
                    logger.error(f"  Service error output: {stderr_output[:500]}")

            # Clean up the failed process
            self._cleanup_failed_process()
            return False

        except Exception as e:
            self.status = ServiceStatus.ERROR
            logger.error(f"✗ Failed to start {self.name}: {e}")
            self._cleanup_failed_process()
            return False

    def _cleanup_failed_process(self):
        """Clean up a failed process to prevent hanging"""
        if self.process is not None:
            try:
                if self.process.poll() is None:  # Process is still running
                    logger.info(f"  Cleaning up failed {self.name} process...")
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"  Force killing {self.name} process...")
                        self.process.kill()
                        self.process.wait()
                self.process = None
            except Exception as e:
                logger.error(f"  Error cleaning up {self.name} process: {e}")

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
        self._shutdown_requested = False
        self._initialize_services()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler():
            if not self._shutdown_requested:
                logger.info("\nShutdown signal received. Stopping services gracefully...")
                self._shutdown_requested = True
                self.stop_all()
                sys.exit(0)
            else:
                logger.warning("Force shutdown requested!")
                sys.exit(1)

        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

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

        # Picture Generation Service (uses myenv)
        # Uses asyncio subprocess internally to avoid threading deadlocks
        self.services["image_gen"] = SubmoduleService(
            name="Picture-Generation",
            path=ServiceConfig.IMAGE_GEN_PATH,
            script="image_server.py",
            host=ServiceConfig.IMAGE_GEN_SERVICE_HOST,
            port=ServiceConfig.IMAGE_GEN_SERVICE_PORT,
            venv_path=ServiceConfig.IMAGE_GEN_PATH / "myenv"
        )

        # Verbose Service - Speech-to-Text and Text-to-Speech (uses myenv)
        # Isolated from image processing to prevent event loop conflicts
        self.services["verbose"] = SubmoduleService(
            name="Verbose-Service",
            path=ServiceConfig.IMAGE_GEN_PATH,
            script="verbose_server.py",
            host=ServiceConfig.VERBOSE_SERVICE_HOST,
            port=ServiceConfig.VERBOSE_SERVICE_PORT,
            venv_path=ServiceConfig.IMAGE_GEN_PATH / "myenv"
        )

    def start_all(self, exclude: list[str] = None) -> bool:
        """
        Start all services, continuing even if some fail

        Args:
            exclude: List of service keys to exclude from startup (e.g., ['verbose'])

        Returns:
            True if at least one service started successfully
        """
        exclude = exclude or []
        logger.info("Starting all services...")
        if exclude:
            logger.info(f"  Excluding: {', '.join(exclude)}")

        failed_services = []
        successful_services = []
        skipped_services = []

        for key, service in self.services.items():
            if key in exclude:
                skipped_services.append(service.name)
                logger.info(f"⊘ Skipping {service.name} (excluded)")
                continue

            try:
                if service.start():
                    successful_services.append(service.name)
                else:
                    failed_services.append(service.name)
                    logger.warning(f"⚠ Skipping {service.name} - failed to start. Continuing with other services...")
            except KeyboardInterrupt:
                logger.info("\nStartup interrupted by user")
                self.stop_all()
                return False
            except Exception as e:
                logger.error(f"Unexpected error starting {service.name}: {e}")
                failed_services.append(service.name)

        # Summary
        logger.info("\n" + "="*60)
        if successful_services:
            logger.info(f"✓ Successfully started: {', '.join(successful_services)}")
        if failed_services:
            logger.warning(f"✗ Failed to start: {', '.join(failed_services)}")
            logger.info("  Continuing with available services...")
        if skipped_services:
            logger.info(f"⊘ Skipped: {', '.join(skipped_services)}")
        logger.info("="*60 + "\n")

        return len(successful_services) > 0

    def stop_all(self):
        """Stop all services, including failed ones"""
        logger.info("Stopping all services...")

        for service in self.services.values():
            try:
                # Stop services that are running or in error state
                if service.status != ServiceStatus.STOPPED:
                    service.stop()
            except Exception as e:
                logger.error(f"Error stopping {service.name}: {e}")
                # Force cleanup
                if service.process:
                    try:
                        service.process.kill()
                    except:
                        pass

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
