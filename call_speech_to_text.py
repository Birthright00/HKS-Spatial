"""
Speech-to-Text Client Script
==============================
Calls the /speech-to-text endpoint of the Picture Generation microservice.
Converts audio files to text transcripts.

Auto-starts and stops the Picture Generation and Verbose Service (includes speech-to-text endpoint).

Usage:
    python call_speech_to_text.py <path_to_audio_file> [--output-dir <directory>] [--keep-services]

Examples:
    python call_speech_to_text.py audio.mp3
    python call_speech_to_text.py audio.mp3 --output-dir transcripts/
    python call_speech_to_text.py audio.mp3 --keep-services
"""

import sys
import argparse
import requests
from pathlib import Path
from datetime import datetime

# Add coordinator to path
sys.path.insert(0, str(Path(__file__).parent / "coordinator"))

from coordinator.service_manager import ServiceManager


class SpeechToTextPipeline:
    """Coordinates speech-to-text conversion with automatic service management"""

    def __init__(self, audio_path: Path, output_dir: Path = None):
        self.audio_path = audio_path
        self.output_dir = output_dir or Path("./output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize service manager
        self.manager = ServiceManager()

        # Timestamp for this run
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.audio_stem = self.audio_path.stem

    def start_services(self):
        """Start Picture Generation and Verbose Service (which includes speech-to-text)"""
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

    def transcribe_audio(self) -> dict:
        """
        Transcribe audio file using the speech-to-text service.

        Returns:
            dict with transcript and file paths
        """
        print("\n" + "="*70)
        print("TRANSCRIBING AUDIO")
        print("="*70)

        image_gen_service = self.manager.get_service("image_gen")
        if not image_gen_service or not image_gen_service.check_health():
            raise RuntimeError("Picture Generation and Verbose Service is not available")

        print(f"\nAudio file: {self.audio_path}")
        print(f"Calling service at: {image_gen_service.url}/speech-to-text")

        try:
            with open(self.audio_path, "rb") as f:
                files = {"file": (self.audio_path.name, f, "audio/mpeg")}
                response = requests.post(
                    f"{image_gen_service.url}/speech-to-text",
                    files=files,
                    timeout=300
                )
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error calling service: {e}")

        result = response.json()

        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            raise RuntimeError(f"Transcription failed: {error_msg}")

        # Extract results
        transcript = result.get("transcript", "")

        print("\n" + "="*60)
        print("TRANSCRIPTION SUCCESSFUL")
        print("="*60)
        print(f"\nTranscript:\n{transcript}\n")

        # Save transcript locally
        local_txt = self.output_dir / f"{self.audio_stem}_transcript_{self.timestamp}.txt"
        local_json = self.output_dir / f"{self.audio_stem}_transcript_{self.timestamp}.json"

        with open(local_txt, "w", encoding="utf-8") as f:
            f.write(transcript)
        print(f"Transcript saved to: {local_txt}")

        # Save JSON
        import json
        json_data = {"transcript": transcript}
        with open(local_json, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"JSON saved to: {local_json}")

        print("="*60)

        return {
            "transcript": transcript,
            "text_file": str(local_txt),
            "json_file": str(local_json)
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

            # Transcribe audio
            result = self.transcribe_audio()

            print("\n" + "="*70)
            print("PIPELINE COMPLETE")
            print("="*70)
            print(f"Transcript: {result['text_file']}")
            print(f"JSON: {result['json_file']}")
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
        description="Transcribe audio file to text using the speech-to-text microservice"
    )
    parser.add_argument(
        "audio_file",
        help="Path to the audio file (MP3 format)"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to save transcript files (default: output/)"
    )
    parser.add_argument(
        "--keep-services",
        action="store_true",
        help="Keep services running after completion"
    )

    args = parser.parse_args()

    # Verify audio file exists
    audio_path = Path(args.audio_file)
    if not audio_path.exists():
        print(f"ERROR: Audio file not found: {args.audio_file}", file=sys.stderr)
        sys.exit(1)

    # Create and run pipeline
    try:
        pipeline = SpeechToTextPipeline(
            audio_path=audio_path,
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
