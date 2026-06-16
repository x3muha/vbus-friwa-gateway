#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  npm run extract:resol -- --archive /path/to/RSC.zip
  npm run extract:resol -- --archive /path/to/ServiceCenterFullSetup.exe

This script extracts only the XML files needed to generate the FriWa profile:
  - MenuFriwa_1.0.xml
  - VBusSpecificationResol.xml

Download the RESOL RSC package yourself from:
  https://www.resol.de/de/produktdetail/170
EOF
}

archive=""
out_dir="vendor/resol-rsc"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --archive)
      archive="${2:-}"
      shift 2
      ;;
    --out)
      out_dir="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$archive" ]]; then
  echo "Missing --archive" >&2
  usage >&2
  exit 2
fi

if [[ ! -f "$archive" ]]; then
  echo "Archive not found: $archive" >&2
  exit 1
fi

if ! command -v 7z >/dev/null 2>&1; then
  echo "7z is required. Install p7zip/7zip first." >&2
  exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$out_dir"
7z x -y "$archive" "-o$tmp/root" >/dev/null

setup="$(find "$tmp/root" -type f \( -iname '*ServiceCenter*Setup*.exe' -o -iname 'ServiceCenterFullSetup.exe' \) | head -n 1 || true)"
if [[ -n "$setup" ]]; then
  7z x -y "$setup" "-o$tmp/setup" >/dev/null
  search_root="$tmp/setup"
else
  search_root="$tmp/root"
fi

menu_xml="$(find "$search_root" -type f -name 'MenuFriwa_1.0.xml' | head -n 1 || true)"
vbus_xml="$(find "$search_root" -type f -name 'VBusSpecificationResol.xml' | head -n 1 || true)"

if [[ -z "$menu_xml" || -z "$vbus_xml" ]]; then
  echo "Required XML files not found." >&2
  echo "MenuFriwa_1.0.xml: ${menu_xml:-missing}" >&2
  echo "VBusSpecificationResol.xml: ${vbus_xml:-missing}" >&2
  exit 1
fi

cp "$menu_xml" "$out_dir/MenuFriwa_1.0.xml"
cp "$vbus_xml" "$out_dir/VBusSpecificationResol.xml"

echo "Extracted:"
echo "  $out_dir/MenuFriwa_1.0.xml"
echo "  $out_dir/VBusSpecificationResol.xml"
echo
echo "Next:"
echo "  npm run generate:profile"
