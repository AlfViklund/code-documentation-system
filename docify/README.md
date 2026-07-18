# docify 🚀

> Living feature documentation anchored to code, for humans and coding agents.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Dashboard-009688.svg)](https://fastapi.tiangolo.com)
[![FastMCP](https://img.shields.io/badge/MCP-Server-purple.svg)](https://modelcontextprotocol.io)

## 📌 Overview

`docify` turns feature documentation into a first-class repository entity:
- **Code Anchors**: Files and AST symbols (classes, functions, methods) linked to feature descriptions.
- **Staleness Checker**: Automatically flags documentation as `stale` when underlying symbol bodies or files change.
- **Symbol Renaming Detection**: Detects symbol renames and offers one-click remap auto-fixes (`docify check --fix-anchors`).
- **AI Coding Agent Integration (FastMCP)**: Connects seamlessly to Claude Desktop, Cursor, and Windsurf (`docify install --project`).
- **Cyberpunk Web Dashboard**: Interactive UI with feature map, live WebSocket updates, and staleness badges (`docify serve`).

---

## ⚡ Quick Start

```bash
# Install docify
pip install docify

# Initialize in project directory
docify init

# Add a feature & link code anchor
docify feature add core-auth --title "Authentication Engine"
docify link core-auth src/auth.ts::AuthService.login

# Check staleness against git changes
docify check --full

# Launch local Web Dashboard
docify serve --port 4321

# Configure MCP for AI Coding Agents
docify install --project
```

## 📄 License

MIT License
