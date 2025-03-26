#!/usr/bin/env python3
"""
PR Format Checker Script
------------------------
Verifies if PR title and body meet the required format standards.
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path

def call_report_check(title, summary, text, conclusion):
    """调用 report_check.py 生成报告"""
    script_dir = Path(__file__).parent
    report_script = script_dir / "report_check.py"
    
    # 确保报告脚本存在
    if not report_script.exists():
        print(f"ERROR: 找不到报告脚本: {report_script}")
        return False
    
    try:
        subprocess.run([
            "python", str(report_script),
            "--title", title,
            "--summary", summary,
            "--text", text,
            "--conclusion", conclusion
        ], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: 调用报告脚本失败: {e}")
        return False

def check_pr_title(title):
    """Check if PR title matches the required pattern"""
    pr_title_regex = os.environ.get("PR_TITLE_REGEX", r"^\[(Feature|Fix|Docs|Refactor|Test|Chore)\] .+")
    
    if not re.match(pr_title_regex, title):
        message = f"""## PR 标题格式错误

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
        return False, message
    
    print(f"✅ PR 标题格式正确：{title}")
    return True, f"PR 标题 `{title}` 格式正确"

def check_pr_body(body):
    """Check if PR body is not empty and contains required sections"""
    if not body or len(body.strip()) < 50:  # 最小有意义描述长度
        message = """## PR 描述错误

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
        return False, message
    
    # 检查最小结构（是否有带标题的章节）
    warning_message = None
    if not re.search(r'#+\s+\w+', body):
        warning_message = """## ⚠️ PR 描述格式建议

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
        print(warning_message)
        # 这只是一个警告，不导致检查失败
    
    print("✅ PR 描述已提供")
    return True, "PR 描述充分" + (f"\n\n{warning_message}" if warning_message else "")

def main():
    """Main function to check PR format"""
    if len(sys.argv) < 2:
        print("Usage: python check_pr.py <PR title> [PR body]")
        sys.exit(1)
    
    pr_title = sys.argv[1]
    pr_body = sys.argv[2] if len(sys.argv) > 2 else ""
    
    title_valid, title_message = check_pr_title(pr_title)
    body_valid, body_message = check_pr_body(pr_body)
    
    # 准备检查结果
    if not (title_valid and body_valid):
        conclusion = "failure"
        title = "PR 格式验证失败"
        summary = "PR 标题或描述不符合要求格式。"
        text = f"{title_message}\n\n{body_message}"
        
        print("❌ PR 格式验证失败。请修复上述问题。")
        
        # 直接调用 report_check.py
        call_report_check(title, summary, text, conclusion)
        
        sys.exit(1)
    else:
        conclusion = "success"
        title = "PR 格式检查通过"
        summary = "PR 标题和描述格式正确。"
        text = """## ✅ PR 格式检查通过

- 标题格式正确
- 描述内容充分

感谢您遵循项目规范！"""
        
        print("✅ PR 格式验证通过。")
        
        # 直接调用 report_check.py
        call_report_check(title, summary, text, conclusion)
        
        sys.exit(0)

if __name__ == "__main__":
    main()