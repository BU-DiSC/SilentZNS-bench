# SilentZNS-bench

# Raw-Bench Experiment Runner

This repository contains a Bash script that launches a FEMU-based ZNS SSD VM, copies the `raw-bench` experiment code into the VM, builds the required tools, runs the selected experiment, copies the results back to the host, and then shuts down the VM. The workflow is designed to make raw-device experiments reproducible across different SSD configurations and experiment types. :contentReference[oaicite:1]{index=1}

---

## Overview

The experiment runner `run.sh` performs the following steps:

1. Selects an SSD configuration using `SSD_ID`.
2. Selects an experiment type using `EXP_ID`.
3. Starts a FEMU VM with the corresponding SSD geometry and timing parameters.
4. Waits for SSH access to the VM.
5. Copies the `raw-bench` directory into the VM.
6. Compiles experiment binaries inside the VM if needed.
7. Runs `run_all.sh` inside the VM with the selected parameters.
8. Copies the generated result files back to the host.
9. Shuts down the VM.

## Repository Layout

The script assumes a directory layout similar to the following: