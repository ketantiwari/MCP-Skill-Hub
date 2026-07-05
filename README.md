# Dynamic MCP Skill Hub

Dynamic MCP Skill Hub is a Python, filesystem-first backend for creating, validating, versioning, publishing, and executing generated MCP tools without using a database in the MVP.

## Web Portal UI

The project now includes a Reflex-based browser portal where you can chat with the agent, let it answer directly, or have it build a tool through the MCP skill hub and show the result in the UI.

## What This Project Builds

- Accepts natural-language requests for new tools, tool updates, rollbacks, or executions.
- Converts requests into canonical tool specifications.
- Generates source code, schemas, tests, manifests, and metadata.
- Validates generated artifacts before publishing.
- Stores every tool and version as immutable files under `workspace/tools`.
- Exposes published tools through an MCP server.
- Executes tools through a sandbox runner.
- Uses Gemini first, Groq as fallback, and Tavily when factual research is needed.
- Keeps audit logs and runtime history on the filesystem.

## Architecture

```text
User Request
  -> Intake Node
  -> Spec Builder Node
  -> Research Node
  -> Code Generation Node
  -> Validation Node
  -> Approval Node
  -> Publish Node
  -> MCP Server / Execute Node
  -> Filesystem Logs and Versioned Manifests
```

## Repository Layout

```text
src/
  dynamic_mcp_skill_hub/
    config/        Environment config
    execution/     Sandboxed tool execution
    llm/           Gemini primary and Groq fallback routing
    mcp/           MCP server registration and discovery
    models/        Strict Python/Pydantic data models
    research/      Tavily adapter
    storage/       Filesystem registry
    utils/         Logging helpers
    validation/    Schema, test, and safety validation
    workflow/      LangGraph workflow skeleton
workspace/
  tools/           Source of truth for tools and versions
  runtime/         Temporary runtime state
  logs/            Audit and execution logs
tests/             Unit and integration tests
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
reflex run
```

Fill `.env` with provider keys before running real generation or research:

- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `TAVILY_API_KEY`

## MVP Rules

- No database, ORM, or DBMS.
- Published versions are immutable.
- Rollback only updates `current.json`.
- Failed validation blocks publishing.
- Destructive tools require approval.
- Runtime caches are convenience only, never the source of truth.

## Example Tool

An initial example tool lives at:

```text
workspace/tools/simple_math/
```

It demonstrates the expected version folder layout, manifests, schema, validation report, publish report, and README.

## Useful Commands

```bash
reflex run
pytest
ruff check .
mypy src
```

## End-to-End Query Test

Once your `.env` has the provider keys, run:

```bash
reflex run
```

That should:

- open the browser portal
- classify the request through Gemini or Groq
- answer directly when possible
- build and publish a tool when the request needs one
- show the latest tool result in the portal
