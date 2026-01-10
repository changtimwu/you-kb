# AGENTS.md - Development Guidelines for You-KB

This file contains guidelines for agentic coding agents working on the You-KB YouTube AI Knowledge Base project.

## Build & Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install fastapi uvicorn  # Additional web dependencies
```

### Running the Application
```bash
# Start web server (main interface)
python3 app.py

# Command-line interface
python3 main.py <URL> [options]

# Knowledge base management
python3 main.py --kb-create <kb_name>                    # Create empty KB
python3 main.py --digest <kb_name> --source <path>      # Add documents to KB
python3 main.py --kb-list                                # List all KBs
python3 main.py --kb-info <kb_name>                      # Show KB details
python3 main.py --chat <kb_name>                          # Interactive chat
```

### Testing
```bash
# No formal test suite currently exists
# Test manually by running the application and verifying functionality

# Test individual components:
python3 -c "from downloader import list_videos; print(list_videos('https://youtube.com/watch?v=TEST', limit=1))"
python3 -c "from rag import create_kb, digest_documents; print('KB creation test passed')"

# Test new digest functionality:
python3 main.py --kb-create test_kb
python3 main.py --digest test_kb --source test.txt --pattern "*.txt"
python3 main.py --kb-list
```

### Linting & Code Quality
```bash
# No formal linting configured
# Manual code review required
# Consider adding: flake8, black, isort for future development
```

## Code Style Guidelines

### Import Organization
- Standard library imports first (os, sys, time, etc.)
- Third-party imports second (yt_dlp, google.generativeai, etc.)
- Local application imports last (from downloader import, from rag import)
- Group imports by type with blank lines between groups
- Use explicit imports over `import *`
- Import modules at the top of files, not inside functions (except conditional imports)

### Formatting & Structure
- Use 4 spaces for indentation (no tabs)
- Maximum line length: ~100 characters
- Use descriptive variable names (e.g., `video_info` not `vi`)
- Function names should be snake_case with descriptive verbs
- Class names should be PascalCase (if any classes are added)
- Constants should be UPPER_SNAKE_CASE

### Type Hints
- No formal type hints currently used
- Consider adding type hints for new functions using Python 3.5+ syntax
- Focus on function parameters and return values

### Docstrings
- Use triple quotes for docstrings
- Include brief description, parameters, and return values
- Follow Google-style or simple format:
```python
def download_subtitles(url, output_dir, lang='en'):
    """
    Downloads subtitles for a given YouTube URL.
    
    Args:
        url: YouTube video/playlist URL
        output_dir: Directory to save subtitles
        lang: Language code (default: 'en')
    
    Returns:
        Dictionary with download status and info
    """
```

### Error Handling
- Use try-except blocks for external API calls and file operations
- Print informative error messages for debugging
- Return None or empty dicts for expected failures
- Use specific exception types when possible
- Include error context in error messages

### Naming Conventions
- Functions: `snake_case_with_descriptive_verbs` (e.g., `download_subtitles`, `parse_vtt`)
- Variables: `snake_case` (e.g., `video_url`, `output_dir`, `api_key`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_LANGUAGE`, `MAX_WORKERS`)
- File names: `snake_case.py` (e.g., `downloader.py`, `transcribe.py`)
- Private functions: prefix with underscore (e.g., `_get_video_info`)

### API Integration Patterns
- Store API keys in separate files (never hardcode)
- Use configuration at module level for API clients
- Handle rate limits and API errors gracefully
- Provide fallback mechanisms (e.g., auto-generated subtitles)

### File I/O Patterns
- Always check if directories exist before creating files
- Use `os.path.join()` for cross-platform compatibility
- Handle FileNotFoundError for optional files
- Use context managers (`with open(...)`) for file operations

### Parallel Processing
- Use `concurrent.futures.ThreadPoolExecutor` for I/O-bound tasks
- Limit workers to reasonable numbers (5-10 for YouTube operations)
- Use tqdm for progress bars in long-running operations
- Handle exceptions in parallel tasks gracefully

### YouTube-Specific Patterns
- Use yt-dlp for all YouTube operations
- Handle both individual videos and playlists/channels
- Check subtitle availability before downloading
- Use iOS client to avoid JavaScript runtime issues
- Extract video IDs from filenames for citation generation

### Web Application Patterns
- Use FastAPI for web endpoints
- Return structured JSON responses
- Handle HTTP status codes appropriately
- Use Pydantic models for request/response validation
- Include CORS headers if needed for frontend integration

### Database Patterns
- Use LanceDB for vector storage
- Create/drop tables for knowledge base updates
- Store embeddings with metadata (video_id, timestamp, source)
- Use pandas for data manipulation before database operations

### Constants & Configuration
- Default language: `'en'`
- Default output directory: `'downloads'`
- Database path: `'.lancedb'`
- Max workers for parallel operations: 5-10
- Chunk size for text processing: 1000 characters
- Embedding model: `'models/text-embedding-004'`

## Development Workflow

1. **Feature Development**: Create functions in appropriate modules
2. **CLI Integration**: Add command-line options in `main.py` if needed
3. **Testing**: Manual testing with real YouTube URLs
4. **Documentation**: Update docstrings and comments
5. **Error Handling**: Add try-catch blocks for edge cases

## Key Dependencies

- `yt-dlp`: YouTube video/subtitle extraction
- `google.generativeai`: Gemini AI for embeddings and transcription
- `lancedb`: Vector database for RAG functionality
- `fastapi`: Web API framework
- `pandas`: Data manipulation
- `tqdm`: Progress bars

## Security Considerations

- Never commit API keys to version control
- Use environment variables or external key files
- Validate user input in web endpoints
- Sanitize file paths to prevent directory traversal
- Handle external API errors without exposing sensitive information