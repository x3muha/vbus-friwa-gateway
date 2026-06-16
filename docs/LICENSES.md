# Licenses And Source Data

## Project License

The source code in this repository is intended to be released under the MIT License.

See:

```text
LICENSE
```

## Runtime Dependencies

The dependency license data below is taken from `package-lock.json`.

| Package | Version | License | Link |
|---|---:|---|---|
| `resol-vbus-core` | 0.6.0 | MIT | https://codeberg.org/DanielWippermann/resol-vbus-core |
| `serialport` | 13.0.0 | MIT | https://github.com/serialport/node-serialport |
| `ws` | 8.21.0 | MIT | https://github.com/websockets/ws |

Important transitive dependencies:

| Package | Version | License | Link |
|---|---:|---|---|
| `typescript` | 5.9.3 | Apache-2.0 | https://github.com/microsoft/TypeScript |
| `@types/node` | 24.13.2 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped |
| `@types/ws` | 8.18.1 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped |
| `@serialport/*` | 10.x/12.x/13.x | MIT | https://github.com/serialport/node-serialport |
| `debug` | 4.4.0 | MIT | https://github.com/debug-js/debug |
| `ms` | 2.1.3 | MIT | https://github.com/vercel/ms |
| `node-addon-api` | 8.3.0 | MIT | https://github.com/nodejs/node-addon-api |
| `node-gyp-build` | 4.8.4 | MIT | https://github.com/prebuild/node-gyp-build |
| `undici-types` | 7.18.2 | MIT | https://github.com/nodejs/undici |

Primary upstream links:

- `typescript`: https://github.com/microsoft/TypeScript
- `@serialport/*`: https://github.com/serialport/node-serialport
- `@types/*`: https://github.com/DefinitelyTyped/DefinitelyTyped

Dependencies are not vendored as source code in this repository. They are installed by npm from `package.json` / `package-lock.json`.

Before a public release, verify this list again with the final `package-lock.json`.

## RESOL / PAW Device Data

The gateway profile `profiles/friwa-0x7611.json` was generated from local RESOL ServiceCenter XML files:

```text
MenuFriwa_1.0.xml
VBusSpecificationResol.xml
```

The profile contains derived device metadata such as value indexes, labels, ranges, units, scaling factors, and VBus live packet structure.

Important:

- The gateway source code is project code.
- `resol-vbus-core` is an external MIT-licensed dependency.
- The RESOL/PAW XML files and any generated profile derived from them may be subject to RESOL/PAW rights or distribution terms.
- For a private repository or local installation this is normally a practical engineering concern.
- For a public GitHub release, clarify whether the generated profile may be redistributed, or document that users must generate it locally from their own RESOL ServiceCenter files.

Safe public-release option:

1. Keep `scripts/extract_resol_rsc_xml.sh`.
2. Keep `scripts/generate_friwa_profile.py`.
3. Keep documentation explaining where users download RSC themselves.
4. Exclude RESOL XML files and downloaded installers.
5. Exclude generated derived mapping artifacts if redistribution is not cleared:
   - `profiles/friwa-0x7611.json`
   - `docs/IO_MAP.md`
   - `docs/IO_MAP_LIGHT.md`
   - generated EDOMI LBS files
6. Let users run the local generation flow:

```bash
npm run extract:resol -- --archive /path/to/RSC.zip
npm run generate:profile
npm run generate:edomi:full
npm run generate:edomi:light
```

Current local development state:

- The generated profile is included locally because it is required for the current FriWa gateway and EDOMI LBS generation.
- Before publishing publicly, decide whether generated mapping artifacts stay in Git or are generated during setup.

## EDOMI LBS Files

Generated EDOMI LBS files under `generated/edomi/LBS/` are generated from this project's profile and generator.

They are intended to follow the same project license as the gateway code, unless a future repository chooses a different explicit license.
