#!/usr/bin/env python3
"""
PR Format Checker Script
------------------------
Verifies if PR title and body meet the required format standards.
Can optionally post results as PR comments.
"""

import os
import re
import sys
import json
import requests

def post_comment(comment):
    """Post a comment to the PR if github token is available"""
    token = os.environ.get('GITHUB_TOKEN')
    pr_number = os.environ.get('PR_NUMBER')
    repo = os.environ.get('REPO_FULL_NAME')
    
    if not all([token, pr_number, repo]):
        print("Warning: Missing required environment variables for posting comments")
        return False
    
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }
    data = {"body": comment}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"Warning: Failed to post comment to PR: {e}")
        if response := getattr(e, 'response', None):
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        return False

def check_pr_title(title):
    """Check if PR title matches the required pattern"""
    pr_title_regex = os.environ.get("PR_TITLE_REGEX", r"^\[(Feature|Fix|Docs|Refactor|Test|Chore)\] .+")
    
    if not re.match(pr_title_regex, title):
        message = f"""## ❌ PR 标题格式错误

您的 PR 标题 `{title}` 不符合要求的格式：
```
{pr_title_regex}
```

### 正确的标题示例：
- [Feature] 添加用户认证功能
- [Fix] 修复数据处理器中的内存泄漏
- [Docs] 更新 API 文档
- [Refactor] 重构用户管理模块
- [Test] 添加集成测试
- [Chore] 更新依赖版本

### 如何修复
1. 点击 PR 标题旁边的编辑按钮（✏️）
2. 修改标题以符合上述格式
3. 点击保存"""
        print(message)
        post_comment(message)
        return False
    
    print(f"✅ PR 标题格式正确：{title}")
    return True

def check_pr_body(body):
    """Check if PR body is not empty and contains required sections"""
    if not body or len(body.strip()) < 50:  # 最小有意义描述长度
        message = """## ❌ PR 描述错误

PR 描述太短或为空。请提供以下信息：

### 必需的章节
```markdown
## 变更内容
描述这个 PR 做了什么改动

## 原因
解释为什么需要这些改动

## 测试
说明如何测试这些改动

## 相关问题
列出相关的 issue 或文档
```

### 如何修复
1. 点击 PR 描述旁边的编辑按钮
2. 添加上述必需的章节
3. 为每个章节提供详细信息
4. 点击保存

好的 PR 描述可以帮助审查者更好地理解您的改动，加快审查过程。"""
        print(message)
        post_comment(message)
        return False
    
    # 检查最小结构（是否有带标题的章节）
    if not re.search(r'#+\s+\w+', body):
        message = """## ⚠️ PR 描述格式建议

您的 PR 描述缺少结构化的章节。建议使用 Markdown 标题来组织描述：

```markdown
## 变更内容
描述这个 PR 做了什么改动

## 原因
解释为什么需要这些改动

## 测试
说明如何测试这些改动

## 相关问题
列出相关的 issue 或文档
```

这种结构可以让审查者更容易理解您的改动。"""
        print(message)
        post_comment(message)
        # 这只是一个警告，不导致检查失败
    
    print("✅ PR 描述已提供")
    return True

def main():
    """Main function to check PR format"""
    if len(sys.argv) < 2:
        print("Usage: python check_pr.py <PR title> [PR body]")
        sys.exit(1)
    
    pr_title = sys.argv[1]
    pr_body = sys.argv[2] if len(sys.argv) > 2 else ""
    
    title_valid = check_pr_title(pr_title)
    body_valid = check_pr_body(pr_body)
    
    if not (title_valid and body_valid):
        print("❌ PR 格式验证失败。请修复上述问题。")
        sys.exit(1)
    else:
        success_message = """## ✅ PR 格式检查通过

- 标题格式正确
- 描述内容充分

感谢您遵循项目规范！"""
        post_comment(success_message)
        print("✅ PR 格式验证通过。")
        sys.exit(0)

if __name__ == "__main__":
    main()