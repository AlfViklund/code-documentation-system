# docify 🚀

> Живая документация фич проекта, привязанная к коду, для людей и кодинг-агентов.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Dashboard-009688.svg)](https://fastapi.tiangolo.com)
[![FastMCP](https://img.shields.io/badge/MCP-Server-purple.svg)](https://modelcontextprotocol.io)
[![Next.js](https://img.shields.io/badge/Next.js-Cyberpunk_UI-black.svg)](https://nextjs.org)

## 📌 О проекте

**docify** превращает документацию фич в первоклассную сущность репозитория:
- **Привязка к коду (Code Anchors)**: файлы и AST-символы (классы, методы, функции) связываются с описанием фичи.
- **Детектор устаревания (Staleness Checker)**: при изменении тела символа или файла фича автоматически помечается как `stale` (требует обновления).
- **Поддержка переименований (Symbol Renaming)**: изменение имени символа без изменения логики определяется автоматически с предложением авто-исправления (`docify check --fix-anchors`).
- **Интеграция с кодинг-агентами (MCP Server)**: интеграция с Claude, Cursor и другими агентами через протокол FastMCP (`docify install --project`).
- **Cyberpunk Web Dashboard**: локальный дашборд с картой фич, статусами старения и хот-релоадом изменений через WebSocket (`docify serve`).

---

## 🏗 Архитектура

Подробный дизайн-документ архитектуры доступен в [docs/docify-design.md](./docs/docify-design.md).

```
code-documentation-system/
├── docify/                    # Python пакет (CLI + MCP + FastAPI backend)
│   ├── src/docify/
│   │   ├── anchors/           # Извлечение AST-символов (Tree-sitter) & Git blob hashes
│   │   ├── checker/           # Проверка устаревания доков (Staleness engine)
│   │   ├── cli/               # CLI интерфейс на Typer
│   │   ├── core/              # Модели данных Pydantic & дисковое хранилище Store
│   │   ├── mcp/               # FastMCP сервер для AI-агентов
│   │   └── web/               # FastAPI REST & WebSocket сервер + встроенные статические файлы UI
├── app/                       # Next.js React Cyberpunk UI Dashboard
├── docs/
│   ├── docify-design.md       # Главный архитектурный документ проекта
│   ├── features/              # Документация фич в формате Markdown с YAML-метаданными
│   ├── specs/                 # Входящие спецификации (ТЗ)
│   └── backlog/               # Бэклог техдолга и задач
└── .docify/
    └── config.yaml            # Конфигурация проекта
```

---

## ⚡ Быстрый старт

### 1. Установка пакета

```bash
# Установка docify через uv или pip
uv pip install -e ./docify
```

### 2. Инициализация в вашем проекте

```bash
docify init
```
Команда создаст структуру `docs/features`, `docs/specs`, `docs/backlog` и `.docify/config.yaml`.

### 3. Создание фичи и привязка к коду

```bash
# Добавить фичу
docify feature add auth-login --title "Вход по логину" --status in-progress --priority p0

# Привязать AST-символ (класс/метод) или файл
docify link auth-login src/auth.ts::AuthService.login
```

### 4. Проверка старения документации

```bash
# Быстрый чек
docify check

# Полный анализ с выводом конкретных диффов изменений
docify check --full

# Автоматическое исправление переименованных символов
docify check --fix-anchors
```

### 5. Обновление статуса документации

После актуализации текста фичи сбросьте состояния устаревания и обновите проверенный коммит:
```bash
docify mark-updated auth-login
```

---

## 🖥 Веб-дашборд (Cyberpunk UI)

Запустите локальный дашборд:
```bash
docify serve --port 4321
```
Перейдите по адресу **http://localhost:4321** для просмотра карты фич, статусов старения, спецификаций и онлайн-консоли. Изменения на диске отображаются мгновенно благодаря встроенному WebSocket хот-релоаду.

---

## 🤖 Подключение MCP для AI-агентов (Claude Desktop / Cursor)

Чтобы подключить `docify` к вашему AI-агенту:

```bash
docify install --project
```
Команда автоматически:
1. Пропишет конфигурацию `docify mcp` в `claude_desktop_config.json`.
2. Добавит стандартный workflow взаимодействия с фичами в `CLAUDE.md`.

---

## 📄 Лицензия

MIT License
