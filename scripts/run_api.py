"""Start the NEXUS Local API on 127.0.0.1 only."""
import uvicorn
from nexus_local.api.app import create_app

if __name__ == "__main__":
    uvicorn.run(create_app(), host="127.0.0.1", port=8400, log_level="info")
