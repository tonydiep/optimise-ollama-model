# GEMINI.md

## Directory Overview

This directory contains notes and sample interactions for optimizing the performance of an Ollama model by adjusting its context size. The goal is to find the optimal `num_ctx` value that maximizes GPU usage while minimizing CPU usage.

## Key Files

*   **`Sample Interaction with Bash Shell A.md`**: This file provides a step-by-step guide on how to interact with an Ollama model (`qwen3-30b-abliterated-custom` in this case) to fine-tune the `num_ctx` parameter. It also shows how to save the model with the optimized context size.

*   **`sample-interaction-with-bash-shell-b.md`**: This file shows an example output of the `ollama ps` command. This command is used to monitor the resource usage (CPU/GPU) of the running Ollama model, which is crucial for the optimization process.

## Usage

The files in this directory serve as a reference guide for optimizing Ollama models. The process involves:

1.  Running an Ollama model.
2.  Using the `/set parameter num_ctx` command to adjust the context size.
3.  Monitoring the resource usage with `ollama ps` in a separate shell.
4.  Repeating steps 2 and 3 until the desired resource utilization is achieved (e.g., GPU at 100% and CPU at 0%).
5.  Saving the optimized model using the `/save` command.
