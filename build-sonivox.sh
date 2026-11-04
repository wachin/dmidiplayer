#!/bin/sh
# Build the native Sonivox EAS synthesizer used by drumstick_py.sonivox.
#
# The Python backend is a ctypes wrapper around this C library.  Keeping the
# DSP native preserves the exact samples, realtime behaviour and timing of the
# C++ dmidiplayer/Drumstick backend.  The resulting library is discovered by
# drumstick_py.sonivox automatically.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE="$ROOT/Linux-SonivoxEas-devel/sonivox"
BUILD="$ROOT/Linux-SonivoxEas-devel/build/sonivox"

if [ ! -f "$SOURCE/CMakeLists.txt" ]; then
    echo "Sonivox source tree not found: $SOURCE" >&2
    exit 1
fi

cmake -S "$SOURCE" -B "$BUILD" \
    -DUSE_44KHZ=ON \
    -DUSE_16BITS_SAMPLES=ON \
    -DBUILD_SHARED_LIBS=ON \
    -DBUILD_TESTING=OFF \
    -DBUILD_APPLICATION=OFF \
    -DCMAKE_BUILD_TYPE=Release
cmake --build "$BUILD" -j"$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)"

echo
echo "Built: $BUILD/libsonivox.so"
echo "Start dmidiplayer-py normally; the SonivoxEAS driver is preferred."
