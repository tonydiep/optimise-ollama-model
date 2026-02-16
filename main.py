#!/usr/bin/env python3

import argparse
import sys
from ollama_controller import OllamaController
from ollama_monitor import OllamaMonitor
from context_searcher import ContextSearcher

def main():
    parser = argparse.ArgumentParser(description='Ollama Context Optimizer')
    parser.add_argument('--model', required=True, help='The name of the Ollama model to optimize')
    parser.add_argument('--min', type=int, required=True, help='Minimum context size to search from')
    parser.add_argument('--max', type=int, required=True, help='Maximum context size to search to')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.min <= 0 or args.max <= 0:
        print("Error: Minimum and maximum context sizes must be positive integers")
        sys.exit(1)
        
    if args.min > args.max:
        print("Error: Minimum context size cannot be greater than maximum context size")
        sys.exit(1)
    
    # Initialize components
    controller = OllamaController(args.model)
    monitor = OllamaMonitor()
    searcher = ContextSearcher(controller, monitor)
    
    try:
        print(f"Starting optimization for model: {args.model}")
        print(f"Searching context size range: {args.min} to {args.max}")
        
        # Find optimal size
        optimal_size = searcher.find_optimal_size(args.min, args.max)
        
        print(f"Optimal context size found: {optimal_size}")
        
        # Save the optimized model
        print("Saving optimized model...")
        if controller.save_model():
            print(f"Model saved successfully with context size {optimal_size}")
        else:
            print("Failed to save the model")
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        # Always close the controller
        controller.close()

if __name__ == "__main__":
    main()