# OpenAI API key configuration (BuildSec)

## 1. Setup (each developer, locally)

```bash
mkdir -p secrets
cp secrets.example/openai.env.example secrets/openai.env
chmod 700 secrets
chmod 600 secrets/openai.env
```

Replace the placeholder in `secrets/openai.env` with your own OpenAI API key. Never send the key by chat, commit it, or paste it into a PR.

## 2. Git protection

Append the content of `.gitignore.additions` to the repository `.gitignore`. Confirm:
```bash
git check-ignore -v secrets/openai.env
git status --short
```

If the credentials file was *ever* committed, `.gitignore` does not untrack it. Stop, revoke/rotate the exposed key, and coordinate history remediation with your team's git-governance rules.

## 3. Application

Use `create_openai_client()` from `src.core.openai_client` in the real Generation Engine adapter. Do not read the file in the API, Orchestrator, or tests directly.

`load_openai_credentials` supports CI/server injection through `OPENAI_API_KEY`, which takes precedence over the local ignored file. This lets production environments use a proper secret manager.

If startup reports a missing model, set `OPENAI_MODEL` in the backend environment. Missing credentials and an unreadable local credentials file produce distinct messages. A provider authentication rejection during execution does not establish its cause; inspect the environment-variable precedence and credentials configuration without printing their values. The runtime does not verify the provider at startup.

Install the official SDK from `requirements.txt` in a virtual environment. Set `OPENAI_MODEL` to the model available to your project, or pass `model=` to `OpenAIGenerator`. The adapter implements the existing `Generator` interface and returns inert source text; it does not write or execute that text, and no production sandbox or validator is supplied by this integration. Inject a fake client in unit tests.

## 4. Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.core.test_openai_credentials -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Never print the API key to test it. Do not use credentials inside untrusted generated-code sandboxes or mount the secrets directory there.

## 5. Git workflow

Create a new `feature/openai-credentials` branch from up-to-date `dev` (per git-governance). Commit tracked configuration, loader, and tests only. Submit PR to `dev`; a human explicitly authorizes squash merge. Do not modify main.
