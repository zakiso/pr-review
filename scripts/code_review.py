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
        print("❌ 缺少必要的环境变量")
        sys.exit(1)
    
    print(f"DEBUG: 获取 PR #{pr_number} 的差异内容，仓库: {repo}")
    print(f"DEBUG: 使用的令牌 (前4位): {token[:4]}...")
    
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = {
        "Accept": "application/vnd.github.v3.diff",
        "Authorization": f"token {token}",
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"DEBUG: 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print(f"INFO: 成功获取差异，内容长度: {len(response.text)} 字符")
            return response.text
        
        response.raise_for_status()
    except Exception as e:
        print(f"ERROR: 获取 PR 差异失败: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"响应状态: {e.response.status_code}")
            print(f"响应内容: {e.response.text}")
        sys.exit(1)
    
    return None

def get_changed_files():
    """Fetch the list of changed files in the PR"""
    token = os.environ.get('GITHUB_TOKEN')
    pr_number = os.environ.get('PR_NUMBER')
    repo = os.environ.get('REPO_FULL_NAME')
    
    print(f"DEBUG: 获取 PR #{pr_number} 中更改的文件")
    
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"DEBUG: 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            files = response.json()
            print(f"INFO: 找到 {len(files)} 个更改的文件")
            return files
        
        response.raise_for_status()
    except Exception as e:
        print(f"ERROR: 获取更改文件失败: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"响应状态: {e.response.status_code}")
            print(f"响应内容: {e.response.text[:200]}...")
        sys.exit(1)
    
    return []

def review_code_with_llm(file_content, file_name):
    """使用 LLM 审查代码"""
    api_key = os.environ.get('OPENAI_API_KEY')
    model_name = os.environ.get('MODEL_NAME', 'gpt-4')
    
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable is not set")
        sys.exit(1)
    
    print(f"DEBUG: 使用 {model_name} 审查文件: {file_name}")
    
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
            print(f"DEBUG: 尝试 #{retry_count+1} 调用 OpenAI API")
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            print("INFO: API 调用成功，分析结果已返回")
            return json.loads(content)
            
        except Exception as e:
            if retry_count == len(retry_delays) - 1:
                print(f"ERROR: LLM 审查出错: {e}")
                return None
            print(f"WARNING: 重试 {retry_count + 1}/{len(retry_delays)}, {delay}秒后: {e}")
            time.sleep(delay)
    
    return None

def format_review_for_file(file_name, review_result):
    """格式化单个文件的审查结果为 Markdown 格式"""
    if not review_result:
        return f"⚠️ 未能成功审查 {file_name}"
    
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
    
    text = f"""
## 代码审查结果: {file_name}

### 总体评分: {review_result['score']}/10

{review_result['summary']}

### 值得表扬的方面 👏
{chr(10).join([f"- {aspect}" for aspect in review_result['positive_aspects']])}

### 发现的问题
"""
    
    if review_result['issues']:
        for issue in review_result['issues']:
            text += f"""
#### {emoji_map.get(issue['type'], '❓')} {severity_map.get(issue['severity'], '❓')} {issue['type'].title()}
- **描述**: {issue['description']}
- **建议**: {issue['suggestion']}
"""
            if issue.get('line_number'):
                text += f"- **位置**: 第 {issue['line_number']} 行\n"
    else:
        text += "\n没有发现重要问题。\n"
    
    return text

def main():
    """主函数"""
    print("🔍 开始代码审查...")
    
    # 获取 PR 中更改的文件
    changed_files = get_changed_files()
    
    # 获取 PR 的 diff (用于参考)
    diff = get_pr_diff()
    
    total_issues = 0
    high_severity_issues = 0
    max_files = int(os.environ.get('MAX_FILES_TO_REVIEW', 10))
    review_threshold = int(os.environ.get('REVIEW_THRESHOLD', 6))
    
    print(f"DEBUG: 将审查最多 {max_files} 个文件，质量阈值: {review_threshold}")
    
    # 初始化审查报告
    file_reviews = []
    issue_details = []
    reviewed_files = 0
    low_quality_files = 0
    
    # 对每个更改的文件进行审查
    for file in changed_files[:max_files]:
        file_name = file['filename']
        print(f"📝 正在审查文件: {file_name}")
        
        # 跳过二进制文件、删除的文件等
        if file['status'] == 'removed' or file.get('binary', False):
            print(f"INFO: 跳过文件 {file_name} (状态: {file['status']})")
            continue
        
        # 获取文件内容
        try:
            print(f"DEBUG: 获取文件内容: {file['raw_url']}")
            response = requests.get(file['raw_url'])
            if response.status_code != 200:
                print(f"WARNING: 无法获取文件内容，状态码: {response.status_code}")
                continue
                
            file_content = response.text
            print(f"INFO: 成功获取文件内容，长度: {len(file_content)} 字符")
        except Exception as e:
            print(f"ERROR: 获取文件内容失败: {e}")
            continue
        
        # 使用 LLM 进行代码审查
        review_result = review_code_with_llm(file_content, file_name)
        reviewed_files += 1
        
        if review_result:
            # 统计问题
            file_issues = len(review_result['issues'])
            total_issues += file_issues
            file_high_issues = sum(1 for issue in review_result['issues'] 
                                 if issue['severity'] == 'high')
            high_severity_issues += file_high_issues
            
            # 如果得分低于阈值，计为低质量文件
            if review_result['score'] < review_threshold:
                low_quality_files += 1
            
            print(f"INFO: 发现 {file_issues} 个问题，其中 {file_high_issues} 个高严重性问题")
            
            # 添加到审查报告
            review_text = format_review_for_file(file_name, review_result)
            file_reviews.append(review_text)
            
            # 添加问题详情
            for issue in review_result['issues']:
                issue_details.append({
                    'file': file_name,
                    'type': issue['type'],
                    'severity': issue['severity'],
                    'description': issue['description'],
                    'suggestion': issue['suggestion'],
                    'line_number': issue.get('line_number')
                })
    
    # 准备总结报告
    if reviewed_files == 0:
        summary = "未能审查任何文件。"
        conclusion = "neutral"
        title = "代码审查未运行"
    else:
        # 确定整体结论
        if high_severity_issues > 0 or low_quality_files > 0:
            conclusion = "failure"
            title = "代码审查发现问题"
            summary = f"发现 {high_severity_issues} 个高严重性问题，{low_quality_files} 个低质量文件。"
        else:
            conclusion = "success"
            title = "代码审查通过"
            summary = f"审查了 {reviewed_files} 个文件，无高严重性问题。"
    
    # 生成最终报告
    report_text = f"""
# 代码审查总结

- 审查的文件数: {reviewed_files}
- 发现的问题总数: {total_issues}
- 高严重性问题: {high_severity_issues}
- 低质量文件数: {low_quality_files}

{'⚠️ 发现高严重性问题，请在合并前解决。' if high_severity_issues > 0 else '✅ 没有发现高严重性问题。'}

## 审查详情

{chr(10).join(file_reviews)}

---
*此代码审查由 AI 辅助完成，仅供参考。*
"""
    
    # 设置输出变量
    with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
        f.write(f"code_review_title={title}\n")
        f.write(f"code_review_summary={summary}\n")
        f.write("code_review_text<<EOF\n")
        f.write(f"{report_text}\n")
        f.write("EOF\n")
        f.write(f"code_review_conclusion={conclusion}\n")
    
    # 如果有高严重性问题，以非零状态退出
    if high_severity_issues > 0:
        print(f"❌ 发现 {high_severity_issues} 个高严重性问题。")
        sys.exit(1)
    else:
        print("✅ 代码审查完成。")
        sys.exit(0)

if __name__ == "__main__":
    main() 