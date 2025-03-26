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
        return
    
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }
    data = {"body": comment}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
    except Exception as e:
        print(f"Warning: Failed to post comment to PR: {e}")

def check_pr_title(title):
    """Check if PR title matches the required pattern"""
    pr_title_regex = os.environ.get("PR_TITLE_REGEX", r"^\[(Feature|Fix|Docs|Refactor|Test|Chore)\] .+")
    
    if not re.match(pr_title_regex, title):
        message = f"""
❌ **PR Title Format Error**

Your PR title `{title}` doesn't match the required pattern:
```
{pr_title_regex}
```

Examples of valid PR titles:
- [Feature] Add user authentication
- [Fix] Resolve memory leak in data processor
- [Docs] Update API documentation
"""
        print(message)
        post_comment(message)
        return False
    
    print(f"✅ PR title format is valid: {title}")
    return True

def check_pr_body(body):
    """Check if PR body is not empty and contains required sections"""
    if not body or len(body.strip()) < 10:  # Minimum meaningful description
        message = """
❌ **PR Description Error**

PR description is too short or empty. Please provide:
- What this PR does
- Why it's needed
- How it was tested
- Any related issues
"""
        print(message)
        post_comment(message)
        return False
    
    # Check for minimum structure (has sections with headers)
    if not re.search(r'#+\s+\w+', body):
        message = """
⚠️ **PR Description Warning**

Your PR description lacks structure. Consider using markdown headers to organize your description:

```markdown
## Changes
Describe what changed

## Reason
Why these changes were made

## Testing
How you tested these changes
```
"""
        print(message)
        # This is just a warning, not a failure
    
    print("✅ PR description is present")
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
        print("❌ PR format validation failed. Please fix the issues above.")
        sys.exit(1)
    else:
        print("✅ PR format validation passed.")
        sys.exit(0)

if __name__ == "__main__":
    main()