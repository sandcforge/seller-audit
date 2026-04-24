# Set up + activate the sandbox in one step. Source this file (don't execute it).
# Lives at the project root; installs everything under ./sandbox/.
#
# First-time use (two steps):
#   source ./activate.sh
#   # -> if ADC is missing, prints an OAuth URL and returns. Open it, sign in
#   #    with a plantstory-BQ-capable Google account, copy the verification
#   #    code Google shows you on the success page, then:
#   AUTH_CODE='4/0...' source ./activate.sh
#
# Every subsequent session:
#   source ./activate.sh             # install + ADC no-op; sandbox activated
#
# What it sets up (idempotent, everything under ./sandbox/):
#   1. gcloud SDK in sandbox/google-cloud-sdk/
#   2. Python 3.12 venv in sandbox/.venv-audit/ with google-cloud-bigquery + pyyaml
#   3. ADC JSON in sandbox/.config/gcloud/application_default_credentials.json
#
# What it activates (every call):
#   PATH += sandbox/google-cloud-sdk/bin
#   VIRTUAL_ENV = sandbox/.venv-audit
#   GOOGLE_APPLICATION_CREDENTIALS = the ADC JSON
#   CLOUDSDK_CORE_PROJECT = GOOGLE_CLOUD_PROJECT = plantstory

# Must be sourced — activation needs to affect the caller's shell.
if ! (return 0 2>/dev/null); then
  echo "activate.sh must be sourced, not executed:  source $0" >&2
  exit 1
fi

_ROOT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
_SANDBOX_DIR="$_ROOT_DIR/sandbox"
# --- 0. ensure sandbox dir exists -----------------------------------------
# activate.sh lives at the project root; install everything under sandbox/
# so the root stays clean and the sandbox is self-contained.
mkdir -p "$_SANDBOX_DIR" || { echo "could not create $_SANDBOX_DIR" >&2; return 1; }
_GCLOUD_BIN="$_SANDBOX_DIR/google-cloud-sdk/bin/gcloud"
_VENV_DIR="$_SANDBOX_DIR/.venv-audit"
_ADC_FILE="$_SANDBOX_DIR/.config/gcloud/application_default_credentials.json"
_UV_CACHE="$_ROOT_DIR/.uv-cache"

# --- 1. gcloud SDK ---------------------------------------------------------
if [[ -x "$_GCLOUD_BIN" ]]; then
  echo "[1/3] gcloud already installed"
else
  echo "[1/3] Installing gcloud SDK..."
  case "$(uname -m)" in
    aarch64|arm64) _TARBALL="google-cloud-cli-linux-arm.tar.gz" ;;
    x86_64)        _TARBALL="google-cloud-cli-linux-x86_64.tar.gz" ;;
    *) echo "Unsupported arch: $(uname -m)" >&2; return 1 ;;
  esac
  # FUSE mounts sometimes refuse to create specific test-fixture / cert files
  # during tar extraction (non-zero exit from tar), but the gcloud binaries
  # themselves extract fine. So we don't trust tar's exit code — instead we
  # check for the gcloud binary afterward and only fail if it's missing.
  ( cd "$_SANDBOX_DIR" \
    && curl -sSL -o gcloud.tar.gz "https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/$_TARBALL" \
    || { echo "gcloud download failed" >&2; exit 1; } )
  ( cd "$_SANDBOX_DIR" && tar -xzf gcloud.tar.gz 2>/dev/null; rm -f gcloud.tar.gz 2>/dev/null; true )
  if [[ ! -x "$_GCLOUD_BIN" ]]; then
    echo "gcloud install failed: $_GCLOUD_BIN missing after extraction" >&2
    return 1
  fi
  echo "      -> $("$_GCLOUD_BIN" --version | head -1)"
fi

export PATH="$_SANDBOX_DIR/google-cloud-sdk/bin:$PATH"

# --- 2. venv ---------------------------------------------------------------
# When running in the Cowork sandbox, the workspace is FUSE-mounted under
# /sessions/<id>/mnt/, and uv's managed Python lives at /sessions/<id>/.local/
# which is wiped on session roll. A venv persisted on FUSE ends up with a
# dangling `bin/python` symlink and goes unusable. So in Cowork we put the
# venv under /sessions/<id>/.venv-audit (session-local, outside FUSE) and
# rebuild it each session — fast because `.uv-cache` is FUSE-persistent and
# pip install just hardlinks wheels from it.
#
# On the user's local machine the regex below doesn't match, so the venv
# stays at $_SANDBOX_DIR/.venv-audit and persists normally.
if [[ "$_SANDBOX_DIR" =~ ^(/sessions/[^/]+)/mnt/ ]]; then
  _VENV_DIR="${BASH_REMATCH[1]}/.venv-audit"
fi

if [[ -x "$_VENV_DIR/bin/python" ]]; then
  echo "[2/3] venv already exists"
else
  if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found. Install it:  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    return 1
  fi
  echo "[2/3] Creating venv at $_VENV_DIR..."
  UV_CACHE_DIR="$_UV_CACHE" uv venv --python 3.12 "$_VENV_DIR" \
    || { echo "uv venv failed" >&2; return 1; }
  echo "      -> installing google-cloud-bigquery, pyyaml..."
  UV_CACHE_DIR="$_UV_CACHE" VIRTUAL_ENV="$_VENV_DIR" \
    uv pip install --quiet google-cloud-bigquery pyyaml \
    || { echo "uv pip install failed" >&2; return 1; }
fi

# --- 3. ADC ----------------------------------------------------------------
# PKCE OAuth flow is inlined here so the sandbox has no external script
# dependencies. Uses the public gcloud installed-app client (same id/secret
# that ships with every gcloud install — not a real secret).
_PKCE_FILE="$_SANDBOX_DIR/pkce.json"

if [[ -f "$_ADC_FILE" ]]; then
  echo "[3/3] ADC already present"
  # Backfill quota_project_id on ADC files written by older versions of this
  # script so the google.auth "without a quota project" warning goes away
  # without requiring users to re-run OAuth.
  python3 - "$_ADC_FILE" <<'PYEOF' || true
import json, sys
adc_path = sys.argv[1]
try:
    with open(adc_path) as f:
        adc = json.load(f)
except Exception:
    sys.exit(0)
if adc.get("type") == "authorized_user" and "quota_project_id" not in adc:
    adc["quota_project_id"] = "plantstory"
    with open(adc_path, "w") as f:
        json.dump(adc, f, indent=2)
    print("      -> backfilled quota_project_id=plantstory")
PYEOF
elif [[ -n "${AUTH_CODE:-}" ]]; then
  echo "[3/3] Exchanging auth code for refresh token..."
  if [[ ! -f "$_PKCE_FILE" ]]; then
    echo "no pkce.json found at $_PKCE_FILE — re-source without AUTH_CODE first to generate the URL" >&2
    return 1
  fi
  python3 - "$AUTH_CODE" "$_PKCE_FILE" "$_ADC_FILE" <<'PYEOF' || { echo "token exchange failed" >&2; return 1; }
import json, os, sys, urllib.parse, urllib.request

auth_code, pkce_path, adc_path = sys.argv[1], sys.argv[2], sys.argv[3]
with open(pkce_path) as f:
    pkce = json.load(f)

data = urllib.parse.urlencode({
    "code": auth_code,
    "client_id": pkce["client_id"],
    "client_secret": pkce["client_secret"],
    "code_verifier": pkce["code_verifier"],
    "grant_type": "authorization_code",
    "redirect_uri": pkce["redirect_uri"],
}).encode()
req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
try:
    resp = json.loads(urllib.request.urlopen(req).read())
except urllib.error.HTTPError as e:
    print(f"token endpoint error: {e.read().decode()}", file=sys.stderr)
    sys.exit(1)

if "refresh_token" not in resp:
    print(f"no refresh_token in response: {resp}", file=sys.stderr)
    sys.exit(1)

os.makedirs(os.path.dirname(adc_path), exist_ok=True)
with open(adc_path, "w") as f:
    json.dump({
        "client_id": pkce["client_id"],
        "client_secret": pkce["client_secret"],
        "refresh_token": resp["refresh_token"],
        "type": "authorized_user",
        # Attach quota/billing to plantstory so google.auth doesn't warn on
        # every BigQuery call. Matches what `gcloud auth application-default
        # login` writes; we write it ourselves because the inlined PKCE flow
        # doesn't go through gcloud.
        "quota_project_id": "plantstory",
    }, f, indent=2)
# Best-effort cleanup; FUSE mounts sometimes refuse deletes. ADC is already
# written at this point, so a failure here shouldn't abort the flow.
try:
    os.remove(pkce_path)
except OSError:
    pass
print(f"ADC written to {adc_path}")
PYEOF
  unset AUTH_CODE
else
  echo "[3/3] ADC not found. Open this URL, sign in (plantstory BQ access),"
  echo "then copy the verification code Google shows you on the success page:"
  echo ""
  python3 - "$_PKCE_FILE" <<'PYEOF' || { echo "failed to generate OAuth URL" >&2; return 1; }
import base64, hashlib, json, os, secrets, sys, urllib.parse

pkce_path = sys.argv[1]
# gcloud's "application-default login" client — ships with every gcloud install.
# The redirect URL is a Google-hosted page that displays a copyable verification
# code after sign-in (so no local server or URL-bar extraction is needed).
client_id = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
client_secret = "d-FL95Q19q7MQmFpd7hHD0Ty"
redirect_uri = "https://sdk.cloud.google.com/applicationdefaultauthcode.html"
scope = "https://www.googleapis.com/auth/cloud-platform"

verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
challenge = base64.urlsafe_b64encode(
    hashlib.sha256(verifier.encode()).digest()
).decode().rstrip("=")

url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
    "response_type": "code",
    "client_id": client_id,
    "redirect_uri": redirect_uri,
    "scope": scope,
    "code_challenge": challenge,
    "code_challenge_method": "S256",
    "access_type": "offline",
    "prompt": "consent",
})
print(url)

os.makedirs(os.path.dirname(pkce_path), exist_ok=True)
with open(pkce_path, "w") as f:
    json.dump({
        "client_id": client_id,
        "client_secret": client_secret,
        "code_verifier": verifier,
        "redirect_uri": redirect_uri,
    }, f)
PYEOF
  echo ""
  echo "Then re-source with:  AUTH_CODE='<the 4/0... code>' source ${BASH_SOURCE[0]}"
  return 2
fi

# --- Activate --------------------------------------------------------------
export GOOGLE_APPLICATION_CREDENTIALS="$_ADC_FILE"
# CLOUDSDK_CORE_PROJECT is read by the gcloud CLI; GOOGLE_CLOUD_PROJECT is
# read by the google-cloud-python clients (bigquery, etc.). Set both.
export CLOUDSDK_CORE_PROJECT="plantstory"
export GOOGLE_CLOUD_PROJECT="plantstory"
# shellcheck disable=SC1091
source "$_VENV_DIR/bin/activate"

echo ""
echo "sandbox ready — gcloud=$(command -v gcloud) venv=$VIRTUAL_ENV adc=$GOOGLE_APPLICATION_CREDENTIALS"

# Tidy internal vars
unset _SANDBOX_DIR _ROOT_DIR _GCLOUD_BIN _VENV_DIR _ADC_FILE _PKCE_FILE _UV_CACHE _TARBALL _need_install
