from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import config

API_URL = "https://api.cloudflare.com/client/v4"
ROOT = config.ROOT


class CloudflareError(RuntimeError):
    pass


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")[:50] or "profile"


class Cloudflare:
    def __init__(self, token: str, account: str) -> None:
        self.token = token
        self.account = account

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            f"{API_URL}{path}",
            data=data,
            method=method,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:300]
            raise CloudflareError(f"{method} {path} -> HTTP {error.code}: {detail}") from error
        if not payload.get("success", False):
            raise CloudflareError(f"{method} {path} -> {json.dumps(payload.get('errors'))[:300]}")
        return payload

    def namespace_id(self) -> str:
        base = f"/accounts/{self.account}/storage/kv/namespaces"
        for entry in self.call("GET", f"{base}?per_page=100")["result"]:
            if entry["title"] == config.CLOUDFLARE.namespace_title:
                return entry["id"]
        return self.call("POST", base, {"title": config.CLOUDFLARE.namespace_title})["result"]["id"]

    def subdomain(self, login: str) -> str:
        path = f"/accounts/{self.account}/workers/subdomain"
        try:
            current = self.call("GET", path)["result"] or {}
        except CloudflareError:
            current = {}
        if current.get("subdomain"):
            return current["subdomain"]
        base = slugify(login)
        failure = "no candidate accepted"
        for candidate in (base, f"{base}-dev", f"{base}-hub", f"{base}-live"):
            try:
                return self.call("PUT", path, {"subdomain": candidate})["result"]["subdomain"]
            except CloudflareError as error:
                failure = str(error)
        raise CloudflareError(f"Could not register a workers.dev subdomain: {failure}")


def write_config(namespace: str, login: str, directory: Path) -> Path:
    target = directory / "wrangler.toml"
    lines = [
        f'name = "{config.CLOUDFLARE.worker_name}"',
        'main = "views_worker.js"',
        'compatibility_date = "2025-01-01"',
        "workers_dev = true",
        "",
        "[[kv_namespaces]]",
        'binding = "VIEWS"',
        f'id = "{namespace}"',
        "",
        "[vars]",
        f'ALLOWED_IDS = "{slugify(login)}"',
        "",
    ]
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def patch_readme(readme: Path, host: str) -> bool:
    content = readme.read_text(encoding="utf-8")
    if config.CLOUDFLARE.placeholder_host not in content:
        return False
    readme.write_text(content.replace(config.CLOUDFLARE.placeholder_host, host), encoding="utf-8")
    return True


def main() -> int:
    login = config.GITHUB.login
    if not (config.CLOUDFLARE.configured and login):
        print("CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID and PROFILE_LOGIN are required", file=sys.stderr)
        return 2
    client = Cloudflare(config.CLOUDFLARE.api_token, config.CLOUDFLARE.account_id)
    try:
        namespace = client.namespace_id()
        host = f"{config.CLOUDFLARE.worker_name}.{client.subdomain(login)}.workers.dev"
    except CloudflareError as error:
        print(f"Cloudflare error: {error}", file=sys.stderr)
        return 1
    config = write_config(namespace, login, ROOT / "cloudflare")
    patched = patch_readme(ROOT / "README.md", host)
    print(f"KV namespace ready: {namespace}")
    print(f"Config written: {config.relative_to(ROOT)}")
    print(f"Counter URL: https://{host}/views/{slugify(login)}")
    print("README updated with the counter URL" if patched else "README already points to a counter URL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
