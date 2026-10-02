#!/usr/bin/env bash
# Run INSIDE the Debian LXC as root, never on the Proxmox host.
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo 'Ejecuta este script como root dentro del LXC Debian.' >&2
  exit 1
fi
if command -v pveversion >/dev/null 2>&1; then
  echo 'Se ha detectado el host Proxmox. No se instalará Docker aquí; entra en el LXC.' >&2
  exit 1
fi
. /etc/os-release
if [ "$ID" != debian ] || [[ ! " ${VERSION_CODENAME:-} " =~ ^\ (bookworm|trixie)\ $ ]]; then
  echo 'Este script está preparado para Debian 12 (bookworm) o 13 (trixie).' >&2
  exit 1
fi
if command -v docker >/dev/null 2>&1; then
  docker compose version
  echo 'Docker ya está instalado; no se han sustituido sus paquetes.'
  exit 0
fi
# Conflicting packages require inspection, never automatic removal of existing engines.
for package in docker.io docker-compose podman-docker containerd runc; do
  if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed'; then
    echo "Existe un paquete potencialmente incompatible: $package. Revisa la instalación existente antes de continuar." >&2
    exit 1
  fi
done
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl gnupg python3
install -m 0755 -d /etc/apt/keyrings
key_tmp=$(mktemp)
trap 'rm -f "$key_tmp"' EXIT
curl --fail --silent --show-error --location https://download.docker.com/linux/debian/gpg -o "$key_tmp"
# Verify the official Docker signing-key fingerprint before trusting the key.
fingerprint=$(gpg --batch --show-keys --with-colons "$key_tmp" | awk -F: '$1=="fpr" {print $10; exit}')
if [ "$fingerprint" != '9DC858229FC7DD38854AE2D88D81803C0EBFCD88' ]; then
  echo 'La firma de Docker no coincide con la identidad esperada. No se instalará la clave.' >&2
  exit 1
fi
install -m 0644 "$key_tmp" /etc/apt/keyrings/docker.asc
arch=$(dpkg --print-architecture)
cat > /etc/apt/sources.list.d/docker.sources <<SOURCES
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: $VERSION_CODENAME
Components: stable
Architectures: $arch
Signed-By: /etc/apt/keyrings/docker.asc
SOURCES
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker version
docker compose version
