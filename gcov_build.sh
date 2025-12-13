#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# gcov_build.sh
# - script location: c2a-core/gcov_build.sh
# - build/run must be done for: c2a-core/examples/mobc
# - coverage target dir should be: c2a-core/target
# ------------------------------------------------------------

# 스크립트가 있는 디렉터리 = c2a-core
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBC_DIR="${ROOT_DIR}/examples/mobc"
MANIFEST="${MOBC_DIR}/Cargo.toml"

# cargo target 디렉터리를 repo root로 고정 (./target == c2a-core/target)
export CARGO_TARGET_DIR="${ROOT_DIR}/target"

# (C/C++ 코드/빌드가 섞여있을 때만 의미 있음. 있어도 무해)
export CC=gcc
export CXX=g++
export CFLAGS="--coverage -O0"
export CXXFLAGS="--coverage -O0"

# 중요: Rust는 LDFLAGS 무시 -> RUSTFLAGS로 링크 인자 전달
export RUSTFLAGS="-C link-arg=--coverage -C link-arg=-lgcov"

echo "[*] ROOT_DIR=${ROOT_DIR}"
echo "[*] MOBC_DIR=${MOBC_DIR}"
echo "[*] CARGO_TARGET_DIR=${CARGO_TARGET_DIR}"

# 1) 완전 클린 (mobc 크레이트 기준으로 clean)
cargo clean --manifest-path "${MANIFEST}"

# 2) 빌드 (반드시 mobc 기준)
cargo build --manifest-path "${MANIFEST}"

# 3) 초기(베이스라인) 커버리지 캡처: c2a-core/target을 스캔
lcov --capture --initial \
  --directory "${CARGO_TARGET_DIR}" \
  --output-file "${CARGO_TARGET_DIR}/coverage_base.info"

# 4) 실행 (mobc 기준)
cd ${MOBC_DIR}
pnpm run devtools:sils

