# Generate The FriWa Profile From RESOL RSC

This project does not need to redistribute RESOL RSC XML files.

Each user can download RESOL RSC from RESOL and generate the local profile from that package.

RESOL product page:

```text
https://www.resol.de/de/produktdetail/170
```

The page describes the ServiceCenter-Software RSC as software for visualization and remote parameterization of RESOL controllers and links the current RSC package in the Software tab.

At the time this project was prepared, the relevant link on that page was:

```text
https://www.resol.de/software/RSC/RSC.zip
```

## Required Local Tool

The extraction helper needs `7z`.

Debian/Raspberry Pi OS example:

```bash
sudo apt-get update
sudo apt-get install -y 7zip
```

Older distributions may call the package `p7zip-full`.

## Download Manually

Download RSC from the RESOL page and place the file somewhere local, for example:

```text
/tmp/RSC.zip
```

Do not commit the downloaded ZIP or EXE to Git.

## Extract The Needed XML Files

From the project directory:

```bash
npm run extract:resol -- --archive /tmp/RSC.zip
```

The script extracts exactly these local files:

```text
vendor/resol-rsc/MenuFriwa_1.0.xml
vendor/resol-rsc/VBusSpecificationResol.xml
```

The `vendor/resol-rsc/*.xml`, `*.zip`, `*.exe`, and extraction directory are ignored by Git.

## Generate The Profile

```bash
npm run generate:profile
```

This creates:

```text
profiles/friwa-0x7611.json
```

## Generate EDOMI Blocks

```bash
npm run generate:edomi:full
npm run generate:edomi:light
```

The generated local EDOMI files are:

```text
/zwischenspeicher/edomi/LBS/19100832/19100832_lbs.php
/zwischenspeicher/edomi/LBS/19100833/19100833_lbs.php
```

## Why This Is Done Locally

The project code is MIT licensed.

The generated profile and EDOMI mappings contain derived device metadata from RESOL RSC XML files. Because the redistribution terms of those XML files are not clarified here, the safest public repository approach is:

- commit the extractor and generator,
- document where users get the RESOL package,
- let users generate the profile locally,
- do not commit RESOL XML files or downloaded RESOL installers.
