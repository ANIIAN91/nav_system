"""
个人主页及导航系统 - FastAPI 后端
"""
import os
import json
import uuid
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlparse, urljoin

import httpx
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import markdown
from jose import JWTError, jwt
from passlib.context import CryptContext

# 配置
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ARTICLES_DIR = BASE_DIR / "articles"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时

# 密码加密上下文（提前初始化用于启动时哈希）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 安全配置 - 通过环境变量设置
SECRET_KEY = os.getenv("SECRET_KEY")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

# 支持两种密码配置方式：
# 1. ADMIN_PASSWORD_HASH - 直接传入 bcrypt 哈希值（生产环境推荐）
# 2. ADMIN_PASSWORD - 传入明文密码，启动时自动哈希（开发/测试环境）
_password_hash = os.getenv("ADMIN_PASSWORD_HASH")
_password_plain = os.getenv("ADMIN_PASSWORD")

if _password_hash and _password_hash.startswith("$2"):
    ADMIN_PASSWORD_HASH = _password_hash
elif _password_plain:
    print(f"[INFO] 检测到 ADMIN_PASSWORD，正在自动生成哈希...")
    ADMIN_PASSWORD_HASH = pwd_context.hash(_password_plain)
    print(f"[INFO] 密码哈希已生成")
else:
    ADMIN_PASSWORD_HASH = None

def validate_security_config():
    """验证安全配置"""
    errors = []

    if not SECRET_KEY:
        errors.append("SECRET_KEY 环境变量未设置")
    elif len(SECRET_KEY) < 16:
        errors.append("SECRET_KEY 太短，建议至少 32 字符")

    if not ADMIN_USERNAME:
        errors.append("ADMIN_USERNAME 环境变量未设置")

    if not ADMIN_PASSWORD_HASH:
        errors.append("需要设置 ADMIN_PASSWORD 或 ADMIN_PASSWORD_HASH")

    return errors

# 启动时验证配置
_security_errors = validate_security_config()
if _security_errors:
    print("=" * 60)
    print("安全配置错误 - 服务无法启动")
    print("=" * 60)
    for err in _security_errors:
        print(f"  - {err}")
    print()
    print("请设置以下环境变量：")
    print("  export SECRET_KEY='your-random-secret-key'")
    print("  export ADMIN_USERNAME='your-username'")
    print("  export ADMIN_PASSWORD='your-password'  # 明文密码，自动哈希")
    print()
    print("或使用预生成的哈希（生产环境推荐）：")
    print("  export ADMIN_PASSWORD_HASH='$2b$12$...'")
    print("=" * 60)
    import sys
    sys.exit(1)

app = FastAPI(title="个人主页导航系统")

# 静态文件和模板
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# 安全认证
security = HTTPBearer(auto_error=False)

# 数据模型
class LoginRequest(BaseModel):
    username: str
    password: str

class LinkItem(BaseModel):
    id: Optional[str] = None
    title: str
    url: str
    icon: Optional[str] = None

class CategoryItem(BaseModel):
    name: str
    auth_required: bool = False
    links: List[LinkItem] = []

class LinksData(BaseModel):
    categories: List[CategoryItem] = []

class FaviconRequest(BaseModel):
    url: str

class SiteSettings(BaseModel):
    icp: Optional[str] = ""
    copyright: Optional[str] = ""
    article_page_title: Optional[str] = "文章"
    site_title: Optional[str] = "个人主页导航"
    link_size: Optional[str] = "medium"  # small, medium, large
    protected_article_paths: Optional[List[str]] = []  # 需要登录才能查看的文章目录

class ArticleSyncRequest(BaseModel):
    path: str  # 文章保存路径，如 "notes/my-article.md"
    content: str  # Markdown 内容
    title: Optional[str] = None  # 文章标题
    tags: Optional[List[str]] = []  # 标签列表
    frontmatter: Optional[dict] = None  # frontmatter 元数据

# 工具函数
def load_settings() -> dict:
    """加载站点设置"""
    settings_file = DATA_DIR / "settings.json"
    if settings_file.exists():
        with open(settings_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"icp": "", "copyright": "", "article_page_title": "文章"}

def save_settings(data: dict):
    """保存站点设置"""
    settings_file = DATA_DIR / "settings.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_links() -> dict:
    """加载导航链接数据"""
    links_file = DATA_DIR / "links.json"
    if links_file.exists():
        with open(links_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"categories": []}

def save_links(data: dict):
    """保存导航链接数据"""
    links_file = DATA_DIR / "links.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(links_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建 JWT Token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[str]:
    """验证 JWT Token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        return username
    except JWTError:
        return None

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """获取当前用户（可选认证）"""
    if credentials is None:
        return None
    return verify_token(credentials.credentials)

async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """要求认证"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="未登录")
    username = verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    return username

# 登录失败计数器（简单的内存限流）
from collections import defaultdict
import time

login_attempts = defaultdict(list)  # IP -> [timestamp, ...]
MAX_LOGIN_ATTEMPTS = 5  # 最大尝试次数
LOGIN_WINDOW_SECONDS = 300  # 5分钟窗口
LOCKOUT_SECONDS = 900  # 锁定15分钟

def check_rate_limit(ip: str) -> tuple[bool, int]:
    """检查登录速率限制，返回 (是否允许, 剩余锁定秒数)"""
    now = time.time()
    # 清理过期记录
    login_attempts[ip] = [t for t in login_attempts[ip] if now - t < LOCKOUT_SECONDS]

    if len(login_attempts[ip]) >= MAX_LOGIN_ATTEMPTS:
        oldest = min(login_attempts[ip])
        remaining = int(LOCKOUT_SECONDS - (now - oldest))
        if remaining > 0:
            return False, remaining
        # 锁定期已过，清空记录
        login_attempts[ip] = []

    return True, 0

def record_failed_login(ip: str):
    """记录失败的登录尝试"""
    login_attempts[ip].append(time.time())

def clear_login_attempts(ip: str):
    """登录成功后清除记录"""
    login_attempts[ip] = []

# 认证接口
@app.post("/api/auth/login")
async def login(request: LoginRequest, req: Request):
    """用户登录"""
    client_ip = req.client.host if req.client else "unknown"

    # 检查速率限制
    allowed, lockout_remaining = check_rate_limit(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"登录尝试次数过多，请在 {lockout_remaining} 秒后重试"
        )

    # 验证用户名
    if request.username != ADMIN_USERNAME:
        record_failed_login(client_ip)
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 使用 bcrypt 验证密码
    if not pwd_context.verify(request.password, ADMIN_PASSWORD_HASH):
        record_failed_login(client_ip)
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 登录成功，清除失败记录
    clear_login_attempts(client_ip)

    access_token = create_access_token(
        data={"sub": request.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/logout")
async def logout():
    """用户登出"""
    return {"message": "已登出"}

@app.get("/api/auth/me")
async def get_me(username: str = Depends(require_auth)):
    """获取当前用户信息"""
    return {"username": username}

# 导航接口
@app.get("/api/links")
async def get_links(current_user: Optional[str] = Depends(get_current_user)):
    """获取导航链接（根据登录状态过滤）"""
    data = load_links()
    if current_user is None:
        # 未登录用户只能看到不需要认证的分组
        data["categories"] = [
            cat for cat in data.get("categories", [])
            if not cat.get("auth_required", False)
        ]
    return data

@app.post("/api/links")
async def add_link(category_name: str, link: LinkItem, username: str = Depends(require_auth)):
    """添加导航链接"""
    data = load_links()
    link.id = str(uuid.uuid4())

    for cat in data.get("categories", []):
        if cat["name"] == category_name:
            cat["links"].append(link.dict())
            save_links(data)
            return {"message": "添加成功", "link": link}

    # 分类不存在，创建新分类
    new_category = {"name": category_name, "auth_required": False, "links": [link.dict()]}
    data.setdefault("categories", []).append(new_category)
    save_links(data)
    return {"message": "添加成功", "link": link}

@app.put("/api/links/{link_id}")
async def update_link(link_id: str, link: LinkItem, username: str = Depends(require_auth)):
    """修改导航链接"""
    data = load_links()

    for cat in data.get("categories", []):
        for i, l in enumerate(cat.get("links", [])):
            if l.get("id") == link_id:
                link.id = link_id
                cat["links"][i] = link.dict()
                save_links(data)
                return {"message": "修改成功", "link": link}

    raise HTTPException(status_code=404, detail="链接不存在")

@app.delete("/api/links/{link_id}")
async def delete_link(link_id: str, username: str = Depends(require_auth)):
    """删除导航链接"""
    data = load_links()

    for cat in data.get("categories", []):
        for i, l in enumerate(cat.get("links", [])):
            if l.get("id") == link_id:
                del cat["links"][i]
                save_links(data)
                return {"message": "删除成功"}

    raise HTTPException(status_code=404, detail="链接不存在")

@app.post("/api/categories")
async def add_category(category: CategoryItem, username: str = Depends(require_auth)):
    """添加分类"""
    data = load_links()
    for cat in data.get("categories", []):
        if cat["name"] == category.name:
            raise HTTPException(status_code=400, detail="分类已存在")

    data.setdefault("categories", []).append(category.dict())
    save_links(data)
    return {"message": "添加成功", "category": category}

@app.put("/api/categories/{category_name}")
async def update_category(category_name: str, category: CategoryItem, username: str = Depends(require_auth)):
    """更新分类"""
    data = load_links()

    # 检查新名称是否与其他分类冲突
    if category.name != category_name:
        for cat in data.get("categories", []):
            if cat["name"] == category.name:
                raise HTTPException(status_code=400, detail="分类名称已存在")

    for cat in data.get("categories", []):
        if cat["name"] == category_name:
            cat["name"] = category.name
            cat["auth_required"] = category.auth_required
            save_links(data)
            return {"message": "更新成功", "category": category}

    raise HTTPException(status_code=404, detail="分类不存在")

@app.delete("/api/categories/{category_name}")
async def delete_category(category_name: str, username: str = Depends(require_auth)):
    """删除分类"""
    data = load_links()
    for i, cat in enumerate(data.get("categories", [])):
        if cat["name"] == category_name:
            del data["categories"][i]
            save_links(data)
            return {"message": "删除成功"}

    raise HTTPException(status_code=404, detail="分类不存在")

# 分类排序
class ReorderRequest(BaseModel):
    direction: str  # up 或 down

@app.post("/api/categories/{category_name}/reorder")
async def reorder_category(category_name: str, request: ReorderRequest, username: str = Depends(require_auth)):
    """调整分类顺序"""
    data = load_links()
    categories = data.get("categories", [])

    for i, cat in enumerate(categories):
        if cat["name"] == category_name:
            if request.direction == "up" and i > 0:
                categories[i], categories[i-1] = categories[i-1], categories[i]
            elif request.direction == "down" and i < len(categories) - 1:
                categories[i], categories[i+1] = categories[i+1], categories[i]
            else:
                return {"message": "无法移动"}
            save_links(data)
            return {"message": "移动成功"}

    raise HTTPException(status_code=404, detail="分类不存在")

# 链接排序
@app.post("/api/links/{link_id}/reorder")
async def reorder_link(link_id: str, request: ReorderRequest, username: str = Depends(require_auth)):
    """调整链接顺序"""
    data = load_links()

    for cat in data.get("categories", []):
        links = cat.get("links", [])
        for i, link in enumerate(links):
            if link.get("id") == link_id:
                if request.direction == "up" and i > 0:
                    links[i], links[i-1] = links[i-1], links[i]
                elif request.direction == "down" and i < len(links) - 1:
                    links[i], links[i+1] = links[i+1], links[i]
                else:
                    return {"message": "无法移动"}
                save_links(data)
                return {"message": "移动成功"}

    raise HTTPException(status_code=404, detail="链接不存在")

# 导航数据导出
@app.get("/api/links/export")
async def export_links(username: str = Depends(require_auth)):
    """导出导航数据"""
    data = load_links()
    return {
        "version": 1,
        "appName": "HomePage-Export",
        "exportTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data": data
    }

# 导航数据导入
class ImportRequest(BaseModel):
    data: dict
    format: str = "native"  # native 或 sunpanel

@app.post("/api/links/import")
async def import_links(request: ImportRequest, username: str = Depends(require_auth)):
    """导入导航数据"""
    if request.format == "sunpanel":
        # 解析 SunPanel 格式
        try:
            sunpanel_data = request.data
            icons = sunpanel_data.get("icons", [])
            categories = []

            for group in icons:
                category_name = group.get("title", "未分类")
                links = []

                for item in group.get("children", []):
                    link = {
                        "id": str(uuid.uuid4()),
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "icon": None
                    }
                    links.append(link)

                # Me 分类设为私密
                auth_required = category_name == "Me"
                categories.append({
                    "name": category_name,
                    "auth_required": auth_required,
                    "links": links
                })

            new_data = {"categories": categories}
            save_links(new_data)
            return {"message": f"导入成功，共 {len(categories)} 个分类", "data": new_data}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"SunPanel 格式解析失败: {str(e)}")
    else:
        # 原生格式
        try:
            import_data = request.data
            if "data" in import_data:
                import_data = import_data["data"]
            if "categories" not in import_data:
                raise ValueError("缺少 categories 字段")
            save_links(import_data)
            return {"message": "导入成功", "data": import_data}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"导入失败: {str(e)}")

# 站点设置接口
@app.get("/api/settings")
async def get_settings():
    """获取站点设置"""
    return load_settings()

@app.put("/api/settings")
async def update_settings(settings: SiteSettings, username: str = Depends(require_auth)):
    """更新站点设置"""
    data = load_settings()
    data.update(settings.dict())
    save_settings(data)
    return {"message": "设置已保存", "settings": data}

# 文章接口
def is_path_protected(path: str, protected_paths: List[str]) -> bool:
    """检查路径是否在受保护目录中"""
    path_parts = Path(path).parts
    for protected in protected_paths:
        protected_parts = Path(protected).parts
        if len(path_parts) >= len(protected_parts):
            if path_parts[:len(protected_parts)] == protected_parts:
                return True
    return False

@app.get("/api/articles")
async def list_articles(current_user: Optional[str] = Depends(get_current_user)):
    """获取文章列表（根据登录状态过滤受保护目录，按创建时间排序）"""
    settings = load_settings()
    protected_paths = settings.get("protected_article_paths", [])

    articles = []
    if ARTICLES_DIR.exists():
        for path in ARTICLES_DIR.rglob("*.md"):
            rel_path = path.relative_to(ARTICLES_DIR)
            rel_path_str = str(rel_path)

            # 如果未登录且路径受保护，跳过
            if current_user is None and is_path_protected(rel_path_str, protected_paths):
                continue

            # 获取文件创建时间（优先使用 ctime，如果不可用则使用 mtime）
            stat = path.stat()
            # 在 Linux 上 st_ctime 是元数据修改时间，st_mtime 是内容修改时间
            # 在 Windows 上 st_ctime 是创建时间
            # 这里使用 st_mtime 作为排序依据，因为它更可靠
            created_time = stat.st_mtime

            articles.append({
                "path": rel_path_str,
                "title": path.stem,
                "category": str(rel_path.parent) if rel_path.parent != Path(".") else None,
                "protected": is_path_protected(rel_path_str, protected_paths),
                "created_time": created_time
            })

    # 按创建时间降序排序（最新的在前）
    articles.sort(key=lambda x: x["created_time"], reverse=True)

    return {"articles": articles}

@app.get("/api/articles/{path:path}")
async def get_article(path: str, current_user: Optional[str] = Depends(get_current_user)):
    """获取文章内容"""
    # 安全校验：防止路径遍历
    article_path = (ARTICLES_DIR / path).resolve()
    if not str(article_path).startswith(str(ARTICLES_DIR.resolve())):
        raise HTTPException(status_code=403, detail="禁止访问")

    # 检查权限
    settings = load_settings()
    protected_paths = settings.get("protected_article_paths", [])
    if current_user is None and is_path_protected(path, protected_paths):
        raise HTTPException(status_code=401, detail="需要登录才能查看此文章")

    if not article_path.exists() or not article_path.suffix == ".md":
        raise HTTPException(status_code=404, detail="文章不存在")

    with open(article_path, "r", encoding="utf-8") as f:
        content = f.read()

    html_content = markdown.markdown(
        content,
        extensions=["fenced_code", "tables", "toc", "codehilite", "nl2br", "sane_lists"]
    )
    return {"path": path, "content": content, "html": html_content}

# 文章同步接口
@app.post("/api/articles/sync")
async def sync_article(request: ArticleSyncRequest, username: str = Depends(require_auth)):
    """同步文章（从 Obsidian 等工具推送）"""
    # 安全校验：防止路径遍历
    safe_path = request.path.replace("..", "").lstrip("/")
    if not safe_path.endswith(".md"):
        safe_path += ".md"

    article_path = (ARTICLES_DIR / safe_path).resolve()
    if not str(article_path).startswith(str(ARTICLES_DIR.resolve())):
        raise HTTPException(status_code=403, detail="禁止访问该路径")

    # 确保目录存在
    article_path.parent.mkdir(parents=True, exist_ok=True)

    # 构建文章内容
    content = request.content

    # 如果有 frontmatter，添加到内容开头
    if request.frontmatter:
        import yaml
        frontmatter_str = yaml.dump(request.frontmatter, allow_unicode=True, default_flow_style=False)
        content = f"---\n{frontmatter_str}---\n\n{content}"

    # 保存文件
    with open(article_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "message": "文章同步成功",
        "path": safe_path,
        "title": request.title or article_path.stem
    }

@app.delete("/api/articles/{path:path}")
async def delete_article(path: str, username: str = Depends(require_auth)):
    """删除文章"""
    # 安全校验：防止路径遍历
    article_path = (ARTICLES_DIR / path).resolve()
    if not str(article_path).startswith(str(ARTICLES_DIR.resolve())):
        raise HTTPException(status_code=403, detail="禁止访问")

    if not article_path.exists():
        raise HTTPException(status_code=404, detail="文章不存在")

    article_path.unlink()
    return {"message": "文章已删除"}

# SSRF 防护：URL 验证
import ipaddress
import socket

def is_safe_url(url: str) -> tuple[bool, str]:
    """
    验证 URL 是否安全，防止 SSRF 攻击
    返回 (是否安全, 错误信息)
    """
    try:
        parsed = urlparse(url)

        # 只允许 http 和 https 协议
        if parsed.scheme not in ('http', 'https'):
            return False, f"不支持的协议: {parsed.scheme}，只允许 http/https"

        # 获取主机名
        hostname = parsed.hostname
        if not hostname:
            return False, "无效的 URL：缺少主机名"

        # 阻止常见的内网主机名
        blocked_hostnames = [
            'localhost', '127.0.0.1', '0.0.0.0',
            'metadata.google.internal',  # GCP 元数据
            '169.254.169.254',  # AWS/Azure/GCP 元数据
            'metadata.azure.com',
        ]
        if hostname.lower() in blocked_hostnames:
            return False, f"禁止访问内部地址: {hostname}"

        # 解析 DNS 并检查 IP 地址
        try:
            ip_addresses = socket.getaddrinfo(hostname, None)
            for addr_info in ip_addresses:
                ip_str = addr_info[4][0]
                ip = ipaddress.ip_address(ip_str)

                # 阻止私有 IP、回环地址、链路本地地址
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False, f"禁止访问内部/私有 IP 地址: {ip_str}"
        except socket.gaierror:
            # DNS 解析失败，允许继续（可能是临时问题）
            pass

        return True, ""
    except Exception as e:
        return False, f"URL 验证失败: {str(e)}"

# 获取网站图标
@app.post("/api/fetch-favicon")
async def fetch_favicon(request: FaviconRequest, username: str = Depends(require_auth)):
    """从网站获取 favicon 并保存"""
    url = request.url
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urlparse(url)

    # SSRF 防护：验证 URL 安全性
    is_safe, error_msg = is_safe_url(url)
    if not is_safe:
        raise HTTPException(status_code=400, detail=error_msg)

    base_url = f"{parsed.scheme}://{parsed.netloc}"
    icons_dir = BASE_DIR / "static" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    # 尝试获取图标的多种方式
    icon_urls = [
        f"{base_url}/favicon.ico",
        f"{base_url}/favicon.png",
        f"{base_url}/apple-touch-icon.png",
    ]

    # 尝试从 HTML 中解析图标链接
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code == 200:
                html = response.text
                # 查找 link 标签中的图标
                patterns = [
                    r'<link[^>]*rel=["\'](?:shortcut )?icon["\'][^>]*href=["\']([^"\']+)["\']',
                    r'<link[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\'](?:shortcut )?icon["\']',
                    r'<link[^>]*rel=["\']apple-touch-icon["\'][^>]*href=["\']([^"\']+)["\']',
                ]
                for pattern in patterns:
                    match = re.search(pattern, html, re.IGNORECASE)
                    if match:
                        icon_url = match.group(1)
                        if not icon_url.startswith('http'):
                            icon_url = urljoin(base_url, icon_url)
                        # 验证解析出的图标 URL
                        if is_safe_url(icon_url)[0]:
                            icon_urls.insert(0, icon_url)
    except Exception:
        pass

    # 尝试下载图标
    for icon_url in icon_urls:
        # SSRF 防护：验证每个图标 URL
        if not is_safe_url(icon_url)[0]:
            continue

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(icon_url, headers={"User-Agent": "Mozilla/5.0"})
                if response.status_code == 200 and len(response.content) > 100:
                    # 生成文件名
                    content_type = response.headers.get("content-type", "")
                    ext = ".ico"
                    if "png" in content_type or icon_url.endswith(".png"):
                        ext = ".png"
                    elif "svg" in content_type or icon_url.endswith(".svg"):
                        ext = ".svg"
                    elif "jpeg" in content_type or "jpg" in content_type:
                        ext = ".jpg"

                    # 使用域名作为文件名
                    filename = parsed.netloc.replace(".", "_") + ext
                    filepath = icons_dir / filename

                    # 保存图标
                    with open(filepath, "wb") as f:
                        f.write(response.content)

                    return {"icon": filename, "message": "图标获取成功"}
        except Exception:
            continue

    return {"icon": None, "message": "未能获取图标"}

# 页面路由
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """导航主页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/articles", response_class=HTMLResponse)
async def articles_page(request: Request):
    """文章列表页"""
    return templates.TemplateResponse("article.html", {"request": request})

@app.get("/articles/{path:path}", response_class=HTMLResponse)
async def article_page(request: Request, path: str):
    """文章详情页"""
    return templates.TemplateResponse("article.html", {"request": request, "path": path})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
