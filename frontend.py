from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import requests
import uvicorn

app = FastAPI()

# Backend URL
BACKEND_URL = "http://localhost:8000/predict/"

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """Uploads an image and sends it to the backend for prediction."""
    try:
        image_bytes = await file.read()
        files = {"file": (file.filename, image_bytes, file.content_type)}
        response = requests.post(BACKEND_URL, files=files)

        if response.status_code == 200:
            return JSONResponse(content=response.json())
        else:
            return JSONResponse(content={"error": "Backend error"}, status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Use different port than backend
