"""Backend entrypoint for packaged app. PyInstaller runs this; it starts uvicorn with port from env."""
import os
import uvicorn

# Import app directly so the frozen bundle can resolve 'src' (uvicorn's string-based
# import fails under PyInstaller).
from src.app.main import app


def main() -> None:
    port = int(os.environ.get("BACKEND_PORT", "8001"))
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
