#!/usr/bin/env python3
"""
Nav System 文章批量同步脚本

功能：
1. 扫描 Obsidian 仓库目录
2. 比较文件哈希值，只同步更改的文件
3. 将文件上传到 Nav System

使用方法：
    python sync_articles.py --vault /path/to/obsidian/vault --api http://localhost:8000 --token YOUR_JWT_TOKEN

或者使用环境变量：
    export NAV_API_URL=http://localhost:8000
    export NAV_JWT_TOKEN=your_token
    python sync_articles.py --vault /path/to/obsidian/vault
"""

import os
import sys
import json
import hashlib
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

try:
    import requests
except ImportError:
    print("请安装 requests 库: pip install requests")
    sys.exit(1)

try:
    import yaml
except ImportError:
    yaml = None
    print("警告: 未安装 PyYAML，frontmatter 解析功能受限")


class ArticleSyncer:
    """文章同步器"""

    def __init__(self, api_url: str, jwt_token: str, vault_path: str, target_path: str = ""):
        self.api_url = api_url.rstrip('/')
        self.jwt_token = jwt_token
        self.vault_path = Path(vault_path)
        self.target_path = target_path
        self.sync_state_file = self.vault_path / ".nav_sync_state.json"
        self.sync_state = self.load_sync_state()

    def load_sync_state(self) -> Dict[str, str]:
        """加载同步状态（文件哈希记录）"""
        if self.sync_state_file.exists():
            try:
                with open(self.sync_state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_sync_state(self):
        """保存同步状态"""
        with open(self.sync_state_file, 'w', encoding='utf-8') as f:
            json.dump(self.sync_state, f, ensure_ascii=False, indent=2)

    def get_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def parse_frontmatter(self, content: str) -> tuple[Optional[Dict], str]:
        """解析 frontmatter"""
        frontmatter_pattern = r'^---\n(.*?)\n---\n'
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if match:
            frontmatter_str = match.group(1)
            body = content[match.end():]

            if yaml:
                try:
                    frontmatter = yaml.safe_load(frontmatter_str)
                    return frontmatter, body
                except Exception:
                    pass

            # 简单解析
            frontmatter = {}
            for line in frontmatter_str.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip().strip('"\'')
            return frontmatter, body

        return None, content

    def extract_tags(self, content: str, frontmatter: Optional[Dict]) -> List[str]:
        """提取标签"""
        tags = []

        # 从 frontmatter 提取
        if frontmatter and 'tags' in frontmatter:
            fm_tags = frontmatter['tags']
            if isinstance(fm_tags, list):
                tags.extend(fm_tags)
            elif isinstance(fm_tags, str):
                tags.extend([t.strip() for t in fm_tags.split(',')])

        # 从内容中提取 #tag 格式
        tag_matches = re.findall(r'#([\w\u4e00-\u9fa5]+)', content)
        for tag in tag_matches:
            if tag not in tags:
                tags.append(tag)

        return tags

    def sync_file(self, file_path: Path, force: bool = False) -> bool:
        """同步单个文件"""
        rel_path = file_path.relative_to(self.vault_path)
        file_hash = self.get_file_hash(file_path)

        # 检查是否需要同步
        if not force and str(rel_path) in self.sync_state:
            if self.sync_state[str(rel_path)] == file_hash:
                return False  # 文件未更改

        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析 frontmatter
        frontmatter, body = self.parse_frontmatter(content)

        # 确定保存路径
        if self.target_path:
            save_path = f"{self.target_path}/{rel_path}"
        else:
            save_path = str(rel_path)

        # 移除 .md 后缀（API 会自动添加）
        if save_path.endswith('.md'):
            save_path = save_path[:-3]

        # 提取标签
        tags = self.extract_tags(content, frontmatter)

        # 构建请求数据
        data = {
            "path": save_path,
            "content": body,
            "title": frontmatter.get('title', file_path.stem) if frontmatter else file_path.stem,
            "tags": tags,
            "frontmatter": frontmatter
        }

        # 发送请求
        try:
            response = requests.post(
                f"{self.api_url}/api/articles/sync",
                json=data,
                headers={
                    "Authorization": f"Bearer {self.jwt_token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )

            if response.status_code in (200, 201):
                # 更新同步状态
                self.sync_state[str(rel_path)] = file_hash
                return True
            else:
                print(f"  错误: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"  请求失败: {e}")
            return False

    def scan_and_sync(self, patterns: List[str] = None, force: bool = False,
                      exclude_patterns: List[str] = None) -> Dict[str, Any]:
        """扫描并同步文件"""
        if patterns is None:
            patterns = ["**/*.md"]
        if exclude_patterns is None:
            exclude_patterns = [".obsidian/**", ".trash/**", ".git/**"]

        results = {
            "synced": [],
            "skipped": [],
            "failed": [],
            "total": 0
        }

        # 收集所有匹配的文件
        files_to_sync = []
        for pattern in patterns:
            for file_path in self.vault_path.glob(pattern):
                if file_path.is_file():
                    # 检查排除模式
                    rel_path = str(file_path.relative_to(self.vault_path))
                    excluded = False
                    for exclude in exclude_patterns:
                        if Path(rel_path).match(exclude.replace("**", "*")):
                            excluded = True
                            break
                    if not excluded:
                        files_to_sync.append(file_path)

        results["total"] = len(files_to_sync)
        print(f"找到 {len(files_to_sync)} 个文件")

        # 同步文件
        for i, file_path in enumerate(files_to_sync, 1):
            rel_path = file_path.relative_to(self.vault_path)
            print(f"[{i}/{len(files_to_sync)}] 处理: {rel_path}")

            try:
                synced = self.sync_file(file_path, force)
                if synced:
                    print(f"  ✓ 已同步")
                    results["synced"].append(str(rel_path))
                else:
                    print(f"  - 跳过（未更改）")
                    results["skipped"].append(str(rel_path))
            except Exception as e:
                print(f"  ✗ 失败: {e}")
                results["failed"].append(str(rel_path))

        # 保存同步状态
        self.save_sync_state()

        return results

    def test_connection(self) -> bool:
        """测试 API 连接"""
        try:
            response = requests.get(
                f"{self.api_url}/api/auth/me",
                headers={"Authorization": f"Bearer {self.jwt_token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                print(f"连接成功！用户: {data.get('username')}")
                return True
            else:
                print(f"连接失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"连接错误: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='Nav System 文章批量同步工具')
    parser.add_argument('--vault', '-v', required=True, help='Obsidian vault 路径')
    parser.add_argument('--api', '-a', default=os.getenv('NAV_API_URL', 'http://localhost:8000'),
                        help='Nav System API 地址')
    parser.add_argument('--token', '-t', default=os.getenv('NAV_JWT_TOKEN', ''),
                        help='JWT Token')
    parser.add_argument('--target', '-d', default='', help='目标保存路径前缀')
    parser.add_argument('--pattern', '-p', action='append', help='文件匹配模式（可多次指定）')
    parser.add_argument('--exclude', '-e', action='append', help='排除模式（可多次指定）')
    parser.add_argument('--force', '-f', action='store_true', help='强制同步所有文件')
    parser.add_argument('--test', action='store_true', help='仅测试连接')

    args = parser.parse_args()

    if not args.token:
        print("错误: 请提供 JWT Token（--token 或 NAV_JWT_TOKEN 环境变量）")
        sys.exit(1)

    syncer = ArticleSyncer(
        api_url=args.api,
        jwt_token=args.token,
        vault_path=args.vault,
        target_path=args.target
    )

    # 测试连接
    if args.test:
        success = syncer.test_connection()
        sys.exit(0 if success else 1)

    print(f"API 地址: {args.api}")
    print(f"Vault 路径: {args.vault}")
    print(f"目标路径: {args.target or '(根目录)'}")
    print()

    # 测试连接
    if not syncer.test_connection():
        print("无法连接到 API，请检查配置")
        sys.exit(1)

    print()

    # 执行同步
    results = syncer.scan_and_sync(
        patterns=args.pattern,
        force=args.force,
        exclude_patterns=args.exclude
    )

    # 打印结果
    print()
    print("=" * 50)
    print("同步完成！")
    print(f"  总计: {results['total']} 个文件")
    print(f"  已同步: {len(results['synced'])} 个")
    print(f"  跳过: {len(results['skipped'])} 个")
    print(f"  失败: {len(results['failed'])} 个")

    if results['failed']:
        print()
        print("失败的文件:")
        for f in results['failed']:
            print(f"  - {f}")


if __name__ == '__main__':
    main()
