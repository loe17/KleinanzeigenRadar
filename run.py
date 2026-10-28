import uvicorn
from app.config import DEFAULT_HOST, DEFAULT_PORT

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=DEFAULT_HOST, port=DEFAULT_PORT, reload=False)
