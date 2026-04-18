#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_UV_DIR="$ROOT_DIR/.local/uv"
LOCAL_UV_BIN="$LOCAL_UV_DIR/uv"
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
CODEX_CONFIG_FILE="$CODEX_HOME_DIR/config.toml"
DEFAULT_GCLOUD_PROJECT="plantstory"

cd "$ROOT_DIR"

install_uv() {
  mkdir -p "$LOCAL_UV_DIR"

  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL="$LOCAL_UV_DIR" sh
    return
  fi

  if command -v wget >/dev/null 2>&1; then
    wget -qO- https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL="$LOCAL_UV_DIR" sh
    return
  fi

  echo "Error: uv is not installed, and neither curl nor wget is available to install it." >&2
  exit 1
}

upsert_root_key() {
  local file="$1"
  local key="$2"
  local value="$3"
  local tmp_file

  tmp_file="$(mktemp)"

  awk -v key="$key" -v value="$value" '
    BEGIN {
      inserted = 0
      replaced = 0
    }
    {
      if ($0 ~ "^" key "[[:space:]]*=") {
        if (!replaced) {
          print key " = " value
          replaced = 1
        }
        next
      }

      if (!inserted && !replaced && $0 ~ /^\[/) {
        print key " = " value
        print ""
        inserted = 1
      }

      print
    }
    END {
      if (!replaced && !inserted) {
        print key " = " value
      }
    }
  ' "$file" > "$tmp_file"

  mv "$tmp_file" "$file"
}

ensure_section_block() {
  local file="$1"
  local header="$2"
  local body="$3"
  local tmp_file

  tmp_file="$(mktemp)"

  awk -v header="$header" -v body="$body" '
    BEGIN {
      in_target = 0
      replaced = 0
      line_count = split(body, lines, "\n")
    }
    {
      if ($0 == header) {
        if (!replaced) {
          print header
          for (i = 1; i <= line_count; i++) {
            if (length(lines[i])) {
              print lines[i]
            }
          }
          print ""
          replaced = 1
        }
        in_target = 1
        next
      }

      if (in_target) {
        if ($0 ~ /^\[/) {
          in_target = 0
          print $0
        }
        next
      }

      print
    }
    END {
      if (!replaced) {
        if (NR > 0) {
          print ""
        }
        print header
        for (i = 1; i <= line_count; i++) {
          if (length(lines[i])) {
            print lines[i]
          }
        }
      }
    }
  ' "$file" > "$tmp_file"

  mv "$tmp_file" "$file"
}

setup_codex_config() {
  local project_header='[projects."'"$ROOT_DIR"'"]'
  local plugin_header='[plugins."computer-use@openai-bundled"]'
  local sandbox_header='[sandbox_workspace_write]'

  mkdir -p "$CODEX_HOME_DIR"

  if [ -f "$CODEX_CONFIG_FILE" ] && [ ! -f "$CODEX_CONFIG_FILE.bak.pre-bootstrap" ]; then
    cp "$CODEX_CONFIG_FILE" "$CODEX_CONFIG_FILE.bak.pre-bootstrap"
  fi

  touch "$CODEX_CONFIG_FILE"

  upsert_root_key "$CODEX_CONFIG_FILE" "model" '"gpt-5.4"'
  upsert_root_key "$CODEX_CONFIG_FILE" "model_reasoning_effort" '"medium"'
  upsert_root_key "$CODEX_CONFIG_FILE" "sandbox_mode" '"workspace-write"'

  ensure_section_block "$CODEX_CONFIG_FILE" "$project_header" 'trust_level = "trusted"'
  ensure_section_block "$CODEX_CONFIG_FILE" "$plugin_header" 'enabled = true'
  ensure_section_block "$CODEX_CONFIG_FILE" "$sandbox_header" 'network_access = true'

  echo "Codex config updated at $CODEX_CONFIG_FILE"

  if [ ! -f "$CODEX_HOME_DIR/auth.json" ]; then
    echo "Codex auth is not set up yet. Open the Codex Desktop app and sign in once on this machine."
  fi
}

ensure_gcloud_adc() {
  local current_project

  if ! command -v gcloud >/dev/null 2>&1; then
    echo "Error: gcloud is required but was not found in PATH." >&2
    echo "Install Google Cloud SDK, then rerun ./setup.sh." >&2
    exit 1
  fi

  if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
    echo "Sandbox gcloud ADC not found. Starting login flow..."
    gcloud auth application-default login
  fi

  current_project="$(gcloud config get-value project 2>/dev/null | tr -d '\r' | xargs || true)"
  if [ -z "$current_project" ] || [ "$current_project" = "(unset)" ]; then
    echo "Setting default gcloud project to $DEFAULT_GCLOUD_PROJECT"
    gcloud config set project "$DEFAULT_GCLOUD_PROJECT"
  fi
}

if command -v uv >/dev/null 2>&1; then
  UV_BIN="$(command -v uv)"
elif [ -x "$LOCAL_UV_BIN" ]; then
  UV_BIN="$LOCAL_UV_BIN"
else
  echo "uv not found. Installing a project-local copy into $LOCAL_UV_DIR ..."
  install_uv
  UV_BIN="$LOCAL_UV_BIN"
fi

setup_codex_config

UV_CACHE_DIR=.uv-cache "$UV_BIN" sync
ensure_gcloud_adc

echo
echo "Environment is ready."
echo "Codex project trust and plugin settings are configured."
echo "Sandbox gcloud ADC is ready."
echo "Activate with: source .venv/bin/activate"
