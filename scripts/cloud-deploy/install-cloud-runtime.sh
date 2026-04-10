#!/usr/bin/env bash
set -euo pipefail

app_root="${APP_ROOT:-/opt/ielts-vocab/current}"
venv_dir="${VENV_DIR:-/opt/ielts-vocab/venv}"
web_root="${WEB_ROOT:-/var/www/ielts-vocab}"
env_dir="${ENV_DIR:-/etc/ielts-vocab}"

install_node20_from_tarball() {
  local node_arch=""
  case "$(uname -m)" in
    x86_64) node_arch="x64" ;;
    aarch64) node_arch="arm64" ;;
    *)
      echo "Unsupported architecture for Node.js 20: $(uname -m)" >&2
      return 1
      ;;
  esac

  local tmpdir
  tmpdir="$(mktemp -d)"
  local base_url="https://nodejs.org/dist/latest-v20.x"
  local archive_name
  archive_name="$(
    curl -fsSL "${base_url}/SHASUMS256.txt" \
      | awk "/node-v[0-9.]+-linux-${node_arch}\\.tar\\.xz/ { print \$2; exit }"
  )"
  if [[ -z "${archive_name}" ]]; then
    echo "Could not determine latest Node.js 20 archive for ${node_arch}" >&2
    rm -rf "${tmpdir}"
    return 1
  fi

  curl -fsSL "${base_url}/${archive_name}" -o "${tmpdir}/${archive_name}"
  rm -rf /opt/node20
  mkdir -p /opt/node20
  tar -xJf "${tmpdir}/${archive_name}" -C /opt/node20 --strip-components=1
  ln -sf /opt/node20/bin/node /usr/local/bin/node
  ln -sf /opt/node20/bin/npm /usr/local/bin/npm
  ln -sf /opt/node20/bin/npx /usr/local/bin/npx
  ln -sf /opt/node20/bin/corepack /usr/local/bin/corepack
  rm -rf "${tmpdir}"
}

configure_postgres_hba() {
  local hba_file="/var/lib/pgsql/data/pg_hba.conf"
  if [[ ! -f "${hba_file}" ]]; then
    return 0
  fi

  sed -ri 's/^host\s+all\s+all\s+127\.0\.0\.1\/32\s+\S+/host    all             all             127.0.0.1\/32            scram-sha-256/' "${hba_file}"
  sed -ri 's/^host\s+all\s+all\s+::1\/128\s+\S+/host    all             all             ::1\/128                 scram-sha-256/' "${hba_file}"
  sed -ri 's/^host\s+replication\s+all\s+127\.0\.0\.1\/32\s+\S+/host    replication     all             127.0.0.1\/32            scram-sha-256/' "${hba_file}"
  sed -ri 's/^host\s+replication\s+all\s+::1\/128\s+\S+/host    replication     all             ::1\/128                 scram-sha-256/' "${hba_file}"
}

dnf install -y git postgresql-server postgresql-contrib python3 python3-pip \
  python3-devel gcc gcc-c++ make openssl-devel libffi-devel tar curl cronie
dnf install -y --disableexcludes=all nginx

if ! dnf install -y certbot python3-certbot-nginx; then
  dnf install -y certbot
fi

if ! command -v node >/dev/null 2>&1 || [[ "$(node -p 'Number(process.versions.node.split(`.`)[0])' 2>/dev/null || echo 0)" -lt 20 ]]; then
  if ! curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -; then
    install_node20_from_tarball
  else
    dnf install -y nodejs || install_node20_from_tarball
  fi
fi

if [[ ! -d /var/lib/pgsql/data/base ]]; then
  postgresql-setup --initdb
fi
configure_postgres_hba

systemctl enable --now postgresql nginx crond
systemctl restart postgresql

mkdir -p "${env_dir}" "${web_root}" /var/backups/ielts-vocab/postgres
chmod 700 "${env_dir}" /var/backups/ielts-vocab

python3 -m venv "${venv_dir}"
"${venv_dir}/bin/pip" install --upgrade pip wheel
"${venv_dir}/bin/pip" install -r "${app_root}/backend/requirements.txt" -r "${app_root}/services/requirements.txt"
"${venv_dir}/bin/pip" install -e "${app_root}/packages/platform-sdk"

corepack enable
corepack prepare pnpm@9.0.0 --activate
pnpm --dir "${app_root}" install --frozen-lockfile
pnpm --dir "${app_root}" build
rm -rf "${web_root:?}/"*
cp -a "${app_root}/dist/." "${web_root}/"

chmod +x "${app_root}/scripts/cloud-deploy/"*.sh
cp "${app_root}/scripts/cloud-deploy/ielts-service@.service" /etc/systemd/system/
cp "${app_root}/scripts/cloud-deploy/ielts-vocab.nginx.conf" /etc/nginx/conf.d/ielts-vocab.conf

systemctl daemon-reload
nginx -t

cat >/etc/cron.d/ielts-vocab-postgres-backup <<'CRON'
17 3 * * * root /opt/ielts-vocab/current/scripts/cloud-deploy/backup-postgres.sh >/var/log/ielts-vocab-postgres-backup.log 2>&1
CRON

echo "Runtime installed. Ensure ${env_dir}/backend.env and ${env_dir}/microservices.env exist before starting services."
