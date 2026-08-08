# ТЗ — `telegram-managed-bot-factory`

## Статус

Единое ТЗ для реализации и публичной упаковки проекта. Заменяет прежние разрозненные материалы по технической концепции и UX.

> **Рынок и scope (исследование 2026-08-08; уточнено).** Hermes QR onboarding создаёт **одного** user-owned Telegram bot под Nous-hosted manager `@HermesSetupBot`, одноразово передаёт его token в локальный `hermes setup`, и существующий Hermes Gateway работает под этой identity. **Это не исходная Factory-идея:** в ней пользователь один раз создаёт и владеет собственным manager bot, включает ему Bot Management Mode, а его независимый worker создаёт/ведёт множество managed children, их isolated runtime и lifecycle. Таким образом, Nous manager → пользовательский Hermes bot — это первый слой; пользовательский manager → его bots — отдельный второй слой (функционально «внуки»), не duplicate native onboarding. Telegram официально разрешает выбрать existing bot как manager и включить ему Bot Management Mode; но до реализации обязателен короткий E2E spike: подтвердить, что bot, уже managed другим manager, может стать manager сам, и не допустить конкурирующий `getUpdates` между Hermes Gateway и Factory worker. Безопасный базовый дизайн — отдельный user-owned manager bot + отдельный persistent Factory worker, не переиспользование текущего Hermes gateway bot как manager.


## 1. Идея и пользовательская ценность

### Описание продукта

> **Создавайте новых Telegram-ботов из Hermes без рутины BotFather, копирования токенов и ручной настройки сервера.** Один manager bot становится личной фабрикой: вы описываете назначение ребёнка, подтверждаете создание одним нажатием в Telegram, а Factory сама получает token ребёнка, создаёт его изолированный runtime и запускает готовый базовый бот.

### Польза в одной фразе

**Один раз настраиваешь manager bot — затем создаёшь новых Telegram-ботов через Hermes одним запросом и одним Telegram confirmation.**

### Какую проблему решает

| Без Factory | С `telegram-managed-bot-factory` |
|---|---|
| Для каждого ребёнка вручную идти в BotFather и копировать token | Один раз настроить manager bot; далее пользователь лишь подтверждает создание child в Telegram |
| Передавать token нового бота в чат, IDE, env или агенту | Factory получает child token сама через официальный Telegram Managed Bots flow |
| Делать вручную каталог, `.env`, сервис и health-check | Factory materialize отдельные instance, secret и runtime по безопасному шаблону |
| Неясно, что уже создано и почему не запустилось | Hermes показывает понятный lifecycle и следующий безопасный шаг |
| Риск смешать токены и данные разных детей | У каждого child — отдельные credentials, state и ограниченный runtime |

### Честная граница

Factory не создаёт bot accounts без разрешения владельца. Telegram требует подтвердить каждого нового managed bot. Это один осмысленный tap, который защищает от несанкционированного массового создания. **После него** получение child token, изоляция и запуск автоматизированы.

## 2. Что позволяет Telegram

Telegram поддерживает официальный механизм **Managed Bots**:

1. Владелец один раз создаёт manager bot в BotFather либо выбирает существующий.
2. В BotFather включается **Bot Management Mode**.
3. У manager bot появляется `can_manage_bots: true`.
4. Factory формирует managed-bot creation link:
   ```text
   https://t.me/newbot/<manager_bot_username>/<suggested_child_username>?name=<display_name>
   ```
5. Владелец открывает ссылку и подтверждает создание в Telegram.
6. Telegram отправляет manager bot update `managed_bot`.
7. Manager вызывает `getManagedBotToken` и получает отдельный token созданного child bot.
8. Factory создаёт isolated instance, сохраняет child token только в secret store и запускает выбранный child profile.

**Следствие:** один token manager bot запускает всю фабрику. У детей по-прежнему отдельные токены, но владелец не переносит их вручную: Factory получает их только после подтверждённого Telegram update.

## 3. Scope продукта

### Публичный пакет

- **PyPI package:** `telegram-managed-bot-factory` — доступность имени проверить до релиза.
- **MCP server name:** `bot-factory`.
- **Python:** 3.11+.
- **MCP transport:** stdio для локального Hermes.
- **Telegram API:** Managed Bots, Bot API 9.6+.
- **MCP SDK:** официальный `mcp` / FastMCP.
- **Telegram SDK:** `aiogram 3` либо небольшой typed adapter; выбрать после spike на актуальной поддержке Managed Bots.
- **Лицензия:** MIT.

Пакет является самостоятельным open-source артефактом. Он не импортирует private code, private deployment details, secret-manager identifiers или credentials. Архитектурные принципы ограничены публично объяснимыми практиками: owner-only access, instance isolation, secret boundaries и reconciliation вместо слепого повторения внешних действий.

### Publication-ready definition

Цель первого релиза — не «репозиторий с кодом», а три проверяемых публичных артефакта:

1. **Public GitHub repository** — исходники, лицензия, README, tests, CI, security policy, release notes и demo evidence.
2. **PyPI project** — устанавливаемый wheel и source distribution `telegram-managed-bot-factory`.
3. **Official MCP Registry entry** — публичная discoverability-карточка, указывающая на конкретный PyPI package и stdio transport.

#### PyPI requirements

До публикации `0.1.0` repository обязан содержать:

- complete `pyproject.toml` с canonical package name, Semantic Version, `requires-python`, license, author, classifiers, dependencies и `[project.urls]` (`Homepage`, `Source`, `Issues`, `Changelog`, `Security`);
- `README.md`, корректно рендерящийся на PyPI: value proposition, что именно создаётся, ограничения Telegram confirmation, install, quickstart, threat model, supported OS/Python и troubleshooting;
- `LICENSE`, `SECURITY.md`, `CHANGELOG.md`, `CONTRIBUTING.md` и `CODE_OF_CONDUCT.md`;
- wheel и sdist, построенные из чистого checkout; `python -m build` и `twine check dist/*` проходят;
- deterministic runtime dependencies и console entry points `bot-factory`, `bot-factory-mcp`, `bot-factory-manager`;
- tests/lint/type check and secret scan green in CI;
- clean-venv installation and real MCP smoke test;
- README не содержит fake badges, invented download numbers, undisclosed telemetry или обещаний полной автоматизации обхода Telegram confirmation.

Release идёт через GitHub Actions **PyPI Trusted Publishing** (OIDC), а не долгоживущий PyPI API token в GitHub Secrets. Dedicated protected `pypi` environment требует manual approval. Publish job получает только built distributions from a separate build job and `id-token: write` at job scope.

Сначала публиковать на **TestPyPI** и выполнять clean-venv install; после подтверждённого live Telegram flow — tagged `v0.1.0` release на PyPI. Pending Trusted Publisher не резервирует package name, поэтому availability name проверяется непосредственно перед первым release.

#### Official MCP Registry requirements

В repository лежит versioned `server.json`:

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "io.github.<github-username>/bot-factory",
  "title": "Bot Factory for Telegram Managed Bots",
  "description": "Provision isolated Telegram Managed Bot instances from Hermes.",
  "version": "0.1.0",
  "packages": [{
    "registryType": "pypi",
    "identifier": "telegram-managed-bot-factory",
    "version": "0.1.0",
    "transport": {"type": "stdio"}
  }]
}
```

Точные schema/version и GitHub namespace подставляются при релизе. Для ownership verification README обязательно содержит:

```html
<!-- mcp-name: io.github.<github-username>/bot-factory -->
```

Server name, README marker, PyPI identifier и release versions должны совпадать. Official MCP Registry находится в preview: он публикует metadata, а не пакет, не является security certification и допускает breaking changes до GA. У registry metadata version immutable, поэтому validate `server.json` до publish и использовать SemVer.

#### Кто что проверяет

- **PyPI:** автоматически проверяет upload, required core metadata и distribution format. Это не ручная экспертиза качества продукта и не знак безопасности; ответственность за tests/security остаётся у maintainers.
- **GitHub Actions:** воспроизводимо запускает quality gates и формирует provenance/attestation релиза.
- **Official MCP Registry:** проверяет schema, authentication namespace и связь с опубликованным PyPI package через README `mcp-name` marker. Он не проверяет, что Factory безопасна или полезна.
- **Hermes curated catalog:** не часть v0.1 promise. Это отдельный PR в `optional-mcps/`, который проходит review Nous; подавать только после PyPI release, documentation и verified demo.

### One-line install: product requirement

Для пользователя Hermes основной happy-path начинается одной командой:

```bash
uvx --from telegram-managed-bot-factory bot-factory install-hermes
```

Команда должна работать без `sudo` и без ручного редактирования YAML. Она:

1. Проверяет Python/`uv`, версию Hermes и доступную user-level install location.
2. Устанавливает или обновляет package в изолированном user environment.
3. Регистрирует безопасный stdio MCP command в Hermes с allowlist только `factory_preflight`, `factory_create_request`, `factory_get_request`, `factory_list_instances`, `factory_start_instance`, `factory_stop_instance`; prompts/resources disabled by default.
4. Создаёт non-secret Factory home/state directories с корректными permissions.
5. Открывает setup wizard. Он передаёт manager token только через local hidden `getpass` prompt — **не** через Hermes, MCP tool, command-line argument или config file.
6. Проверяет `getMe`/`can_manage_bots`, owner allowlist и запускает manager worker only after explicit local confirmation.
7. Выполняет `hermes mcp test bot-factory` and returns a human-readable success/failure result without tokens.

One-line install не означает zero-consent: после него пользователь всё равно самостоятельно включает Bot Management Mode в BotFather и один раз скрыто вводит manager token. Это единственные неизбежные security actions; остальное должно быть автоматическим.

Documented fallbacks: `pipx install telegram-managed-bot-factory` and a manual `hermes mcp add` path for restricted/offline environments. Но README, PyPI description и demo ведут пользователя прежде всего через one-line happy path.

### Две части системы

```text
Hermes + MCP control plane              Factory manager runtime
──────────────────────────              ───────────────────────
создать request                         принимает Telegram updates 24/7
показать понятный status                получает child token
показать inventory                      materialize isolated instance
start / stop instance                   запускает child runtime

              ↕ controlled non-secret state / local IPC

Telegram owner → confirms creation → managed_bot update → active child bot
```

MCP запускается Hermes лишь на время сессии, поэтому не может сам круглосуточно принимать Telegram updates. Для полноценной фабрики нужен отдельный persistent manager worker/service. Hermes — удобная и умная control plane; worker — надёжный event/runtime plane. LLM не участвует в получении и хранении token.

## 4. UX: первый запуск

### Основное правило работы с manager token

MCP-инструмент **никогда не принимает token строкой**. Token нельзя отправлять Hermes в чат, передавать в MCP argument, помещать в YAML, shell history или CLI argument `--token ...`.

Первичная передача секрета выполняется вне агентского диалога интерактивным локальным setup-wizard:

```text
bot-factory setup
```

### Мастер настройки — progressive disclosure

Пользователь видит только один необходимый шаг за раз.

#### Экран 1 — manager bot

```text
Добро пожаловать в Bot Factory

Чтобы создавать и управлять дочерними ботами, нужен один manager bot.

[Открыть BotFather]  [У меня уже есть manager bot]
```

Короткая подсказка: «Создайте нового bot или выберите существующего. Это единственный bot, чей token потребуется Factory».

#### Экран 2 — management mode

```text
Включите Bot Management Mode

1. Откройте настройки выбранного bot в BotFather.
2. Включите Bot Management Mode.
3. Вернитесь сюда.

[Открыть BotFather settings]  [Проверить]
```

Не показывать здесь filesystem, Bitwarden, deployment или child tokens.

#### Экран 3 — скрытый ввод token

```text
Подключить manager bot

Вставьте token в скрытое поле терминала.
Он не будет показан, записан в историю shell или передан Hermes.

Manager token: •••••••••••••••••
```

Технический контракт:

- ввод через `getpass`, без echo;
- token не принимается как CLI argument;
- wizard сразу проверяет его методом `getMe`;
- UI и logs отображают максимум маску `123456…cDeF`;
- после проверки token сразу записывается в `SecretStore`, а не остаётся в памяти дольше нужного.

#### Экран 4 — итог проверки

```text
✓ Token действителен
✓ Manager: @my_factory_bot
✓ Bot Management Mode включён
✓ Вы — разрешённый владелец
✓ Secret store защищён

[Запустить Factory]
```

Wizard создаёт private secret directory, state store и manager worker configuration. Он также подключает MCP к Hermes без ручного редактирования YAML. Если service installation невозможен в текущей системе, wizard даёт **одну** безопасную copy-paste команду без secrets и объясняет причину.

Итоговый статус в Hermes:

```text
Bot Factory ready · Manager @my_factory_bot · 0 active bots
```

## 5. UX: создание нового child bot

### Happy path

Пользователь пишет Hermes естественным языком:

> «Создай закрытого бота для напоминаний клиентам. Название Client Reminder».

Hermes задаёт лишь недостающий минимум. Если username можно вывести безопасно, он предлагает его, а не вынуждает пользователя придумывать инфраструктурные детали.

Затем показывается компактная карточка:

```text
Новый бот
• Client Reminder — @client_reminder_bot
• Режим: приватный, отвечает только вам
• Назначение: напоминания клиентам

[Создать в Telegram]
```

Кнопка открывает официальный Telegram confirmation flow с предзаполненными именем и username. Владелец может проверить/изменить их и подтверждает создание один раз.

Далее Factory автоматически получает child token, создаёт runtime и присылает в тот же Telegram-чат:

```text
✅ Client Reminder создан и запущен
@client_reminder_bot · private owner-only

[Открыть бота] [Проверить health]
```

Token ребёнка не отображается, не пересылается, не копируется в буфер и не просится у пользователя.

### Human-friendly lifecycle

| Внутреннее состояние | Текст для пользователя | Действие |
|---|---|---|
| `pending_confirmation` | «Откройте отправленную ссылку и подтвердите создание в Telegram» | Открыть ссылку |
| `managed_update_received` | «Telegram подтвердил нового бота; подготавливаю его» | Подождать |
| `active` | «✅ Бот создан и запущен» | Открыть / health |
| `failed` | «Не удалось подготовить runtime; token не показывался и не потерян» | Безопасная причина |
| `reconciliation_required` | «Telegram прислал несопоставленный результат. Повторно ничего не создавал» | Привязать / проигнорировать |
| management mode disabled | «У manager bot не включён Bot Management Mode» | Открыть BotFather |

Запрещено показывать stack trace, raw Telegram updates, tokens, secret-file paths, внутренние IP/hostname или технические IDs, не нужные пользователю.

## 6. Secret и runtime design

### Default для демо и локального запуска

```text
factory-secrets/                  mode 0700
├── manager-token                 mode 0600
└── children/
    ├── client_reminder_bot       mode 0600
    └── ...

factory-state/                    mode 0700
└── factory.sqlite                # non-secret lifecycle, offsets, idempotency

instances/                        # non-secret manifests / templates
└── <slug>/manifest.json

runtime/<slug>/                   mode 0700 per child
```

- Worker читает token manager bot из protected file descriptor при старте.
- MCP возвращает только `secret_configured: true` и `child_token_stored: true`.
- Manager token не наследуется child processes.
- Каждый child получает только свой token и минимум нужных переменных.
- `.gitignore` и CI secret scan запрещают попадание secrets в Git.
- Все пути выбираются конфигурацией worker; MCP не принимает path к token, secret directory или shell command.

### Production option

Поддержать `SecretStore` interface. В v0.1 работает local file backend. Bitwarden Secrets Manager — optional adapter после MVP; его добавление не изменяет happy path и не должно быть обязательным для демки.

### Token lifecycle

- Child token появляется только после официального подтверждённого `managed_bot` update.
- Manager получает его через `getManagedBotToken`, а не через модель или чат.
- Дубликат update не создаёт второго instance и не переписывает secret.
- Rotation, deletion и revoke — отдельные explicit actions с подтверждением.
- При неясном внешнем результате перейти в `reconciliation_required`; не повторять создание автоматически.

## 7. Factory manager runtime

Команда `bot-factory-manager run` запускает постоянный worker.

Он обязан:

- получить manager token только из `BOT_FACTORY_MANAGER_TOKEN_FILE` или `SecretStore`, не из CLI argument;
- на старте вызвать `getMe` и проверить manager username, `can_manage_bots`, owner allowlist и secret store; при failure завершиться без побочных действий;
- использовать long polling в MVP и durable offset;
- принимать factory actions только от configured owner Telegram IDs;
- создать pending request и deep link до external confirmation;
- сопоставлять managed update с pending request по ожидаемому username и owner;
- после совпавшего update получить child token и записать его через `SecretStore`;
- создать non-secret instance manifest, `0700` state dir и private child runtime;
- обеспечить state machine и idempotency;
- для unknown/mismatched/partial result не угадывать, а ставить `reconciliation_required`.

### State machine

```text
pending_confirmation
  → managed_update_received
  → token_received
  → instance_materialized
  → active

ошибка до active → failed
unknown / mismatch / partial external effect → reconciliation_required
active → stopped → retired
```

## 8. MCP tools для Hermes

По умолчанию expose только эти инструменты.

### `factory_preflight` — read-only

Возвращает manager username/ID, `can_manage_bots`, worker health, readiness SecretStore и счётчики pending/active/reconciliation. Не раскрывает tokens, paths или raw config.

### `factory_create_request`

Аргументы:

- `display_name` — 1–64 characters;
- `username` — 5–32 characters, заканчивается на `bot`;
- `profile` — MVP `owner_echo`;
- `owner_telegram_id` — только allowlist;
- optional non-secret `purpose`;
- `notify_owner` — optional, default `true`.

Действие:

1. Проверить preflight и collision username/slug.
2. Создать non-secret pending request.
3. Сформировать managed-bot confirmation link.
4. Вернуть request ID и отправить владельцу одну кнопку/ссылку, если `notify_owner=true`.
5. Не получать и не хранить token во время этого MCP call.

### `factory_get_request` — read-only

Возвращает lifecycle state, human-readable status и следующий шаг для конкретного request.

### `factory_list_instances` — read-only

Показывает non-secret inventory: slug, username, profile, creator, lifecycle, health, last verified update. Не показывает token или secret path.

### `factory_start_instance` и `factory_stop_instance`

Требуют `confirm=true`, owner allowlist и существующий slug. Не принимают произвольные paths/команды. Destructive/revoke/remove tools не включать в default MCP allowlist.

### MCP 2026-07-28: progressive-modern strategy

Проект обязан использовать применимые возможности MCP `2026-07-28`, но без фальшивого заявления, что каждый host уже умеет их. На 2026-08-08 локальный Hermes 0.18.0 содержит Python `mcp` 1.26.0; поэтому v0.1 обязан иметь legacy stdio fallback, а modern capabilities включаются только после capability negotiation и отдельной реальной проверки.

**Обязательная modern baseline:** официальный Python MCP SDK v2+ в package, dual-era transport tests, explicit request/task handles вместо session state, `server/discover`, strict JSON Schema 2020-12, structured output, Streamable HTTP modern-mode test, MRTR test, Tasks extension test, redacted OpenTelemetry trace propagation. Внешний продукт не считается готовым, если эти вещи только упомянуты в README и не выполнены проверяемо в tests/demo.

- `factory_create_request` **сразу** возвращает явно передаваемый `request_id`; вся кросс-вызовная state живёт в durable Factory store, а не в MCP session. Это соответствует stateless core 2026-07-28 и остаётся корректным при restart/reconciliation.
- `factory_get_request(request_id)` — обязательный portable fallback. Когда клиент реально объявляет `io.modelcontextprotocol/tasks`, создание дополнительно возвращает standard task handle, а worker обновляет его через `tasks/get`/`tasks/update`; при текущем Hermes работает та же state machine через `request_id`.
- Human approval остаётся в Telegram. MRTR (`input_required`) реализуется и тестируется modern client-ом как дополнительная UX-подсказка «подтвердите в Telegram», никогда не как замена Telegram confirmation; `requestState` AEAD/HMAC-protected, short-lived, bound to owner и single-use server-side.
- Все tools получают строгие JSON Schema 2020-12 input/output contracts и structured status (`request_id`, `state`, `next_action`, `retry_after_ms`), с `oneOf` для profile-specific args. External `$ref` запрещены; schemas bounded по depth/size.
- Remote Streamable HTTP modern-mode поддерживает `server/discover`, stateless requests, `Mcp-Method`/`Mcp-Name` header validation, deterministic tool order, private cache hints и OpenTelemetry trace context. Token, username, owner ID и raw error body не попадают в traces.
- `subscriptions/listen` и MCP Apps реализуются как optional capability demo только после проверки host support. Apps дают operator status card/profile picker в clients с sandboxed UI; Telegram/Hermes text flow всегда имеет полноценный text fallback.
- Не использовать для нового кода deprecated Roots, Sampling, Logging или HTTP+SSE; logs — stderr/structured OpenTelemetry with redaction.

## 9. Child profiles: MVP и понятные showcase cases

`owner_echo` остаётся обязательным engineering smoke-profile: owner-only `/start`, `/help`, `/health` и echo с instance identity; только child token, без shell, Hermes tools, Bitwarden, manager token, соседних instances или LLM keys.

Но README/demo не строятся вокруг echo. В v0.1 включить ещё **три коротких полезных built-in profiles**, которые запускаются без API key, shell, стороннего SaaS и ручного кода после одного Telegram confirmation:

| Profile | Что пользователь получает за минуту | Почему это понятно |
|---|---|---|
| `quick_faq` | Public menu chatbot: приветствие, 3–8 вопросов/ответов, кнопка «связаться» | Микро-бот для услуги, мероприятия, портфолио или канала без разработки |
| `lead_inbox` | Public bot спрашивает имя и сообщение, явно сообщает о сохранении заявки и пересылает summary только owner | «Собрать заявки» для фрилансера/малого бизнеса; видна бизнес-польза |
| `link_inbox` | Owner-only личный inbox: сохранить URL/заметку, `/list`, `/done` | Быстрый personal productivity bot, который начинает быть полезен сразу |

Общие ограничения:

- `quick_faq`: content только из instance-local validated config; no remote fetch/HTML injection.
- `lead_inbox`: до первого вопроса показывает короткое privacy notice; собирает минимум данных (имя optional + текст), не пересылает третьим лицам и имеет owner-only `/export`/`/purge` с явным подтверждением. SQLite/Pydantic records привязаны к instance и не попадают в MCP result/logs.
- `link_inbox`: доступен только owner allowlist; URL не fetch-ится автоматически и не исполняется; metadata хранится instance-local.
- Все profiles возвращают human-friendly `/health` с profile, version и safe status, но не token/config paths/IDs.
- Первый launch каждого profile — deterministic и local. **AI-chat bot не входит в v0.1:** ему нужны отдельные model credentials, cost controls, content policy и security review. Он не должен быть «одним checkbox» с наследованием manager/Hermes secrets.

`owner_chat` / Hermes-agent child — отдельный v0.2 после security review: отдельный low-privilege process, отдельная model credential, deny-by-default toolset, без наследования Telegram/Bitwarden secrets.

## 10. Demo-first acceptance flow

Демо должно занимать 60–90 секунд и показывать пользу, а не терминал.

1. Hermes показывает: **«Bot Factory ready · Manager @… · 0 active bots»**.
2. Пользователь: **«Сделай FAQ-бота для моих услуг: цены, примеры, связь»**.
3. Hermes показывает готовую card/profile preview `quick_faq` и CTA **«Создать в Telegram»**.
4. Пользователь подтверждает создание одним tap.
5. UI/status меняется: «Ожидаю Telegram confirmation… → Получаю доступ… → Создаю isolated runtime… → Запускаю…».
6. Приходит: **«✅ FAQ Bot готов»**, кнопка **«Открыть бота»**.
7. Пользователь открывает child и за один tap получает ответ на FAQ; `/health` возвращает safe status.
8. Hermes показывает inventory: `FAQ Bot · active · quick_faq · just now`.
9. README содержит ещё два 60–90-second сценария: `lead_inbox` («собери заявки») и `link_inbox` («сохраняй ссылки и заметки»).

На видео и скриншотах нельзя показывать token, secret path, Bitwarden ID, raw update, внутренний host/IP, shell command с token или настоящие user IDs.

### UX acceptance criteria

- Setup завершается без ручного редактирования Hermes config YAML.
- Новый child требует от владельца не более одного Telegram confirmation action.
- Пользователь не вставляет и не видит child token.
- Статус до `active` объясняется одной человеческой строкой.
- Happy-path demo укладывается в 90 секунд.
- При failure Factory не создаёт повторно child без reconciliation.

## 11. Security requirements

- Strict Pydantic schemas для MCP tools.
- Secrets никогда не входят в prompts, MCP results, logs, manifests, SQLite state, CI output или Git.
- Logging идёт в stderr без raw update body и credentials.
- `getpass` flow не пишет token в shell history.
- slug: `[a-z][a-z0-9_]{2,63}`; path traversal и symlink escape запрещены.
- Existing slug не перезаписывается.
- Child token доступен только соответствующему instance process.
- Manager и child workers работают с разными least-privilege identities там, где позволяет deployment.
- Unknown external outcome требует reconciliation, не blind retry.

## 12. Тесты и готовность v0.1

### Unit tests

- management mode disabled/enabled preflight;
- validation owner, name, username, slug;
- deep link generation;
- state transitions и idempotency;
- matched/mismatched `managed_bot` update;
- secret only in `0600` store, absent from logs/state/manifest;
- traversal, symlink escape, duplicate instance rejection;
- child sees only own token env;
- tool schemas, authorization и default tool allowlist;
- `quick_faq`, `lead_inbox`, `link_inbox`: deterministic startup, access control, data minimization, per-instance isolation и safe `/health`;
- modern MCP: dual-era negotiation, `server/discover`, stateless explicit handle, schema composition, MRTR expiry/tamper/replay rejection, Tasks state/authorization/cancel и trace redaction.

### Integration test с fake Telegram API

1. `factory_create_request`.
2. Simulate user confirmation + `managed_bot` update.
3. Worker fetches fake child token.
4. Manifest + secret file are created.
5. `owner_echo` starts and responds to owner.
6. Non-owner is rejected.
7. No token appears in stdout or non-secret artifacts.

### Реальная проверка перед PyPI

1. Реальный manager bot с включённым Bot Management Mode; доказать `getMe.can_manage_bots == true`.
2. Создать один disposable managed child через реальную confirmation link.
3. Доказать получение child token без утечки в Git/logs.
4. Доказать `/health` и owner-only reply child bot.
5. Остановить и удалить disposable local instance по runbook, без заявления, что Telegram account автоматически удалён.
6. Зелёные `pytest`, `ruff check .`, wheel/sdist build и `twine check`.
7. Установить опубликованный PyPI package в чистый venv.
8. Реально выполнить `hermes mcp test bot-factory` и безопасный `factory_preflight`.

## 13. План реализации на выходные

1. Создать отдельный public repository и проверить PyPI name.
2. Сделать spike реального manager Bot API: `getMe.can_manage_bots`, creation deep link, update shape, `getManagedBotToken`. Не писать основной код до подтверждения этого на disposable child.
3. Реализовать typed models, SQLite state machine, SecretStore и path boundaries через TDD.
4. Реализовать polling manager worker и fake Telegram integration test.
5. Реализовать isolated `owner_echo` child launcher.
6. Реализовать FastMCP control plane с указанным минимальным набором tools.
7. Реализовать setup wizard, human-friendly status copy, README и demo script.
8. Добавить CI, secret scan, threat model и runbook.
9. Провести live end-to-end verification, затем PyPI release `0.1.0`.

## 14. Формулировки после реального релиза

### README / PyPI

> `telegram-managed-bot-factory` connects Hermes to Telegram Managed Bots. Configure one manager bot once, then create isolated child bots through a simple Telegram confirmation flow. The factory retrieves child credentials directly from Telegram, keeps secrets out of the agent context, and provisions each child with its own runtime boundary.

### Для HR / CTO

> Open-source MCP control plane and secure runtime for Telegram Managed Bots: one-time manager-bot onboarding, owner-confirmed child provisioning, automatic credential retrieval through Telegram’s managed-bot API, and isolated per-bot execution boundaries.

Использовать это только после публичного GitHub repository, PyPI release и подтверждённой end-to-end проверки.

## Источники

- Telegram: [Managed Bots](https://core.telegram.org/bots/features#managed-bots).
- Telegram Bot API: `can_manage_bots`, `managed_bot`, `getManagedBotToken`, `replaceManagedBotToken`.
- Telegram MTProto reference: [Managed bots](https://core.telegram.org/api/bots/managed-bots).
