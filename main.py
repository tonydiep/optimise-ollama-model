#!/usr/bin/env python3

import argparse
import subprocess
import sys
import re
import time
from ollama_controller import OllamaController
from context_searcher import ContextSearcher


def get_model_context_length(model_name):
    """Get the maximum context length for a given model"""
    try:
        result = subprocess.run(
            ["ollama", "show", model_name], capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            # Look for context length in the output
            match = re.search(r"context length\s+(\d+)", result.stdout, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None
    except Exception:
        return None


def timestamped_print(message):
    """Print message with timestamp"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def main():
    parser = argparse.ArgumentParser(description="Ollama Context Optimizer")
    parser.add_argument(
        "--model", required=True, help="The name of the Ollama model to optimize"
    )
    parser.add_argument(
        "--min",
        type=int,
        default=4096,
        help="Minimum context size to search from (default: 4096)",
    )
    parser.add_argument(
        "--max",
        type=int,
        help="Maximum context size to search to (default: model context length or 1000000)",
    )

    args = parser.parse_args()

    # Set default max context length based on model if not provided
    if args.max is None:
        model_max = get_model_context_length(args.model)
        if model_max:
            args.max = model_max
        else:
            args.max = 1000000  # Default fallback

    # Validate arguments
    if args.min <= 0 or args.max <= 0:
        print("Error: Minimum and maximum context sizes must be positive integers")
        sys.exit(1)

    if args.min > args.max:
        print("Error: Minimum context size cannot be greater than maximum context size")
        sys.exit(1)

    # Initialize components
    timestamped_print(f"Initializing Ollama controller for model: {args.model}")
    controller = OllamaController(args.model)
    searcher = ContextSearcher(controller)

    try:
        timestamped_print(f"Starting optimization for model: {args.model}")
        timestamped_print(f"Searching context size range: {args.min} to {args.max}")

        # Find optimal size
        timestamped_print("Starting binary search for optimal context size...")
        optimal_size = searcher.find_optimal_size(args.min, args.max)
        timestamped_print(f"Optimal context size found: {optimal_size}")

        # Save the optimized model
        timestamped_print("Saving optimized model...")
        if controller.save_model(optimal_size):
            timestamped_print(f"Model saved successfully with context size {optimal_size}")
        else:
            timestamped_print("Failed to save the model")

    except KeyboardInterrupt:
        timestamped_print("\nOperation cancelled by user")
    except Exception as e:
        timestamped_print(f"Error occurred: {e}")
    finally:
        # Always close the controller
        timestamped_print("Closing controller...")
        controller.close()
        timestamped_print("Controller closed.")


if __name__ == "__main__":
    main()
