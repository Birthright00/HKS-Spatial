"""
Text-to-Speech Client Script
==============================
Calls the /text-to-speech endpoint of the Picture Generation microservice.
Converts text to audio speech files.

Auto-starts and stops the Picture Generation and Verbose Service (includes text-to-speech endpoint).

Usage:
    python call_text_to_speech.py "<text>" [--output-dir <directory>] [--keep-services]
    python call_text_to_speech.py --file <path_to_text_file> [--output-dir <directory>] [--keep-services]

Examples:
    python call_text_to_speech.py "Hello, this is a test of text to speech"
    python call_text_to_speech.py --file response.txt --output-dir audio/
    python call_text_to_speech.py "Welcome home" --keep-services
"""

import sys
import argparse
import requests
from pathlib import Path
from datetime import datetime

# Add coordinator to path
sys.path.insert(0, str(Path(__file__).parent / "coordinator"))

from coordinator.service_manager import ServiceManager


class TextToSpeechPipeline:
    """Coordinates text-to-speech conversion with automatic service management"""

    def __init__(self, text: str, output_dir: Path = None):
        self.text = text
        self.output_dir = output_dir or Path("./output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize service manager
        self.manager = ServiceManager()

        # Timestamp for this run
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def start_services(self):
        """Start Picture Generation and Verbose Service (which includes text-to-speech)"""
        print("\n" + "="*70)
        print("STARTING Picture Generation and Verbose Service")
        print("="*70)

        # Get the image generation service and start it
        image_gen_service = self.manager.get_service("image_gen")
        if not image_gen_service:
            raise RuntimeError("Image generation service not found in ServiceManager")

        success = image_gen_service.start()

        if not success:
            raise RuntimeError("Failed to start Picture Generation and Verbose Service")

        print("\n✓ Service started successfully\n")

    def stop_services(self):
        """Stop all services"""
        print("\n" + "="*70)
        print("STOPPING SERVICES")
        print("="*70)

        self.manager.stop_all()
        print("✓ Services stopped\n")

    def convert_text_to_speech(self) -> dict:
        """
        Convert text to speech using the text-to-speech service.

        Returns:
            dict with audio file path
        """
        print("\n" + "="*70)
        print("CONVERTING TEXT TO SPEECH")
        print("="*70)

        image_gen_service = self.manager.get_service("image_gen")
        if not image_gen_service or not image_gen_service.check_health():
            raise RuntimeError("Picture Generation and Verbose Service is not available")

        print(f"\nText preview: {self.text[:100]}{'...' if len(self.text) > 100 else ''}")
        print(f"Calling service at: {image_gen_service.url}/text-to-speech")

        # Prepare request payload
        payload = {"text": self.text}

        try:
            response = requests.post(
                f"{image_gen_service.url}/text-to-speech",
                json=payload,
                timeout=300
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error calling service: {e}")

        result = response.json()

        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            raise RuntimeError(f"Text-to-speech conversion failed: {error_msg}")

        # Extract audio file path from service
        audio_file_path = result.get("audio_file_path")

        if not audio_file_path:
            raise RuntimeError("Service did not return audio file path")

        print("\n" + "="*60)
        print("TEXT-TO-SPEECH CONVERSION SUCCESSFUL")
        print("="*60)

        # Download the audio file
        audio_filename = Path(audio_file_path).name

        try:
            download_response = requests.get(
                f"{image_gen_service.url}/download-audio/{audio_filename}",
                timeout=60
            )
            download_response.raise_for_status()

            # Save audio locally
            local_audio = self.output_dir / f"speech_{self.timestamp}.mp3"

            with open(local_audio, "wb") as f:
                f.write(download_response.content)

            print(f"Audio saved to: {local_audio}")
            print("="*60)

            return {
                "success": True,
                "local_audio_path": str(local_audio),
                "remote_audio_path": audio_file_path
            }

        except requests.exceptions.RequestException as e:
            print(f"Warning: Could not download audio file: {e}")
            print(f"Audio available at service location: {audio_file_path}")
            print("="*60)

            return {
                "success": True,
                "remote_audio_path": audio_file_path
            }

    def run(self, keep_services: bool = False):
        """
        Execute the full pipeline.

        Args:
            keep_services: If True, keep services running after completion
        """
        try:
            # Start services
            self.start_services()

            # Convert text to speech
            result = self.convert_text_to_speech()

            print("\n" + "="*70)
            print("PIPELINE COMPLETE")
            print("="*70)
            if result.get("local_audio_path"):
                print(f"Audio file: {result['local_audio_path']}")
            else:
                print(f"Audio file (remote): {result.get('remote_audio_path')}")
            print("="*70 + "\n")

            return result

        finally:
            if not keep_services:
                self.stop_services()
            else:
                print("\n⚠ Services kept running (use --keep-services flag or stop manually)")
                print("To stop services: python -m coordinator.main stop\n")


def main():
    parser = argparse.ArgumentParser(
        description="Convert text to speech using the text-to-speech microservice"
    )

    # Text input options (mutually exclusive)
    text_group = parser.add_mutually_exclusive_group(required=True)
    text_group.add_argument(
        "text",
        nargs="?",
        help="Text to convert to speech (use quotes for multi-word text)"
    )
    text_group.add_argument(
        "--file",
        help="Path to text file to convert to speech"
    )

    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to save audio files (default: output/)"
    )
    parser.add_argument(
        "--keep-services",
        action="store_true",
        help="Keep services running after completion"
    )

    args = parser.parse_args()

    # Get text content
    if args.file:
        # Read from file
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"ERROR: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)

        with open(file_path, "r", encoding="utf-8") as f:
            text_content = f.read()
    else:
        # Use command line argument
        text_content = args.text

    if not text_content or not text_content.strip():
        print("ERROR: No text provided", file=sys.stderr)
        sys.exit(1)

    # Create and run pipeline
    try:
        pipeline = TextToSpeechPipeline(
            text=text_content,
            output_dir=Path(args.output_dir)
        )

        pipeline.run(keep_services=args.keep_services)
        sys.exit(0)

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
