import uuid
import shutil
from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from pathlib import Path

router = APIRouter(
    prefix="/upload",
    tags=["upload"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/image")
async def upload_image(request: Request, file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File is not a valid image.")

    file_extension = Path(file.filename).suffix
    file_name = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / file_name

    try:
        # Use shutil.copyfileobj to efficiently stream the file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        print(f"Error saving file: {e}") # For debugging
        raise HTTPException(status_code=500, detail="Could not save file.")
    finally:
        file.file.close()

    # Construct the full URL robustly
    base_url = str(request.base_url).rstrip('/')
    file_url = f"{base_url}/{UPLOAD_DIR}/{file_name}"
    
    return {"image_url": file_url}
