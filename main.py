#!/usr/bin/env python3

import argparse
import logging
import subprocess
import sys
import re
import time
from ollama_controller import OllamaController
from context_searcher import ContextSearcher

TIMEFORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_MIN_CONTEXT = 4096
DEFAULT_MAX_CONTEXT = 1000000
TIMEOUT_SHOW = 30

logger = logging.getLogger(__name__)


def get_model_context_length(model_name: str) -> int | None:
    """Get the maximum context length for a given model"""
    try:
        result = subprocess.run(
            ["ollama", "show", model_name],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SHOW,
        )
        if result.returncode == 0:
            match = re.search(r"context length\s+(\d+)", result.stdout, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None
    except Exception:
        return None


def main() -> None:
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

    logger.info(f"Initializing Ollama controller for model: {args.model}")
    controller = OllamaController(args.model)
    searcher = ContextSearcher(controller)

    try:
        logger.info(f"Starting optimization for model: {args.model}")
        logger.info(f"Searching context size range: {args.min} to {args.max}")

        optimal_size = searcher.find_optimal_size(args.min, args.max)
        logger.info(f"Optimal context size found: {optimal_size}")

        logger.info("Saving optimized model...")
        if controller.save_model(optimal_size):
            logger.info(f"Model saved successfully with context size {optimal_size}")
        else:
            logger.error("Failed to save the model")

    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Error occurred: {e}")
    finally:
        logger.info("Closing controller...")
        controller.close()
        logger.info("Controller closed.")


if __name__ == "__main__":
    main()
