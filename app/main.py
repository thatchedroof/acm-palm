# %%
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.generativeai as palm
from dotenv import load_dotenv
from uploads import UploadType
from pypdf import PdfReader
import uvicorn
import os
import markdown


load_dotenv()
PALM_API_KEY = os.getenv("API_KEY")

palm.configure(api_key=PALM_API_KEY)
os.makedirs("./static", exist_ok=True)
os.makedirs("./uploads", exist_ok=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

PROMPT = "Describe the following text"
cache: dict[str, str] = {}


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "prompt": PROMPT}
    )


@app.post("/", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile):
    content: str = ""
    try:
        contents = file.file.read()
        path = f"uploads/{file.filename}"
        with open(path, "wb") as f:
            f.write(contents)

            if file.content_type == UploadType.PDF.value:
                reader = PdfReader(path)
                content = reader.pages[0].extract_text()
            else:
                content = contents.decode()

            content = content[0:500] + "..."

            if content in cache:
                return templates.TemplateResponse(
                    "file.html",
                    {
                        "request": request,
                        "file_name": file.filename,
                        "content": content,
                        "ai": cache[content],
                    },
                )

    except Exception as e:
        return templates.TemplateResponse(
            "error.html", {"request": request, "error": e}
        )
    finally:
        file.file.close()

    if content == "":
        content = "Failed to extract text"
        res = ""
        return templates.TemplateResponse(
            "file.html",
            {
                "request": request,
                "file_name": file.filename,
                "content": content,
                "ai": res,
                "prompt": PROMPT,
            },
        )

    res = content
    for i in range(0, 10):
        print(res)
        res = palm.chat(
            messages=f"Translate the following text to German.\n\n{res}",
            examples=(
                "Translate the following text to German.\n\nHello! How are you?",
                "Hallo! Wie geht's?",
            ),
        ).last
        print(res)
        res = palm.chat(
            messages=f"Translate the following text to English.\n\n{res}",
            examples=(
                "Translate the following text to English.\n\nHallo! Wie geht's?",
                "Hello! How are you?",
            ),
        ).last

    res = markdown.markdown(res)

    cache[content] = res

    return templates.TemplateResponse(
        "file.html",
        {
            "request": request,
            "file_name": file.filename,
            "content": content,
            "ai": res,
            "prompt": PROMPT,
        },
    )


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)

# %%
