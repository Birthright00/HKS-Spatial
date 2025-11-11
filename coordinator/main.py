"""
HKS-Spatial Main Coordinator
============================
Main entry point for managing and coordinating all microservices.
"""

import sys
import argparse
import logging
from pathlib import Path

from .service_manager import ServiceManager, call_rag_service, call_image_gen_service
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
        # Start all services
        success = manager.start_all()
        print("\n=== Services Status ===")
        for name, info in manager.get_status().items():
            status_emoji = "✓" if info["healthy"] else "✗"
            print(f"{status_emoji} {name}: {info['status']} ({info['url']})")

        if success:
            print("\n✓ All services started successfully!")
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
            print("\n✗ Some services failed to start")
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


def cmd_analyze(args, manager: ServiceManager):
    """Analyze an image using RAG service"""
    print("\n=== Analyzing Image ===\n")

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)

    print(f"Analyzing: {image_path}")
    print("Calling RAG service...")

    result = call_rag_service(str(image_path), manager)

    if result and result.get("success"):
        print("\n=== Analysis Results ===\n")
        print(result.get("analysis", "No analysis text returned"))

        if args.json and result.get("json_summary"):
            print("\n=== JSON Summary ===\n")
            import json
            print(json.dumps(result["json_summary"], indent=2))

        if args.output:
            output_path = Path(args.output)
            output_path.write_text(result.get("analysis", ""))
            print(f"\n✓ Results saved to: {output_path}")
    else:
        error = result.get("error") if result else "Service unavailable"
        print(f"\n✗ Analysis failed: {error}")
        sys.exit(1)


def cmd_edit(args, manager: ServiceManager):
    """Edit an image using image generation service"""
    print("\n=== Editing Image ===\n")

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)

    reference_path = None
    if args.reference:
        reference_path = Path(args.reference)
        if not reference_path.exists():
            print(f"Error: Reference image not found: {reference_path}")
            sys.exit(1)

    print(f"Editing: {image_path}")
    print(f"Prompt: {args.prompt}")
    if reference_path:
        print(f"Reference: {reference_path}")
    print("\nCalling image generation service...")

    edited_base64 = call_image_gen_service(
        str(image_path),
        args.prompt,
        manager,
        str(reference_path) if reference_path else None
    )

    if edited_base64:
        import base64
        from PIL import Image
        from io import BytesIO

        # Decode and save
        image_data = base64.b64decode(edited_base64)
        edited_image = Image.open(BytesIO(image_data))

        output_path = Path(args.output) if args.output else image_path.parent / f"{image_path.stem}_edited.png"
        edited_image.save(output_path)

        print(f"\n✓ Edited image saved to: {output_path}")
    else:
        print("\n✗ Image editing failed")
        sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="HKS-Spatial Microservices Coordinator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start all services
  python -m coordinator.main start

  # Start specific service
  python -m coordinator.main start --service rag

  # Check status
  python -m coordinator.main status

  # Analyze an image
  python -m coordinator.main analyze --image path/to/image.jpg

  # Edit an image
  python -m coordinator.main edit --image path/to/image.jpg --prompt "Replace floor with wood"
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start services")
    start_parser.add_argument("--service", help="Start specific service (rag, image_gen)")

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop services")
    stop_parser.add_argument("--service", help="Stop specific service")

    # Status command
    status_parser = subparsers.add_parser("status", help="Check service status")

    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart services")
    restart_parser.add_argument("--service", help="Restart specific service")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze image with RAG")
    analyze_parser.add_argument("--image", required=True, help="Path to image")
    analyze_parser.add_argument("--output", help="Output file for analysis")
    analyze_parser.add_argument("--json", action="store_true", help="Include JSON summary")

    # Edit command
    edit_parser = subparsers.add_parser("edit", help="Edit image")
    edit_parser.add_argument("--image", required=True, help="Path to image")
    edit_parser.add_argument("--prompt", required=True, help="Edit prompt")
    edit_parser.add_argument("--reference", help="Reference/mask image")
    edit_parser.add_argument("--output", help="Output file for edited image")

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
        "analyze": cmd_analyze,
        "edit": cmd_edit,
    }

    commands[args.command](args, manager)


if __name__ == "__main__":
    main()
