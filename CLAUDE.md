# CLAUDE.md — Odoo 19 Development Standard (Master Operating Manual)

This is the standing operating manual for **any** Odoo 19 work in this workspace: new custom development, changes to existing modules, bug fixing, and review/checking. Re-read it at the start of every session. It governs **Python (server/ORM), XML (views/data/security), and JavaScript (OWL)** equally. Everything you produce must match the **Odoo 19 standard as it exists in the source**, not as remembered from older versions. When I give you a development command, follow the relevant parts below end-to-end without being reminded.

---

## CONTENTS

**A. Foundations & ground rules** — 0 Source is truth · 1 Community vs Enterprise & dependencies · 2 Where code lives & environments · 3 Decision framework (is customization justified?) · 4 Pre-flight & requirements
**B. How to write the code** — 5 Skeleton, manifest & naming · 6 Python/ORM · 7 XML (views/actions/menus, view types, search bar, smart buttons, activities & record linking) · 8 JavaScript/OWL & assets · 9 Security & access · 10 Multi-company · 11 Internationalization · 12 Configuration & feature flags
**C. Data, records & persistence** — 13 Database & transactions · 14 Performance, search & scale · 15 Sequences & master data · 16 Attachments & file storage · 17 Logging, monitoring & observability · 18 Mail, chatter, activities, email templates & notifications
**D. Processing & integration** — 19 Cron, background, queues & automation · 20 External API & integration · 21 Data import/export · 22 Reports (QWeb) & analytics
**E. Domain-specific safety** — 23 Domain modules (accounting, inventory, MRP, HR, etc.) · 24 Studio compatibility
**F. Changing existing systems** — 25 Extending/inheriting · 26 Migration, upgrade & backward compatibility · 27 Bug-fixing (root cause first) · 28 Refactoring & technical debt
**G. Verify, ship & operate** — 29 Testing & quality gates · 30 Review & sign-off checklist · 31 Version control & CI/CD · 32 Deployment, rollback & operations · 33 Documentation & handover
**H. AI agent operating rules** — 34 How you operate · 35 Never do · 36 Stop and ask · 37 Required response format · 38 Golden rules
**START HERE** (activation, at the end)

---

# PART A — FOUNDATIONS & GROUND RULES

## RULE 0 — SOURCE IS THE ONLY TRUTH (most important)

The official Odoo 19 source is available locally. **Both trees are strictly READ-ONLY — never modify anything inside them.**

```
Community source:   /Users/jainik/workspace/19.0
Enterprise source:  /Users/jainik/workspace/enterprise/19.0
```

Your training data may be outdated for v19. The source is the only authority.
- **Grep the source, never guess** — confirm the exact spelling/signature of every model, field, method, decorator, mixin, view tag/attribute, XML record type, JS import path, registry, service, hook, and asset bundle before using it.
- **Learn by example** — find the closest core/enterprise module doing the same thing and mirror its current pattern.
- **Cite what you found** — when you choose to use X, state the source file path where you saw it. If you can't find it, don't use it.
- **Source wins** over memory and over this file. If anything here conflicts with the actual source, follow the source and flag it.
- **Never invent** APIs, dependencies, XML IDs, view names, model names, OWL imports, or security rules. Everything is verified from source.
- **Community vs Enterprise:** a module is Community if it lives under `…/19.0/addons` (and odoo core), Enterprise if under `…/enterprise/19.0`. Classify any dependency this way before relying on it.

## 1. COMMUNITY vs ENTERPRISE & DEPENDENCIES

- Establish the **target edition first** (Community-only or Enterprise-enabled). If unknown, ask once before designing dependencies.
- A module may only `depends` on modules that physically exist in the target's addons. For a Community target, never depend on a module found only under the enterprise tree (build it custom instead).
- You may always **read** enterprise source to learn patterns even for a Community build.
- Before adding any dependency: verify it **exists** and is **installable** in the target tree, verify it is **actually required**, avoid unnecessary deps, confirm **license** compatibility, and note **why** it exists.
- **Third-party modules:** before relying on one, review code quality, security, maintenance activity, v19 compatibility, and license.

## 2. WHERE CODE LIVES & ENVIRONMENTS

- All custom code goes in a **dedicated custom addons directory**, never inside the core trees. Default: `/Users/jainik/workspace/custom_addons/`. If a different path is configured, ask once.
- **Never** edit core source; to change core behaviour, layer it from your own module via inheritance (§25).
- **Always identify the environment** (development / test / staging / production) before any action. Never assume production access. Keep dev/test/staging/prod settings separate and never hardcode environment values (§12, §32).

## 3. DECISION FRAMEWORK — is customization even justified?

Before building anything, walk this preference order and stop at the first that solves it:
1. **Standard Odoo** feature  →  2. **Configuration**  →  3. **Studio**  →  4. **Inheritance/extension** of existing modules  →  5. **New custom module**  →  6. **Core modification (never, unless explicitly approved by me)**.
- Justify why a lower-cost option does not work before choosing a higher-cost one, and note the long-term maintenance impact.

## 4. PRE-FLIGHT & REQUIREMENTS

Before writing code:
1. **Classify the task:** new module, edit existing (which), bug fix, or review.
2. **Clarify requirements** — objective, stakeholders, success criteria, assumptions, constraints, dependencies, risks, and **non-functional requirements** (performance, scalability, security, availability, compliance, usability). Do not start with unclear requirements (§36).
3. **Identify the source of each rule** — standard Odoo, customer-specific, legal, accounting, or workflow preference — and document it.
4. **Recon the source** for the exact v19 patterns/APIs you will use; produce a short findings note citing file paths. Show it before coding (§29 workflow).
5. **For edits:** read the target module **completely** first — manifest, models, security, views, data, reports, tests — then pick the cleanest extension mechanism.

---

# PART B — HOW TO WRITE THE CODE

## 5. MODULE SKELETON, MANIFEST & NAMING

Standard layout (include only what's needed):
```
module/
  __init__.py, __manifest__.py
  controllers/  models/  wizards/        # python
  views/  report/                        # xml + qweb
  security/ir.model.access.csv, security/*.xml   # access + groups + record rules
  data/  demo/                           # data records / demo
  static/src/...  static/description/icon.png    # owl js, xml templates, scss
  i18n/*.po, *.pot
  tests/   README.md
```
- `__manifest__.py` (confirm full key set from a core module): `name, summary, description, author, website, category, version "19.0.1.0.0", license, depends, data (dependency order — security before views), assets, demo, application, installable, auto_install`.
- `__init__.py` chains imports (`from . import models`).
- **Naming:** lowercase `snake_case`; consistent custom prefix; avoid generic or duplicate names; keep model `_name`, technical names and XML IDs consistent and stable.

## 6. PYTHON / ORM (verify spellings in source)

- `from odoo import models, fields, api`; `from odoo.exceptions import UserError, ValidationError`. Modern ORM only — no deprecated decorators.
- Models: `_name`, `_description`, `_order`; `_inherit` (list when combining mixins) per source patterns.
- Fields: `snake_case`, with `string` and `help`; relational fields set `comodel_name` + `ondelete`; `Selection` for states.
- **`tracking=True` — only when needed:** add it solely to fields whose change history carries real business/audit value. Every tracked field posts a chatter message and adds write-time overhead, so over-tracking both spams the chatter and slows writes (§18). Don't track high-churn, computed-noise or low-value fields.
- **`index=True` — only when needed:** index a field **only** if you actually filter / search / group / order by it (§14). Indexes speed reads but slow every write and cost storage, so blanket-indexing breaks write performance — judge per field, don't index by default. Confirm the right index kind from source before using a variant (e.g. `index=True`/btree vs `index='trigram'` for `ilike` text search, §0); a `store=True` computed field you search on needs the same indexing judgement. Verify existing indexes first to avoid duplicates (§13).
- **Relational writes:** use the modern ORM `Command` helpers (`Command.create/update/delete/unlink/link/clear/set`) — confirm availability/spelling in source; prefer them over legacy tuple syntax.
- **Computed fields:** correct `@api.depends`; no recursive dependencies; `store=True` only when you must search/group on it (justify it); add an inverse only if writable; keep computation batch-safe; mind invalidation/performance (§14).
- Validation: hard rules via `@api.constrains` (raise `ValidationError`); `@api.onchange` is UX-only, not enforcement.
- CRUD overrides call `super()`; use the current multi-create pattern (e.g. `@api.model_create_multi`); operate on recordsets, not single records; **no `search()` inside loops** (§14).
- **Wizards** = transient models: validate input, keep business logic in the model layer, support batch operations.
- **Error handling:** `UserError` for user-facing action problems, `ValidationError` for validation, log unexpected exceptions (§17), never expose stack traces to end users, always give a meaningful message.
- User-facing strings translatable (§11). Logging via module logger, no `print` (§17). `sudo()` only with justification, never to bypass access (§9) or company rules (§10). Raw SQL only when unavoidable and always parameterized.

## 7. XML — VIEWS, ACTIONS, MENUS

- `<record model="...">` for `ir.ui.view`, `ir.actions.*`, `ir.cron`, `ir.sequence`, `res.groups`, `ir.rule`, mail templates, etc.
- **Confirm live view tags from source** (e.g. `<list>` vs `<tree>` in 19) — never assume.
- **View types — provide the right ones, not just list + form:** the action's `view_mode` should offer every view that fits how users actually consume the data. v19 **core/Community**: `form`, `list`, `kanban`, `calendar`, `pivot`, `graph`, `activity`, `search` (plus `qweb` for reports). **Enterprise-only**: `gantt`, `cohort`, `map`, `grid`, spreadsheet `dashboard` — use only if that edition/dependency physically exists in the target tree (§1). Match view to purpose: transactional browsing → `list` + `kanban` + `form`; date/scheduling → `calendar` (or `gantt`); analysis/reporting → `pivot` + `graph`; follow-ups/workload → `activity`; geo → `map`. **Add the analytical and scheduling views wherever the model carries dates, amounts, states or measures worth slicing** — don't ship a bare list+form when a pivot, graph or calendar would serve the user. Declare each as its own `ir.ui.view`, set the `measures`/`group_by`/date fields the view needs on **index-backed** columns (§14), confirm every view-type tag and attribute from a core module that already uses it (§0), and secure visibility by group where relevant (§9).
- **Activities (`mail.activity`):** where records need follow-ups, approvals, reminders or scheduled to-dos, add the `mail.activity.mixin`, expose the **`activity` view** (and the chatter activity widget on the form), and define the activity types, default responsible users and deadlines; schedule via `activity_schedule()` per core patterns. Restrict to records with real business value and avoid activity/chatter spam — full activity/chatter rules live in §18.
- **External IDs:** `module.descriptive_id`, lowercase snake_case, stable and meaningful; preserve across versions (§26).
- `noupdate="1"` for config the user may edit and that must survive upgrades; mandatory config in `data/`, demo in `demo/`; respect load order.
- **Actions:** define and secure window/server/client actions; control visibility by group.
- **Menus:** follow core navigation patterns; avoid needless depth; group related items; respect permissions.
- **Search views & the search bar:** define an explicit `<search>` view per business model — never rely on the bare default. Expose the right searchable `<field>`s (use `filter_domain` / explicit operators for fuzzy or multi-field text search), meaningful saved `<filter>`s, and `<group>`-by options; add a `<searchpanel>` for category/hierarchy faceting where it aids navigation. Pre-apply filters through the action `context` (`search_default_<filter_name>`). Confirm the live `<search>` / `<field>` / `<filter>` / `<group>` / `<searchpanel>` tags and attributes from a core search view in source (§0); keep every searched/filtered/grouped field index-backed and domains selective (§14).
- **Smart buttons (stat buttons):** surface related records and KPIs in the form header. Put `<button class="oe_stat_button" type="object" name="action_…" icon="fa-…">` inside the form's **button box**, and show the figure with a `statinfo` widget field. Back the figure with a **batched** computed count (`read_group` / `_compute_*` over the recordset — never `search()` per record, §14). The button method returns an `ir.actions.act_window` that is **domain-scoped** to the related records and sets `context` `default_<link_field>` so creating from the button auto-links back. Confirm the button-box element/name, the `oe_stat_button` class, the `statinfo` widget name and the action-dict keys from a core form view before using them (§0); gate visibility by group/state where relevant (§9).
- **Linking records & cross-model navigation:** model the relationship first — `Many2one` with its matching inverse `One2many`, correct `ondelete`, and consistent `company_id` (§6, §10) — then expose it in the UI via the smart button + scoped action above, with `context` `default_*` to pre-fill the link on create. For a single-record jump, return an act_window in `form` view with `res_id`. Never hardcode database IDs or action IDs — reference window actions by XML ID (`%(module.action_xmlid)d`). Keep navigation reachable from **both** sides so every linked object can be opened from its counterpart.
- **End-to-end UX flow (design the whole path, not the pieces):** model relation → computed count feeds the **smart button** → clicking opens the **domain-scoped action** → its **search view** lets the user filter/group within that related set → creating there pre-fills the link via `context` defaults, closing the loop back to the source record. Verify this full round-trip (counts update, scoping is correct, defaults apply, both directions navigate) as part of view validation, not just the individual widgets.
- **Domain & context:** validate domains and context values; never hardcode database IDs; avoid unsafe context assumptions.
- **View validation before delivery:** compiles with no warnings; xpath targets exist; inherited views load cleanly; no duplicate field declarations; fields referenced by modifiers/`invisible`/domains are present; modifiers and domains evaluate correctly; search views load; all declared view types (kanban/calendar/pivot/graph/activity, etc.) load and render with valid fields/measures; stat buttons render with correct counts and their actions open with the right domain/context. Prefer additive xpath over `replace` and verify xpaths against the real source (§24, §25).

## 8. JAVASCRIPT / OWL & ASSETS (confirm every path in source)

- Start files with `/** @odoo-module **/`; ES modules; import from real v19 paths (`@odoo/owl`, `@web/core/registry`, `@web/...`) — confirm, don't assume older paths.
- Components small/composable; state via `useState`; data via the current service (ORM service / `rpc`); register in the correct registry (actions/views/fields/systray/services) — confirm names.
- Templates in `static/src/**/*.xml` with matching `t-name`. Patch with the current patch utility; extend registries, don't replace core entries.
- **Assets:** declare bundles in the manifest `assets` key (confirm v19 dict format from a core manifest); verify the bundle exists, files load, SCSS compiles, no duplicate registration, correct order. No jQuery/legacy widgets unless the source proves it's still correct.
- **OWL review:** correct component lifecycle, `useState` usage, service injection, registry registration, reactive updates, event cleanup / no memory leaks, mobile rendering.

## 9. SECURITY & ACCESS (mandatory for every new model)

- **Access design first** — for every new model decide and document who can **read / create / write / delete**, then express it.
- `ir.model.access.csv` row for **every** model (least privilege per group); `res.groups` + category for new roles; `ir.rule` record rules for scoping (company, own-records).
- Never grant broad access or use `sudo()` to paper over a missing rule.
- **Data privacy:** don't expose sensitive fields unnecessarily; never log personal/confidential data (§17); verify portal visibility and attachment permissions (§16).
- **Secrets:** store outside source (`ir.config_parameter` or secret store), never in code/VCS; restrict and audit access; rotate where applicable (§20).
- **Threat surfaces to review:** authentication, authorization, record rules, exposed endpoints/controllers, API auth, file uploads, portal access, CSRF, data leakage, privilege escalation (§9, §30).
- **Auditability:** critical business actions and workflow/approval transitions must be traceable; preserve audit history.

## 10. MULTI-COMPANY & TENANT ISOLATION

- Evaluate **every** business model for company isolation; add and default `company_id` correctly.
- Verify record rules, reports, integrations and attachments respect company boundaries; test with multiple active companies; never `sudo()` past company restrictions.

## 11. INTERNATIONALIZATION (i18n)

- All user-facing text translatable (wrap with the current translation function — confirm v19 usage); never hardcode visible strings.
- Generate/update `.pot`; preserve existing translations; verify translated UI still renders correctly.

## 12. CONFIGURATION & FEATURE FLAGS

- Use `res.config.settings` for user-facing configuration; store values via `ir.config_parameter`; provide defaults; validate before use; document required settings.
- For gradual/riskier rollout use config-driven **feature flags** (no hardcoded behaviour switches); support disabling a risky customization; document activation steps.

---

# PART C — DATA, RECORDS & PERSISTENCE

## 13. DATABASE & TRANSACTIONS

- Let the ORM own the schema; never alter PostgreSQL tables manually in production; prefer ORM fields over manual DDL.
- Verify existing indexes before adding custom ones; avoid duplicate indexes; review query/EXPLAIN plans on large data; never drop columns/tables without migration verification (§26).
- **Transactions:** keep them short; avoid long-running transactions; use **savepoints** for risky operations; never commit manually unless absolutely required; handle rollback paths.
- **Concurrency:** consider concurrent users; prevent duplicate record creation and duplicate sequence assignment; verify cron, import and API concurrency.

## 14. PERFORMANCE, SEARCH & SCALE

- Assume large datasets. Index fields you filter/search/group by; avoid broad stored computes.
- Aggregate with `read_group`; use `mapped`/`filtered`/`prefetch`; never `search()` in a loop; keep domains selective.
- Batch long operations and crons (`limit`/chunks); avoid loading huge recordsets into memory; for **>1M-record** tables avoid offset pagination and full scans, verify EXPLAIN plans, test on production-sized data.
- Heavy reporting → read-only SQL **view model** (`_auto = False`) — confirm declaration from source.
- **Benchmark** form/list/search/report/import/export/cron/API before sign-off.

## 15. SEQUENCES & MASTER DATA

- Use `ir.sequence` for all business references; never generate numbers manually; support company-specific sequences (§10); consistent codes in `data/`.
- **Master data:** prevent duplicates; enforce unique constraints and reference integrity; validate critical fields; define ownership.

## 16. ATTACHMENTS & FILE STORAGE

- Store files via `ir.attachment`; never store large binaries in custom tables/columns; verify attachment access rights; clean orphaned attachments; watch storage growth and backup strategy.

## 17. LOGGING, MONITORING & OBSERVABILITY

- Module logger `_logger = logging.getLogger(__name__)`, no `print`. Levels: `debug` (dev), `info` (business events), `warning` (recoverable), `error` (failures). Never log passwords/tokens/secrets/PII.
- Provide actionable error messages, logs, metrics and health checks. Monitor cron failures, integration failures, performance bottlenecks and queue backlogs (§19, §32).

## 18. MAIL, CHATTER, ACTIVITIES & NOTIFICATIONS

- Add `mail.thread`/`mail.activity.mixin` only where there's business value; track only meaningful fields (avoid chatter spam); `message_post()` per core patterns with standard subtypes.
- **Activities/mail safety:** verify activity create/complete/schedule/notify, chatter performance, template rendering, email-queue processing.
- **Notifications:** use mail templates; avoid duplicate emails / notification spam; verify recipient logic, translations, and (where relevant) outgoing/incoming mail servers, aliases, bounce handling and unsubscribe compliance.
- **Email templates (`mail.template`):** define them as data records (in `data/`, `noupdate="1"` so user edits survive upgrades), one per business event. Set `model_id`, `subject`, `email_from` / `partner_to` / `email_to` and, for attachments, `report_template_ids` — never hardcode recipient addresses; resolve recipients from partner/relational fields via dynamic placeholders. Render dynamic content with the **v19 templating syntax confirmed from a core `mail.template`** (`{{ … }}` inline expressions and `<t t-out="…">` in the body — verify, don't assume, §0); keep all business logic in the model and let the template only render. Make `subject` and `body_html` **translatable** and set the per-recipient `lang` expression so each recipient is emailed in their language (§11). Send through the template (`env.ref(xmlid).send_mail(res_id, …)` / framework helper) rather than building raw emails. Validate every template before delivery: renders with real **and** edge-case data, no broken/empty placeholders, no secret/PII leakage (§9, §17), correct attachments, and clean queue processing.

---

# PART D — PROCESSING & INTEGRATION

## 19. CRON, BACKGROUND, QUEUES & AUTOMATION

- Define `ir.cron` in `data/`; the method lives on a model (confirm call convention). **Heavy/long tasks must not run in a user request** — move to cron/queue.
- Jobs **idempotent and restart-safe**; batch with `limit`; prevent overlap/duplicate execution and duplicate processing; provide progress tracking; log failures so one bad record doesn't abort the batch.
- **Queue jobs:** verify retries, idempotency, failure handling, concurrency, monitoring, cleanup.
- **Server/automated actions:** verify execution permissions, recordset availability, multi-record execution, no unsafe `eval`, no infinite loops/recursion, idempotency, proper error handling.

## 20. EXTERNAL API & INTEGRATION

- Always set **timeouts**; bounded, idempotent retries with backoff; log request/response errors with context but never secrets.
- Credentials in `ir.config_parameter`/secret store, never in code (§9). Provide a connection-test action.
- **API contracts:** version external APIs; document and validate request/response formats; preserve backward compatibility.
- Integration patterns: REST, webhooks, file transfer, direct DB (use cautiously). Verify auth, error handling, retry, timeouts, monitoring, logging (§30).

## 21. DATA IMPORT / EXPORT

- **Import:** validate all data before commit; batch large sets; log failed rows separately; preserve external IDs so imports are idempotent and prevent duplicates; support rollback.
- **Export:** verify performance, data accuracy, access rights, sensitive-field protection.
- Support standard Odoo import/export formats; verify round-trip import/export and external-identifier preservation.

## 22. REPORTS (QWeb) & ANALYTICS

- Prefer QWeb (report action + template + `paperformat`); no layout hacks; keep heavy calculations in models, templates only render; verify PDF generation on large data.
- **Analytics/dashboards:** meaningful KPIs, actionable reports, filters and drill-downs; build on efficient data sources (§14).

---

# PART E — DOMAIN-SPECIFIC SAFETY

## 23. DOMAIN MODULES — never bypass standard workflows

**General rule:** mirror the exact pattern the core domain module uses; follow standard state transitions; don't force states or bypass posting/movement/valuation logic; verify downstream documents and flows.
- **Accounting & localization:** never modify posted journal entries directly (use reversals); respect lock dates; no direct SQL on accounting tables; verify fiscal localization, tax reports, statutory/country requirements.
- **Inventory:** never modify stock quants directly — use stock moves/move lines; verify reservations and valuation impact.
- **Manufacturing:** respect MO/work-order workflows; don't bypass stock movement; verify BOM and valuation effects.
- **HR & payroll:** verify payroll/salary rules, leave allocations, attendance integrations; protect employee privacy; meet legal compliance.
- **eCommerce / Website:** verify checkout, payment providers, availability, pricing, taxes, customer access (§9).
- **Subscription / Rental:** verify recurring invoicing, renewals/cancellations, prorating; reservations, availability, returns, invoicing impact.
- **Helpdesk / Marketing:** verify SLA/escalation/assignment/visibility; campaign triggers, email frequency, unsubscribe compliance, tracking.
- **POS:** verify offline behaviour, sync, multi-session; don't block POS loading; optimise asset size; confirm POS asset bundles from source (§8).
- **Approvals/workflows:** define approval levels, escalation, rejection and delegation paths; verify the audit trail (§18).

## 24. STUDIO COMPATIBILITY

- Don't break Studio-generated fields/views; verify inherited views coexist with Studio customizations; avoid `position="replace"` on views Studio may extend — prefer **additive xpath** (§7, §25).

---

# PART F — CHANGING EXISTING SYSTEMS

## 25. EXTENDING / INHERITING EXISTING MODULES

Always layer changes from your own module; never edit the original.
- **Models:** `_inherit = 'model'` to add fields/methods; override + `super()` to change behaviour (full replace only when necessary); use classical/prototype/delegation inheritance per source.
- **Views:** new `ir.ui.view` with `inherit_id` + `<xpath expr position>` (`attributes/before/after/inside/replace`); find the target external id in source; prefer additive positions over `replace` (§24).
- **JS:** patch via the current patch utility; extend registries, don't replace core (§8).

## 26. MIGRATION, UPGRADE & BACKWARD COMPATIBILITY

- Never rename/delete fields, models or **XML IDs** without a migration plan; preserve XML IDs, security groups and public APIs; document breaking changes; provide migration mapping.
- Provide migration scripts for schema changes (confirm the migration folder/version convention from source); supply safe defaults when adding non-null fields to populated models.
- **Upgrade test matrix:** fresh install; upgrade from previous custom version; existing production data; existing scheduled actions, security groups, XML IDs, attachments. Test upgrades on a **copy of production data**, validating record counts, foreign keys, attachments, users/groups, sequences, scheduled actions and reports before/after.
- **Dependency upgrades:** verify compatibility, upgrade/migration/security/performance impact, and re-test all dependent modules.
- **Deprecation:** announce with a timeline, provide a migration path, keep backward compatibility as long as feasible.

## 27. BUG-FIXING (root cause first)

Always establish root cause before touching code; show the analysis with the fix:
1. Reproduce and describe (expected vs actual). 2. Identify root cause and **why the current code fails**. 3. Verify against the v19 source — our code or platform behaviour? 4. Check whether standard behaviour already handles it. 5. List affected files. 6. Implement the **minimal** fix (never rewrite a module for a small bug). 7. Verify no regression; test install, upgrade and existing workflows. 8. Document root cause, fix, test results and rollback plan.

## 28. REFACTORING & TECHNICAL DEBT

- Refactor only when justified; preserve behaviour; add tests before major refactors; verify upgrade and performance impact.
- No unexplained `TODO`s; document temporary workarounds, known limitations and deprecated customizations; remove dead code.

---

# PART G — VERIFY, SHIP & OPERATE

## 29. TESTING & QUALITY GATES + WORKFLOW

- Tests in `tests/` using the current base class (confirm, e.g. `TransactionCase`) and correct `@tagged` markers; cover constraints, computes, workflow transitions, crons, controllers.
- Install/upgrade on a test DB with **zero errors/warnings** in the log; run configured linters; provide demo data; define and validate **UAT** acceptance criteria with business sign-off.
- **Verify the execution environment before running anything** — never assume the command; confirm the real `odoo-bin` location, addons paths and database config, then use the correct invocation (e.g. `odoo-bin -d <db> -u <module> --stop-after-init` or the Apps UI).
- **Workflow:** Phase 1 **Recon (no code)** → report patterns with file-path citations + a short plan, wait for confirmation. Phase 2 implement in small scoped steps; after each step report what changed, files touched, and how to install/test; verify a clean log before moving on.

## 30. REVIEW & SIGN-OFF CHECKLIST (before presenting any solution)

Self-review every solution against, and report PASS/concern for each:
**Source compliance** (verified, nothing invented) · **Security** (auth, record rules, data exposure, secrets, CSRF, portal) · **Performance** (queries/reports/imports/exports/API/cron benchmarked) · **Multi-company** · **Upgrade safety** (XML IDs, migration, test matrix) · **Dependency correctness & license** · **Translation support** · **Test coverage** · **No unrelated files changed** · **Root cause addressed** · **Rollback plan exists** · **Documentation**. For Enterprise-grade work also confirm auditability, scalability, availability, DR, monitoring, supportability.

## 31. VERSION CONTROL & CI/CD

- One logical change per commit; meaningful messages; small focused PRs; document breaking changes; never commit secrets/credentials/env files or unnecessary generated files.
- CI must, before merge/deploy: run install tests, upgrade tests, linting, security validation and dependency validation, and **block on failure**.
- Every module/integration/deployment has a named **owner**.

## 32. DEPLOYMENT, ROLLBACK & OPERATIONS

- **Before production:** backup DB; verify upgrade path and rollback plan; verify scheduled actions, access rights, reports, integrations and logs; assess security/performance/data-loss/upgrade/user-impact **risk**.
- **Rollback/DR readiness:** verified backup + restore + rollback steps + data-recovery plan; verify recovery-time expectations and that recovery is tested.
- **After deployment:** verify logs, scheduled jobs, reports, integrations, user access and business workflows.
- **Ops:** monitoring + alerting; capacity planning (DB/attachment/server/API growth); incident management (severity, RCA, impact, resolution, prevention); release management (versioned releases, release notes, tags). On **Odoo.sh/SaaS** verify build, deployment pipeline, staging validation, backup policy and environment variables.

## 33. DOCUMENTATION & HANDOVER

- Document custom models/fields, configuration steps, cron jobs, integrations, deployment requirements, troubleshooting and an error catalog; record **architectural decisions** (problem, options, choice, reasoning, impact).
- For project closure / knowledge transfer: business overview → technical architecture → key customizations → deployment → support procedures → common issues → maintenance schedule; confirm docs, deployment, KT and support handover complete.

---

# PART H — AI AGENT OPERATING RULES

## 34. HOW YOU OPERATE

- Verify before assuming; cite source file paths for non-trivial choices.
- Make **minimal, scoped** changes inside the custom addons dir only; never touch core trees or unrelated files; never change coding style needlessly.
- Read the existing module **completely** before editing (manifest, security, views, data, reports, tests).
- Reuse existing Odoo mechanisms over inventing new ones; produce minimal diffs and explain reasoning, root cause, impact and testing.
- If this file conflicts with the source, the **source wins** — flag it.

## 35. NEVER DO

Modify Odoo core · skip source validation, security review, upgrade testing, or rollback planning · deploy untested code · invent APIs/IDs/views/models/imports/security rules · hardcode IDs or credentials · use `sudo()` without justification · bypass security, accounting, inventory or other standard workflows · rename fields/XML IDs without migration · rewrite a module for a small change · remove existing features unless explicitly requested · ignore multi-company, performance or upgrade impact.

## 36. STOP AND ASK

Stop and ask me before proceeding when: requirements are ambiguous; multiple valid implementation paths exist; the change involves **data deletion**, **destructive migrations**, **accounting/inventory/MRP logic**, or **security rule changes**; or production access/impact is implied.

## 37. REQUIRED RESPONSE FORMAT (for every fix or feature)

Provide, in order:
1. Requirement summary  2. Root-cause analysis (for bugs)  3. Odoo 19 **source references** (file paths)  4. Proposed solution  5. Impact analysis (modules, users, integrations, reports, workflows, database)  6. Files affected  7. Test plan  8. Upgrade/deployment plan  9. Rollback plan  10. Risks.

## 38. GOLDEN RULES

1. Source code is the truth. 2. Standard Odoo before customization. 3. Configuration before code. 4. Inheritance before replacement. 5. Security before convenience. 6. Upgrade safety before shortcuts. 7. Correct design before optimization hacks. 8. Testing before deployment. 9. Documentation before handover. 10. Root cause before fix.

---

### START HERE (every task)
Confirm: **(a)** new module or edit to an existing one (which)? **(b)** target edition — Community-only or Enterprise-enabled? **(c)** the custom addons path. Then run **Phase 1 (Recon)** against `/Users/jainik/workspace/19.0` and `/Users/jainik/workspace/enterprise/19.0` and report the exact Python, XML and OWL patterns you will use — each with the source file path where you found it — **before** writing any code. Then proceed per §29 (Workflow) and deliver in the §37 format.
