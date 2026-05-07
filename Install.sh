#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 기본 설정
PYTHON_VERSION="3.11"
INSTALL_DIR="$HOME/.libpyl"
GITHUB_REPO="danidevlab/Lib.pyl"
GITHUB_API="https://api.github.com/repos/$GITHUB_REPO/releases/latest"

echo -e "${GREEN}=== Lib.pyl 런타임 설치 시작 ===${NC}"

# 1. OS 감지
OS="$(uname -s)"
case $OS in
  Linux*)   OS_TYPE="Linux";;
  Darwin*)  OS_TYPE="Darwin";;
  *)        OS_TYPE="UNKNOWN";;
esac

echo -e "${YELLOW}운영체제: $OS_TYPE${NC}"

# 2. 다운로드 URL 확인
echo -e "${YELLOW}최신 릴리스 확인 중...${NC}"
DOWNLOAD_URL=$(curl -fsSL $GITHUB_API | grep '"browser_download_url"' | cut -d'"' -f4 | head -1)

if [ -z "$DOWNLOAD_URL" ]; then
  echo -e "${RED}다운로드 URL을 찾을 수 없습니다.${NC}"
  exit 1
fi

echo -e "${GREEN}다운로드 URL: $DOWNLOAD_URL${NC}"

# 3. 설치 디렉토리 생성
mkdir -p "$INSTALL_DIR"
echo -e "${GREEN}설치 디렉토리 생성: $INSTALL_DIR${NC}"

# 4. 파일 다운로드
echo -e "${YELLOW}파일 다운로드 중...${NC}"
DOWNLOAD_FILE="$INSTALL_DIR/libpyl.tar.gz"
curl -fsSL -o "$DOWNLOAD_FILE" "$DOWNLOAD_URL"

if [ ! -f "$DOWNLOAD_FILE" ]; then
  echo -e "${RED}다운로드 실패${NC}"
  exit 1
fi

echo -e "${GREEN}다운로드 완료${NC}"

# 5. 압축 해제
echo -e "${YELLOW}압축 해제 중...${NC}"
tar -xzf "$DOWNLOAD_FILE" -C "$INSTALL_DIR"
rm "$DOWNLOAD_FILE"
echo -e "${GREEN}압축 해제 완료${NC}"

# 6. 실행 권한 설정
chmod +x "$INSTALL_DIR/libpyl"
echo -e "${GREEN}실행 권한 설정 완료${NC}"

# 7. PATH에 추가
SHELL_RC=""
if [ -f "$HOME/.bashrc" ]; then
  SHELL_RC="$HOME/.bashrc"
elif [ -f "$HOME/.zshrc" ]; then
  SHELL_RC="$HOME/.zshrc"
fi

if [ ! -z "$SHELL_RC" ] && ! grep -q ".libpyl" "$SHELL_RC"; then
  echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$SHELL_RC"
  echo -e "${GREEN}PATH 환경변수 설정 완료${NC}"
fi

# 8. 바탕화면 바로가기 생성 (Linux)
if [ "$OS_TYPE" = "Linux" ] && [ -d "$HOME/Desktop" ]; then
  cat > "$HOME/Desktop/Lib.pyl.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Lib.pyl
Icon=$INSTALL_DIR/libpyl.png
Exec=$INSTALL_DIR/libpyl
Terminal=true
Categories=Development;
EOF
  chmod +x "$HOME/Desktop/Lib.pyl.desktop"
  echo -e "${GREEN}바탕화면 바로가기 생성 완료${NC}"
fi

# 9. macOS 바로가기 생성
if [ "$OS_TYPE" = "Darwin" ] && [ -d "$HOME/Applications" ]; then
  mkdir -p "$HOME/Applications/Lib.pyl.app/Contents/MacOS"
  cp "$INSTALL_DIR/libpyl" "$HOME/Applications/Lib.pyl.app/Contents/MacOS/"
  echo -e "${GREEN}macOS 애플리케이션 바로가기 생성 완료${NC}"
fi

echo -e "${GREEN}=== 설치 완료 ===${NC}"
echo -e "${YELLOW}다음 명령어로 확인하세요:${NC}"
echo -e "${GREEN}$INSTALL_DIR/libpyl --version${NC}"
echo -e "${YELLOW}새 터미널을 열거나 다음을 실행하세요:${NC}"
echo -e "${GREEN}source $SHELL_RC${NC}"
