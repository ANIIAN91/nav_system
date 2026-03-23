#!/usr/bin/env python3
"""
Nav System 文章批量同步脚本。

功能：
1. 扫描 Obsidian 仓库目录
2. 比较文件哈希值，只同步更改的文件
3. 将文件上传到 Nav System
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None
    print("警告: 未安装 PyYAML，frontmatter 解析功能受限")

try:
    from scripts.nav_client import NavClient, NavClientError
except ImportError:
    from nav_client import NavClient, NavClientError


class ArticleSyncer:
    """文章同步器。"""

    def __init__(self, api_url: str, jwt_token: str, vault_path: str, target_path: str = ""):
        self.api_url = api_url.rstrip("/")
        self.vault_path = Path(vault_path)
        self.target_path = target_path
        self.sync_state_file = self.vault_path / ".nav_sync_state.json"
        self.sync_state = self.load_sync_state()
        self.client = NavClient(self.api_url, jwt_token)

    def close(self) -> None:
        """关闭 HTTP 客户端。"""
        self.client.close()

    def load_sync_state(self) -> Dict[str, str]:
        """加载同步状态（文件哈希记录）。"""
        if self.sync_state_file.exists():
            try:
                return json.loads(self.sync_state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def save_sync_state(self) -> None:
        """保存同步状态。"""
        self.sync_state_file.write_text(
            json.dumps(self.sync_state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值。"""
        return hashlib.md5(file_path.read_bytes()).hexdigest()

    def parse_frontmatter(self, content: str) -> tuple[Optional[Dict], str]:
        """解析 frontmatter。"""
        match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
        if not match:
            return None, content

        frontmatter_str = match.group(1)
        body = content[match.end() :]

        if yaml:
            try:
                return yaml.safe_load(frontmatter_str), body
            except Exception:
                pass

        frontmatter = {}
        for line in frontmatter_str.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                frontmatter[key.strip()] = value.strip().strip("\"'")
        return frontmatter, body

    def extract_tags(self, content: str, frontmatter: Optional[Dict]) -> List[str]:
        """提取标签。"""
        tags = []
        if frontmatter and "tags" in frontmatter:
            frontmatter_tags = frontmatter["tags"]
            if isinstance(frontmatter_tags, list):
                tags.extend(frontmatter_tags)
            elif isinstance(frontmatter_tags, str):
                tags.extend([item.strip() for item in frontmatter_tags.split(",") if item.strip()])

        for tag in re.findall(r"#([\w\u4e00-\u9fa5]+)", content):
            if tag not in tags:
                tags.append(tag)
        return tags

    def sync_file(self, file_path: Path, force: bool = False) -> bool:
        """同步单个文件。"""
        rel_path = file_path.relative_to(self.vault_path)
        rel_path_str = str(rel_path)
        file_hash = self.get_file_hash(file_path)

        if not force and self.sync_state.get(rel_path_str) == file_hash:
            return False

        content = file_path.read_text(encoding="utf-8")
        frontmatter, body = self.parse_frontmatter(content)

        if self.target_path:
            save_path = f"{self.target_path}/{rel_path}"
        else:
            save_path = rel_path_str
        if save_path.endswith(".md"):
            save_path = save_path[:-3]

        data = {
            "path": save_path,
            "content": body,
            "title": frontmatter.get("title", file_path.stem) if frontmatter else file_path.stem,
            "tags": self.extract_tags(content, frontmatter),
            "frontmatter": frontmatter,
        }

        try:
            self.client.sync_article(data)
            self.sync_state[rel_path_str] = file_hash
            return True
        except NavClientError as exc:
            print(f"  错误: {exc}")
            return False
        except Exception as exc:
            print(f"  请求失败: {exc}")
            return False

    def scan_and_sync(
        self,
        patterns: List[str] | None = None,
        force: bool = False,
        exclude_patterns: List[str] | None = None,
    ) -> Dict[str, Any]:
        """扫描并同步文件。"""
        patterns = patterns or ["**/*.md"]
        exclude_patterns = exclude_patterns or [".obsidian/**", ".trash/**", ".git/**"]

        results = {"synced": [], "skipped": [], "failed": [], "total": 0}
        files_to_sync: list[Path] = []
        for pattern in patterns:
            for file_path in self.vault_path.glob(pattern):
                if not file_path.is_file():
                    continue
                rel_path = str(file_path.relative_to(self.vault_path))
                excluded = any(Path(rel_path).match(pattern.replace("**", "*")) for pattern in exclude_patterns)
                if not excluded:
                    files_to_sync.append(file_path)

        results["total"] = len(files_to_sync)
        print(f"找到 {len(files_to_sync)} 个文件")

        for index, file_path in enumerate(files_to_sync, 1):
            rel_path = file_path.relative_to(self.vault_path)
            print(f"[{index}/{len(files_to_sync)}] 处理: {rel_path}")
            try:
                synced = self.sync_file(file_path, force)
                if synced:
                    print("  ✓ 已同步")
                    results["synced"].append(str(rel_path))
                else:
                    print("  - 跳过（未更改）")
                    results["skipped"].append(str(rel_path))
            except Exception as exc:
                print(f"  ✗ 失败: {exc}")
                results["failed"].append(str(rel_path))

        self.save_sync_state()
        return results

    def test_connection(self) -> bool:
        """测试 API 连接。"""
        try:
            data = self.client.check_me()
            print(f"连接成功！用户: {data.get('username')}")
            return True
        except NavClientError as exc:
            print(f"连接失败: {exc}")
            return False
        except Exception as exc:
            print(f"连接错误: {exc}")
            return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Nav System 文章批量同步工具")
    parser.add_argument("--vault", "-v", required=True, help="Obsidian vault 路径")
    parser.add_argument(
        "--api",
        "-a",
        default=os.getenv("NAV_API_URL", "http://localhost:8001"),
        help="Nav System API 地址",
    )
    parser.add_argument("--token", "-t", default=os.getenv("NAV_JWT_TOKEN", ""), help="JWT Token")
    parser.add_argument("--target", "-d", default="", help="目标保存路径前缀")
    parser.add_argument("--pattern", "-p", action="append", help="文件匹配模式（可多次指定）")
    parser.add_argument("--exclude", "-e", action="append", help="排除模式（可多次指定）")
    parser.add_argument("--force", "-f", action="store_true", help="强制同步所有文件")
    parser.add_argument("--test", action="store_true", help="仅测试连接")
    args = parser.parse_args()

    if not args.token:
        print("错误: 请提供 JWT Token（--token 或 NAV_JWT_TOKEN 环境变量）")
        sys.exit(1)

    syncer = ArticleSyncer(
        api_url=args.api,
        jwt_token=args.token,
        vault_path=args.vault,
        target_path=args.target,
    )

    try:
        if args.test:
            sys.exit(0 if syncer.test_connection() else 1)

        print(f"API 地址: {args.api}")
        print(f"Vault 路径: {args.vault}")
        print(f"目标路径: {args.target or '(根目录)'}")
        print()

        if not syncer.test_connection():
            print("无法连接到 API，请检查配置")
            sys.exit(1)

        print()
        results = syncer.scan_and_sync(
            patterns=args.pattern,
            force=args.force,
            exclude_patterns=args.exclude,
        )

        print()
        print("=" * 50)
        print("同步完成！")
        print(f"  总计: {results['total']} 个文件")
        print(f"  已同步: {len(results['synced'])} 个")
        print(f"  跳过: {len(results['skipped'])} 个")
        print(f"  失败: {len(results['failed'])} 个")

        if results["failed"]:
            print()
            print("失败的文件:")
            for file_name in results["failed"]:
                print(f"  - {file_name}")
    finally:
        syncer.close()


if __name__ == "__main__":
    main()
