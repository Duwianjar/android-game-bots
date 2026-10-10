#!/bin/bash

# Script untuk menginstall Gradle Wrapper
# Digunakan jika gradle CLI tidak tersedia di sistem

set -e

GRADLE_VERSION="8.1.2"
GRADLE_URL="https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip"
GRADLE_ZIP="gradle-${GRADLE_VERSION}-bin.zip"

echo "======================================"
echo "Installing Gradle Wrapper v${GRADLE_VERSION}"
echo "======================================"
echo ""

# Check if already installed
if [ -f "android/gradlew" ]; then
    echo "✅ Gradle wrapper sudah terinstall"
    echo ""
    echo "Testing gradle wrapper..."
    cd android
    ./gradlew --version
    exit 0
fi

# Create temp directory
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

echo "📥 Downloading Gradle ${GRADLE_VERSION}..."
curl -L -o "$GRADLE_ZIP" "$GRADLE_URL"

echo "📦 Extracting..."
unzip -q "$GRADLE_ZIP"

echo "🔧 Creating wrapper..."
cd "gradle-${GRADLE_VERSION}"
./bin/gradle wrapper --gradle-version "${GRADLE_VERSION}"

echo "📋 Copying wrapper files..."
cd "$OLDPWD"
ANDROID_DIR="$OLDPWD/../android"

# Copy wrapper files
cp -r "gradle-${GRADLE_VERSION}/gradlew" "$ANDROID_DIR/"
cp -r "gradle-${GRADLE_VERSION}/gradle" "$ANDROID_DIR/"

# Make executable
chmod +x "$ANDROID_DIR/gradlew"

# Cleanup
cd "$OLDPWD"
rm -rf "$TMP_DIR"

echo ""
echo "✅ Gradle wrapper berhasil diinstall!"
echo ""
echo "Testing..."
cd "$ANDROID_DIR"
./gradlew --version

echo ""
echo "======================================"
echo "✅ DONE!"
echo "======================================"
echo ""
echo "Sekarang Anda bisa build project dengan:"
echo "  cd android"
echo "  ./gradlew assembleDebug"
