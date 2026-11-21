name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: tesistrack
        ports: ['5432:5432']
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s --health-timeout 5s --health-retries 10
    env:
      SECRET_KEY: ci-clave-solo-para-pruebas-0123456789-abcdefghijklmnopqrstuvwxyz-QWERTY
      DEBUG: 'False'
      ALLOWED_HOSTS: localhost,127.0.0.1,testserver
      DB_NAME: tesistrack
      DB_USER: postgres
      DB_PASSWORD: postgres
      DB_HOST: localhost
      DB_PORT: '5432'
      DB_SSLMODE: disable
      CRON_TOKEN: token-ci
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
      - run: pip install -r requirements.txt
      - run: python manage.py check
      - run: python manage.py check --deploy --fail-level WARNING
      - run: python manage.py makemigrations --check --dry-run
      - run: python manage.py test

  # Aplica las migraciones en Supabase. Vercel despliega solo (integración con GitHub).
  migrate:
    needs: test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    env:
      SECRET_KEY: ${{ secrets.SECRET_KEY }}
      DEBUG: 'False'
      DB_NAME: ${{ secrets.DB_NAME }}
      DB_USER: ${{ secrets.DB_USER }}
      DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
      DB_HOST: ${{ secrets.DB_HOST }}
      DB_PORT: ${{ secrets.DB_PORT }}
      DB_SSLMODE: require
      DB_DISABLE_SERVER_SIDE_CURSORS: 'True'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
      - run: pip install -r requirements.txt
      - run: python manage.py migrate --noinput