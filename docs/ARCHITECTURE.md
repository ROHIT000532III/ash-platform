# ASH AI Enterprise Architecture

## Overview

ASH AI Enterprise is a modern AI desktop platform built with a modular architecture.

## High-Level Architecture

User
↓
Desktop Application (Electron + React)
↓
Backend API (FastAPI)
↓
AI Runtime
↓
Model Providers
↓
Memory Engine

## Core Modules

- Desktop UI
- Backend API
- AI Runtime
- Model Manager
- Memory Manager
- Plugin System
- Settings
- File Manager

## Technology

Frontend:
- Electron
- React
- TypeScript
- Vite

Backend:
- Python
- FastAPI
- Ollama

Database:
- SQLite (initial)