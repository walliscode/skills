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

snake_re='^[a-z][a-z0-9]*(_[a-z0-9]+)*$'
pascal_re='^[A-Z][a-zA-Z0-9]*$'

fail() {
  echo "new_cpp_file.sh: $1" >&2
  exit 1
}

if [[ ! "$name" =~ $snake_re && ! "$name" =~ $pascal_re ]]; then
  fail "name must be PascalCase or snake_case: $name"
fi

[[ "$dir" == /* ]] && fail "dir must be relative to the repo root: $dir"

dir="${dir%/}"
IFS='/' read -ra components <<< "$dir"
for component in "${components[@]}"; do
  [[ "$component" == ".." ]] && fail "dir must not contain '..': $dir"
  [[ "$component" =~ $snake_re ]] || fail "dir component must be snake_case: $component"
done

namespace="${dir//\//::}"

if [[ -e "$dir/$name.hpp" || -e "$dir/$name.cpp" ]]; then
  fail "refusing to overwrite existing file in $dir for $name"
fi

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
