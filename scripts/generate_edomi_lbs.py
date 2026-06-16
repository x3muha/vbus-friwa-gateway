#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


DEFAULT_LBS_ID = 19100832
CONFIG_INPUTS = [
    (1, "Gateway Host/IP #init=10.0.1.221"),
    (2, "Port #init=8787"),
    (3, "HTTPS 0/1 #init=0"),
    (4, "User #init=admin"),
    (5, "Passwort #init=admin"),
    (6, "Bearer Token"),
    (7, "Aktiv 1/0 #init=1"),
    (8, "Intervall Sekunden #init=60"),
    (9, "TRIGGER = Sofort lesen"),
    (10, "Debug RAW 1/0 #init=0"),
    (11, "SSL pruefen 1/0 #init=0"),
    (12, "Timeout Sekunden #init=8"),
]


def php_string(value):
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def clean_label(value):
    return str(value).replace("[", "(").replace("]", ")").replace("\n", " ").strip()


def display_label(item):
    return clean_label(item.get("_edomi", {}).get("label") or item.get("label") or item.get("key"))


def mapping_for(item, variant):
    if variant == "full":
        return item.get("edomi", {}).get("full") or {
            "input": item.get("input"),
            "output": item.get("output"),
        }
    return item.get("edomi", {}).get(variant)


def select_items(profile, variant):
    live = []
    params = []
    for item in profile["live"]:
        mapping = mapping_for(item, variant)
        if mapping and mapping.get("output") is not None:
            merged = dict(item)
            merged["_edomi"] = mapping
            live.append(merged)
    for item in profile["parameters"]:
        mapping = mapping_for(item, variant)
        if not mapping or mapping.get("enabled") is False:
            continue
        if mapping.get("input") is None and mapping.get("output") is None:
            continue
        merged = dict(item)
        merged["_edomi"] = mapping
        params.append(merged)
    live.sort(key=lambda item: item["_edomi"].get("output", 9999))
    params.sort(key=lambda item: item["_edomi"].get("output", item["_edomi"].get("input", 9999)))
    return live, params


def require_unique(name, pairs):
    used = {}
    errors = []
    for nr, label in pairs:
        if nr is None:
            continue
        if nr in used:
            errors.append(f"{name}{nr} doppelt: {used[nr]} / {label}")
        else:
            used[nr] = label
    if errors:
        raise ValueError("\n".join(errors))


def validate_numbers(live, params, status_outputs):
    input_pairs = [(nr, label) for nr, label in CONFIG_INPUTS]
    output_pairs = []
    declared_outputs = set()
    for item in live:
        nr = item["_edomi"].get("output")
        output_pairs.append((nr, item["key"]))
        declared_outputs.add(nr)
    for item in params:
        mapping = item["_edomi"]
        input_pairs.append((mapping.get("input"), item["key"]))
        output = mapping.get("output")
        if output is not None and not mapping.get("reuseOutput"):
            output_pairs.append((output, item["key"]))
            declared_outputs.add(output)
        elif output is not None and output not in declared_outputs:
            raise ValueError(f"A{output} fuer {item['key']} soll wiederverwendet werden, ist aber nicht deklariert")
    output_pairs.extend(status_outputs)
    require_unique("E", input_pairs)
    require_unique("A", output_pairs)


def range_text(p):
    if p.get("min") is None and p.get("max") is None:
        return ""
    unit = (" " + p.get("unit", "").strip()) if p.get("unit") else ""
    return f" ({p.get('min','')}..{p.get('max','')}{unit})"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--variant", choices=["full", "light"], default="full")
    parser.add_argument("--lbs-id", type=int)
    args = parser.parse_args()

    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    variant_meta = profile.get("edomi", {}).get("variants", {}).get(args.variant, {})
    lbs_id = args.lbs_id or variant_meta.get("lbsId") or DEFAULT_LBS_ID
    name = variant_meta.get("name") or ("VBus FriWa Gateway Light" if args.variant == "light" else "VBus FriWa Gateway")

    live, params = select_items(profile, args.variant)
    writable = [p for p in params if p.get("writable") and p["_edomi"].get("input")]
    state_items = []
    for item in live + params:
        output = item["_edomi"].get("output")
        if output is not None:
            state_items.append((item["key"], output))
    max_state_output = max([nr for _, nr in state_items] + [0])
    if variant_meta.get("statusAfterGap"):
        status_start = max_state_output + 2
    else:
        status_start = int(variant_meta.get("statusStart") or (90 if args.variant == "light" else 209))
    status_outputs = [
        (status_start, "OK 1/0"),
        (status_start + 1, "Status Text"),
        (status_start + 2, "Fehlertext"),
        (status_start + 3, "HTTP-Code"),
        (status_start + 4, "Zeitstempel"),
        (status_start + 5, "Letzter Write"),
        (status_start + 6, "RAW JSON"),
    ]
    validate_numbers(live, params, status_outputs)

    lines = []
    lines.append("###[DEF]###")
    lines.append(f"[name = {name}]")
    lines.append("")
    for nr, label in CONFIG_INPUTS:
        if label.startswith("TRIGGER = "):
            lines.append(f"[e#{nr} TRIGGER = {label[len('TRIGGER = '):]}]")
        else:
            lines.append(f"[e#{nr} = {label}]")
    lines.append("")
    for p in writable:
        ein = p["_edomi"]["input"]
        lines.append(f"[e#{ein} TRIGGER = {display_label(p)}{range_text(p)}]")
    lines.append("")
    for f in live:
        unit = f.get("unit", "").strip()
        lines.append(f"[a#{f['_edomi']['output']} = {display_label(f)}{(' ' + unit) if unit else ''}]")
    lines.append("")
    for p in params:
        mapping = p["_edomi"]
        if mapping.get("output") is None or mapping.get("reuseOutput"):
            continue
        unit = p.get("unit", "").strip()
        lines.append(f"[a#{mapping['output']} = {display_label(p)}{(' ' + unit) if unit else ''}]")
    lines.append("")
    for nr, label in status_outputs:
        lines.append(f"[a#{nr} = {label}]")
    lines.append("")
    lines.append("[v#1 = 0] Aktiv")
    lines.append("[v#91 = 0] Pending")
    lines.append("[v#100 = ] letzte Ausgaenge JSON")
    lines.append("###[/DEF]###")
    lines.append("")

    lines.append("###[HELP]###")
    lines.append(f"{name} ({lbs_id})")
    lines.append("")
    lines.append("Zweck:")
    lines.append("- Bindet den Dienst vbus-friwa-gateway an EDOMI an.")
    lines.append("- EDOMI spricht HTTP mit dem Gateway; keine VBus-/Serial-Logik im Baustein.")
    lines.append("- Ausgaenge werden nur bei Wertwechsel geschrieben.")
    lines.append("- Beim Start und beim Trigger E9 wird /api/state gelesen.")
    lines.append("- Bei Aenderung eines schreibbaren Eingangs wird /api/write gesendet.")
    lines.append("- Nach dem Write setzt der Baustein den passenden Ausgang aus dem Gateway-Readback.")
    lines.append("- Mehrere EDOMI-Bausteine duerfen denselben Gateway nutzen; der Gateway serialisiert VBus-Zugriffe intern.")
    lines.append("")
    lines.append("Config:")
    lines.append("- E1 Host/IP, E2 Port, E3 HTTPS, E4/E5 Basic Auth, E6 optional Bearer Token.")
    lines.append("- E7 aktiviert den zyklischen Read, E8 Intervall Sekunden.")
    lines.append("- E10 schreibt RAW JSON auf den RAW-Ausgang, E11 aktiviert SSL-Zertifikatspruefung.")
    lines.append("")
    lines.append("Read-Ablauf:")
    lines.append("1. E9 oder Intervall startet den EXEC-Teil.")
    lines.append("2. EXEC ruft GET /api/state am Gateway auf.")
    lines.append("3. Gateway liefert den letzten bekannten State.")
    lines.append("4. Der Baustein mappt Gateway-Keys auf EDOMI-Ausgaenge.")
    lines.append("5. Ausgaenge werden nur bei Wertwechsel gesetzt.")
    lines.append("")
    lines.append("Write-Ablauf:")
    lines.append("1. Ein schreibbarer Eingang wird beschrieben.")
    lines.append("2. EXEC sendet POST /api/write mit Gateway-Key und Wert.")
    lines.append("3. Gateway skaliert den Wert passend zum Profil.")
    lines.append("4. Gateway liest den alten Wert, schreibt, liest danach erneut.")
    lines.append("5. Der Ausgang wird aus dem echten Readback gesetzt, nicht blind aus dem Wunschwert.")
    lines.append("Beispiel: E16=60 schreibt 0x0130 Warmwasser Soll raw=600; A16 zeigt danach den echten Readback.")
    lines.append("")
    lines.append("Mehrere Bausteine/Clients:")
    lines.append("- Mehrere EDOMI-Elemente, vbus-test und WebSocket-Clients koennen parallel auf den Gateway zugreifen.")
    lines.append("- Nur der Gateway darf direkt auf den seriellen VBus-Port zugreifen.")
    lines.append("- vbus-test ohne --direct nutzt ebenfalls die Gateway-API.")
    lines.append("- vbus-test --direct darf nicht parallel zum systemd-Service auf demselben Serial-Port laufen.")
    lines.append("")
    lines.append("Sicherheit:")
    lines.append("- Standard ist admin/admin, damit ein lokaler Test sofort funktioniert.")
    lines.append("- Fuer produktiven Betrieb Passwort aendern oder Bearer Token nutzen.")
    lines.append("- TLS/HTTPS kann im Gateway aktiviert werden; E3 schaltet den Baustein auf HTTPS.")
    lines.append("- E11 aktiviert Zertifikatspruefung, fuer selbstsignierte lokale Zertifikate meist 0 lassen.")
    lines.append("")
    lines.append("Mapping:")
    lines.append(f"- Variante: {args.variant}.")
    lines.append("- Schreibbare Werte haben E/A gleich, ausser wenn ein Parameter bewusst einen Live-Ausgang als Readback nutzt.")
    lines.append("- Die Nummerierung kommt aus profiles/friwa-0x7611.json unter edomi.full bzw. edomi.light.")
    lines.append("- Sichtbare E/A-Namen enthalten keine Hex-Indizes; diese Liste enthaelt die genaue Zuordnung.")
    lines.append("- Parameter-Indexliste:")
    for p in writable:
        mapping = p["_edomi"]
        out = mapping.get("output")
        lines.append(f"  E{mapping['input']}/A{out}: {p['indexHex']} {display_label(p)}")
    lines.append("###[/HELP]###")
    lines.append("")

    lines.append("###[LBS]###")
    lines.append("<?php")
    lines.append("function LB_LBSID($id) {")
    lines.append("    if (!($E=logic_getInputs($id))) return;")
    lines.append("    $enabled = (intval($E[7]['value'])==1);")
    lines.append("    $interval = max(5, intval($E[8]['value']));")
    lines.append("    $needRun = false;")
    lines.append("    if ($E[7]['refresh']==1) {")
    lines.append("        if ($enabled) { logic_setVar($id,1,1); $needRun = true; }")
    lines.append("        else { logic_setVar($id,1,0); logic_setVar($id,91,0); logic_setState($id,0); return; }")
    lines.append("    }")
    lines.append("    if (!$enabled) { logic_setState($id,0); return; }")
    lines.append("    if ($E[1]['refresh']==1 || $E[2]['refresh']==1 || $E[3]['refresh']==1 || $E[4]['refresh']==1 ||")
    lines.append("        $E[5]['refresh']==1 || $E[6]['refresh']==1 || $E[8]['refresh']==1 || $E[9]['refresh']==1 ||")
    lines.append("        $E[10]['refresh']==1 || $E[11]['refresh']==1 || $E[12]['refresh']==1) $needRun = true;")
    write_checks = [f"$E[{p['_edomi']['input']}]['refresh']==1" for p in writable]
    for i in range(0, len(write_checks), 4):
        chunk = " || ".join(write_checks[i:i + 4])
        prefix = "    if (" if i == 0 else "        "
        suffix = ") $needRun = true;" if i + 4 >= len(write_checks) else " ||"
        lines.append(prefix + chunk + suffix)
    lines.append("    if (intval(logic_getVar($id,91))==1) $needRun = true;")
    lines.append("    if (intval(logic_getState($id))==1 && intval(logic_getVar($id,1))==1) $needRun = true;")
    lines.append("    if (!$needRun) return;")
    lines.append("    logic_setInputsQueued($id,$E);")
    lines.append("    if (logic_getStateExec($id)==0) {")
    lines.append("        logic_setVar($id,91,0);")
    lines.append("        logic_callExec(LBSID,$id,false);")
    lines.append("    } else {")
    lines.append("        logic_setVar($id,91,1);")
    lines.append("        logic_setState($id,1,1000);")
    lines.append("        return;")
    lines.append("    }")
    lines.append("    logic_setState($id,1,$interval*1000);")
    lines.append("}")
    lines.append("?>")
    lines.append("###[/LBS]###")
    lines.append("")

    lines.append("###[EXEC]###")
    lines.append("<?php")
    lines.append('require(dirname(__FILE__)."/../../../../main/include/php/incl_lbsexec.php");')
    lines.append("set_time_limit(30);")
    lines.append("sql_connect();")
    lines.append("")
    lines.append("function _friwa32_set_changed($id,$out,$val){")
    lines.append("    static $cache=array();")
    lines.append("    if(!isset($cache[$id])){")
    lines.append("        $tmp=json_decode((string)logic_getVar($id,100),true);")
    lines.append("        $cache[$id]=is_array($tmp)?$tmp:array();")
    lines.append("    }")
    lines.append("    $k=strval($out);")
    lines.append("    if(!array_key_exists($k,$cache[$id]) || strval($cache[$id][$k])!==strval($val)){")
    lines.append("        logic_setOutput($id,$out,$val);")
    lines.append("        $cache[$id][$k]=$val;")
    lines.append("        logic_setVar($id,100,json_encode($cache[$id]));")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("function _friwa32_short($s,$len=500){")
    lines.append("    $s=str_replace(array(\"\\r\",\"\\n\",\"\\t\"),' ',(string)$s);")
    lines.append("    return strlen($s)>$len ? substr($s,0,$len).'...' : $s;")
    lines.append("}")
    lines.append("")
    lines.append("function _friwa32_request($method,$url,$body,$user,$pass,$token,$sslVerify,$timeout,&$httpCode,&$err){")
    lines.append("    $httpCode=0; $err='';")
    lines.append("    if(!function_exists('curl_init')){ $err='curl fehlt'; return false; }")
    lines.append("    $ch=curl_init();")
    lines.append("    curl_setopt($ch,CURLOPT_URL,$url);")
    lines.append("    curl_setopt($ch,CURLOPT_RETURNTRANSFER,true);")
    lines.append("    curl_setopt($ch,CURLOPT_CONNECTTIMEOUT,min(5,$timeout));")
    lines.append("    curl_setopt($ch,CURLOPT_TIMEOUT,$timeout);")
    lines.append("    curl_setopt($ch,CURLOPT_SSL_VERIFYPEER,$sslVerify);")
    lines.append("    curl_setopt($ch,CURLOPT_SSL_VERIFYHOST,$sslVerify?2:0);")
    lines.append("    $headers=array('Accept: application/json');")
    lines.append("    if($token!=='') $headers[]='Authorization: Bearer '.$token;")
    lines.append("    else if($user!=='') curl_setopt($ch,CURLOPT_USERPWD,$user.':'.$pass);")
    lines.append("    if($method==='POST'){")
    lines.append("        $headers[]='Content-Type: application/json';")
    lines.append("        curl_setopt($ch,CURLOPT_POST,true);")
    lines.append("        curl_setopt($ch,CURLOPT_POSTFIELDS,$body);")
    lines.append("    }")
    lines.append("    curl_setopt($ch,CURLOPT_HTTPHEADER,$headers);")
    lines.append("    $resp=curl_exec($ch);")
    lines.append("    if($resp===false){ $err='curl: '.curl_error($ch); curl_close($ch); return false; }")
    lines.append("    $httpCode=intval(curl_getinfo($ch,CURLINFO_HTTP_CODE));")
    lines.append("    curl_close($ch);")
    lines.append("    if($httpCode<200 || $httpCode>=300){ $err='HTTP '.$httpCode.' Antwort: '._friwa32_short($resp,240); return false; }")
    lines.append("    return $resp;")
    lines.append("}")
    lines.append("")
    lines.append("$WRITE_MAP=array(")
    for p in writable:
        mapping = p["_edomi"]
        lines.append(f"    {mapping['input']}=>array('key'=>{php_string(p['key'])},'index'=>{php_string(p['indexHex'])},'out'=>{mapping['output']},'label'=>{php_string(display_label(p))}),")
    lines.append(");")
    lines.append("$STATE_MAP=array(")
    for key, output in sorted(state_items, key=lambda item: (item[1], item[0])):
        lines.append(f"    {php_string(key)}=>{output},")
    lines.append(");")
    lines.append("")
    lines.append("if(!($E=logic_getInputsQueued($id))) $E=logic_getInputs($id);")
    lines.append("if($E){")
    lines.append("    $set=function($o,$v) use($id){ _friwa32_set_changed($id,$o,$v); };")
    lines.append("    if(intval($E[7]['value'])!=1) return;")
    lines.append("    $host=trim((string)$E[1]['value']);")
    lines.append("    $port=max(1,intval($E[2]['value']));")
    lines.append("    $https=intval($E[3]['value'])==1;")
    lines.append("    $user=(string)$E[4]['value'];")
    lines.append("    $pass=(string)$E[5]['value'];")
    lines.append("    $token=trim((string)$E[6]['value']);")
    lines.append("    $debug=intval($E[10]['value'])==1;")
    lines.append("    $sslVerify=intval($E[11]['value'])==1;")
    lines.append("    $timeout=max(3,intval($E[12]['value']));")
    lines.append(f"    $set({status_start + 4},date('Y-m-d H:i:s'));")
    lines.append(f"    if($host===''){{ $set({status_start},0); $set({status_start + 2},'Gateway Host/IP fehlt'); $set({status_start + 1},'fehler'); return; }}")
    lines.append("    $base=($https?'https':'http').'://'.$host.':'.$port;")
    lines.append("    $wrote=0;")
    lines.append("    foreach($WRITE_MAP as $ein=>$meta){")
    lines.append("        if(isset($E[$ein]) && $E[$ein]['refresh']==1 && trim((string)$E[$ein]['value'])!==''){")
    lines.append("            $payload=json_encode(array('key'=>$meta['key'],'value'=>$E[$ein]['value']), JSON_UNESCAPED_UNICODE);")
    lines.append("            $code=0; $err='';")
    lines.append("            $resp=_friwa32_request('POST',$base.'/api/write',$payload,$user,$pass,$token,$sslVerify,$timeout,$code,$err);")
    lines.append(f"            $set({status_start + 3},$code);")
    lines.append(f"            $set({status_start + 5},$meta['index'].' '.$meta['label'].'='.$E[$ein]['value']);")
    lines.append(f"            if($resp===false){{ $set({status_start},0); $set({status_start + 2},$err); $set({status_start + 1},'write fehler '.$meta['index']); continue; }}")
    lines.append("            $data=json_decode($resp,true);")
    lines.append(f"            if(!is_array($data)){{ $set({status_start},0); $set({status_start + 2},'ungueltiges JSON bei write '.$meta['index']); $set({status_start + 1},'write json fehler'); continue; }}")
    lines.append("            if(isset($data['value']) && is_array($data['value']) && array_key_exists('value',$data['value'])) $set($meta['out'],$data['value']['value']);")
    lines.append(f"            $set({status_start},1); $set({status_start + 1},'write ok '.$meta['index']); $set({status_start + 2},'');")
    lines.append("            $wrote++;")
    lines.append("        }")
    lines.append("    }")
    lines.append("    $code=0; $err='';")
    lines.append("    $resp=_friwa32_request('GET',$base.'/api/state','',$user,$pass,$token,$sslVerify,$timeout,$code,$err);")
    lines.append(f"    $set({status_start + 3},$code);")
    lines.append(f"    if($resp===false){{ $set({status_start},0); $set({status_start + 2},$err); $set({status_start + 1},'read fehler'); return; }}")
    lines.append(f"    if($debug) $set({status_start + 6},_friwa32_short($resp,4000)); else $set({status_start + 6},'');")
    lines.append("    $data=json_decode($resp,true);")
    lines.append(f"    if(!is_array($data) || !isset($data['values']) || !is_array($data['values'])){{ $set({status_start},0); $set({status_start + 2},'ungueltiges JSON'); $set({status_start + 1},'json fehler'); return; }}")
    lines.append("    foreach($data['values'] as $entry){")
    lines.append("        if(is_array($entry) && isset($entry['key']) && array_key_exists('value',$entry) && isset($STATE_MAP[$entry['key']])){")
    lines.append("            $out=intval($STATE_MAP[$entry['key']]);")
    lines.append(f"            if($out>0 && $out<={max(max_state_output, status_start + 6)}) $set($out,$entry['value']);")
    lines.append("        }")
    lines.append("    }")
    lines.append(f"    $set({status_start},1);")
    lines.append(f"    $set({status_start + 2},'');")
    lines.append(f"    $set({status_start + 1},($wrote>0?'write+read ok':'read ok').' Werte='.count($data['values']));")
    lines.append("}")
    lines.append("?>")
    lines.append("###[/EXEC]###")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        sys.exit(1)
