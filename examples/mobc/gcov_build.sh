#cargo clean

export CC=gcc
export CXX=g++
export CFLAGS="--coverage -O0"
export CXXFLAGS="--coverage -O0"

# 중요 -> Rust는 LDFLAGS를 무시함.
export RUSTFLAGS="-C link-arg=--coverage -C link-arg=-lgcov"

# 이후 빌드
cargo build        # 또는 cargo run

lcov --capture --initial --directory ./target --output-file ./target/coverage_base.info

cargo run

