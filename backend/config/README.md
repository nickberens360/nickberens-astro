# RAG Data Sources Configuration

This directory contains configuration files for the RAG (Retrieval-Augmented Generation) system.

## Configuration File: `data_sources.yaml`

The `data_sources.yaml` file centralizes all configuration for data sources, retrievers, and prompts used in the RAG system.

### Structure

#### 1. Data Sources (`data_sources`)
- `base_path`: Base directory for all data files
- `output_file`: Name of the unified data file
- `sources`: List of data sources with their configurations
  - `name`: Source identifier
  - `file`: Source file name
  - `sections`: Configuration for processing different sections
  - `is_list_source`: Whether the entire source is a list (e.g., illustrations)

#### 2. Retrievers (`retrievers`)
Configuration for each retriever including:
- `description`: Human-readable description
- `search_kwargs`: Search parameters (e.g., `k` for number of results)
- `keywords`: Keywords that route queries to this retriever

#### 3. Collection (`collection`)
- `name_pattern`: Pattern for vector store collection names

#### 4. Prompts (`prompts`)
- `qa_system`: System prompt for Q&A chain
- `history_aware`: Prompt for history-aware query reformulation

### Adding New Data Sources

To add a new data source:

1. Add the source configuration under `data_sources.sources`:
```yaml
- name: "projects"
  file: "projects.json"
  sections:
    - name: "projects"
      field: "projects"
      is_list: true
      item_fields:
        - name
        - description
        - technologies
```

2. Add a corresponding retriever configuration:
```yaml
projects:
  description: "Good for answering questions about Nick's projects and portfolio."
  search_kwargs:
    k: 6
  keywords:
    - project
    - portfolio
    - built
    - created
    - developed
```

3. Run the build script to regenerate the unified data:
```bash
python backend/scripts/build_unified_data.py
```

### Modifying Prompts

To customize the AI assistant's behavior, modify the prompts in the `prompts` section. The prompts support placeholder variables like `{context}` and `{input}`.

### Configuration Loading

The configuration is automatically loaded by the `DataSourceConfig` class, which provides:
- Singleton pattern for consistent configuration access
- Fallback to default values if config file is missing
- Helper methods for accessing configuration values

### Usage in Code

```python
from backend.core.data_source_config import config

# Access data sources
sources = config.data_sources

# Access retrievers
retrievers = config.retrievers

# Get unified data path
path = config.get_unified_data_path()
```