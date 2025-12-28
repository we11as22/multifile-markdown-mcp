#!/bin/bash
# Script for testing library mode with conda environment

set -e

echo "=== Setting up conda environment for library testing ==="

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "Error: conda is not installed or not in PATH"
    exit 1
fi

ENV_NAME="agent-memory-mcp-test"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Remove existing environment if it exists
if conda env list | grep -q "^${ENV_NAME} "; then
    echo "Removing existing conda environment: ${ENV_NAME}"
    conda env remove -n "${ENV_NAME}" -y
fi

# Create new conda environment with Python 3.11
echo "Creating conda environment: ${ENV_NAME} with Python 3.11"
conda create -n "${ENV_NAME}" python=3.11 -y

# Activate environment
echo "Activating conda environment"
eval "$(conda shell.bash hook)"
conda activate "${ENV_NAME}"

# Install project in editable mode with dev dependencies
echo "Installing project dependencies..."
cd "${PROJECT_DIR}"
pip install -e ".[dev]"

# Start PostgreSQL using docker-compose
echo "Starting PostgreSQL database..."
cd "${PROJECT_DIR}/docker"
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
timeout=60
counter=0
until docker-compose exec -T postgres pg_isready -U memory_user -d agent_memory > /dev/null 2>&1; do
    sleep 2
    counter=$((counter + 2))
    if [ $counter -ge $timeout ]; then
        echo "Error: PostgreSQL did not become ready within ${timeout} seconds"
        docker-compose logs postgres
        exit 1
    fi
done
echo "PostgreSQL is ready!"

# Set environment variables for tests
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=agent_memory
export POSTGRES_USER=memory_user
export POSTGRES_PASSWORD=change_me_in_production
export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

# Run tests
echo "Running library tests..."
cd "${PROJECT_DIR}"
pytest tests/test_library.py -v --tb=short

# Check test results
TEST_EXIT_CODE=$?

# Cleanup
echo "Cleaning up..."
docker-compose down

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "=== All tests passed! ==="
else
    echo "=== Some tests failed (exit code: $TEST_EXIT_CODE) ==="
fi

exit $TEST_EXIT_CODE

