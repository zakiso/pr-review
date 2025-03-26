#!/usr/bin/env python3
"""
LLM-based Code Review Script
---------------------------
Uses OpenAI's API to perform automated code review on PR changes.
"""

import os
import sys
import json
import time
import requests
from openai import OpenAI

def get_pr_diff():
    """Fetch the PR diff from GitHub API"""
    token = os.environ.get('GITHUB_TOKEN')
    pr_number = os.environ.get('PR_NUMBER')
    repo = os.environ.get('REPO_FULL_NAME')
    
    if not all([token, pr_number, repo]):
        print("❌ Required environment variables are not set")
        sys.exit(1)
    
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = {
        "Accept": "application/vnd.github.v3.diff",
        "Authorization": f"token {token}",
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching PR diff: {e}")
        sys.exit(1)

def get_changed_files():
    """Fetch the list of changed files in the PR"""
    token = os.environ.get('GITHUB_TOKEN')
    pr_number = os.environ.get('PR_NUMBER')
    repo = os.environ.get('REPO_FULL_NAME')
    
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching changed files: {e}")
        sys.exit(1)

def post_review_comment(body, path=None, line=None, side=None):
    """Post a review comment to the PR"""
    token = os.environ.get('GITHUB_TOKEN')
    pr_number = os.environ.get('PR_NUMBER')
    repo = os.environ.get('REPO_FULL_NAME')
    
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
    }
    
    # 如果没有指定文件和行号，发送一般性评论
    if not all([path, line]):
        data = {
            "body": body,
            "event": "COMMENT"
        }
    else:
        # 发送针对具体代码行的评论
        data = {
            "body": body,
            "event": "COMMENT",
            "comments": [{
                "path": path,
                "line": line,
                "side": side or "RIGHT",
                "body": body
            }]
        }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
    except Exception as e:
        print(f"Error posting review comment: {e}")

def review_code_with_llm(file_content, file_name):
    """使用 LLM 审查代码"""
    api_key = os.environ.get('OPENAI_API_KEY')
    model_name = os.environ.get('MODEL_NAME', 'gpt-4')
    
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable is not set")
        sys.exit(1)
    
    client = OpenAI(api_key=api_key)
    
    prompt = f"""
作为一个专业的代码审查者，请审查以下代码变更。这是文件 {file_name} 的内容：

{file_content}

请从以下几个方面进行分析：
1. 代码质量：评估代码的可读性、复杂性和维护性
2. 潜在问题：识别可能的 bug、性能问题或安全漏洞
3. 最佳实践：检查是否遵循编程最佳实践
4. 改进建议：提供具体的改进建议

请以 JSON 格式返回结果：
{{
    "score": [1-10的整数评分],
    "issues": [
        {{
            "type": ["bug" | "performance" | "security" | "style" | "best_practice"],
            "severity": ["high" | "medium" | "low"],
            "description": "问题描述",
            "suggestion": "改进建议",
            "line_number": "相关行号（如果适用）"
        }}
    ],
    "summary": "总体评价",
    "positive_aspects": ["值得表扬的方面列表"]
}}
"""

    max_retries = 3
    retry_delays = [1, 2, 4]
    
    for retry_count, delay in enumerate(retry_delays):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            if retry_count == len(retry_delays) - 1:
                print(f"Error in LLM review: {e}")
                return None
            print(f"Retry {retry_count + 1}/{len(retry_delays)} after {delay}s: {e}")
            time.sleep(delay)

def format_review_comment(file_name, review_result):
    """格式化审查结果为 Markdown 格式"""
    if not review_result:
        return f"⚠️ Failed to review {file_name}"
    
    emoji_map = {
        "bug": "🐛",
        "performance": "⚡",
        "security": "🔒",
        "style": "💅",
        "best_practice": "✨"
    }
    
    severity_map = {
        "high": "🔴",
        "medium": "🟡",
        "low": "🟢"
    }
    
    comment = f"""
## 代码审查结果: {file_name}

### 总体评分: {review_result['score']}/10

{review_result['summary']}

### 值得表扬的方面 👏
{chr(10).join([f"- {aspect}" for aspect in review_result['positive_aspects']])}

### 发现的问题
"""
    
    if review_result['issues']:
        for issue in review_result['issues']:
            comment += f"""
#### {emoji_map.get(issue['type'], '❓')} {severity_map.get(issue['severity'], '❓')} {issue['type'].title()}
- **描述**: {issue['description']}
- **建议**: {issue['suggestion']}
"""
            if issue.get('line_number'):
                comment += f"- **位置**: 第 {issue['line_number']} 行\n"
    else:
        comment += "\n没有发现重要问题。\n"
    
    comment += "\n---\n*此代码审查由 AI 辅助完成，仅供参考。*"
    return comment

def main():
    """主函数"""
    print("🔍 开始代码审查...")
    
    # 获取 PR 中更改的文件
    changed_files = get_changed_files()
    
    # 获取 PR 的 diff
    diff = get_pr_diff()
    
    total_issues = 0
    high_severity_issues = 0
    
    # 对每个更改的文件进行审查
    for file in changed_files:
        file_name = file['filename']
        print(f"📝 正在审查文件: {file_name}")
        
        # 跳过二进制文件、删除的文件等
        if file['status'] == 'removed' or file.get('binary', False):
            continue
        
        # 获取文件内容
        try:
            response = requests.get(file['raw_url'])
            response.raise_for_status()
            file_content = response.text
        except Exception as e:
            print(f"Error fetching file content: {e}")
            continue
        
        # 使用 LLM 进行代码审查
        review_result = review_code_with_llm(file_content, file_name)
        
        if review_result:
            # 统计问题
            file_issues = len(review_result['issues'])
            total_issues += file_issues
            high_severity_issues += sum(1 for issue in review_result['issues'] 
                                     if issue['severity'] == 'high')
            
            # 发送审查评论
            comment = format_review_comment(file_name, review_result)
            post_review_comment(comment, file_name)
            
            # 对于每个具体问题，添加行内评论
            for issue in review_result['issues']:
                if issue.get('line_number'):
                    issue_comment = (f"{emoji_map.get(issue['type'], '❓')} "
                                   f"{severity_map.get(issue['severity'], '❓')} "
                                   f"**{issue['type'].title()}**: {issue['description']}\n\n"
                                   f"建议: {issue['suggestion']}")
                    post_review_comment(issue_comment, file_name, 
                                      int(issue['line_number']))
    
    # 发送总结评论
    summary = f"""
# 代码审查总结

- 审查的文件数: {len(changed_files)}
- 发现的问题总数: {total_issues}
- 高严重性问题: {high_severity_issues}

{'⚠️ 发现高严重性问题，请在合并前解决。' if high_severity_issues > 0 else '✅ 没有发现高严重性问题。'}
"""
    post_review_comment(summary)
    
    # 如果有高严重性问题，以非零状态退出
    if high_severity_issues > 0:
        print("❌ 发现高严重性问题，请查看 PR 评论获取详细信息。")
        sys.exit(1)
    else:
        print("✅ 代码审查完成。")
        sys.exit(0)

if __name__ == "__main__":
    main() 