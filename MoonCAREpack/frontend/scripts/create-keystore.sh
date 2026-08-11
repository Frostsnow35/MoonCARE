#!/bin/sh
# Create a signing keystore for releasing the MoonCARE APK.
# Run once locally. Keep keystore-file and passwords safe; never commit them.
#
# Usage: sh scripts/create-keystore.sh
# Requires: keytool (bundled with JDK 17/21)

set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
KEYSTORE_PATH="${1:-$APP_DIR/android/mooncare-release.keystore}"
ALIAS="mooncare"
VALIDITY_DAYS=10000

echo ">> Generating release keystore at: $KEYSTORE_PATH"
echo ">> Alias: $ALIAS  (valid ${VALIDITY_DAYS} days)"

# keytool prompts for keystore + key passwords. Use the same password for both
# (required for the current signing.gradle template) and remember it.
keytool -genkeypair \
  -v \
  -keystore "$KEYSTORE_PATH" \
  -alias "$ALIAS" \
  -keyalg RSA \
  -keysize 2048 \
  -validity "$VALIDITY_DAYS"

echo ""
echo "Keystore created: $KEYSTORE_PATH"
echo ""
echo "Build a signed release APK with:"
echo "  cd frontend && npm run apk -- --release \\"
echo "    --keystore android/mooncare-release.keystore \\"
echo "    --store-pass '<YOUR_PASSWORD>' \\"
echo "    --alias mooncare"
echo ""
echo "IMPORTANT: back this keystore up somewhere safe. If you lose it you can"
echo "never publish an update to the same app signature."
