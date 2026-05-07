import json
import sqlite3
import time
import types


DB = "/app/backend/data/webui.db"
USER_ID = "cc5bae74-8fcd-4576-846d-59779fd8aa80"
TOOL_ID = "local_project_readonly_tools"
TOOL_NAME = "Local Project Readonly Tools"
WRITE_TOOL_ID = "local_workspace_write_tools"
WRITE_TOOL_NAME = "Local Workspace Write Tools"


TOOL_CONTENT = r'''
import fnmatch
import json
import os
import re
import subprocess
from pathlib import Path


class Tools:
    ROOT = Path("/host/projects").resolve()
    DEFAULT_EXCLUDES = {
        ".git", ".idea", ".vscode", "node_modules", "vendor", "storage", "bootstrap/cache",
        "dist", "build", ".next", ".nuxt", "coverage", ".cache", "tmp", "temp",
    }
    TEXT_EXTENSIONS = {
        ".php", ".js", ".jsx", ".ts", ".tsx", ".vue", ".json", ".md", ".yml", ".yaml",
        ".env", ".example", ".xml", ".sql", ".css", ".scss", ".html", ".txt", ".lock",
    }

    def _resolve_project(self, project_path: str) -> Path:
        if not project_path or not project_path.strip():
            raise ValueError("project_path is required. Example: personal/my-app")
        raw = project_path.strip()
        if raw.startswith("/host/projects/") or raw == "/host/projects":
            candidate = Path(raw)
        else:
            candidate = self.ROOT / raw.lstrip("/")
        resolved = candidate.resolve()
        if resolved != self.ROOT and self.ROOT not in resolved.parents:
            raise ValueError("project_path must stay inside /host/projects")
        if not resolved.exists() or not resolved.is_dir():
            raise ValueError(f"project not found: {project_path}")
        return resolved

    def _resolve_file(self, project_path: str, file_path: str) -> Path:
        project = self._resolve_project(project_path)
        if not file_path or not file_path.strip():
            raise ValueError("file_path is required")
        candidate = (project / file_path.strip().lstrip("/")).resolve()
        if candidate != project and project not in candidate.parents:
            raise ValueError("file_path must stay inside the project")
        if not candidate.exists() or not candidate.is_file():
            raise ValueError(f"file not found: {file_path}")
        return candidate

    def _is_excluded_dir(self, path: Path) -> bool:
        parts = set(path.parts)
        if any(part in parts for part in self.DEFAULT_EXCLUDES):
            return True
        return any(part.startswith(".") and part not in {".env", ".github"} for part in path.parts)

    def _read_text(self, path: Path, max_bytes: int = 200000) -> str:
        data = path.read_bytes()[:max_bytes]
        if b"\x00" in data:
            raise ValueError("binary file skipped")
        return data.decode("utf-8", errors="replace")

    def _iter_files(self, project: Path, file_glob: str = ""):
        patterns = [p.strip() for p in file_glob.split(",") if p.strip()] if file_glob else []
        for root, dirs, files in os.walk(project):
            root_path = Path(root)
            dirs[:] = [d for d in dirs if not self._is_excluded_dir(root_path / d)]
            for name in files:
                path = root_path / name
                rel = path.relative_to(project).as_posix()
                if patterns and not any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(name, pat) for pat in patterns):
                    continue
                if path.suffix and path.suffix.lower() not in self.TEXT_EXTENSIONS and name not in {".env", ".env.example"}:
                    continue
                yield path

    def list_projects(self, depth: int = 3, limit: int = 200) -> str:
        """List likely project directories under /host/projects.
        :param depth: Maximum directory depth to inspect from /host/projects.
        :param limit: Maximum number of projects to return.
        """
        depth = max(1, min(int(depth), 5))
        limit = max(1, min(int(limit), 500))
        results = []
        markers = {"composer.json", "package.json", "artisan", ".git"}
        for root, dirs, files in os.walk(self.ROOT):
            root_path = Path(root)
            rel_parts = root_path.relative_to(self.ROOT).parts if root_path != self.ROOT else ()
            if len(rel_parts) > depth:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in self.DEFAULT_EXCLUDES]
            found = sorted(markers.intersection(files + dirs))
            if found and root_path != self.ROOT:
                results.append(f"{root_path.relative_to(self.ROOT).as_posix()}  markers={','.join(found)}")
                if len(results) >= limit:
                    break
        return "\n".join(results) if results else "No projects found under /host/projects."

    def project_search(self, project_path: str, query: str, file_glob: str = "", max_results: int = 50) -> str:
        """Search text in a project using Python-only read access.
        :param project_path: Project path under /host/projects, for example personal/my-app.
        :param query: Literal text or regex to search for.
        :param file_glob: Optional comma-separated glob filters, for example *.php,routes/*.php.
        :param max_results: Maximum matches to return.
        """
        project = self._resolve_project(project_path)
        if not query:
            raise ValueError("query is required")
        max_results = max(1, min(int(max_results), 200))
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error:
            pattern = re.compile(re.escape(query), re.IGNORECASE)
        matches = []
        for path in self._iter_files(project, file_glob):
            try:
                text = self._read_text(path, max_bytes=300000)
            except Exception:
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    rel = path.relative_to(project).as_posix()
                    snippet = line.strip()[:240]
                    matches.append(f"{rel}:{line_no}: {snippet}")
                    if len(matches) >= max_results:
                        return "\n".join(matches)
        return "\n".join(matches) if matches else "No matches found."

    def read_project_file(self, project_path: str, file_path: str, start_line: int = 1, max_lines: int = 200) -> str:
        """Read a bounded slice of a file from a mounted project.
        :param project_path: Project path under /host/projects.
        :param file_path: File path relative to the project root.
        :param start_line: First line number to return, starting at 1.
        :param max_lines: Maximum number of lines to return.
        """
        path = self._resolve_file(project_path, file_path)
        start_line = max(1, int(start_line))
        max_lines = max(1, min(int(max_lines), 500))
        text = self._read_text(path, max_bytes=500000)
        lines = text.splitlines()
        end = min(len(lines), start_line + max_lines - 1)
        output = [f"# {path.name} lines {start_line}-{end} of {len(lines)}"]
        for idx in range(start_line - 1, end):
            output.append(f"{idx + 1}: {lines[idx]}")
        return "\n".join(output)

    def git_status_diff(self, project_path: str, include_diff: bool = True, max_chars: int = 12000) -> str:
        """Show git status and optionally diff for a project without writing to it.
        :param project_path: Project path under /host/projects.
        :param include_diff: Include git diff output when true.
        :param max_chars: Maximum output characters.
        """
        project = self._resolve_project(project_path)
        max_chars = max(1000, min(int(max_chars), 40000))
        safe = f"safe.directory={project.as_posix()}"

        def run(args):
            return subprocess.run(
                ["git", "-c", safe, "-C", project.as_posix(), *args],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=10,
            ).stdout.strip()

        status = run(["status", "--short"])
        parts = ["# git status --short", status or "clean"]
        if include_diff:
            parts.extend(["", "# git diff", run(["diff", "--no-ext-diff", "--"])])
        return "\n".join(parts)[:max_chars]

    def composer_info(self, project_path: str) -> str:
        """Read composer.json and summarize PHP/Laravel dependencies and scripts.
        :param project_path: Project path under /host/projects.
        """
        path = self._resolve_file(project_path, "composer.json")
        data = json.loads(self._read_text(path))
        keys = ["name", "description", "type", "license"]
        out = {k: data.get(k) for k in keys if data.get(k)}
        out["require"] = data.get("require", {})
        out["require-dev"] = data.get("require-dev", {})
        out["scripts"] = data.get("scripts", {})
        out["autoload"] = data.get("autoload", {})
        return json.dumps(out, indent=2, ensure_ascii=False)

    def package_info(self, project_path: str) -> str:
        """Read package.json and summarize Node/JS dependencies and scripts.
        :param project_path: Project path under /host/projects.
        """
        path = self._resolve_file(project_path, "package.json")
        data = json.loads(self._read_text(path))
        out = {
            "name": data.get("name"),
            "version": data.get("version"),
            "type": data.get("type"),
            "scripts": data.get("scripts", {}),
            "dependencies": data.get("dependencies", {}),
            "devDependencies": data.get("devDependencies", {}),
        }
        return json.dumps(out, indent=2, ensure_ascii=False)

    def laravel_routes(self, project_path: str, max_lines: int = 300) -> str:
        """Read Laravel route files. This does not execute php artisan.
        :param project_path: Project path under /host/projects.
        :param max_lines: Maximum route lines to return.
        """
        project = self._resolve_project(project_path)
        routes_dir = project / "routes"
        if not routes_dir.exists():
            return "No routes directory found."
        max_lines = max(20, min(int(max_lines), 1000))
        output = []
        emitted = 0
        for path in sorted(routes_dir.glob("*.php")):
            try:
                lines = self._read_text(path).splitlines()
            except Exception:
                continue
            output.append(f"# routes/{path.name}")
            count = 0
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if "Route::" in stripped or "->name(" in stripped or "->middleware(" in stripped:
                    output.append(f"{i}: {stripped}")
                    count += 1
                    emitted += 1
                    if emitted >= max_lines:
                        return "\n".join(output)
            if count == 0:
                output.append("no obvious Route:: lines")
        return "\n".join(output)

    def migration_schema_reader(self, project_path: str, max_files: int = 80) -> str:
        """Summarize Laravel migration schema operations.
        :param project_path: Project path under /host/projects.
        :param max_files: Maximum migration files to inspect.
        """
        project = self._resolve_project(project_path)
        migrations = project / "database" / "migrations"
        if not migrations.exists():
            return "No database/migrations directory found."
        files = sorted(migrations.glob("*.php"))[-max(1, min(int(max_files), 300)):]
        output = []
        schema_re = re.compile(r"Schema::(create|table|drop|dropIfExists)\(([^)]+)\)")
        column_re = re.compile(r"\$table->([a-zA-Z_][a-zA-Z0-9_]*)\(([^;]*)")
        for path in files:
            text = self._read_text(path)
            entries = []
            for line in text.splitlines():
                s = line.strip()
                if schema_re.search(s) or column_re.search(s) or "foreign" in s or "index" in s or "unique" in s:
                    entries.append(s[:220])
            if entries:
                output.append(f"# {path.name}")
                output.extend(entries[:80])
        return "\n".join(output) if output else "No schema operations found."

    def php_lint(self, project_path: str, file_path: str) -> str:
        """Run php -l on one PHP file if PHP exists in the Open WebUI container.
        :param project_path: Project path under /host/projects.
        :param file_path: PHP file path relative to the project root.
        """
        path = self._resolve_file(project_path, file_path)
        if path.suffix.lower() != ".php":
            raise ValueError("php_lint only accepts .php files")
        php = subprocess.run(["sh", "-lc", "command -v php"], text=True, stdout=subprocess.PIPE).stdout.strip()
        if not php:
            return "php is not installed inside the Open WebUI container, so php_lint cannot run here. Use Codex or add PHP to a custom Open WebUI image for this tool."
        result = subprocess.run([php, "-l", path.as_posix()], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
        return result.stdout.strip()
'''


WRITE_TOOL_CONTENT = r'''
import os
import re
import shutil
import subprocess
import time
from pathlib import Path


class Tools:
    ROOT = Path("/workspace").resolve()
    TRASH = ROOT / ".ai-local-trash"
    HOST_UID = 1000
    HOST_GID = 1000
    TEXT_EXTENSIONS = {
        ".php", ".js", ".jsx", ".ts", ".tsx", ".vue", ".json", ".md", ".yml", ".yaml",
        ".env", ".example", ".xml", ".sql", ".css", ".scss", ".html", ".txt", ".lock",
        ".gitignore", ".editorconfig", ".conf", ".ini", ".stub", ".blade.php",
    }
    MAX_WRITE_BYTES = 500_000
    MAX_READ_BYTES = 500_000
    COMMANDS = {
        "git_status": [["git", "status", "--short"]],
        "git_init": [["git", "init"]],
        "composer_create_laravel": [["composer", "create-project", "laravel/laravel"]],
        "composer_install": [["composer", "install"]],
        "composer_update": [["composer", "update"]],
        "npm_create_vite": [["npm", "create", "vite@latest"]],
        "npm_install": [["npm", "install"]],
        "npm_run_build": [["npm", "run", "build"]],
        "npm_test": [["npm", "test"]],
        "php_artisan": [["php", "artisan"]],
    }

    def _ensure_root(self) -> None:
        self.ROOT.mkdir(parents=True, exist_ok=True)
        self.TRASH.mkdir(parents=True, exist_ok=True)
        self._chown_path(self.ROOT)
        self._chown_path(self.TRASH)

    def _chown_path(self, path: Path, recursive: bool = False) -> None:
        try:
            if recursive and path.is_dir():
                for root, dirs, files in os.walk(path):
                    for name in dirs + files:
                        try:
                            os.chown(Path(root) / name, self.HOST_UID, self.HOST_GID)
                        except OSError:
                            pass
            os.chown(path, self.HOST_UID, self.HOST_GID)
        except OSError:
            pass

    def _resolve(self, path: str = "") -> Path:
        self._ensure_root()
        raw = (path or "").strip()
        if raw.startswith("/workspace/") or raw == "/workspace":
            candidate = Path(raw)
        elif raw.startswith("/"):
            raise ValueError("absolute paths are not allowed; use a path inside /workspace")
        else:
            candidate = self.ROOT / raw
        resolved = candidate.resolve()
        if resolved != self.ROOT and self.ROOT not in resolved.parents:
            raise ValueError("path must stay inside /workspace")
        return resolved

    def _is_text_path(self, path: Path) -> bool:
        return path.suffix.lower() in self.TEXT_EXTENSIONS or path.name in {
            ".env", ".env.example", ".gitignore", ".editorconfig",
        }

    def _read_text(self, path: Path) -> str:
        data = path.read_bytes()[: self.MAX_READ_BYTES]
        if b"\x00" in data:
            raise ValueError("binary file skipped")
        return data.decode("utf-8", errors="replace")

    def list_workspace(self, path: str = "", depth: int = 3, limit: int = 200) -> str:
        """List files and directories inside the writable /workspace.
        :param path: Optional path inside /workspace.
        :param depth: Maximum directory depth to include.
        :param limit: Maximum entries to return.
        """
        root = self._resolve(path)
        if not root.exists():
            return f"not found: {path or '/workspace'}"
        depth = max(1, min(int(depth), 6))
        limit = max(1, min(int(limit), 500))
        if root.is_file():
            return root.relative_to(self.ROOT).as_posix()
        output = []
        for current, dirs, files in os.walk(root):
            current_path = Path(current)
            rel_parts = current_path.relative_to(root).parts if current_path != root else ()
            if len(rel_parts) >= depth:
                dirs[:] = []
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "vendor", ".ai-local-trash"}]
            for name in sorted(dirs):
                rel = (current_path / name).relative_to(self.ROOT).as_posix()
                output.append(f"{rel}/")
                if len(output) >= limit:
                    return "\n".join(output)
            for name in sorted(files):
                rel = (current_path / name).relative_to(self.ROOT).as_posix()
                output.append(rel)
                if len(output) >= limit:
                    return "\n".join(output)
        return "\n".join(output) if output else "workspace is empty"

    def read_workspace_file(self, file_path: str, start_line: int = 1, max_lines: int = 200) -> str:
        """Read a bounded slice of a text file inside /workspace.
        :param file_path: File path inside /workspace.
        :param start_line: First line number to return, starting at 1.
        :param max_lines: Maximum number of lines to return.
        """
        path = self._resolve(file_path)
        if not path.exists() or not path.is_file():
            raise ValueError(f"file not found: {file_path}")
        text = self._read_text(path)
        lines = text.splitlines()
        start_line = max(1, int(start_line))
        max_lines = max(1, min(int(max_lines), 500))
        end = min(len(lines), start_line + max_lines - 1)
        output = [f"# {path.relative_to(self.ROOT).as_posix()} lines {start_line}-{end} of {len(lines)}"]
        for idx in range(start_line - 1, end):
            output.append(f"{idx + 1}: {lines[idx]}")
        return "\n".join(output)

    def create_directory(self, dir_path: str) -> str:
        """Create a directory inside /workspace.
        :param dir_path: Directory path inside /workspace.
        """
        path = self._resolve(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        self._chown_path(path)
        return f"directory ready: {path.relative_to(self.ROOT).as_posix()}"

    def write_file(self, file_path: str, content: str, overwrite: bool = False) -> str:
        """Write a text file inside /workspace.
        :param file_path: File path inside /workspace.
        :param content: Text content to write.
        :param overwrite: Overwrite existing file when true.
        """
        path = self._resolve(file_path)
        if path.exists() and not overwrite:
            raise ValueError("file already exists; set overwrite=true to replace it")
        if path.exists() and path.is_dir():
            raise ValueError("target is a directory")
        data = content.encode("utf-8")
        if len(data) > self.MAX_WRITE_BYTES:
            raise ValueError(f"content is too large; max {self.MAX_WRITE_BYTES} bytes")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._chown_path(path.parent)
        self._chown_path(path)
        return f"wrote {len(data)} bytes: {path.relative_to(self.ROOT).as_posix()}"

    def append_file(self, file_path: str, content: str) -> str:
        """Append text to a file inside /workspace.
        :param file_path: File path inside /workspace.
        :param content: Text content to append.
        """
        path = self._resolve(file_path)
        data = content.encode("utf-8")
        if len(data) > self.MAX_WRITE_BYTES:
            raise ValueError(f"content is too large; max {self.MAX_WRITE_BYTES} bytes")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(content)
        self._chown_path(path.parent)
        self._chown_path(path)
        return f"appended {len(data)} bytes: {path.relative_to(self.ROOT).as_posix()}"

    def replace_in_file(self, file_path: str, old: str, new: str, count: int = 0) -> str:
        """Replace literal text in a text file inside /workspace.
        :param file_path: File path inside /workspace.
        :param old: Literal text to find.
        :param new: Replacement text.
        :param count: Maximum replacements; 0 means all.
        """
        if old == "":
            raise ValueError("old text cannot be empty")
        path = self._resolve(file_path)
        if not path.exists() or not path.is_file():
            raise ValueError(f"file not found: {file_path}")
        text = self._read_text(path)
        max_count = max(0, int(count))
        occurrences = text.count(old) if max_count == 0 else min(text.count(old), max_count)
        if occurrences == 0:
            raise ValueError("old text not found")
        updated = text.replace(old, new, max_count if max_count else -1)
        path.write_text(updated, encoding="utf-8")
        self._chown_path(path)
        return f"replaced {occurrences} occurrence(s): {path.relative_to(self.ROOT).as_posix()}"

    def move_path(self, source_path: str, target_path: str, overwrite: bool = False) -> str:
        """Move or rename a file/directory inside /workspace.
        :param source_path: Existing source path inside /workspace.
        :param target_path: Target path inside /workspace.
        :param overwrite: Replace target when true.
        """
        source = self._resolve(source_path)
        target = self._resolve(target_path)
        if not source.exists():
            raise ValueError(f"source not found: {source_path}")
        if target.exists():
            if not overwrite:
                raise ValueError("target already exists; set overwrite=true to replace it")
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source.as_posix(), target.as_posix())
        self._chown_path(target, recursive=target.is_dir())
        return f"moved {source_path} -> {target.relative_to(self.ROOT).as_posix()}"

    def delete_path(self, path: str) -> str:
        """Move a file/directory inside /workspace to /workspace/.ai-local-trash.
        :param path: Path inside /workspace to move to trash.
        """
        target = self._resolve(path)
        if target == self.ROOT or target == self.TRASH:
            raise ValueError("refusing to delete workspace root or trash root")
        if not target.exists():
            raise ValueError(f"path not found: {path}")
        stamp = time.strftime("%Y%m%d-%H%M%S")
        rel = target.relative_to(self.ROOT).as_posix().replace("/", "__")
        trash_target = self.TRASH / f"{stamp}__{rel}"
        trash_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(target.as_posix(), trash_target.as_posix())
        self._chown_path(trash_target, recursive=trash_target.is_dir())
        return f"moved to trash: {trash_target.relative_to(self.ROOT).as_posix()}"

    def run_workspace_command(self, command: str, args: list[str] | None = None, cwd: str = "", timeout: int = 120) -> str:
        """Run an allowlisted command inside /workspace.
        :param command: One of git_status, git_init, composer_create_laravel, composer_install, composer_update, npm_create_vite, npm_install, npm_run_build, npm_test, php_artisan.
        :param args: Extra arguments appended to the allowlisted prefix.
        :param cwd: Working directory inside /workspace.
        :param timeout: Timeout in seconds, max 600.
        """
        if command not in self.COMMANDS:
            raise ValueError(f"command not allowed: {command}")
        args = args or []
        if not isinstance(args, list) or any(not isinstance(arg, str) for arg in args):
            raise ValueError("args must be a list of strings")
        if any("\x00" in arg for arg in args):
            raise ValueError("invalid null byte in args")
        workdir = self._resolve(cwd)
        workdir.mkdir(parents=True, exist_ok=True)
        cmd = [*self.COMMANDS[command][0], *args]
        binary = shutil.which(cmd[0])
        if not binary:
            return f"{cmd[0]} is not installed inside the Open WebUI container. The workspace files can still be created/edited, but this command cannot run here yet."
        timeout = max(1, min(int(timeout), 600))
        env = {
            **os.environ,
            "CI": "1",
            "NO_COLOR": "1",
            "HOME": "/tmp",
            "COMPOSER_HOME": "/tmp/composer",
            "COMPOSER_ALLOW_SUPERUSER": "1",
            "NPM_CONFIG_CACHE": "/tmp/npm-cache",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "safe.directory",
            "GIT_CONFIG_VALUE_0": "*",
        }
        result = subprocess.run(
            cmd,
            cwd=workdir.as_posix(),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        self._chown_path(workdir, recursive=True)
        output = result.stdout[-20000:]
        return f"$ {' '.join(cmd)}\nexit_code={result.returncode}\n{output}"
'''


def build_specs():
    module = types.ModuleType("tool_preview")
    exec(TOOL_CONTENT, module.__dict__)
    # Keep specs explicit so this script can run in `docker exec` without
    # importing Open WebUI's full app environment.
    return [
        {
            "name": "list_projects",
            "description": "List likely project directories under /host/projects.",
            "parameters": {
                "type": "object",
                "properties": {
                    "depth": {"type": "integer", "description": "Maximum directory depth to inspect from /host/projects.", "default": 3},
                    "limit": {"type": "integer", "description": "Maximum number of projects to return.", "default": 200},
                },
                "required": [],
            },
        },
        {
            "name": "project_search",
            "description": "Search text in a project using Python-only read access.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Project path under /host/projects, for example personal/my-app."},
                    "query": {"type": "string", "description": "Literal text or regex to search for."},
                    "file_glob": {"type": "string", "description": "Optional comma-separated glob filters, for example *.php,routes/*.php.", "default": ""},
                    "max_results": {"type": "integer", "description": "Maximum matches to return.", "default": 50},
                },
                "required": ["project_path", "query"],
            },
        },
        {
            "name": "read_project_file",
            "description": "Read a bounded slice of a file from a mounted project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Project path under /host/projects."},
                    "file_path": {"type": "string", "description": "File path relative to the project root."},
                    "start_line": {"type": "integer", "description": "First line number to return, starting at 1.", "default": 1},
                    "max_lines": {"type": "integer", "description": "Maximum number of lines to return.", "default": 200},
                },
                "required": ["project_path", "file_path"],
            },
        },
        {
            "name": "git_status_diff",
            "description": "Show git status and optionally diff for a project without writing to it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Project path under /host/projects."},
                    "include_diff": {"type": "boolean", "description": "Include git diff output when true.", "default": True},
                    "max_chars": {"type": "integer", "description": "Maximum output characters.", "default": 12000},
                },
                "required": ["project_path"],
            },
        },
        {
            "name": "composer_info",
            "description": "Read composer.json and summarize PHP/Laravel dependencies and scripts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Project path under /host/projects."},
                },
                "required": ["project_path"],
            },
        },
        {
            "name": "package_info",
            "description": "Read package.json and summarize Node/JS dependencies and scripts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Project path under /host/projects."},
                },
                "required": ["project_path"],
            },
        },
        {
            "name": "laravel_routes",
            "description": "Read Laravel route files. This does not execute php artisan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Project path under /host/projects."},
                    "max_lines": {"type": "integer", "description": "Maximum route lines to return.", "default": 300},
                },
                "required": ["project_path"],
            },
        },
        {
            "name": "migration_schema_reader",
            "description": "Summarize Laravel migration schema operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Project path under /host/projects."},
                    "max_files": {"type": "integer", "description": "Maximum migration files to inspect.", "default": 80},
                },
                "required": ["project_path"],
            },
        },
        {
            "name": "php_lint",
            "description": "Run php -l on one PHP file if PHP exists in the Open WebUI container.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Project path under /host/projects."},
                    "file_path": {"type": "string", "description": "PHP file path relative to the project root."},
                },
                "required": ["project_path", "file_path"],
            },
        },
    ]


def build_write_specs():
    module = types.ModuleType("write_tool_preview")
    exec(WRITE_TOOL_CONTENT, module.__dict__)
    return [
        {
            "name": "list_workspace",
            "description": "List files and directories inside the writable /workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Optional path inside /workspace.", "default": ""},
                    "depth": {"type": "integer", "description": "Maximum directory depth to include.", "default": 3},
                    "limit": {"type": "integer", "description": "Maximum entries to return.", "default": 200},
                },
                "required": [],
            },
        },
        {
            "name": "read_workspace_file",
            "description": "Read a bounded slice of a text file inside /workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "File path inside /workspace."},
                    "start_line": {"type": "integer", "description": "First line number to return, starting at 1.", "default": 1},
                    "max_lines": {"type": "integer", "description": "Maximum number of lines to return.", "default": 200},
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "create_directory",
            "description": "Create a directory inside /workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dir_path": {"type": "string", "description": "Directory path inside /workspace."},
                },
                "required": ["dir_path"],
            },
        },
        {
            "name": "write_file",
            "description": "Write a text file inside /workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "File path inside /workspace."},
                    "content": {"type": "string", "description": "Text content to write."},
                    "overwrite": {"type": "boolean", "description": "Overwrite existing file when true.", "default": False},
                },
                "required": ["file_path", "content"],
            },
        },
        {
            "name": "append_file",
            "description": "Append text to a file inside /workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "File path inside /workspace."},
                    "content": {"type": "string", "description": "Text content to append."},
                },
                "required": ["file_path", "content"],
            },
        },
        {
            "name": "replace_in_file",
            "description": "Replace literal text in a text file inside /workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "File path inside /workspace."},
                    "old": {"type": "string", "description": "Literal text to find."},
                    "new": {"type": "string", "description": "Replacement text."},
                    "count": {"type": "integer", "description": "Maximum replacements; 0 means all.", "default": 0},
                },
                "required": ["file_path", "old", "new"],
            },
        },
        {
            "name": "move_path",
            "description": "Move or rename a file/directory inside /workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_path": {"type": "string", "description": "Existing source path inside /workspace."},
                    "target_path": {"type": "string", "description": "Target path inside /workspace."},
                    "overwrite": {"type": "boolean", "description": "Replace target when true.", "default": False},
                },
                "required": ["source_path", "target_path"],
            },
        },
        {
            "name": "delete_path",
            "description": "Move a file/directory inside /workspace to /workspace/.ai-local-trash.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path inside /workspace to move to trash."},
                },
                "required": ["path"],
            },
        },
        {
            "name": "run_workspace_command",
            "description": "Run an allowlisted command inside /workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Allowlisted command.",
                        "enum": [
                            "git_status",
                            "git_init",
                            "composer_create_laravel",
                            "composer_install",
                            "composer_update",
                            "npm_create_vite",
                            "npm_install",
                            "npm_run_build",
                            "npm_test",
                            "php_artisan",
                        ],
                    },
                    "args": {"type": "array", "items": {"type": "string"}, "description": "Extra arguments appended to the allowlisted prefix.", "default": []},
                    "cwd": {"type": "string", "description": "Working directory inside /workspace.", "default": ""},
                    "timeout": {"type": "integer", "description": "Timeout in seconds, max 600.", "default": 120},
                },
                "required": ["command"],
            },
        },
    ]


def upsert_tool_record(conn, tool_id, tool_name, content, specs, meta, now):
    existing = conn.execute("select id from tool where id = ?", (tool_id,)).fetchone()
    if existing:
        conn.execute(
            "update tool set user_id=?, name=?, content=?, specs=?, meta=?, updated_at=? where id=?",
            (USER_ID, tool_name, content, json.dumps(specs), json.dumps(meta), now, tool_id),
        )
    else:
        conn.execute(
            "insert into tool (id, user_id, name, content, specs, meta, created_at, updated_at, valves) values (?, ?, ?, ?, ?, ?, ?, ?, null)",
            (tool_id, USER_ID, tool_name, content, json.dumps(specs), json.dumps(meta), now, now),
        )


def upsert_tools():
    readonly_specs = build_specs()
    write_specs = build_write_specs()
    tools_to_register = [
        (
            TOOL_ID,
            TOOL_NAME,
            TOOL_CONTENT,
            readonly_specs,
            {
                "description": "Read-only tools for searching and inspecting projects mounted at /host/projects.",
                "manifest": {},
            },
        ),
        (
            WRITE_TOOL_ID,
            WRITE_TOOL_NAME,
            WRITE_TOOL_CONTENT,
            write_specs,
            {
                "description": "Scoped write tools for creating and editing projects only inside /workspace.",
                "manifest": {},
            },
        ),
    ]
    now = int(time.time())

    conn = sqlite3.connect(DB)
    try:
        conn.execute("PRAGMA busy_timeout=5000")
        for tool_id, tool_name, content, specs, meta in tools_to_register:
            upsert_tool_record(conn, tool_id, tool_name, content, specs, meta, now)

        row = conn.execute("select settings from user where id = ?", (USER_ID,)).fetchone()
        settings = json.loads(row[0]) if row and row[0] else {}
        tools = settings.get("tools")
        if not isinstance(tools, list):
            tools = []
        for tool_id, *_ in tools_to_register:
            if tool_id not in tools:
                tools.append(tool_id)
        settings["tools"] = tools
        conn.execute("update user set settings = ?, updated_at = ? where id = ?", (json.dumps(settings), now, USER_ID))
        conn.commit()
    finally:
        conn.close()

    for tool_id, _, _, specs, _ in tools_to_register:
        print(f"tool upserted: {tool_id}")
        print("functions:", ", ".join(spec["name"] for spec in specs))


if __name__ == "__main__":
    upsert_tools()
