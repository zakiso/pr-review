#!/bin/bash
set -e

# 读取环境变量
COMMIT_REGEX=${COMMIT_REGEX:-'^(feat|fix|docs|style|refactor|test|chore|perf)(\(.+\))?: [A-Z].+'}
GITHUB_TOKEN=${GITHUB_TOKEN}
PR_NUMBER=${PR_NUMBER}
REPO_FULL_NAME=${REPO_FULL_NAME}
IGNORE_COMMIT_CHECK=${IGNORE_COMMIT_CHECK:-"false"}

# 输出调试信息
echo "DEBUG: 检查 PR #${PR_NUMBER} 在仓库 ${REPO_FULL_NAME}"
echo "DEBUG: 使用提交正则表达式: ${COMMIT_REGEX}"
echo "DEBUG: 忽略提交检查失败: ${IGNORE_COMMIT_CHECK}"

echo "🔍 检查提交信息格式..."

# 使用 GitHub REST API 获取 PR 中的所有提交
echo "DEBUG: 获取提交信息..."
COMMITS_JSON=$(curl -s -H "Authorization: token ${GITHUB_TOKEN}" \
              -H "Accept: application/vnd.github.v3+json" \
              "https://api.github.com/repos/${REPO_FULL_NAME}/pulls/${PR_NUMBER}/commits")

# 检查 API 调用是否成功并输出调试信息
if [[ "$COMMITS_JSON" == *"Not Found"* ]] || [[ "$COMMITS_JSON" == *"Bad credentials"* ]]; then
    echo "❌ 获取提交信息失败: $COMMITS_JSON"
    
    # 设置输出变量
    echo "commit_check_title=提交信息获取失败" >> $GITHUB_OUTPUT
    echo "commit_check_summary=无法获取 PR 中的提交信息。" >> $GITHUB_OUTPUT
    echo "commit_check_text=API 返回错误：$COMMITS_JSON" >> $GITHUB_OUTPUT
    echo "commit_check_conclusion=failure" >> $GITHUB_OUTPUT
    
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
    
    # 设置输出变量
    echo "commit_check_title=提交信息解析失败" >> $GITHUB_OUTPUT
    echo "commit_check_summary=API 返回的数据结构不正确。" >> $GITHUB_OUTPUT
    echo "commit_check_text=API 返回了非数组结构：\`\`\`json\n$COMMITS_JSON\n\`\`\`" >> $GITHUB_OUTPUT
    echo "commit_check_conclusion=failure" >> $GITHUB_OUTPUT
    
    exit 1
fi

echo "DEBUG: 检查完成。总提交数: $TOTAL_COMMITS, 不符合规范: $INVALID_COUNT"

# 如果有无效的提交，创建失败检查结果
if [ $INVALID_COUNT -gt 0 ]; then
    # 准备报告内容
    report_text="## 提交信息格式检查失败

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

    # 设置输出变量
    echo "commit_check_title=提交信息格式检查失败" >> $GITHUB_OUTPUT
    echo "commit_check_summary=发现 ${INVALID_COUNT}/${TOTAL_COMMITS} 个提交信息格式不符合规范。" >> $GITHUB_OUTPUT
    echo "commit_check_text<<EOF" >> $GITHUB_OUTPUT
    echo "$report_text" >> $GITHUB_OUTPUT
    echo "EOF" >> $GITHUB_OUTPUT
    echo "commit_check_conclusion=failure" >> $GITHUB_OUTPUT
    
    echo "❌ 提交信息格式检查失败。"
    
    # 如果设置了忽略提交检查失败，则以成功状态退出
    if [ "$IGNORE_COMMIT_CHECK" = "true" ]; then
        echo "INFO: 已设置忽略提交检查失败，继续执行"
        exit 0
    fi
    
    exit 1
else
    # 准备成功报告内容
    report_text="## 提交信息格式检查通过

所有 ${TOTAL_COMMITS} 个提交都符合规范要求。做得很好！"

    # 设置输出变量
    echo "commit_check_title=提交信息格式检查通过" >> $GITHUB_OUTPUT
    echo "commit_check_summary=所有 ${TOTAL_COMMITS} 个提交都符合规范要求。" >> $GITHUB_OUTPUT
    echo "commit_check_text<<EOF" >> $GITHUB_OUTPUT
    echo "$report_text" >> $GITHUB_OUTPUT
    echo "EOF" >> $GITHUB_OUTPUT
    echo "commit_check_conclusion=success" >> $GITHUB_OUTPUT
    
    echo "✅ 所有提交信息格式正确。"
    exit 0
fi