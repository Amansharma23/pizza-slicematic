# SliceMatic Local Setup

This project can run in two local modes:

- `app.py`: Gradio UI mounted on FastAPI. Default URL: `http://127.0.0.1:7860/`.
- `server.py`: custom HTML frontend from `web/` plus the same FastAPI API. Default URL: `http://127.0.0.1:7861/`.

## Prerequisites

- Python 3.12 or newer.
- `uv` is recommended.
- Optional: Node.js only if you need to work on the PowerPoint generator in `ppt/slicematic.js`.

## Recommended Run With uv

From the repository root:

```powershell
uv run python app.py
```

Open:

```text
http://127.0.0.1:7860/
```

To run the custom HTML frontend instead:

```powershell
uv run python server.py
```

Open:

```text
http://127.0.0.1:7861/
```

The API docs for the custom frontend are available at:

```text
http://127.0.0.1:7861/docs
```

## Windows Fallback Without uv

If `uv` is not installed but the Windows Python launcher is available, create a local virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open:

```text
http://127.0.0.1:7860/
```

To run the custom HTML frontend with the same virtual environment:

```powershell
.\.venv\Scripts\python.exe server.py
```

## Useful Checks

Run the test suite:

```powershell
uv run pytest
```

Or, with the fallback virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest
```

Check the health endpoint while the app is running:

```powershell
Invoke-RestMethod http://127.0.0.1:7860/api/health
```

Expected response:

```json
{ "status": "ok", "brand": "SliceMatic" }
```

## Local Runtime Notes

- Local orders are appended to `database/orders_log.txt`.
- Menu files are loaded from `menu_data/`.
- Set `PORT` to override the default port:

```powershell
$env:PORT = "8000"
.\.venv\Scripts\python.exe app.py
```

Then open `http://127.0.0.1:8000/`.
