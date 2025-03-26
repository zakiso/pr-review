#!/bin/bash
set -e

# 读取环境变量
COMMIT_REGEX=${COMMIT_REGEX:-'^(feat|fix|docs|style|refactor|test|chore|perf)(\(.+\))?: [A-Z].+'}
GITHUB_TOKEN=${GITHUB_TOKEN}
PR_NUMBER=${PR_NUMBER}
REPO_FULL_NAME=${REPO_FULL_NAME}

# 输出调试信息
echo "DEBUG: 检查 PR #${PR_NUMBER} 在仓库 ${REPO_FULL_NAME}"

# 函数：发送 PR 评论
post_comment() {
    local comment="$1"
    local api_url="https://api.github.com/repos/${REPO_FULL_NAME}/issues/${PR_NUMBER}/comments"
    
    # 直接输出要发送的评论 (用于测试)
    echo "INFO: 将发送以下评论到 PR (如果有权限):"
    echo "---BEGIN COMMENT---"
    echo "$comment"
    echo "---END COMMENT---"
    
    # 尝试发送评论
    echo "DEBUG: 发送评论到 $api_url"
    response=$(curl -s -w "%{http_code}" -X POST \
        -H "Authorization: token ${GITHUB_TOKEN}" \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Content-Type: application/json" \
        -d "{\"body\": $(echo "$comment" | jq -R -s .)}" \
        "$api_url")
    
    http_code=${response: -3}
    if [ $http_code -ne 201 ]; then
        echo "WARNING: 发送评论失败，状态码: ${http_code}"
        echo "响应: ${response%???}"
    else
        echo "INFO: 评论发送成功"
    fi
}

echo "🔍 检查提交信息格式..."

# 使用 GitHub REST API 获取 PR 中的所有提交
echo "DEBUG: 获取提交信息..."
COMMITS_JSON=$(curl -s -H "Authorization: token ${GITHUB_TOKEN}" \
              -H "Accept: application/vnd.github.v3+json" \
              "https://api.github.com/repos/${REPO_FULL_NAME}/pulls/${PR_NUMBER}/commits")

# 检查 API 调用是否成功并输出调试信息
if [[ "$COMMITS_JSON" == *"Not Found"* ]] || [[ "$COMMITS_JSON" == *"Bad credentials"* ]]; then
    echo "❌ 获取提交信息失败: $COMMITS_JSON"
    exit 1
fi

# 调试信息 - 输出 JSON 结构前几行
echo "DEBUG: API 返回 JSON 结构的前 150 个字符:"
echo "$COMMITS_JSON" | head -c 150

# 初始化错误信息
INVALID_COMMITS=""
TOTAL_COMMITS=0
INVALID_COUNT=0

# 使用更可靠的方法处理 JSON
echo "DEBUG: 解析提交信息..."
if echo "$COMMITS_JSON" | jq -e 'type == "array"' > /dev/null 2>&1; then
    COMMIT_COUNT=$(echo "$COMMITS_JSON" | jq 'length')
    echo "DEBUG: 找到 $COMMIT_COUNT 个提交"
    
    for i in $(seq 0 $((COMMIT_COUNT - 1))); do
        commit_hash=$(echo "$COMMITS_JSON" | jq -r ".[$i].sha")
        # 尝试获取第一行提交信息
        commit_msg=$(echo "$COMMITS_JSON" | jq -r ".[$i].commit.message" | head -1)
        # 尝试获取作者名，如果失败则使用"未知作者"
        author=$(echo "$COMMITS_JSON" | jq -r ".[$i].commit.author.name // \"未知作者\"")
        
        echo "DEBUG: 提交: ${commit_hash:0:7} by $author: $commit_msg"
        
        ((TOTAL_COMMITS++))
        
        # 验证提交信息格式
        if [[ ! "$commit_msg" =~ $COMMIT_REGEX ]]; then
            ((INVALID_COUNT++))
            INVALID_COMMITS="${INVALID_COMMITS}
- [\`${commit_hash:0:7}\`](https://github.com/${REPO_FULL_NAME}/commit/${commit_hash}) by ${author}: \`${commit_msg}\`"
        fi
    done
else
    # 如果不是数组，可能是错误消息
    echo "❌ API 返回非数组结构，可能是错误。请检查 GITHUB_TOKEN 权限。"
    echo "$COMMITS_JSON" | jq '.'
    exit 1
fi

echo "DEBUG: 检查完成。总提交数: $TOTAL_COMMITS, 不符合规范: $INVALID_COUNT"

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