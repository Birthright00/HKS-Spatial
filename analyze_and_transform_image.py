#!/usr/bin/env python3
"""
Analyze and Transform Image - Main Coordinator Script
======================================================

This script coordinates the complete workflow:
1. Start microservices (RAG-Langchain and Picture-Generation)
2. Analyze image with RAG service → Get JSON analysis
3. Transform image with Picture-Generation service → Get edited image
4. Save results and stop services

Usage:
    python analyze_and_transform_image.py <image_path> [--output-dir <dir>] [--keep-services]

Examples:
    # Basic usage - analyze and transform
    python analyze_and_transform_image.py room.jpg

    # Specify output directory
    python analyze_and_transform_image.py room.jpg --output-dir results/

    # Keep services running after completion
    python analyze_and_transform_image.py room.jpg --keep-services
"""

import sys
import argparse
import json
import requests
from pathlib import Path
from datetime import datetime

# Add coordinator to path
sys.path.insert(0, str(Path(__file__).parent / "coordinator"))

from coordinator.service_manager import ServiceManager
from coordinator.config import ServiceConfig


class ImageAnalysisTransformPipeline:
    """Coordinates analysis and transformation of images"""

    def __init__(self, image_path: Path, output_dir: Path = None):
        self.image_path = image_path
        self.output_dir = output_dir or Path("./output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize service manager
        self.manager = ServiceManager()

        # Timestamp for this run
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.image_stem = self.image_path.stem

    def start_services(self):
        """Start RAG service only (picture generation runs directly)"""
        print("\n" + "="*70)
        print("STARTING RAG SERVICE")
        print("="*70)

        rag_service = self.manager.get_service("rag")
        if not rag_service:
            raise RuntimeError("RAG service not found")

        success = rag_service.start()

        if not success:
            raise RuntimeError("Failed to start RAG service")

        print("\n✓ RAG service started successfully")
        print("Note: Picture generation will run directly (not as a service)\n")

    def stop_services(self):
        """Stop RAG service"""
        print("\n" + "="*70)
        print("STOPPING RAG SERVICE")
        print("="*70)

        rag_service = self.manager.get_service("rag")
        if rag_service:
            rag_service.stop()
        print("✓ RAG service stopped\n")

    def analyze_image(self) -> dict:
        """
        Step 1: Analyze image with RAG service

        Returns:
            dict with analysis_text and analysis_json
        """
        print("\n" + "="*70)
        print("STEP 1: ANALYZING IMAGE")
        print("="*70)

        rag_service = self.manager.get_service("rag")
        if not rag_service or not rag_service.check_health():
            raise RuntimeError("RAG service is not available")

        print(f"\nImage: {self.image_path}")
        print(f"Calling RAG service at: {rag_service.url}")

        try:
            with open(self.image_path, "rb") as f:
                files = {"file": f}
                response = requests.post(
                    f"{rag_service.url}/analyze",
                    files=files,
                    timeout=120
                )

            if response.status_code != 200:
                raise RuntimeError(f"RAG service error: {response.text}")

            result = response.json()

            if not result.get("success"):
                raise RuntimeError(f"Analysis failed: {result.get('error')}")

            # Save analysis text
            analysis_text_file = self.output_dir / f"{self.image_stem}_analysis_{self.timestamp}.txt"
            with open(analysis_text_file, "w", encoding="utf-8") as f:
                f.write(result["analysis_text"])

            print(f"\n✓ Analysis complete")
            print(f"  Saved to: {analysis_text_file}")

            # Save JSON
            if result.get("analysis_json"):
                json_file = self.output_dir / f"{self.image_stem}_analysis_{self.timestamp}.json"
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(result["analysis_json"], f, indent=2)
                print(f"  JSON saved to: {json_file}")

            return result

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to call RAG service: {e}")

    def transform_image(self, analysis_json: dict) -> Path:
        """
        Step 2: Transform image with Picture Generation - Direct subprocess call

        Args:
            analysis_json: JSON analysis from step 1

        Returns:
            Path to transformed image
        """
        print("\n" + "="*70)
        print("STEP 2: TRANSFORMING IMAGE")
        print("="*70)

        # Save JSON to file for transform_image.py
        json_file = self.output_dir / f"{self.image_stem}_prompts_{self.timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(analysis_json, f, indent=2)

        print(f"\nJSON prompts saved: {json_file}")

        # Output path for transformed image
        output_image = self.output_dir / f"{self.image_stem}_transformed_{self.timestamp}.jpg"

        num_issues = len(analysis_json.get("issues", []))
        print(f"Number of issues to transform: {num_issues}")
        print(f"This may take a while - processing {num_issues} issues sequentially...")
        print("Each issue involves segmentation + image editing (~3-5 minutes per issue)")

        # Get Python executable from picture-generation venv
        pic_gen_path = ServiceConfig.IMAGE_GEN_PATH
        pic_gen_venv = pic_gen_path / "myenv"

        # Windows or Unix
        python_exe = pic_gen_venv / "Scripts" / "python.exe"
        if not python_exe.exists():
            python_exe = pic_gen_venv / "bin" / "python"

        if not python_exe.exists():
            raise RuntimeError(f"Picture generation venv not found at {pic_gen_venv}")

        # Call transform_image.py directly as subprocess
        transform_script = pic_gen_path / "transform_image.py"

        print(f"\nCalling: {python_exe} {transform_script}")
        print(f"  Input: {self.image_path}")
        print(f"  Prompts: {json_file}")
        print(f"  Output: {output_image}")

        try:
            import subprocess
            result = subprocess.run(
                [
                    str(python_exe),
                    str(transform_script),
                    str(self.image_path.resolve()),  # Use absolute path
                    str(json_file.resolve()),  # Use absolute path
                    str(output_image.resolve())  # Use absolute path
                ],
                cwd=str(pic_gen_path),  # Run in picture-generation directory
                capture_output=False,  # Don't capture - let output stream to console
                timeout=num_issues * 400  # 6-7 minutes per issue
            )

            if result.returncode != 0:
                raise RuntimeError(f"Transformation failed with return code {result.returncode}")

            if not output_image.exists():
                raise RuntimeError(f"Transformation did not create output file: {output_image}")

            print(f"\n✓ Transformation complete")
            print(f"  Saved to: {output_image}")

            return output_image

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Transformation timed out after {num_issues * 400} seconds")
        except Exception as e:
            raise RuntimeError(f"Failed to run transformation: {e}")

    def run(self, keep_services: bool = False):
        """
        Execute the complete pipeline

        Args:
            keep_services: If True, don't stop services after completion
        """
        try:
            # Validate image exists
            if not self.image_path.exists():
                raise FileNotFoundError(f"Image not found: {self.image_path}")

            print("\n" + "="*70)
            print("IMAGE ANALYSIS & TRANSFORMATION PIPELINE")
            print("="*70)
            print(f"Input: {self.image_path}")
            print(f"Output directory: {self.output_dir}")
            print("="*70)

            # Start services
            self.start_services()

            # Step 1: Analyze
            analysis_result = self.analyze_image()

            # Check if we have JSON for transformation
            if not analysis_result.get("analysis_json"):
                print("\n⚠ Warning: No JSON analysis found, skipping transformation")
                return

            # Step 2: Transform
            self.transform_image(analysis_result["analysis_json"])

            # Success
            print("\n" + "="*70)
            print("✓ PIPELINE COMPLETE")
            print("="*70)
            print(f"\nResults saved in: {self.output_dir}")
            print(f"  - Analysis text: {self.image_stem}_analysis_{self.timestamp}.txt")
            print(f"  - Analysis JSON: {self.image_stem}_analysis_{self.timestamp}.json")
            print(f"  - Transformed image: {self.image_stem}_transformed_{self.timestamp}.jpg")
            print()

        except KeyboardInterrupt:
            print("\n\n⚠ Pipeline interrupted by user")
            sys.exit(1)

        except Exception as e:
            print(f"\n✗ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        finally:
            if not keep_services:
                self.stop_services()
            else:
                print("\n⚠ Services are still running (--keep-services was specified)")
                print("To stop manually: Ctrl+C or use service manager")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Analyze and transform images for dementia-friendly design",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python analyze_and_transform_image.py room.jpg

  # Specify output directory
  python analyze_and_transform_image.py room.jpg --output-dir results/

  # Keep services running after completion
  python analyze_and_transform_image.py room.jpg --keep-services

Workflow:
  1. Start RAG-Langchain service (analyzes image)
  2. Start Picture-Generation service (transforms image)
  3. Analyze image → Get JSON recommendations
  4. Transform image → Apply recommendations
  5. Save results and stop services (unless --keep-services)
        """
    )

    parser.add_argument(
        "image",
        type=str,
        help="Path to the image to analyze and transform"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="./output",
        help="Output directory for results (default: ./output)"
    )

    parser.add_argument(
        "--keep-services",
        action="store_true",
        help="Keep services running after completion"
    )

    args = parser.parse_args()

    # Validate configuration
    try:
        ServiceConfig.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nPlease create a .env file with required API keys.")
        print("See .env.example for template.")
        sys.exit(1)

    # Run pipeline
    pipeline = ImageAnalysisTransformPipeline(
        image_path=Path(args.image),
        output_dir=Path(args.output_dir)
    )

    pipeline.run(keep_services=args.keep_services)


if __name__ == "__main__":
    main()
