#!/usr/bin/env bash
# Build, sign, and verify the Florabase Android release APK.
# Reads keystore path and credentials strictly from environment variables.
# Refuses to emit florabase-<version>.apk unless signed and verified via apksigner.

set -euo pipefail
set +x

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SKIP_SYNC=false
for arg in "$@"; do
  case "$arg" in
    --skip-sync)
      SKIP_SYNC=true
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 2
      ;;
  esac
done

REQUIRED_VARS=(
  FLORABASE_ANDROID_KEYSTORE
  FLORABASE_ANDROID_STORE_PASSWORD
  FLORABASE_ANDROID_KEY_ALIAS
  FLORABASE_ANDROID_KEY_PASSWORD
)

MISSING_VARS=()
for var_name in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var_name:-}" ]; then
    MISSING_VARS+=("$var_name")
  fi
done

if [ "${#MISSING_VARS[@]}" -gt 0 ]; then
  echo "Android release signing environment variables are missing: ${MISSING_VARS[*]}" >&2
  echo "Set all four variables (FLORABASE_ANDROID_KEYSTORE, FLORABASE_ANDROID_STORE_PASSWORD, FLORABASE_ANDROID_KEY_ALIAS, FLORABASE_ANDROID_KEY_PASSWORD) to build a signed release APK." >&2
  echo "See docs/mobile.md for one-time keystore creation and signing instructions." >&2
  exit 1
fi

if [ ! -f "$FLORABASE_ANDROID_KEYSTORE" ]; then
  echo "Android keystore file not found at FLORABASE_ANDROID_KEYSTORE path." >&2
  exit 1
fi

SDK_DIR="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}}"
if [ ! -d "$SDK_DIR" ]; then
  echo "Android SDK not found (set ANDROID_HOME; see docs/mobile.md)." >&2
  exit 1
fi
export ANDROID_HOME="$SDK_DIR"
export ANDROID_SDK_ROOT="$SDK_DIR"

APKSIGNER="$(find "$SDK_DIR/build-tools" -maxdepth 2 -type f -name apksigner 2>/dev/null | sort -V | tail -n 1 || true)"
if [ -z "$APKSIGNER" ] || [ ! -x "$APKSIGNER" ]; then
  echo "apksigner not found under $SDK_DIR/build-tools (install build-tools;36.0.0; see docs/mobile.md)." >&2
  exit 1
fi

VERSION_NAME="$(python3 scripts/mobile_version.py --version-name)"
VERSION_CODE="$(python3 scripts/mobile_version.py --version-code)"

if [ "$SKIP_SYNC" != "true" ]; then
  # Always rebuild frontend/dist with debug HTTP disabled so debug dist never leaks into a release APK.
  make mobile-sync MOBILE_DEBUG_HTTP=false
fi

RELEASE_OUT_DIR="$ROOT_DIR/mobile/android/app/build/outputs/apk/release"
rm -f "$RELEASE_OUT_DIR/florabase-${VERSION_NAME}.apk" "$RELEASE_OUT_DIR/florabase-${VERSION_NAME}.apk.sha256"

(cd "$ROOT_DIR/mobile/android" && ./gradlew assembleRelease)

SIGNED_RAW_APK="$RELEASE_OUT_DIR/app-release.apk"
if [ ! -f "$SIGNED_RAW_APK" ]; then
  echo "Signed release APK not produced at $SIGNED_RAW_APK (unsigned builds are rejected for release output)." >&2
  exit 1
fi

echo "Verifying APK signature with $APKSIGNER..."
VERIFY_OUTPUT="$("$APKSIGNER" verify --print-certs "$SIGNED_RAW_APK")"
printf '%s\n' "$VERIFY_OUTPUT"

CERT_SHA256="$(printf '%s\n' "$VERIFY_OUTPUT" | awk -F': ' '/Signer #1 certificate SHA-256 digest:/ {print tolower($2); exit}' | tr -d '[:space:]:')"
if [ -z "$CERT_SHA256" ]; then
  echo "Could not parse Signer #1 certificate SHA-256 digest from apksigner output." >&2
  exit 1
fi

if [ -n "${FLORABASE_ANDROID_CERT_SHA256:-}" ]; then
  EXPECTED_CERT_SHA256="$(printf '%s' "$FLORABASE_ANDROID_CERT_SHA256" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]:')"
  if [ "$CERT_SHA256" != "$EXPECTED_CERT_SHA256" ]; then
    echo "Signing certificate SHA-256 mismatch!" >&2
    echo "  Expected (FLORABASE_ANDROID_CERT_SHA256): $EXPECTED_CERT_SHA256" >&2
    echo "  Actual (APK signer #1):                   $CERT_SHA256" >&2
    exit 1
  fi
  echo "Signer certificate SHA-256 matches FLORABASE_ANDROID_CERT_SHA256."
fi

FINAL_APK="$RELEASE_OUT_DIR/florabase-${VERSION_NAME}.apk"
FINAL_SHA="$RELEASE_OUT_DIR/florabase-${VERSION_NAME}.apk.sha256"

cp -f "$SIGNED_RAW_APK" "$FINAL_APK"
(cd "$RELEASE_OUT_DIR" && sha256sum "florabase-${VERSION_NAME}.apk" > "florabase-${VERSION_NAME}.apk.sha256")

APK_SHA256="$(awk '{print $1}' "$FINAL_SHA")"
echo "Release APK:   $FINAL_APK"
echo "Version:       ${VERSION_NAME} (versionCode ${VERSION_CODE})"
echo "Signer SHA256: $CERT_SHA256"
echo "APK SHA-256:   $APK_SHA256"
