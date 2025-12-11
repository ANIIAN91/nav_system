# 欢迎使用

欢迎使用个人主页导航系统！

## 功能介绍

本系统提供以下功能：

1. **导航站** - 分类展示常用链接
2. **文章展示** - 支持 Markdown 文章在线展示
3. **权限控制** - 部分内容需登录后才可见

## 使用方法

### 添加链接

1. 点击右上角「登录」按钮
2. 输入用户名和密码（默认: admin / admin123）
3. 点击「管理」按钮
4. 选择分类并填写链接信息

### 添加文章

将 Markdown 文件放入 `articles/` 目录即可自动识别。

## 技术栈

- 前端：HTML + CSS + JavaScript
- 后端：Python FastAPI
- 数据存储：JSON / Markdown 文件

```python
# 示例代码
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

## 更多信息

请参考项目 RESET_GUIDE.md 文档。
