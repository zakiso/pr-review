# PR & Commit Format Validator

A GitHub Action that validates Pull Request quality and commit message formats using both rule-based checks and AI-powered analysis.

## Features

- ✅ **Commit Message Validation**: Ensures commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/) specification
- ✅ **PR Title Format Check**: Validates PR titles follow required patterns (e.g., `[Feature] Add login page`)
- ✅ **PR Description Quality**: Checks for complete and meaningful descriptions
- ✅ **AI-Powered Quality Analysis**: Uses OpenAI's models to evaluate PR quality and provide improvement suggestions
- ✅ **Automated Feedback**: Posts detailed feedback as comments directly on the PR

## Usage

### Basic usage

```yaml
name: PR Validation

on:
  pull_request:
    branches: [ main ]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Validate PR and Commits
        uses: your-username/pr-check-action@v1
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

### Advanced usage with customization

```yaml
name: PR Validation

on:
  pull_request:
    branches: [ main, develop ]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Validate PR and Commits
        uses: your-username/pr-check-action@v1
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          commit-regex: '^(feat|fix|chore|docs|style|refactor|perf|test|ci)(\(.+\))?: [A-Z].+'
          pr-title-regex: '^\[(Feature|Fix|Chore|Docs)\] .+'
          main-branch: 'develop'
          model-name: 'gpt-3.5-turbo'
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `openai-api-key` | OpenAI API Key for LLM validation | Yes | - |
| `commit-regex` | Regex pattern for commit message validation | No | `^(feat\|fix\|docs\|style\|refactor\|test\|chore\|perf)(\(.+\))?: [A-Z].+` |
| `pr-title-regex` | Regex pattern for PR title validation | No | `^\[(Feature\|Fix\|Docs\|Refactor\|Test\|Chore)\] .+` |
| `main-branch` | Name of the main branch to compare commits against | No | `main` |
| `model-name` | OpenAI model to use for validation | No | `gpt-4` |
| `skip-llm-check` | Set to "true" to skip LLM validation | No | `false` |

## Workflow

1. **Commit Message Check**: Validates all commit messages in the PR against the provided regex pattern
2. **PR Title & Body Check**: Ensures the PR title follows the specified format and the description is meaningful
3. **LLM Quality Analysis**: Uses OpenAI's models to evaluate PR quality and provide actionable feedback
4. **Feedback Comments**: Posts results as comments on the PR

## Examples

### Commit Message Format

Valid examples:
- `feat: Add user authentication`
- `fix(auth): Resolve session timeout issue`
- `docs: Update API documentation`

### PR Title Format

Valid examples:
- `[Feature] Add user login functionality`
- `[Fix] Resolve memory leak in data processor`
- `[Docs] Update API documentation`

## Setting up the repository for this action

1. Create a new repository for your action
2. Copy all the files from this repository into your new repo
3. Make sure the scripts in the `scripts` directory are executable:
   ```bash
   chmod +x scripts/*.sh scripts/*.py
   ```
4. Add the repository to the GitHub Marketplace (optional)

## Tips

1. **API Usage**: The LLM validation uses OpenAI's API which may incur costs. Use `skip-llm-check: 'true'` for less critical PRs.
2. **Custom Regex Patterns**: Adjust the regex patterns to match your project's specific conventions.
3. **GitHub Token**: The action uses the default `github.token` for PR comments. No additional configuration is needed.

## License

MIT