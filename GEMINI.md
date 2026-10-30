# Project Customizations & Guidelines: pangan-watcher

This project is configured with active Antigravity customizations including Skills, Workflows, Subagents, and MCP servers.

## Active MCP Servers

1. **`codebase-memory` (codebase-memory-mcp)**:
   - High-performance local structural code-intelligence knowledge graph engine.
   - Tools: `index_repository`, `search_graph`, `query_graph`, `trace_path`, `get_code_snippet`, `get_file_outline`, `get_graph_schema`, `compare_graphs`, `get_architecture`, `search_code`, `list_projects`, `delete_project`, `index_status`, `check_index_coverage`, `detect_changes`, `manage_adr`, `ingest_traces`.
   - Used for tracing function call chains, finding callers/callees, architectural mapping, and fast context retrieval with minimal token footprint.

2. **`chrome-devtools` (chrome-devtools-mcp)**:
   - Browser automation and UI inspection tools.

3. **`memory` (@modelcontextprotocol/server-memory)**:
   - Persistent graph entity & relation memory across sessions.

## Specialized Codebase Memory Subagents

- **`codebase-memory-scout`**: Fast Tier-1 positive graph lookup for quick definitions and callers.
- **`codebase-memory`**: Tier-2 task-directed verification of call chains, symbol relationships, and changes.
- **`codebase-memory-auditor`**: Tier-3 thorough structural audits and completeness verification.

## Customization Workflow & Rules

- Use `search_graph` and `trace_path` before reading raw files across large scopes.
- When tracing bugs or refactoring, check symbol impacts with `detect_changes`.
- Consult relevant skills in `.agents/skills/` and workflows in `.agents/workflows/` when executing standard developer procedures.

