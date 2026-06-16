# Git Release Checklist

Use this before pushing the project to a repository.

## Required Files

- `README.md`
- `LICENSE`
- `package.json`
- `package-lock.json`
- `tsconfig.json`
- `src/`
- `scripts/`
- `config/example.json`
- `systemd/vbus-friwa-gateway.service`
- `docs/EDOMI_HANDOFF.md`
- `docs/RESOL_RSC_PROFILE.md`
- `docs/LICENSES.md`

## Generated Or Local Files

Do not commit:

- `node_modules/`
- `dist/`, unless the target repo intentionally ships built JavaScript.
- `generated/`
- `vendor/resol-rsc/*.xml`
- downloaded RESOL ZIP/EXE files
- local `/etc/vbus-friwa-gateway/config.json`
- secrets, tokens, TLS private keys, or real passwords
- temporary read-all logs unless they are intentionally kept as examples

Decide before public release:

- Whether `profiles/friwa-0x7611.json` may be redistributed.
- Whether generated IO maps and EDOMI LBS files may be redistributed.
- If not, exclude them and require users to generate them locally from their RESOL RSC download.

## Validation

Run:

```bash
npm install
npm run extract:resol -- --archive /path/to/RSC.zip
npm run generate:profile
npm run generate:edomi:full
npm run generate:edomi:light
npm run build
npm run check
php -d display_errors=1 -l -n generated/edomi/LBS/19100832/19100832_lbs.php
php -d display_errors=1 -l -n generated/edomi/LBS/19100833/19100833_lbs.php
```

Optional hardware/API tests on a FriWa node:

```bash
vbus-test --config /etc/vbus-friwa-gateway/config.json --read 0x0130
vbus-test --config /etc/vbus-friwa-gateway/config.json --read --all
```

## Security Before Release

- Change default `admin:admin` in production.
- Use Bearer token or TLS if the gateway is reachable beyond a trusted LAN.
- Never commit TLS private keys.
- Keep `writes.enabled` configurable.
- Use `writes.deny` for values that should not be writable in a given installation.

## EDOMI Import

Full block:

```text
generated/edomi/LBS/19100832/19100832_lbs.php
```

Light block:

```text
generated/edomi/LBS/19100833/19100833_lbs.php
```

The Light block is the recommended first import for normal use.
