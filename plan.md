# Product Requirement Document (PRD)

## Project Name: Project Look Open Source (CLI Edition)

**Status:** Approved / Production-Ready

**Author:** AI Collaborator & Project Lead

**Date:** May 2026

---

## 1. Executive Summary & Objective

**Project Look Open Source** is a developer-focused Command Line Interface (CLI) application that aggregates, caches, and exports high-quality open-source learning resources (books, projects, and courses).

The primary objective is to eliminate the manual overhead of browsing multiple curation sites or raw web scraping. By introducing a multi-source engine architecture—leveraging the **GitHub Search API** and **Open Library API**—combined with a local caching layer, the tool delivers a lightning-fast, highly customizable, and offline-capable terminal experience for discovering educational engineering materials.

---

## 2. User Experience & Core Features

### 2.1 Multi-Source Search Engine

* **Description:** The application accepts user queries directly via terminal arguments and allows users to dynamically target specific resource ecosystems or query all of them concurrently.
* **Supported Platforms:**
* **GitHub:** Discovers repositories, frameworks, code implementations, and curated awesome-lists.
* **Open Library:** Discovers free books, reference texts, and academic literature.


* **Source Selection Behavior:** Users can pass specific flags to toggle which sources to query. If no source flag is specified, the application defaults to searching **all sources** simultaneously.

### 2.2 Intelligent Error Handling & Source Fallbacks

* **Description:** The application must maintain a resilient and helpful user experience when external platforms fail, encounter network timeouts, or go down entirely.
* **Platform Downtime Workflow:**
* If a selected source (e.g., GitHub) is unresponsive, down, or returning server errors, the application must **not** crash or display unreadable stack traces.
* The CLI will immediately display a clear, user-friendly error message indicating which source is unavailable (e.g., `[Error]: GitHub is currently unreachable or experiencing downtime.`).
* **Interactive Recovery Prompt:** The application will then prompt the user directly in the terminal to choose a recovery path:
1. **Retry:** Re-attempt the search on the unavailable source (useful for temporary network drops).
2. **Switch Source:** Automatically pivot and run the search query against alternative active sources (e.g., Open Library).
3. **Abort:** Cancel the active network search cleanly.





### 2.3 Rate Limit Mitigation & Guardrails

* **Description:** The tool must actively manage user consumption to prevent exhausting free API boundaries and handle rate exceptions gracefully.
* **GitHub Token Management:** Unauthenticated requests are highly restricted. The CLI must provide a configuration path allowing users to input a personal API token to significantly elevate their daily search limits.
* **Rate Limitation Recovery:** If an external provider signals that the rate limit has been hit, the application must catch the exception, inform the user with a helpful instruction on how to add a token, and automatically fall back to serving matching records exclusively from the local cache.

### 2.4 Local Caching & Offline Mode

* **Description:** To minimize network latency, reduce external API calls, and enable complete offline functionality, the application instantly saves every successfully fetched resource to a local cache.
* **Workflow Logic:**
1. User enters a search term and selects sources.
2. The application checks the local cache for entries matching the search term *and* the selected sources.
3. **Cache Hit:** Instantly displays local data (0ms network overhead).
4. **Cache Miss / Partial Cache Miss:** Hits the active external APIs, displays results, and silently updates the local cache in the background.


* **Bypass Control:** Include a force-refresh flag (`--refresh` / `-r`) to intentionally bypass the cache, run fresh live queries, and overwrite outdated local records.

### 2.5 Cache Browsing & History Management

* **Description:** Users must be able to audit and browse their previously cached datasets.
* **Flags:**
* `--history` / `-hs`: Displays a clean tabular overview of all previously searched terms, the sources they came from, resource counts, and timestamps.
* `--offline` / `-o`: Explicitly restricts execution to the local database, completely skipping network stack actions (ideal for environments without internet access).



### 2.6 Resource Classification & Quality Filtering

* **Description:** The tool must ingest metrics from incoming payloads to compute a uniform reputation flag, filtering out low-quality or abandoned projects by default while still ensuring data is saved.
* **Evaluation Logic:**
* **GitHub Repositories:** If a repository has **$>100$ stars**, it is flagged as `reputable`. If it has **$\le 100$ stars**, it is flagged as non-reputable.
* **Open Library Books:** Because items cataloged by Open Library represent structured, published print materials, they are automatically flagged as `reputable`.
* *Note:* Regardless of the rating, **all fetched resources are saved to the local cache database**.


* **Default Behavioral Filtering:** By default, the CLI search command will only display items flagged as `reputable`.
* **Flags:**
* `--include-all` / `-a`: Overrides the default layout filter to display all cached or fetched records, including those flagged as non-reputable.



### 2.7 Document Export (PDF Generation)

* **Description:** Users can compile active search results into a clean, well-formatted PDF report containing active, clickable hyperlinks to the resource paths.
* **Flags:**
* `--export <path>` / `-e <path>`: Generates a dedicated PDF asset at the specified destination path.



---

## 3. Data Architecture & Schema Design

To ensure optimal speed and seamless native integration with Python's boolean types, the caching engine uses a zero-configuration SQLite relational layer.

### 3.1 Entity Relationship Overview

The schema is built on a one-to-many relationship: a single unique `search_term` in the `queries` table can map to multiple entries within the `resources` table.

```
+------------------+          +-------------------+
|     QUERIES      |          |     RESOURCES     |
+------------------+          +-------------------+
| id (PK)          |1       * | id (PK)           |
| search_term      |----------| query_id (FK)     |
| created_at       |          | source            |
|                  |          | title             |
|                  |          | description       |
|                  |          | url               |
|                  |          | reputable         |
+------------------+          +-------------------+

```

### 3.2 `queries` Table

Defines the history log of distinct search keywords executed by the user.

| Column Name   | Data Type | Modifiers                 | Description                                         |
| ------------- | --------- | ------------------------- | --------------------------------------------------- |
| `id`          | INTEGER   | PRIMARY KEY AUTOINCREMENT | Unique Identifier                                   |
| `search_term` | TEXT      | UNIQUE NOT NULL           | The normalized string queried by user               |
| `created_at`  | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Metadata tracking record age for cache invalidation |

### 3.3 `resources` Table

Holds the specific aggregated payload blocks returned from the targeted APIs.

| Column Name   | Data Type | Modifiers                                      | Description                                                                                  |
| ------------- | --------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `id`          | INTEGER   | PRIMARY KEY AUTOINCREMENT                      | Unique Identifier                                                                            |
| `query_id`    | INTEGER   | FOREIGN KEY -> `queries(id)` ON DELETE CASCADE | Links asset back to the parent search term                                                   |
| `source`      | TEXT      | NOT NULL                                       | String literal identifying origin context (`github` or `open_library`)                       |
| `title`       | TEXT      | NOT NULL                                       | Resource/Repository Name or Book Title                                                       |
| `description` | TEXT      |                                                | Summary, catalog snippet, or repository context                                              |
| `url`         | TEXT      | NOT NULL                                       | Active hyperlink back to resource destination                                                |
| `reputable`   | BOOLEAN   | NOT NULL                                       | Maps directly to Python `True`/`False` based on star metrics or source publishing validation |

---

## 4. Technical Architecture & Component Tree

### 4.1 Tech Stack Selection

* **Language:** Python 3.10+
* **Argument Parsing:** `click` (Decorator-driven library for building clean subcommands and robust flag arrays).
* **Terminal Formatting:** `rich` (For rendering asynchronous loaders, colorized status flags, and data grids).
* **Network Operations:** `requests` (Handles HTTP resource streaming).
* **Local Storage:** `MySQL` (External relational DB; requires `mysql-connector-python` for Python integration).
* **Document Generator:** `fpdf2` or `reportlab` (Compiles system arrays into binary PDFs with working hyperlinks).

### 4.2 Target Directory Structure

```
project_look/
│
├── core/
│   ├── __init__.py
│   ├── api_client.py     # Dispatches requests to GitHub/OpenLibrary with structured User-Agents/Tokens
│   └── cache_manager.py  # SQLite connection pooling, schema generation, and query filtering
│
├── cli/
│   ├── __init__.py
│   ├── commands.py       # Main Click setup defining interface entry points and interactive hooks
│   └── display.py        # Formatting layer wrapping 'rich' layouts for console tables
│
├── utils/
│   └── pdf_engine.py     # PDF document structure and clickable link mapping
│
├── config.json           # User configuration profiles (Personal Access Tokens, default target paths)
└── main.py               # Application entry point

```

---

## 5. Interface & Command Specification

The CLI follows standard POSIX argument conventions. Below are the functional specifications for terminal outputs:

### 5.1 Comprehensive Multi-Source Search (Default behavior)

```bash
$ look "data structures"

```

* **Expected Output:** Runs a concurrent cache evaluation across both sources. If a cache miss occurs, displays an elegant progress spinner (`Searching GitHub and Open Library APIs...`), populates the local cache tables, and prints out a combined table showing only reputable elements.

### 5.2 Handling Source Downtime (Interactive Prompt)

```bash
$ look "machine learning" --source github

```

* **Expected Output Scenario (GitHub Down):**

```
[!] Error: GitHub is currently unreachable or experiencing downtime.

How would you like to proceed?
[1] Retry searching GitHub
[2] Switch source to Open Library
[3] Abort search

Select an option (1-3): _

```

### 5.3 Offline History Audit

```bash
$ look --history

```

* **Expected Output:**

```
+--------------------+--------------+----------------+---------------------+
| Search Term        | Source(s)    | Total Cached   | Last Updated        |
+--------------------+--------------+----------------+---------------------+
| data structures    | github, ol   | 45 resources   | 2026-05-15 14:22:11 |
| machine learning   | github       | 15 resources   | 2026-05-18 10:05:00 |
+--------------------+--------------+----------------+---------------------+

```

### 5.4 Fully Inclusive Filtered Search & PDF Output

```bash
$ look "operating systems" --include-all --source open_library --export ~/Desktop/os_books.pdf

```

* **Expected Output:** Targets only the Open Library cache/API, bypasses the reputation filter to display *all* discovered records (including any non-reputable entries), renders them to the terminal, and compiles them cleanly into a hyperlinked PDF dropped onto the user's desktop.