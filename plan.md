# Product Requirement Document (PRD)

## Project Name: Project Look Open Source (CLI & API Edition)

**Status:** Approved / Production-Ready

**Author:** AI Collaborator & Project Lead

**Date:** May 2026

---

## 1. Executive Summary & Objective

**Project Look Open Source** is a developer-focused application that aggregates, caches, and exports high-quality open-source learning resources (books, projects, and courses).

The primary objective is to eliminate the manual overhead of browsing multiple curation sites or raw web scraping. By introducing a multi-source engine architecture—leveraging the **GitHub Search API** and **Open Library API**—combined with a local caching layer and a structured web API interface, the tool delivers a lightning-fast, highly customizable, and offline-capable developer experience for discovering educational engineering materials.

---

## 2. User Experience & Core Features

### 2.1 Multi-Source Search Engine

* **Description:** The application accepts user queries directly and allows targeting of specific resource ecosystems or querying all of them concurrently.
* **Supported Platforms:**
* **GitHub (GH):** Discovers repositories, frameworks, code implementations, and curated awesome-lists.
* **Open Library (OL):** Discovers free books, reference texts, and academic literature.


* **Source Selection Behavior:** Users can toggle which sources to query. If no specific source is isolated, the system defaults to searching **all sources** simultaneously.

### 2.2 Intelligent Error Handling & Source Fallbacks

* **Description:** The application maintains a resilient and helpful user experience when external platforms fail, encounter network timeouts, or go down entirely.
* **Platform Downtime Workflow:**
* If a selected source is unresponsive, down, or returning server errors, the system must **not** crash or display unreadable stack traces.
* The engine will capture the network failure and expose a clear, user-friendly message indicating which source is unavailable (e.g., `[Error]: GitHub is currently unreachable or experiencing downtime.`).
* **Interactive Recovery Prompt (CLI Mode):** The terminal interface will prompt the user directly to choose a recovery path:
1. **Retry:** Re-attempt the search on the unavailable source.
2. **Switch Source:** Automatically pivot and run the search query against alternative active sources (e.g., Open Library).
3. **Abort:** Cancel the active network search cleanly.


* **API Mode Recovery:** The web server will intercept the backend timeout and respond with an informative JSON payload detailing the error and suggesting local database fallback routes.



### 2.3 Rate Limit Mitigation & Guardrails

* **Description:** The tool actively manages user consumption to prevent exhausting free API boundaries and handle rate exceptions gracefully.
* **GitHub Token Management:** Unauthenticated requests are highly restricted. The system accepts a personal API token configuration to significantly elevate search limits.
* **Rate Limitation Recovery:** If an external provider signals that the rate limit has been hit, the application catches the exception, informs the user with a helpful instruction on how to attach a token, and automatically falls back to serving matching records exclusively from the local cache.

### 2.4 Local Caching & Offline Mode

* **Description:** To minimize network latency, reduce external API calls, and enable complete offline functionality, the application instantly saves every successfully fetched resource to a local cache database.
* **Workflow Logic:**
1. User enters a search term and selects sources.
2. The application checks the local cache for entries matching the search term *and* the selected sources.
3. **Cache Hit:** Instantly displays local data (0ms network overhead).
4. **Cache Miss / Partial Cache Miss:** Hits the active external APIs, displays results, and silently updates the local cache in the background.


* **Bypass Control:** Include a force-refresh option to intentionally bypass the cache, run fresh live queries, and overwrite outdated local records.

### 2.5 Cache Browsing & History Management

* **Description:** Users can audit, query, and browse their previously cached datasets.
* **Capabilities:**
* **History Audit:** Displays a clean tabular overview of all previously searched terms, the sources they came from, resource counts, and timestamps.
* **Offline Isolation:** Explicitly restricts execution to the local database, completely skipping network stack actions (ideal for environments without internet access).



### 2.6 Resource Classification & Quality Filtering

* **Description:** The tool ingests metrics from incoming payloads to compute a uniform reputation flag, filtering out low-quality or abandoned projects by default while still ensuring data is saved.
* **Evaluation Logic:**
* **GitHub Repositories:** If a repository has **$>100$ stars**, it is flagged as `reputable = True`. If it has **$\le 100$ stars**, it is flagged as `reputable = False`.
* **Open Library Books:** Because items cataloged by Open Library represent structured, published print materials, they are automatically flagged as `reputable = True`.
* *Note:* Regardless of the rating, **all fetched resources are saved to the local cache database**.


* **Default Behavioral Filtering:** By default, the system will only display items flagged as `reputable = True`.
* **Overrides:** Users can explicitly choose to bypass the reputation filter to display all cached or fetched records, including those flagged as non-reputable.

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

| Column Name | Data Type | Modifiers | Description |
| --- | --- | --- | --- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique Identifier |
| `search_term` | TEXT | UNIQUE NOT NULL | The normalized string queried by user |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Metadata tracking record age for cache invalidation |

### 3.3 `resources` Table

Holds the specific aggregated payload blocks returned from the targeted APIs.

| Column Name | Data Type | Modifiers | Description |
| --- | --- | --- | --- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique Identifier |
| `query_id` | INTEGER | FOREIGN KEY -> `queries(id)` ON DELETE CASCADE | Links asset back to the parent search term |
| `source` | TEXT | NOT NULL | String literal identifying origin context (`github` or `open_library`) |
| `title` | TEXT | NOT NULL | Resource/Repository Name or Book Title |
| `description` | TEXT |  | Summary, catalog snippet, or repository context |
| `url` | TEXT | NOT NULL | Active hyperlink back to resource destination |
| `reputable` | BOOLEAN | NOT NULL | Maps directly to Python `True`/`False` based on star metrics or source publishing validation |

---

## 4. API Endpoint Specifications

The application can expose its core pipeline via a lightweight web service. All endpoints accept URL parameters to drive search, storage, and file generation.

### 4.1 Search & Cache Router

* **Endpoint:** `/search/<source>/<resource>`
* **Method:** `GET`
* **Description:** Executes a look-up. Queries the specified engine, updates the database on a cache miss, prints records locally to the server logs, and serves a structured JSON payload to the caller.
* **Valid URL Parameters:**
* `<source>`:
* `DB`: Queries *only* the local database cache (Offline/Local Engine).
* `GH`: Queries the live GitHub API.
* `OL`: Queries the live Open Library API.
* `ALL`: Sweeps all three engines (`DB`, `GH`, `OL`) concurrently and merges results.


* `<resource>`: The URL-encoded target topic (e.g., `data+structures`).



#### Example Request:

```bash
GET /search/ALL/operating+systems

```

#### Example JSON Response (Success Payload):

```json
{
  "search_term": "operating systems",
  "results_count": 2,
  "resources": [
    {
      "title": "Modern Operating Systems",
      "source": "open_library",
      "url": "https://openlibrary.org/books/OL1234M",
      "reputable": true
    },
    {
      "title": "awesome-os-dev",
      "source": "github",
      "url": "https://github.com/user/awesome-os-dev",
      "reputable": false
    }
  ]
}

```

#### Example JSON Response (Source Down Failure Event):

```json
{
  "error": "GitHub API is down or unresponsive.",
  "fallback_available": true,
  "suggested_action": "Re-try request using /search/DB/operating+systems or change source parameter to OL"
}

```

### 4.2 Document Export & Download Router

* **Endpoint:** `/download/<resource>/<source>/<type>`
* **Method:** `GET`
* **Description:** Fetches the filtered dataset from cache or live engines, compiles the structural records into a raw file stream, and initiates an attachment download in the user's browser or client app.
* **Valid URL Parameters:**
* `<resource>`: The URL-encoded target topic stored in the schema.
* `<source>`: The filter engine origin context (`DB`, `GH`, `OL`, or `ALL`).
* `<type>`: The targeted file format layout:
* `txt`: Generates a clean, plain-text markdown summary format.
* `pdf`: Generates a structured binary PDF with active embedded links.





#### Example Request:

```bash
GET /download/operating+systems/ALL/pdf

```

#### Expected HTTP Output Headers:

```http
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="operating_systems_resources.pdf"

```

---

## 5. Interface & Command Specification (CLI Engine)

The CLI companion binary tracks standard POSIX parameter designs.

### 5.1 Basic Execution

```bash
$ look "data structures"

```

* **Behavior:** Runs a default sweep across all sources, rendering a `rich` console grid of records matching `reputable = True`.

### 5.2 Explicit Source Overrides

```bash
# Search books exclusively
$ look "compiler design" --source open_library

# Search everything including non-reputable entries
$ look "networking" --include-all

```

### 5.3 System History Audits

```bash
$ look --history

```

* **Console Output Layout:**

```
+--------------------+--------------+----------------+---------------------+
| Search Term        | Source(s)    | Total Cached   | Last Updated        |
+--------------------+--------------+----------------+---------------------+
| data structures    | github, ol   | 45 resources   | 2026-05-15 14:22:11 |
| machine learning   | github       | 15 resources   | 2026-05-18 10:05:00 |
+--------------------+--------------+----------------+---------------------+

```