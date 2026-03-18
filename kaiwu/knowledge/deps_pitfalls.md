# Dependency & Environment Pitfalls

Common pitfalls when working with package managers, virtual environments, and containerized builds.

---

## Python

### pip install and virtual environments
- `pip install` in system Python may require `--user` flag or a virtual environment
- Always check if a virtualenv/venv is active before installing: `which python` or `python -m site --user-site`
- Create a venv when starting a new project:
  ```bash
  python -m venv .venv
  source .venv/bin/activate   # Linux/macOS
  .venv\Scripts\activate      # Windows
  ```

### Package name != import name
Common mismatches that cause confusion:
| pip install | import as |
|------------|-----------|
| `Pillow` | `PIL` |
| `pycryptodome` | `Crypto` |
| `python-dateutil` | `dateutil` |
| `beautifulsoup4` | `bs4` |
| `scikit-learn` | `sklearn` |
| `opencv-python` | `cv2` |
| `python-dotenv` | `dotenv` |
| `PyYAML` | `yaml` |
| `python-jose` | `jose` |

### Version conflicts
- Check what's installed before upgrading: `pip show <pkg>`
- Blindly upgrading one package may break others that depend on a specific version
- Use `pip check` to detect broken dependencies
- When conflicts arise, isolate the project in its own venv

### requirements.txt vs pyproject.toml
- Check which the project already uses; do not create the wrong one
- `requirements.txt`: flat list, used with `pip install -r`
- `pyproject.toml`: modern standard (PEP 621), used with `pip install .` or build tools
- Do not mix both for dependency specification unless `requirements.txt` is just a `pip freeze` export

### Other Python pitfalls
- `pip install` may compile C extensions -- ensure build tools are available (`build-essential` on Linux, Visual C++ Build Tools on Windows)
- `pip install --upgrade pip` first if pip is outdated and failing on newer packages
- On Chinese networks, use mirror sources (see `china_kb.md` section 3) to avoid timeouts

---

## Node.js

### npm install vs npm ci
- `npm install`: reads `package.json`, updates `package-lock.json`, installs/upgrades packages
- `npm ci`: reads `package-lock.json` only, deletes `node_modules` first, installs exact versions -- use this in CI/production for reproducible builds
- Never delete `package-lock.json` or `yarn.lock` to "fix" issues -- these lock files ensure deterministic installs

### node_modules corruption
- When facing strange module resolution errors, the nuclear option works:
  ```bash
  rm -rf node_modules
  npm install    # or npm ci
  ```
- On Windows, `node_modules` deep nesting can cause path-too-long errors; use `npm` 7+ which uses a flat structure

### Version mismatches
- Check Node.js version: `node --version` -- some packages require specific major versions
- Use `.nvmrc` or `engines` field in `package.json` to document required Node version
- `npx` runs the local version of a CLI tool; prefer it over global installs

### Global vs local installs
- Prefer local installs (`npx <tool>` or `./node_modules/.bin/<tool>`) over `npm install -g`
- Global installs can conflict between projects using different versions
- Exception: CLI tools you use across projects (e.g., `npm`, `yarn`, `pnpm` themselves)

### Other Node.js pitfalls
- `npm audit` may report vulnerabilities with no available fix -- do not blindly run `npm audit fix --force` as it can introduce breaking changes
- Peer dependency warnings: read them carefully; they often indicate real incompatibilities
- `postinstall` scripts can fail silently; check `npm install` output for errors

---

## Docker

### Multi-stage builds
- Copy only needed artifacts from build stage, not the entire build context:
  ```dockerfile
  FROM node:18 AS build
  WORKDIR /app
  COPY package*.json ./
  RUN npm ci
  COPY . .
  RUN npm run build

  FROM nginx:alpine
  COPY --from=build /app/dist /usr/share/nginx/html
  ```
- This drastically reduces final image size and attack surface

### Layer caching
- Put rarely-changing instructions (dependency install) BEFORE frequently-changing ones (code copy):
  ```dockerfile
  # Good: deps cached until package.json changes
  COPY package*.json ./
  RUN npm ci
  COPY . .

  # Bad: any code change invalidates npm ci cache
  COPY . .
  RUN npm ci
  ```

### Volume mounts on Windows
- Docker Desktop on Windows: path format is `/c/Users/...` not `C:\Users\...`
- WSL2 backend has better performance for volume mounts than Hyper-V backend
- File watching (e.g., Vite HMR, webpack) may not work through volume mounts -- use polling mode:
  ```js
  // vite.config.js
  server: { watch: { usePolling: true } }
  ```

### Container timezone
- Containers default to UTC; if your app needs local time:
  ```dockerfile
  ENV TZ=Asia/Shanghai
  RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
  ```
- Or mount host timezone: `-v /etc/localtime:/etc/localtime:ro`

### Other Docker pitfalls
- `.dockerignore` should exclude `node_modules`, `.git`, `__pycache__`, `.env` files
- `COPY . .` copies everything not in `.dockerignore` -- keep it updated
- `RUN apt-get update && apt-get install -y ...` should be in a single `RUN` to avoid stale cache layers
- Use `--no-cache-dir` with pip inside Docker to save image space: `RUN pip install --no-cache-dir -r requirements.txt`
- Health checks: add `HEALTHCHECK` instruction for production containers

---

## General Tips

- **Pin versions** in lock files and requirements; "latest" is not reproducible
- **Document your environment** in the project README: required runtime versions, env vars, setup steps
- **Test in a clean environment** (fresh venv, fresh container, CI) to catch "works on my machine" issues
- **On Chinese networks**, configure mirror sources for pip, npm, Docker, etc. before installing anything (see `china_kb.md`)
