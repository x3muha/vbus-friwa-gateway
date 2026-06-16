#!/usr/bin/env python3
import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


TYPE_FACTORS = {
    "Temperature": 0.1,
    "TemperatureLong": 0.1,
    "TemperatureShort": 0.1,
    "HysteresisLong": 0.1,
    "HysteresisShort": 0.1,
    "Flow": 0.1,
    "Kubikmeter": 0.1,
    "Version": 0.01,
    "Release": 0.001,
    "Number": 1,
    "Percent": 1,
    "Volumen": 1,
    "Liter": 1,
    "Time": 1,
    "TagesSchaltuhr": 1,
    "WeekTime": 1,
    "Boolean": 1,
    "boolean": 1,
}

LIGHT_EXPLICIT_IDS = {
    "OptionZirkulation",
    "ZirkulationLaufzeit",
    "Zirkulationsperrzeit",
    "ZirkulationTempMin",
    "ZirkulationHysterese",
    "OptionRuecklaufverteilung",
    "RuecklaufverteilungEin",
    "RuecklaufverteilungAus",
    "HystereseUp",
    "HystereseDown",
    "OptionNotbetrieb",
    "Notbetrieb",
    "WarmwasserSoll",
    "BlockierschutzPause",
    "BlockierschutzDauer",
    "GrundfosTempOffset",
    "GrundfosFlowOffset",
    "GrundfosTempBereich",
    "GrundfosFlowBereich",
    "GrundfosTempMax",
    "GrundfosFlowMax",
    "LosReisZeit",
    "MaxDurchfluss",
    "ZapfungErkennung",
}

LIGHT_SKIP_TYPES = {
    "WeekTime",
    "TagesSchaltuhr",
}

LIGHT_LABELS = {
    "mindrehzahl1": "Relais 1 Mindestdrehzahl",
    "zirkulationsperrzeit": "Zirkulation Sperrzeit",
    "grundfostempoffset": "Grundfos Temperatur Offset min",
    "grundfosflowoffset": "Grundfos Durchfluss Offset min",
    "grundfostempbereich": "Grundfos Temperatur Bereich",
    "grundfosflowbereich": "Grundfos Durchfluss Bereich",
    "grundfostempmax": "Grundfos Temperatur max",
    "grundfosflowmax": "Grundfos Durchfluss max",
    "losreiszeit": "Losreissimpuls Dauer",
    "Mindrehzahl1": "Relais 1 Mindestdrehzahl",
    "OptionZirkulation": "Zirkulation Modus",
    "ZirkulationLaufzeit": "Zirkulation Laufzeit",
    "Zirkulationsperrzeit": "Zirkulation Sperrzeit",
    "ZirkulationTempMin": "Zirkulation Mindesttemperatur",
    "ZirkulationHysterese": "Zirkulation Hysterese",
    "OptionRuecklaufverteilung": "Ruecklaufverteilung aktiv",
    "RuecklaufverteilungEin": "Ruecklaufverteilung Einschalt-DT",
    "RuecklaufverteilungAus": "Ruecklaufverteilung Ausschalt-DT",
    "HystereseUp": "Regelung Mindest-DT",
    "HystereseDown": "Regelung Einschalt-DT",
    "OptionNotbetrieb": "Notbetrieb aktiv",
    "Notbetrieb": "Notbetrieb Prozent",
    "BlockierschutzPause": "Blockierschutz Pause",
    "BlockierschutzDauer": "Blockierschutz Dauer",
    "WarmwasserSoll": "Warmwasser Soll",
    "GrundfosTempOffset": "Grundfos Temperatur Offset min",
    "GrundfosFlowOffset": "Grundfos Durchfluss Offset min",
    "GrundfosTempBereich": "Grundfos Temperatur Bereich",
    "GrundfosFlowBereich": "Grundfos Durchfluss Bereich",
    "GrundfosTempMax": "Grundfos Temperatur max",
    "GrundfosFlowMax": "Grundfos Durchfluss max",
    "LosReisZeit": "Losreissimpuls Dauer",
    "MaxDurchfluss": "Maximaler Durchfluss",
    "ZapfungErkennung": "Zapfung Mindestdurchfluss",
}


def parse_number(value):
    if value is None:
        return None
    value = value.strip().replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


def key_from_label(label, fallback):
    base = label.lower()
    repl = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        " ": "_",
        "-": "_",
        ".": "",
        "/": "_",
    }
    for src, dst in repl.items():
        base = base.replace(src, dst)
    base = re.sub(r"[^a-z0-9_]+", "", base)
    base = re.sub(r"_+", "_", base).strip("_")
    return base or fallback


def text_for_line(line):
    for text in line.findall("text"):
        if text.get("lang") == "de" and text.text:
            return text.text.strip()
    for text in line.findall("text"):
        if text.text:
            return text.text.strip()
    return ""


def menu_values(menu_root):
    values = {}
    for mv in menu_root.iter("menuValue"):
        value_id = mv.get("id")
        index = mv.get("index")
        if not value_id or not index:
            continue
        menu_type = mv.find("menuType")
        type_name = menu_type.get("base") if menu_type is not None else ""
        factor = TYPE_FACTORS.get(type_name, 1)
        if menu_type is not None and type_name not in {
            "Temperature",
            "TemperatureLong",
            "TemperatureShort",
            "HysteresisLong",
            "HysteresisShort",
        }:
            store_factor = parse_number(menu_type.findtext("storeFactor"))
            if store_factor is not None:
                factor = store_factor
        if value_id in {"HystereseUp", "HystereseDown"}:
            factor = 0.1
        values[value_id] = {
            "id": value_id,
            "index": int(index[2:], 16) if index.lower().startswith("0x") else int(index),
            "indexHex": f"0x{(int(index[2:], 16) if index.lower().startswith('0x') else int(index)):04X}",
            "label": value_id,
            "menu": "",
            "type": type_name,
            "unit": (menu_type.findtext("unit") if menu_type is not None else "") or "",
            "factor": factor,
            "min": (menu_type.findtext("minimum") if menu_type is not None else None),
            "max": (menu_type.findtext("maximum") if menu_type is not None else None),
            "default": (menu_type.findtext("default") if menu_type is not None else None),
            "writable": False,
        }

    for menu in menu_root.iter("menu"):
        menu_id = menu.get("id") or ""
        for line in menu.findall("line"):
            refs = [ref.text for ref in line.findall("valueref") if ref.text]
            if not refs:
                continue
            label = text_for_line(line)
            actions = {action.get("type") for action in line.findall("action") if action.get("type")}
            for ref in refs:
                if ref in values:
                    values[ref]["label"] = label or values[ref]["label"]
                    values[ref]["menu"] = menu_id
                    if "edit" in actions:
                        values[ref]["writable"] = True
    return values


def live_fields(vbus_root):
    result = []
    output = 1
    for packet in vbus_root.iter("packet"):
        if (packet.findtext("source") or "").lower() != "0x7611":
            continue
        if (packet.findtext("destination") or "").lower() != "0x0010":
            continue
        if (packet.findtext("command") or "").lower() != "0x0100":
            continue
        for field in packet.findall("field"):
            name = field.findtext("name") or ""
            subfields = field.findall("field")
            item = {
                "key": f"live.{key_from_label(name, f'a{output}')}",
                "label": name,
                "output": output,
                "edomi": {
                    "full": {"output": output},
                    "light": {"output": output},
                },
                "unit": field.findtext("unit") or "",
                "format": "number",
            }
            if subfields:
                parts = []
                for sub in subfields:
                    parts.append({
                        "offset": int(sub.findtext("offset") or "0"),
                        "bitSize": int(sub.findtext("bitSize") or "16"),
                        "factor": parse_number(sub.findtext("factor")) or 1,
                    })
                item["parts"] = parts
                if name == "Wärmemenge":
                    item["format"] = "heat"
                elif name == "Version":
                    item["format"] = "version"
            else:
                item["offset"] = int(field.findtext("offset") or "0")
                item["bitSize"] = int(field.findtext("bitSize") or "8")
                item["factor"] = parse_number(field.findtext("factor")) or 1
                if field.findtext("format") == "t":
                    item["format"] = "time"
                if item["bitSize"] == 1:
                    item["bitPos"] = int(field.findtext("bitPos") or "0")
                    item["format"] = "boolean"
            result.append(item)
            output += 1
        break
    return result


def has_range(value):
    return value.get("min") is not None or value.get("max") is not None


def is_light_parameter(value):
    if not value["writable"]:
        return False
    if value["id"] in LIGHT_EXPLICIT_IDS:
        return True
    if has_range(value) and value["type"] not in LIGHT_SKIP_TYPES:
        return True
    return False


def light_label(value):
    return LIGHT_LABELS.get(value["id"]) or LIGHT_LABELS.get(key_from_label(value["id"], "")) or value["label"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--menu-xml", required=True)
    parser.add_argument("--vbus-xml", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    menu_root = ET.parse(args.menu_xml).getroot()
    vbus_root = ET.parse(args.vbus_xml).getroot()

    live = live_fields(vbus_root)
    values = menu_values(menu_root)

    parameters = []
    sorted_values = sorted(values.values(), key=lambda item: (not item["writable"], item["index"], item["id"]))
    output_no = 25
    light_no = 21
    for value in sorted_values:
        full_mapping = {"output": output_no}
        if value["writable"]:
            full_mapping["input"] = output_no

        light_mapping = None
        if value["id"] == "WarmwasserSoll":
            light_mapping = {
                "enabled": True,
                "input": 16,
                "output": 16,
                "reuseOutput": True,
                "label": light_label(value),
                "note": "Uses live Warmwassersolltemperatur output A16 as readback.",
            }
        elif is_light_parameter(value):
            light_mapping = {
                "enabled": True,
                "input": light_no,
                "output": light_no,
                "label": light_label(value),
            }
            light_no += 1

        param = {
            "key": f"param.{value['indexHex'].lower()}.{key_from_label(value['id'], 'value')}",
            "index": value["index"],
            "indexHex": value["indexHex"],
            "label": value["label"],
            "menu": value["menu"],
            "type": value["type"],
            "unit": value["unit"],
            "factor": value["factor"],
            "min": value["min"],
            "max": value["max"],
            "default": value["default"],
            "writable": value["writable"],
            "output": output_no,
            "edomi": {
                "full": full_mapping,
            },
        }
        if value["writable"]:
            param["input"] = output_no
        if light_mapping:
            param["edomi"]["light"] = light_mapping
        parameters.append(param)
        output_no += 1

    profile = {
        "id": "friwa-0x7611",
        "name": "RESOL/PAW FriWa 0x7611",
        "edomi": {
            "variants": {
                "full": {
                    "lbsId": 19100832,
                    "name": "VBus FriWa Gateway",
                    "statusStart": 209,
                },
                "light": {
                    "lbsId": 19100833,
                    "name": "VBus FriWa Gateway Light",
                    "statusAfterGap": True,
                },
            }
        },
        "peerAddress": 0x7611,
        "peerAddressHex": "0x7611",
        "livePacketId": "00_0010_7611_10_0100",
        "live": live,
        "parameters": parameters,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
