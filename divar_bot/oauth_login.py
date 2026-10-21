"""OAuth 2.0 login for Divar Kenar using the user's own consent screen.

The user signs in on Divar's own page and approves the requested scopes.
This script never asks for or stores the user's Divar password or SMS code.
"""
from __future__ import annotations
import json
import os
import secrets
import threading
import urllib.parse
import urllib.request
import urllib.error
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

AUTH_URL = "https://oauth.divar.ir/oauth2/auth"
TOKEN_URL = "https://oauth.divar.ir/oauth2/token"
TOKEN_FILE = Path(os.getenv("DIVAR_TOKEN_FILE", "divar_tokens.json"))

class OAuthError(RuntimeError):
    pass

def _post_form(data: dict) -> dict:
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL, data=encoded, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise OAuthError(f"Token endpoint returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise OAuthError(f"Could not connect to OAuth server: {exc.reason}") from exc

def login():
    client_id = os.getenv("DIVAR_CLIENT_ID", "").strip()
    client_secret = os.getenv("DIVAR_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("DIVAR_REDIRECT_URI", "").strip()
    scopes = os.getenv("DIVAR_OAUTH_SCOPES", "offline_access").strip()

    if not client_id or not client_secret or not redirect_uri:
        raise SystemExit(
            "لطفاً DIVAR_CLIENT_ID، DIVAR_CLIENT_SECRET و DIVAR_REDIRECT_URI را تنظیم کنید.\n"
            "این مقادیر را از پنل توسعه‌دهندگان کنار دیوار بگیرید و Redirect URI را همان‌جا ثبت کنید."
        )

    parsed_redirect = urlparse(redirect_uri)
    if parsed_redirect.scheme not in ("http", "https") or not parsed_redirect.hostname:
        raise SystemExit("DIVAR_REDIRECT_URI باید یک URL معتبر http/https باشد.")
    if parsed_redirect.query or parsed_redirect.fragment:
        raise SystemExit("Redirect URI نباید query یا fragment داشته باشد.")

    host = parsed_redirect.hostname
    port = parsed_redirect.port or (443 if parsed_redirect.scheme == "https" else 80)
    callback_path = parsed_redirect.path or "/"
    state = secrets.token_urlsafe(32)
    result = {}
    event = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            req_url = urlparse(self.path)
            if req_url.path != callback_path:
                self.send_error(404)
                return
            params = parse_qs(req_url.query)
            returned_state = params.get("state", [""])[0]
            if not secrets.compare_digest(returned_state, state):
                result["error"] = "پارامتر state معتبر نیست؛ درخواست رد شد."
            elif params.get("error"):
                result["error"] = params.get("error_description", params["error"])[0]
            elif not params.get("code"):
                result["error"] = "کد مجوز از دیوار دریافت نشد."
            else:
                result["code"] = params["code"][0]
            page = ("درخواست مجوز دریافت شد. می‌توانید این پنجره را ببندید."
                    if "code" in result else "ورود/مجوز کامل نشد. می‌توانید پنجره را ببندید.")
            body = ("<!doctype html><html lang='fa'><meta charset='utf-8'>"
                    "<title>Divar OAuth</title><body dir='rtl' style='font-family:sans-serif'>"
                    f"<h3>{page}</h3></body></html>").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            event.set()

        def log_message(self, *_args):
            return

    # This callback server is intended for a registered local redirect URI.
    # If the provider requires HTTPS/public callback, host it at the registered URI instead.
    try:
        server = HTTPServer((host, port), Handler)
    except OSError as exc:
        raise SystemExit(
            f"نتوانستم روی {host}:{port} برای callback گوش بدهم: {exc}\n"
            "مطمئن شوید Redirect URI در پنل کنار با این برنامه سازگار است."
        ) from exc

    auth_query = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": state,
    })
    auth_url = f"{AUTH_URL}?{auth_query}"
    print("مرورگر باز می‌شود؛ ورود را فقط در صفحه رسمی دیوار انجام دهید.")
    print("اگر مرورگر باز نشد، این آدرس را باز کنید:\n", auth_url)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        webbrowser.open(auth_url)
        if not event.wait(timeout=300):
            raise SystemExit("زمان انتظار برای تأیید تمام شد. دوباره اجرا کنید.")
    finally:
        server.shutdown()
        server.server_close()

    if "error" in result:
        raise SystemExit(f"خطای احراز هویت: {result['error']}")

    tokens = _post_form({
        "code": result["code"],
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    })
    if not tokens.get("access_token"):
        raise OAuthError(f"پاسخ توکن نامعتبر است: {tokens}")

    # Save locally; restrict permissions on POSIX systems.
    TOKEN_FILE.write_text(json.dumps(tokens, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass
    print(f"ورود/اجازه با موفقیت انجام شد. توکن‌ها در {TOKEN_FILE} ذخیره شدند.")
    print("فایل توکن محرمانه است؛ آن را برای دیگران ارسال نکنید یا در Git قرار ندهید.")
    print("Scopes دریافت‌شده:", tokens.get("scope", "(در پاسخ اعلام نشده)"))

def refresh():
    client_id = os.getenv("DIVAR_CLIENT_ID", "").strip()
    client_secret = os.getenv("DIVAR_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("DIVAR_REDIRECT_URI", "").strip()
    if not client_id or not client_secret or not redirect_uri:
        raise SystemExit("تنظیمات OAuth را در متغیرهای محیطی وارد کنید.")
    if not TOKEN_FILE.exists():
        raise SystemExit(f"فایل توکن پیدا نشد: {TOKEN_FILE}")
    tokens = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")
    if not refresh_token or not access_token:
        raise SystemExit("refresh_token یا access_token در فایل وجود ندارد؛ دوباره login اجرا کنید.")
    fresh = _post_form({
        "code": access_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "redirect_uri": redirect_uri,
        "refresh_token": refresh_token,
    })
    if not fresh.get("access_token"):
        raise OAuthError(f"پاسخ تازه‌سازی توکن نامعتبر است: {fresh}")
    TOKEN_FILE.write_text(json.dumps(fresh, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass
    print("توکن با موفقیت تازه‌سازی شد.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="احراز هویت رسمی OAuth برای کنار دیوار")
    parser.add_argument("action", choices=["login", "refresh"])
    args = parser.parse_args()
    login() if args.action == "login" else refresh()
