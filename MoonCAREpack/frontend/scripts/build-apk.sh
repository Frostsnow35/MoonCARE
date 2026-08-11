#!/bin/sh
# MoonCARE APK build script.
#
# Builds the Capacitor Android project and produces an APK you can side-load
# directly onto an Android phone (no store needed).
#
# Usage:
#   cd frontend
#   npm run apk                 # debug APK (fast, no signing)
#   npm run apk -- --release    # release APK (needs a keystore, see below)
#   npm run apk -- --server http://1.2.3.4:18000   # bundle a default server
#
# Requirements on the build machine (your own PC or a server):
#   - Node.js 20+, npm 10+
#   - JDK 17 or 21  (Capacitor 8 requires JDK 21 to compile; 17 works for APK 8.5)
#   - Android SDK with platform 36 and build-tools; ANDROID_HOME or local.properties
#   - For release builds: a generated keystore (see scripts/create-keystore.sh)
#
# The APK will be written to frontend/android/app/build/outputs/apk/<buildtype>/.

set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$APP_DIR"

BUILD_TYPE="debug"
DEFAULT_SERVER=""
SIGNING_KEYSTORE=""
SIGNING_PASSWORD=""
SIGNING_ALIAS=""

# ---- parse args ------------------------------------------------------------
for arg in "$@"; do
  case "$arg" in
    --release) BUILD_TYPE="release" ;;
    --server=*) DEFAULT_SERVER="${arg#*=}" ;;
    --server) shift; DEFAULT_SERVER="${1:-}" ;;
    --keystore=*) SIGNING_KEYSTORE="${arg#*=}" ;;
    --keystore) shift; SIGNING_KEYSTORE="${1:-}" ;;
    --store-pass=*) SIGNING_PASSWORD="${arg#*=}" ;;
    --alias=*) SIGNING_ALIAS="${arg#*=}" ;;
    --alias) shift; SIGNING_ALIAS="${1:-}" ;;
    -h|--help)
      sed -n '1,20p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
  esac
done

# ---- build the web assets --------------------------------------------------
echo ">> Building frontend web assets..."
npm run build

# ---- optional: bake a default server URL into the web build ----------------
if [ -n "$DEFAULT_SERVER" ]; then
  echo ">> Baking default server address: $DEFAULT_SERVER"
  # Store it so the app can pre-fill / connect on first launch. It can still be
  # overridden later from Profile -> 服务器地址.
  cat > /tmp/mooncare-server-probe.js <<EOF
try {
  const key = 'mooncare_server_base'
  if (!localStorage.getItem(key)) {
    localStorage.setItem(key, '${DEFAULT_SERVER}')
  }
} catch (e) {}
EOF
  # Inject into index.html before the app bundle (works for Capacitor + PWA).
  INJECTED="<script>$(cat /tmp/mooncare-server-probe.js)</script>"
  if ! grep -q 'mooncare_server_base' dist/index.html; then
    sed -i "s|<div id=\"app\"></div>|<div id=\"app\"></div>${INJECTED}|" dist/index.html
  fi
fi

# ---- ensure Capacitor Android platform exists ------------------------------
if [ ! -d "android" ]; then
  echo ">> Adding Capacitor Android platform..."
  npx cap add android
fi

echo ">> Syncing web assets into android/ ..."
npx cap sync android

# ---- Android runtime hardening ----------------------------------------------
# The app is a remote-first WebView: it talks to an http://<server-ip> origin.
# Capacitor only writes usesCleartextTraffic for Cordova-plugin projects, so we
# patch the generated manifest explicitly. Also add INTERNET (already present)
# and keep the app installable even when the shell is served over https.
MANIFEST="android/app/src/main/AndroidManifest.xml"
if [ -f "$MANIFEST" ]; then
  if ! grep -q 'usesCleartextTraffic="true"' "$MANIFEST"; then
    sed -i 's|<application |<application android:usesCleartextTraffic="true" |' "$MANIFEST"
    echo ">> Patched AndroidManifest.xml with android:usesCleartextTraffic=\"true\""
  fi
  if ! grep -q 'android.permission.INTERNET' "$MANIFEST"; then
    sed -i 's|</manifest>|<uses-permission android:name="android.permission.INTERNET" />\n</manifest>|' "$MANIFEST"
  fi
fi

# ---- Android SDK discovery -------------------------------------------------
if [ -z "${ANDROID_HOME:-}" ] && [ -f "android/local.properties" ]; then
  echo ">> Using android/local.properties for SDK location."
fi

# ---- build -----------------------------------------------------------------
cd android

if [ "$BUILD_TYPE" = "release" ]; then
  echo ">> Building release APK..."
  if [ -n "$SIGNING_KEYSTORE" ]; then
    # Write signing config into the project if not already present.
    KEYSTORE_ABS="$(CDPATH= cd -- "$(dirname -- "$SIGNING_KEYSTORE")" && pwd)/$(basename -- "$SIGNING_KEYSTORE")"
    STORE_PASS="${SIGNING_PASSWORD:-}"
    ALIAS="${SIGNING_ALIAS:-mooncare}"
    if [ -z "$STORE_PASS" ]; then
      echo "ERROR: --store-pass is required for a signed release build." >&2
      exit 1
    fi
    cat > signing.gradle <<EOF
android {
    signingConfigs {
        release {
            storeFile file('${KEYSTORE_ABS}')
            storePassword '${STORE_PASS}'
            keyAlias '${ALIAS}'
            keyPassword '${STORE_PASS}'
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
        }
    }
}
EOF
    if ! grep -q "apply from: 'signing.gradle'" app/build.gradle; then
      echo "apply from: '../signing.gradle'" >> app/build.gradle
    fi
    echo ">> Signing config applied from $KEYSTORE_ABS (alias=$ALIAS)"
  else
    echo ">> No keystore provided; building an UNSIGNED release APK."
  fi
  ./gradlew assembleRelease
  APK_DIR="app/build/outputs/apk/release"
else
  echo ">> Building debug APK..."
  ./gradlew assembleDebug
  APK_DIR="app/build/outputs/apk/debug"
fi

cd "$APP_DIR"

echo ""
echo "======================================================"
echo " Build finished."
find "android/$APK_DIR" -name "*.apk" -exec ls -lh {} \;
echo "======================================================"
echo "Install to a connected phone:"
echo "  adb install android/$APK_DIR/app-$BUILD_TYPE.apk"
echo ""
echo "Or copy the APK to your phone and open it (enable 'Install unknown apps')."
echo "Default server baked: ${DEFAULT_SERVER:-none (user sets it on the Login screen)}"
