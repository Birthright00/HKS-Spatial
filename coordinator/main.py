"""
HKS-Spatial Main Coordinator
============================
Main entry point for managing and coordinating all microservices.
"""

import sys
import argparse
import logging
from pathlib import Path

from .service_manager import ServiceManager
from .config import ServiceConfig

logger = logging.getLogger(__name__)


def cmd_start(args, manager: ServiceManager):
    """Start all services"""
    print("\n=== Starting HKS-Spatial Services ===\n")

    if args.service:
        # Start specific service
        service = manager.get_service(args.service)
        if service:
            success = service.start()
            sys.exit(0 if success else 1)
        else:
            print(f"Error: Unknown service '{args.service}'")
            print(f"Available services: {', '.join(manager.services.keys())}")
            sys.exit(1)
    else:
        # Start all services (excluding any specified)
        exclude = args.exclude.split(',') if args.exclude else []
        success = manager.start_all(exclude=exclude)
        print("\n=== Services Status ===")
        for name, info in manager.get_status().items():
            status_emoji = "✓" if info["healthy"] else "✗"
            print(f"{status_emoji} {name}: {info['status']} ({info['url']})")

        if success:
            print("\n✓ Services started!")
            print("\nServices are running. Press Ctrl+C to stop.\n")
            try:
                # Keep running
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\nShutting down...")
                manager.stop_all()
        else:
            print("\n✗ No services could be started")
            sys.exit(1)


def cmd_stop(args, manager: ServiceManager):
    """Stop all services"""
    print("\n=== Stopping HKS-Spatial Services ===\n")

    if args.service:
        service = manager.get_service(args.service)
        if service:
            service.stop()
        else:
            print(f"Error: Unknown service '{args.service}'")
            sys.exit(1)
    else:
        manager.stop_all()

    print("✓ Services stopped")


def cmd_status(args, manager: ServiceManager):
    """Check status of all services"""
    print("\n=== HKS-Spatial Services Status ===\n")

    status = manager.get_status()

    for name, info in status.items():
        status_emoji = "✓" if info["healthy"] else "✗"
        print(f"{status_emoji} {name}:")
        print(f"   Status: {info['status']}")
        print(f"   URL: {info['url']}")
        print(f"   Health: {'Healthy' if info['healthy'] else 'Unhealthy'}")
        print()


def cmd_restart(args, manager: ServiceManager):
    """Restart services"""
    print("\n=== Restarting HKS-Spatial Services ===\n")

    if args.service:
        service = manager.get_service(args.service)
        if service:
            success = service.restart()
            sys.exit(0 if success else 1)
        else:
            print(f"Error: Unknown service '{args.service}'")
            sys.exit(1)
    else:
        success = manager.restart_all()
        sys.exit(0 if success else 1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="HKS-Spatial Microservices Coordinator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start all services
  python -m coordinator.main start

  # Start all services except verbose (to save credits during testing)
  e.g: python -m coordinator.main start --exclude verbose

  # Start specific service
  python -m coordinator.main start --service rag

  # Check status
  python -m coordinator.main status

  # Stop services
  python -m coordinator.main stop

Note: For image analysis and transformation, use analyze_and_transform_image.py
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start services")
    start_parser.add_argument("--service", help="Start specific service (rag, image_gen, verbose)")
    start_parser.add_argument("--exclude", help="Exclude services (comma-separated, e.g., 'verbose' or 'verbose,image_gen')")

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop services")
    stop_parser.add_argument("--service", help="Stop specific service")

    # Status command
    subparsers.add_parser("status", help="Check service status")

    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart services")
    restart_parser.add_argument("--service", help="Restart specific service")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Validate configuration
    try:
        ServiceConfig.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nPlease create a .env file with required API keys.")
        print("See .env.example for template.")
        sys.exit(1)

    # Initialize service manager
    manager = ServiceManager()

    # Execute command
    commands = {
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "restart": cmd_restart,
    }

    commands[args.command](args, manager)


if __name__ == "__main__":
    main()
