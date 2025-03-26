#!/usr/bin/env python3
"""
LLM-based PR Validator
----------------------
Uses OpenAI's API to evaluate PR quality and provide improvement suggestions.
"""

import os
import sys
import json
import time
import requests
from openai import OpenAI

def post_comment(comment):
    """Post a comment to the PR"""
    token = os.environ.get('GITHUB_TOKEN')
    pr_number = os.environ.get('PR_NUMBER')
    repo = os.environ.get('REPO_FULL_NAME')
    
    if not all([token, pr_number, repo]):
        print("ERROR: 缺少必要的环境变量 (GITHUB_TOKEN, PR_NUMBER 或 REPO_FULL_NAME)")
        return
    
    print(f"DEBUG: 发送评论到 PR #{pr_number} 在仓库 {repo}")
    print(f"DEBUG: 使用的令牌 (前4位): {token[:4]}...")
    
    # 输出评论内容 (用于测试)
    print("INFO: 将发送以下评论到 PR (如果有权限):")
    print("---BEGIN COMMENT---")
    print(comment[:200] + "..." if len(comment) > 200 else comment)
    print("---END COMMENT---")
    
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }
    data = {"body": comment}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"DEBUG: 响应状态码: {response.status_code}")
        
        if response.status_code == 201:
            print("INFO: 评论成功发送")
            return True
            
        response.raise_for_status()
    except Exception as e:
        print(f"ERROR: 发送评论失败: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"响应状态: {e.response.status_code}")
            print(f"响应内容: {e.response.text}")
    
    return False

def evaluate_pr_with_llm(title, body):
    """Evaluate PR quality using OpenAI API"""
    # Get API key and model from env vars
    api_key = os.environ.get('OPENAI_API_KEY')
    model_name = os.environ.get('MODEL_NAME', 'gpt-4')

    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable is not set")
        sys.exit(1)
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Create the prompt for the LLM
    prompt = f"""
You are an expert code reviewer tasked with evaluating the quality of a GitHub Pull Request.
Analyze the following PR title and description to determine if it meets high-quality standards.

PR Title: {title}
PR Description:
{body}

Evaluate based on these criteria:
1. Clarity: Is the purpose of the PR clearly communicated?
2. Completeness: Does it explain what changes were made and why?
3. Technical Detail: Are implementation details sufficiently explained?
4. Testing: Is there information about how the changes were tested?

Respond with a JSON object containing:
{{
  "quality_score": [1-10 integer score],
  "is_acceptable": [boolean, true if score >= 6],
  "strengths": [array of strengths],
  "improvement_suggestions": [array of specific suggestions for improvement],
  "explanation": [brief explanation of your evaluation]
}}
"""

    # Maximum retries for API call
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            print(f"🤖 使用 {model_name} 评估 PR...")
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Extract the response content
            content = response.choices[0].message.content
            
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                print(f"Error parsing JSON from API response: {content[:200]}...")
                retry_count += 1
                time.sleep(2)
                
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            retry_count += 1
            time.sleep(2)
    
    print("❌ Failed to get a valid response from the OpenAI API after multiple retries")
    sys.exit(1)

def format_feedback_comment(result):
    """Format the LLM feedback as a GitHub comment"""
    emoji_map = {
        1: "🚨", 2: "🚨", 3: "🚨", 4: "⚠️", 5: "⚠️",
        6: "👍", 7: "👍", 8: "✅", 9: "🌟", 10: "🌟"
    }
    
    score = result["quality_score"]
    emoji = emoji_map.get(score, "🔍")
    
    comment = f"""
## {emoji} PR 质量评估

**评分: {score}/10** - {result["explanation"]}

### 优点
{chr(10).join([f"- {s}" for s in result["strengths"]])}

### 改进建议
{chr(10).join([f"- {s}" for s in result["improvement_suggestions"]])}

---
*此评估由 AI 生成，仅供参考。*
"""
    return comment

def main():
    """Main function to validate PR using LLM"""
    if len(sys.argv) < 2:
        print("Usage: python llm_check.py <PR title> [PR body]")
        sys.exit(1)
    
    pr_title = sys.argv[1]
    pr_body = sys.argv[2] if len(sys.argv) > 2 else ""
    
    print(f"DEBUG: 评估 PR 标题: '{pr_title}'")
    print(f"DEBUG: PR 描述长度: {len(pr_body)} 字符")
    
    # Run LLM evaluation
    evaluation = evaluate_pr_with_llm(pr_title, pr_body)
    
    # Print results
    print(f"🤖 LLM 质量评分: {evaluation['quality_score']}/10")
    print(f"🤖 是否可接受: {'是' if evaluation['is_acceptable'] else '否'}")
    print("\n🤖 优点:")
    for strength in evaluation['strengths']:
        print(f"  - {strength}")
    
    print("\n🤖 改进建议:")
    for suggestion in evaluation['improvement_suggestions']:
        print(f"  - {suggestion}")
    
    print(f"\n🤖 评价: {evaluation['explanation']}")
    
    # Post comment to GitHub if possible
    formatted_comment = format_feedback_comment(evaluation)
    comment_success = post_comment(formatted_comment)
    
    if not comment_success:
        print("\nWARNING: 无法发送评论到 PR，但将继续处理")
        print("评论内容如下:\n")
        print(formatted_comment)
    
    # Exit with appropriate status code
    if not evaluation['is_acceptable']:
        print("\n❌ PR 质量不符合最低标准。请参考上述建议。")
        sys.exit(1)
    else:
        print("\n✅ PR 质量符合最低标准。")
        sys.exit(0)

if __name__ == "__main__":
    main()