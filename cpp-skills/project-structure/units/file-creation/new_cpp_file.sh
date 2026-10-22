#!/usr/bin/env bash
# Writes a matching .hpp and .cpp pair from fixed skeletons.
# Run from the repo root: new_cpp_file.sh --dir <dir> --name <name>
set -euo pipefail

usage() {
  echo "usage: new_cpp_file.sh --dir <repo-relative-dir> --name <name>" >&2
  exit 2
}

dir=""
name=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) dir="${2:-}"; shift 2 ;;
    --name) name="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done
[[ -n "$dir" && -n "$name" ]] || usage

dir="${dir%/}"
namespace="${dir//\//::}"

banner() {
  cat <<EOF
/**
 * @file ${name}.$1
 * @brief
 */
EOF
}

mkdir -p "$dir"

{
  banner hpp
  echo
  echo "#pragma once"
  echo
  echo "// headers"
  echo
  echo "namespace ${namespace} {"
  echo
  echo "}  // namespace ${namespace}"
} > "$dir/$name.hpp"

{
  banner cpp
  echo
  echo "// headers"
  echo
  echo "namespace ${namespace} {"
  echo
  echo "}  // namespace ${namespace}"
} > "$dir/$name.cpp"
