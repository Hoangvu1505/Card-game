import uvicorn
import socketio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# --- SỬA LẠI DÒNG NÀY ---
# Chỉ import 'sio', KHÔNG import 'app' vì app sẽ được tạo ở ngay bên dưới
from server_config import sio 
# ------------------------

# Tạo ứng dụng FastAPI tại đây
app = FastAPI()

# Bọc FastAPI bằng SocketIO
sio_app = socketio.ASGIApp(sio, app)

# Mount thư mục Static (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- IMPORT CÁC BỘ XỬ LÝ (HANDLERS) ---
# Việc import này sẽ kích hoạt code trong các file đó để đăng ký sự kiện với sio
import handlers.general
import handlers.caro
import handlers.tienlen
import handlers.blackjack

@app.get("/")
async def get():
    with open("templates/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000)) 
    # Lưu ý: chạy biến 'sio_app' chứ không phải 'app'
    uvicorn.run("main:sio_app", host="0.0.0.0", port=port, reload=False)