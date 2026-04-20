# LinkedIn Group Crawler

Project Python dùng Playwright để đăng nhập LinkedIn, crawl bài viết từ LinkedIn Group, chọn top post theo ngày, và expose API qua FastAPI để n8n gọi hằng ngày.

## Tính năng

- Đăng nhập LinkedIn bằng Playwright sync API.
- Lưu session vào `storage/linkedin_state.json` để tái sử dụng.
- Crawl bài viết từ LinkedIn Group URL với khả năng scroll nhiều lần.
- Parse các trường `author`, `content`, `posted_at_raw`, `likes`, `comments`, `reposts`, `post_url`.
- Chuẩn hóa thời gian tương đối LinkedIn như `5m`, `2h`, `1d`.
- Lọc bài viết theo `target_date` hoặc ngày hiện tại.
- Tính `score = likes + comments + reposts` và chọn top post.
- Expose API cho `GET /health`, `POST /login`, `POST /crawl-linkedin-group`.
- Có logging, xử lý lỗi, lưu screenshot khi crawl lỗi.

## Cấu trúc thư mục

```text
linkedin_group_crawler/
├─ app/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ config.py
│  ├─ schemas/
│  ├─ services/
│  ├─ utils/
│  └─ api/
├─ storage/
├─ data/
│  ├─ raw/
│  └─ output/
├─ tests/
├─ .env.example
├─ .gitignore
├─ README.md
└─ requirements.txt
```

## Yêu cầu

- Python 3.11+
- Playwright Chromium

## Cài đặt

### 1. Tạo virtualenv

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Cài package

```bash
pip install -r requirements.txt
```

### 3. Cài browser cho Playwright

```bash
playwright install
```

### 4. Tạo file `.env`

Copy `.env.example` thành `.env` rồi điền thông tin:

```env
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
HEADLESS=false
STATE_PATH=storage/linkedin_state.json
DEFAULT_SCROLL_TIMES=8
DEFAULT_SCROLL_DELAY_MS=2000
DEFAULT_MAX_ITEMS=50
API_KEY=optional-secret-key
HOST=0.0.0.0
PORT=8000
```

## Chạy local

Trong thư mục project `linkedin_group_crawler`:

```bash
uvicorn app.main:app --reload
```

Hoặc:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API

### 1. GET `/health`

Response:

```json
{
  "success": true,
  "message": "Service is healthy",
  "data": null
}
```

### 2. POST `/login`

Mục đích:

- Dùng `LINKEDIN_EMAIL` và `LINKEDIN_PASSWORD` trong `.env`.
- Mở trang login LinkedIn bằng Playwright.
- Cho phép xử lý thủ công nếu gặp captcha hoặc checkpoint.
- Lưu session vào `storage/linkedin_state.json`.

Ví dụ cURL:

```bash
curl -X POST "http://127.0.0.1:8000/login" \
  -H "Content-Type: application/json" \
  -d "{\"force_relogin\": false}"
```

Response thành công:

```json
{
  "success": true,
  "message": "LinkedIn session saved successfully",
  "state_path": "storage/linkedin_state.json"
}
```

### 3. POST `/crawl-linkedin-group`

Ví dụ request:

```bash
curl -X POST "http://127.0.0.1:8000/crawl-linkedin-group" \
  -H "Content-Type: application/json" \
  -d "{
    \"group_url\": \"https://www.linkedin.com/groups/xxxxxx/\",
    \"max_items\": 50,
    \"target_date\": \"2026-04-19\"
  }"
```

Response mẫu:

```json
{
  "success": true,
  "message": "Crawl completed successfully",
  "data": {
    "group_url": "https://www.linkedin.com/groups/xxxxxx/",
    "target_date": "2026-04-19",
    "total_posts_scraped": 18,
    "total_posts_in_target_date": 7,
    "top_post": {
      "author": "Nguyen Van A",
      "content": "Some content...",
      "posted_at_raw": "3h",
      "posted_at": "2026-04-19T18:30:00",
      "likes": 120,
      "comments": 25,
      "reposts": 5,
      "score": 150,
      "post_url": "https://www.linkedin.com/..."
    }
  }
}
```

## Lưu ý về session và cookie

- Session được lưu tại `storage/linkedin_state.json`.
- Không commit file này lên git.
- Nếu session hết hạn, gọi lại `POST /login`.
- LinkedIn có thể yêu cầu captcha hoặc checkpoint. Khi đó Playwright sẽ `pause()` để bạn xử lý thủ công.

## Lưu ý về selector LinkedIn

- DOM của LinkedIn thay đổi khá thường xuyên.
- Project này đã dùng nhiều selector fallback để dễ bảo trì.
- Nếu crawl không ra dữ liệu đúng, hãy inspect HTML thực tế của group và tinh chỉnh trong:
  - `app/services/crawler_service.py`
  - `app/services/parser_service.py`

## Debug

- Khi crawl lỗi, screenshot sẽ được lưu tại `data/raw/error.png`.
- HTML trang group gần nhất sẽ được lưu tại `data/raw/last_group_page.html` để phục vụ debug.

## Tích hợp với n8n

Luồng gợi ý:

1. Dùng HTTP Request node gọi `POST /crawl-linkedin-group` mỗi ngày.
2. Truyền `group_url`, `max_items`, `target_date`.
3. Lấy `data.top_post` để gửi sang Google Sheets, Slack, Telegram, hoặc database.
4. Nếu bạn đặt `API_KEY`, thêm header `x-api-key` trong node n8n.

## Chạy test

```bash
pytest
```

## Gợi ý vận hành

- Nên chạy `POST /login` thủ công trước lần đầu tiên.
- Sau đó để n8n gọi `POST /crawl-linkedin-group` hằng ngày.
- Nếu dùng server thật, hãy bật `HEADLESS=true` sau khi login ổn định.
