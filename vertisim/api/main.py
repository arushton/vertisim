from fastapi import FastAPI, HTTPException
import numpy as np
from pydantic import BaseModel


app = FastAPI()

class NpyData(BaseModel):
    states: list

@app.get("/read-npy", response_model=NpyData)
def read_npy():
    try:
        data = np.load('../../../output/state.npy', allow_pickle=True).tolist()
        if len(data) == 0:
            return {"data": []}   
        return {"states": data}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# from fastapi import FastAPI, WebSocket, HTTPException
# from fastapi.templating import Jinja2Templates
# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler
# import numpy as np
# from pydantic import BaseModel

# app = FastAPI()

# templates = Jinja2Templates(directory="templates")

# # Your BaseModel
# class NpyData(BaseModel):
#     states: list

# # File watcher to handle reloads on .npy file change
# class ReloadHandler(FileSystemEventHandler):
#     def __init__(self, ws: WebSocket):
#         self.ws = ws

#     async def on_modified(self, event):
#         # Your file path
#         if event.src_path == "../../../output/state.npy":
#             await self.ws.send_text("reload")

# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     event_handler = ReloadHandler(websocket)
#     observer = Observer()
#     observer.schedule(event_handler, path=".", recursive=False)
#     observer.start()

# @app.get("/")
# def read_root():
#     try:
#         data = np.load('../../../output/state.npy', allow_pickle=True).tolist()
#         if len(data) == 0:
#             return templates.TemplateResponse("index.html", {"request": None, "states": []})
#         return templates.TemplateResponse("index.html", {"request": None, "states": data})
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
