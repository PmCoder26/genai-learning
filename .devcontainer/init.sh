#!/bin/bash

set -e

docker network inspect genai >/dev/null 2>&1 || \
    docker network create genai

docker volume inspect genai_postgres_data >/dev/null 2>&1 || \
    docker volume create genai_postgres_data

docker volume inspect genai_ollama_data >/dev/null 2>&1 || \
    docker volume create genai_ollama_data