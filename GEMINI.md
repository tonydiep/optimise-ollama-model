# GEMINI.md

## Directory Overview

This directory contains notes and sample interactions for optimizing the performance of an Ollama model by adjusting its context size. The goal is to find the optimal `num_ctx` value that maximizes GPU usage while minimizing CPU usage.

## Usage

The files in this directory serve as a reference guide for optimizing Ollama models. The process involves:

1.  Running an Ollama model.
2.  Using the `/set parameter num_ctx` command to adjust the context size.
3.  Monitoring the resource usage with `ollama ps` in a separate shell.
4.  Repeating steps 2 and 3 until the desired resource utilization is achieved (e.g., GPU at 100% and CPU at 0%).
5.  Saving the optimized model using the `/save` command.
