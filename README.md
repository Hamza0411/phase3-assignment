# Phase 3 Assignment - Academic Audit Engine & CI/CD Pipeline

A FastAPI-based academic audit backend with an automated GitHub Actions CI/CD quality gate and Render cloud deployment.

## Features
* **Audit Engine**: Validates prerequisites, cross-listing, and credit tallies via FastAPI endpoints (`main.py`)[cite: 1].
* **CI/CD Pipeline**: Automated workflow using GitHub Actions (`.github/workflows/ci.yml`) to run dependency installations, linters, and tests[cite: 1, 8].
* **Cloud Hosting**: Deployed live on Render.

## Tech Stack
* Python, FastAPI, Uvicorn
* Pytest, Flake8
* GitHub Actions, Render
