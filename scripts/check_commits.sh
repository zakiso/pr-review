#!/bin/bash
set -e

# Read regex pattern from environment variable or use default
COMMIT_REGEX=${COMMIT_REGEX:-'^(feat|fix|docs|style|refactor|test|chore|perf)(\(.+\))?: [A-Z].+'}
MAIN_BRANCH=${MAIN_BRANCH:-'main'}

echo "🔍 Checking commit messages against pattern: $COMMIT_REGEX"
echo "🔍 Using main branch: $MAIN_BRANCH"

# Get PR commits (fetch origin to ensure we have the latest)
git fetch origin $MAIN_BRANCH --quiet
COMMITS=$(git log --pretty=format:"%H %s" origin/$MAIN_BRANCH..HEAD)

if [ -z "$COMMITS" ]; then
  echo "⚠️ No commits found between origin/$MAIN_BRANCH and HEAD. This might indicate an issue with branch setup."
  exit 0
fi

# Track if any commit fails validation
VALIDATION_FAILED=0

while IFS= read -r commit_line; do
  # Extract commit hash and message
  COMMIT_HASH=$(echo "$commit_line" | cut -d' ' -f1)
  COMMIT_MSG=$(echo "$commit_line" | cut -d' ' -f2-)
  
  # Validate against regex
  if [[ ! "$COMMIT_MSG" =~ $COMMIT_REGEX ]]; then
    echo "❌ Invalid commit message: $COMMIT_MSG (commit: ${COMMIT_HASH:0:7})"
    echo "   Message should match pattern: $COMMIT_REGEX"
    echo "   Examples of valid formats:"
    echo "   - feat: Add new login feature"
    echo "   - fix(auth): Resolve session timeout issue"
    echo "   - docs: Update API documentation"
    VALIDATION_FAILED=1
  else
    echo "✅ Valid commit message: $COMMIT_MSG"
  fi
done <<< "$COMMITS"

if [ $VALIDATION_FAILED -eq 1 ]; then
  echo "❌ Commit message validation failed. Please fix the issues above and update your PR."
  exit 1
else
  echo "✅ All commit messages are valid."
  exit 0
fi