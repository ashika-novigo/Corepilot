from fastapi import FastAPI # pyright: ignore[reportMissingImports]

app=FastAPI()

@app.get('/')
def main():
    return {"data":"main file is running"}
