#!/usr/bin/env python3
"""
GitHub Checks API 结果提交脚本
用于将验证结果发送到 GitHub Checks API
"""

import os
import sys
import json
import argparse
import requests

def create_check_run(title, summary, text, conclusion):
    """创建检查结果"""
    token = os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('REPO_FULL_NAME')
    sha = os.environ.get('GITHUB_SHA')
    check_name = os.environ.get('CHECK_NAME', 'PR 验证')
    
    if not all([token, repo, sha]):
        print(f"ERROR: 缺少必要的环境变量: GITHUB_TOKEN={token!=None}, REPO_FULL_NAME={repo}, GITHUB_SHA={sha}")
        return False
    
    print(f"DEBUG: 创建检查结果 '{title}' 在仓库 {repo}, SHA: {sha[:7]}")
    url = f"https://api.github.com/repos/{repo}/check-runs"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "name": check_name,
        "head_sha": sha,
        "status": "completed",
        "conclusion": conclusion,  # success, failure, neutral, cancelled, skipped, timed_out
        "output": {
            "title": title,
            "summary": summary,
            "text": text
        }
    }
    
    try:
        print(f"INFO: 发送检查结果到 GitHub API")
        response = requests.post(url, headers=headers, json=data)
        print(f"DEBUG: 响应状态码: {response.status_code}")
        
        if response.status_code == 201:
            print(f"INFO: 成功创建检查结果")
            return True
        else:
            print(f"ERROR: 创建检查结果失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR: 提交检查结果时出错: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='提交检查结果到 GitHub Checks API')
    parser.add_argument('--title', required=True, help='检查结果标题')
    parser.add_argument('--summary', required=True, help='检查结果摘要')
    parser.add_argument('--text', required=True, help='检查结果详细文本')
    parser.add_argument('--conclusion', required=True, 
                        choices=['success', 'failure', 'neutral', 'cancelled', 'skipped', 'timed_out'],
                        help='检查结果结论')
    
    args = parser.parse_args()
    
    success = create_check_run(
        title=args.title,
        summary=args.summary,
        text=args.text,
        conclusion=args.conclusion
    )
    
    if not success:
        print("WARNING: 无法提交检查结果，但仍将继续")
        # 打印检查结果以便查看
        print("\n===== 检查结果 =====")
        print(f"标题: {args.title}")
        print(f"结论: {args.conclusion}")
        print(f"摘要: {args.summary}")
        print(f"详细内容:\n{args.text}")
        print("=====================\n")
    
    sys.exit(0 if success or args.conclusion == 'success' else 1)

if __name__ == "__main__":
    main() 