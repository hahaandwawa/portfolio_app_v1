"""Backend entrypoint for packaged app. PyInstaller runs this; it starts uvicorn with port from env."""
import os
import uvicorn


def main() -> None:
    port = int(os.environ.get("BACKEND_PORT", "8001"))
    uvicorn.run("src.app.main:app", host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
