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
from openai import OpenAI

def evaluate_pr_with_llm(title, body):
    """Evaluate PR quality using OpenAI API"""
    # Get API key and model from env vars
    api_key = os.environ.get('OPENAI_API_KEY')
    model_name = os.environ.get('MODEL_NAME', 'gpt-4')

    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable is not set")
        with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
            f.write("llm_check_title=LLM 评估失败\n")
            f.write("llm_check_summary=缺少 OpenAI API 密钥。\n")
            f.write("llm_check_text=请配置 OPENAI_API_KEY 环境变量。\n")
            f.write("llm_check_conclusion=failure\n")
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
    with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
        f.write("llm_check_title=LLM 评估失败\n")
        f.write("llm_check_summary=无法获取有效的 LLM 响应。\n")
        f.write("llm_check_text=在多次重试后仍无法从 OpenAI API 获取有效响应。请检查 API 连接和模型可用性。\n")
        f.write("llm_check_conclusion=failure\n")
    sys.exit(1)

def format_feedback_text(result):
    """Format the LLM feedback as a report text"""
    emoji_map = {
        1: "🚨", 2: "🚨", 3: "🚨", 4: "⚠️", 5: "⚠️",
        6: "👍", 7: "👍", 8: "✅", 9: "🌟", 10: "🌟"
    }
    
    score = result["quality_score"]
    emoji = emoji_map.get(score, "🔍")
    
    report_text = f"""
## {emoji} PR 质量评估

**评分: {score}/10** - {result["explanation"]}

### 优点
{chr(10).join([f"- {s}" for s in result["strengths"]])}

### 改进建议
{chr(10).join([f"- {s}" for s in result["improvement_suggestions"]])}

---
*此评估由 AI 生成，仅供参考。*
"""
    return report_text

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
    
    # Format the feedback
    report_text = format_feedback_text(evaluation)
    
    # Set output variables for GitHub check
    with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
        if evaluation['is_acceptable']:
            f.write("llm_check_title=PR 质量评估通过\n")
            f.write(f"llm_check_summary=PR 质量评分: {evaluation['quality_score']}/10，达到合格标准。\n")
            f.write("llm_check_conclusion=success\n")
        else:
            f.write("llm_check_title=PR 质量评估未通过\n")
            f.write(f"llm_check_summary=PR 质量评分: {evaluation['quality_score']}/10，未达到合格标准。\n")
            f.write("llm_check_conclusion=failure\n")
        
        f.write("llm_check_text<<EOF\n")
        f.write(f"{report_text}\n")
        f.write("EOF\n")
    
    # Exit with appropriate status code
    if not evaluation['is_acceptable']:
        print("\n❌ PR 质量不符合最低标准。请参考上述建议。")
        sys.exit(1)
    else:
        print("\n✅ PR 质量符合最低标准。")
        sys.exit(0)

if __name__ == "__main__":
    main()