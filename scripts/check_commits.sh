#!/bin/bash
set -e

# 读取环境变量
COMMIT_REGEX=${COMMIT_REGEX:-'^(feat|fix|docs|style|refactor|test|chore|perf)(\(.+\))?: [A-Z].+'}
GITHUB_TOKEN=${GITHUB_TOKEN}
PR_NUMBER=${PR_NUMBER}
REPO_FULL_NAME=${REPO_FULL_NAME}

# 函数：发送 PR 评论
post_comment() {
    local comment="$1"
    local api_url="https://api.github.com/repos/${REPO_FULL_NAME}/issues/${PR_NUMBER}/comments"
    
    # 确保评论内容被正确转义为 JSON
    local json_body=$(echo "$comment" | jq -R -s '{body: .}')
    
    response=$(curl -s -w "%{http_code}" -X POST \
        -H "Authorization: token ${GITHUB_TOKEN}" \
        -H "Accept: application/vnd.github.v3+json" \
        -d "${json_body}" \
        "${api_url}")
    
    http_code=${response: -3}
    if [ $http_code -ne 201 ]; then
        echo "Warning: Failed to post comment to PR. Status code: ${http_code}"
        echo "Response: ${response%???}"
    fi
}

echo "🔍 检查提交信息格式..."

# 使用 GitHub REST API 获取 PR 中的所有提交
COMMITS_JSON=$(curl -s -H "Authorization: token ${GITHUB_TOKEN}" \
                  -H "Accept: application/vnd.github.v3+json" \
                  "https://api.github.com/repos/${REPO_FULL_NAME}/pulls/${PR_NUMBER}/commits")

# 检查 API 调用是否成功
if [ $? -ne 0 ] || [[ $COMMITS_JSON == *"message"*"Not Found"* ]]; then
    echo "❌ 获取提交信息失败"
    exit 1
fi

# 初始化错误信息
INVALID_COMMITS=""
TOTAL_COMMITS=0
INVALID_COUNT=0

# 使用 jq 解析 JSON 并检查每个提交
while read -r line; do
    if [ -z "$line" ]; then
        continue
    fi
    
    # 解析每一行的数据
    commit_hash=$(echo "$line" | cut -d' ' -f1)
    author=$(echo "$line" | cut -d' ' -f2)
    commit_msg=$(echo "$line" | cut -d' ' -f3-)
    
    ((TOTAL_COMMITS++))
    
    # 验证提交信息格式
    if [[ ! "$commit_msg" =~ $COMMIT_REGEX ]]; then
        ((INVALID_COUNT++))
        INVALID_COMMITS="${INVALID_COMMITS}
- [\`${commit_hash:0:7}\`](https://github.com/${REPO_FULL_NAME}/commit/${commit_hash}) by ${author}: \`${commit_msg}\`"
    fi
done < <(echo "$COMMITS_JSON" | jq -r '.[] | "\(.sha) \(.commit.author.name) \(.commit.message | split("\n")[0])"')

# 如果有无效的提交，发送评论并退出
if [ $INVALID_COUNT -gt 0 ]; then
    # 准备评论内容
    comment_text="## ❌ 提交信息格式检查失败

发现 ${INVALID_COUNT}/${TOTAL_COMMITS} 个提交信息格式不符合规范。

### 不符合规范的提交：${INVALID_COMMITS}

### 提交信息格式要求
提交信息必须符合以下格式：
\`\`\`
${COMMIT_REGEX}
\`\`\`

### 正确的示例
- \`feat: 添加用户登录功能\`
- \`fix(auth): 修复会话超时问题\`
- \`docs: 更新 API 文档\`
- \`style: 优化代码格式\`
- \`refactor: 重构数据处理模块\`
- \`test: 添加用户验证测试\`
- \`chore: 更新依赖版本\`
- \`perf: 优化查询性能\`

### 如何修复
1. 使用 \`git rebase -i\` 修改提交信息
2. 或者创建新的提交来替换不规范的提交

需要帮助？请参考 [Conventional Commits](https://www.conventionalcommits.org/) 规范。"

    # 发送评论
    post_comment "$comment_text"
    
    echo "❌ 提交信息格式检查失败。详细信息已添加到 PR 评论中。"
    exit 1
else
    comment_text="## ✅ 提交信息格式检查通过

所有 ${TOTAL_COMMITS} 个提交都符合规范要求。做得很好！"
    
    # 发送成功评论
    post_comment "$comment_text"
    
    echo "✅ 所有提交信息格式正确。"
    exit 0
fi