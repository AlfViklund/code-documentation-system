---
id: ui-dashboard
title: Cyberpunk React Live Dashboard
status: implemented
priority: p2
tags:
- ui
- react
- nextjs
- cyberpunk
anchors:
- type: file
  path: app/page.tsx
  blob: a31e61b1c2ad0917784a9717ae200d244dcb820d
- type: file
  path: app/layout.tsx
  blob: a04fc6a6f2c304aa67a3f193ed711b5038aa9a01
updated_at: '2026-07-18'
verified_commit: f7bbc09f04df53261a13e2b955057316c0057bc7
---

## Что делает

Модуль `ui-dashboard` представляет собой интерактивный веб-интерфейс на базе Next.js, React и Tailwind CSS, выдержанный в неоновом киберпанк-стиле (hot pink, cyan glow, dark panels).

### Возможности дашборда

1. **Интерактивная карта фич**:
   - Фильтрация по статусам (`planned`, `in-progress`, `implemented`, `needs-update`) и тегам.
   - Визуальные индикаторы состояния старения (`fresh` - зеленый, `stale` - желтый, `broken` - красный пульсирующий, `empty-body` - оранжевый).

2. **Просмотр и редактирование**:
   - Чтение документации с нормальным рендерингом Markdown (заголовки, цитаты, кодовые блоки, списки).
   - Интерактивная привязка кодовых анкоров (файлы и AST-символы) прямо из UI.
   - Мгновенный сброс статуса устаревания по кнопке `MARK UPDATED`.

3. **Интеграция спецификаций и бэклога**:
   - Просмотр и загрузка ТЗ (Markdown с YAML-фронтматтером).
   - Мониторинг задач технического долга (`debt`) и перспективного развития (`growth`).

4. **Адаптивность и живое соединение**:
   - Автоматическое подключение к WebSocket с индикацией статуса сети (`Connected` / `Reconnecting`).
   - Поддержка просмотра с мобильных устройств и планшетов.
