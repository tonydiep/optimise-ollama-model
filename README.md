# Ollama Context Optimizer

A command-line tool to automatically find the largest context size (`num_ctx`) for an Ollama model that fits entirely on your GPU, and then saves the result as a new model.

## Overview

When running large language models, maximizing GPU utilization is key to performance. This tool automates the tedious process of finding the "sweet spot" for a model's context size. It uses a binary search algorithm to quickly determine the maximum `num_ctx` that can be allocated without offloading to the CPU, ensuring optimal inference speed.

## How It Works

The application intelligently manages two separate shell interactions with Ollama:

1.  **An Interactive Shell (`ollama run`)**: The tool sends commands to this shell to incrementally change the model's context size.
2.  **A Monitoring Shell (`ollama ps`)**: After each change, the tool runs `ollama ps` to check if the model is running on `100% GPU` or if it has been partially offloaded to the `CPU`.

Based on the feedback from the monitoring shell, the binary search algorithm narrows down the range until it finds the highest possible context size that keeps the model exclusively on the GPU. Finally, it uses the `/save` command to create a new, optimized version of your model with this setting baked in.

## Prerequisites

*   Python 3.8+
*   Ollama must be installed and the `ollama` daemon must be running.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd optimise-ollama-model
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    The core script may have dependencies. A `requirements.txt` file will be provided.
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the main script from the command line, specifying the model you want to optimize and a search range for the context size.

```bash
python main.py --model [model-name] --min [min-context-size] --max [max-context-size]
```

**Arguments:**

*   `--model`: (Required) The name of the Ollama model you want to optimize (e.g., `llama3:8b`).
*   `--min`: (Required) The starting lower bound for the context size search (e.g., `4096`).
*   `--max`: (Required) The starting upper bound for the context size search (e.g., `65536`).

**Example:**

To find the optimal context size for `qwen3-30b-abliterated-custom` between 4,000 and 80,000, you would run:

```bash
python main.py --model qwen3-30b-abliterated-custom --min 4000 --max 80000
```

The tool will print its progress as it searches and will notify you upon completion, indicating the name of the newly saved model (e.g., `qwen3-30b-abliterated-custom-optimized`).
