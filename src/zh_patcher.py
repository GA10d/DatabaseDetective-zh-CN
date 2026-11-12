# -*- coding: utf-8 -*-
"""Database Detective: Minor Crimes Division 简体中文汉化补丁 安装/还原程序"""
import os, sys, json, hashlib, shutil, re, struct, traceback

VERSION = "1.2"
FILES = ["resources.assets", "sharedassets0.assets", "sharedassets1.assets", "level0", "level1", "level2",
         "globalgamemanagers"]  # globalgamemanagers：资源索引（部分消息按标题加载）
DLL_FILE = "Managed/Scripts.dll"   # 代码里的硬编码文本（引导小人台词等）
BACKUP_DIR = "zh_backup"
FALLBACK_ASSET_NAME = "LiberationSans SDF - Fallback"
SOURCE_FONT_NAME = "LiberationSans"


def data_dir():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "data")


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------- 找游戏目录 ----------------
def is_game_dir(p):
    return p and os.path.isfile(os.path.join(p, "copOS.exe")) and os.path.isdir(os.path.join(p, "copOS_Data"))


def steam_libraries():
    libs = []
    try:
        import winreg
        for hive, key in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")):
            try:
                with winreg.OpenKey(hive, key) as k:
                    for name in ("SteamPath", "InstallPath"):
                        try:
                            libs.append(winreg.QueryValueEx(k, name)[0])
                        except OSError:
                            pass
            except OSError:
                pass
    except ImportError:
        pass
    more = []
    for lib in libs:
        vdf = os.path.join(lib, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            txt = open(vdf, encoding="utf-8", errors="ignore").read()
            more += [m.replace("\\\\", "\\") for m in re.findall(r'"path"\s+"([^"]+)"', txt)]
    return list(dict.fromkeys(libs + more))


def find_game():
    here = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
    for p in (here, os.path.dirname(here), os.getcwd()):
        if is_game_dir(p):
            return p
    for lib in steam_libraries():
        p = os.path.join(lib, "steamapps", "common", "Database Detective")
        if is_game_dir(p):
            return p
    return None


# ---------------- 状态 ----------------
def manifest_path(game):
    return os.path.join(game, BACKUP_DIR, "manifest.json")


def load_manifest(game):
    try:
        return json.load(open(manifest_path(game), encoding="utf-8"))
    except Exception:
        return None


def is_installed(game):
    m = load_manifest(game)
    if not m:
        return False
    d = os.path.join(game, "copOS_Data")
    return all(os.path.isfile(os.path.join(d, f)) and sha1(os.path.join(d, f)) == h for f, h in m["patched"].items())


# ---------------- 补丁 ----------------
def build_nodes(raw):
    from UnityPy.helpers.TypeTreeNode import TypeTreeNode
    return TypeTreeNode.from_list([TypeTreeNode(l, t, n, 0, 0, m_MetaFlag=f) for l, t, n, f in raw])


def face_info(old, font_path):
    """只改字体名，保留原字体的行高/上下沿等度量：
    Noto 的上沿(1.16em)比原字体(0.9em)高很多，用它自己的度量会让纯中文行变高、压到下方元素。"""
    fi = dict(old)
    fi.update({"m_FamilyName": "Noto Sans SC", "m_StyleName": "Regular"})
    return fi


def script_name(o):
    s = o.read(check_read=False).m_Script.read()
    return (s.m_Namespace + "." if s.m_Namespace else "") + s.m_ClassName


# ---------------- DLL 硬编码字符串（原位覆盖 #US 堆） ----------------
def _us_heap(data):
    i = data.find(b"BSJB")
    if i < 0:
        raise ValueError("找不到 .NET 元数据")
    vlen = struct.unpack_from("<I", data, i + 12)[0]
    p = i + 16 + vlen
    nstreams = struct.unpack_from("<H", data, p + 2)[0]; p += 4
    for _ in range(nstreams):
        off, size = struct.unpack_from("<II", data, p); p += 8
        e = data.index(b"\0", p); name = data[p:e]; p = (e + 4) & ~3
        if name == b"#US":
            return i + off, size
    raise ValueError("找不到 #US 字符串堆")


def _blob_len(data, p):
    b = data[p]
    if b & 0x80 == 0:
        return b, 1
    if b & 0xC0 == 0x80:
        return ((b & 0x3F) << 8) | data[p + 1], 2
    return ((b & 0x1F) << 24) | (data[p + 1] << 16) | (data[p + 2] << 8) | data[p + 3], 4


def patch_dll_strings(path, mapping):
    """把 #US 堆里与 mapping 键完全相同的字符串原位替换为译文（译文不得长于原文）。返回替换数。"""
    data = bytearray(open(path, "rb").read())
    base, size = _us_heap(data)
    p, n_done = base + 1, 0
    while p < base + size:
        n, w = _blob_len(data, p)
        if n == 0:
            p += w; continue
        en = bytes(data[p + w:p + w + n - 1]).decode("utf-16-le", "replace")
        zh = mapping.get(en)
        if zh is not None and len(zh) <= len(en):
            raw = zh.encode("utf-16-le")
            nn = len(raw) + 1
            if w == 1:
                data[p] = nn
            elif w == 2:
                data[p] = 0x80 | (nn >> 8); data[p + 1] = nn & 0xFF
            else:
                data[p:p + 4] = bytes([0xC0 | (nn >> 24), (nn >> 16) & 0xFF, (nn >> 8) & 0xFF, nn & 0xFF])
            data[p + w:p + w + len(raw)] = raw
            data[p + w + len(raw)] = 1 if any(ord(c) > 0x7E for c in zh) else 0
            # 剩余字节填 0x00：每个都是合法的空条目，堆仍可顺序解析
            for k in range(p + w + nn, p + w + n):
                data[k] = 0
            n_done += 1
        p += w + n
    open(path, "wb").write(bytes(data))
    return n_done


def patch_game(staging, log):
    import UnityPy
    from PIL import Image
    from UnityPy.enums import TextureFormat
    D = data_dir()
    tr = json.load(open(os.path.join(D, "translation.json"), encoding="utf-8"))
    raw_nodes = json.load(open(os.path.join(D, "typetrees.json")))
    nodes = {k: build_nodes(v) for k, v in raw_nodes.items()}
    font_path = os.path.join(D, "NotoSansSC-Regular.ttf")
    font_bytes = open(font_path, "rb").read()
    ui, tas, manual = tr["ui"], tr["textassets"], tr["manual"]
    res_renames = tr.get("resources", {})
    ui_nowrap = set(tr.get("ui_nowrap", []))
    data_path = staging  # 从临时副本读取，避免占用游戏文件
    st = {"text": 0, "ui": 0, "manual": 0, "font": 0, "fallback_asset": None, "settings": 0, "res": 0}
    outputs = {}
    for fn in FILES:
        log(f"  处理 {fn} ...")
        env = UnityPy.load(os.path.join(data_path, fn))
        sf = list(env.files.values())[0]
        changed = False
        fonts = {}
        later = []
        for o in list(sf.objects.values()):
            tn = o.type.name
            if tn == "TextAsset":
                d = o.read()
                s = d.m_Script if isinstance(d.m_Script, str) else d.m_Script.decode("utf-8", "surrogateescape")
                h = hashlib.sha1(s.encode("utf-8", "surrogateescape")).hexdigest()
                if h in tas:
                    d.m_Script = tas[h]["zh"]; d.save(); changed = True; st["text"] += 1
            elif tn == "Texture2D":
                name = o.peek_name()
                if name in manual:
                    d = o.read()
                    m = manual[name]
                    if (d.m_Width, d.m_Height) == (m["w"], m["h"]):
                        img = Image.open(os.path.join(D, "manual", m["file"]))
                        fmt = TextureFormat.RGBA32 if img.mode == "RGBA" else TextureFormat.RGB24
                        d.set_image(img, target_format=fmt); d.save(); changed = True; st["manual"] += 1
            elif tn == "Font":
                fonts[o.path_id] = o
            elif tn == "ResourceManager" and res_renames:
                # 资源索引改名：代码按（已汉化的）标题拼路径加载消息文本/语音
                t = o.read_typetree()
                new = []
                for k, v in t["m_Container"]:
                    if k in res_renames:
                        k = res_renames[k]; st["res"] += 1
                    new.append((k, v))
                new.sort(key=lambda kv: kv[0].encode("utf-8"))
                t["m_Container"] = new
                o.save_typetree(t); changed = True
            elif tn == "MonoBehaviour":
                try:
                    full = script_name(o)
                except Exception:
                    continue
                if full in ("TMPro.TextMeshProUGUI", "TMPro.TextMeshPro"):
                    t = o.read_typetree(nodes[full])
                    if t["m_text"] in ui:
                        if t["m_text"] in ui_nowrap:
                            t["m_TextWrappingMode"] = 0   # 文本框按英文宽度设计，中文放不下时不要换行
                        t["m_text"] = ui[t["m_text"]]
                        o.save_typetree(t, nodes[full]); changed = True; st["ui"] += 1
                elif full in ("TMPro.TMP_FontAsset", "TMPro.TMP_Settings"):
                    later.append((o, full))
        # 字体：fallback 动态字体资源 + 它的源 Font
        fb_pid = None
        for o, full in later:
            if full == "TMPro.TMP_FontAsset":
                t = o.read_typetree(nodes[full])
                if t["m_Name"] == FALLBACK_ASSET_NAME and t["m_AtlasPopulationMode"] == 1 and t["m_SourceFontFile"]["m_FileID"] == 0:
                    src = fonts.get(t["m_SourceFontFile"]["m_PathID"])
                    if src is None:
                        continue
                    ft = src.read_typetree()
                    ft["m_FontData"] = list(font_bytes) if isinstance(ft["m_FontData"], list) else font_bytes
                    ft["m_FontNames"] = ["Noto Sans SC"]
                    src.save_typetree(ft); st["font"] += 1
                    t["m_FaceInfo"] = face_info(t["m_FaceInfo"], font_path)
                    t["m_AtlasWidth"] = t["m_AtlasHeight"] = 2048
                    t["m_FreeGlyphRects"] = [{"m_X": 0, "m_Y": 0, "m_Width": 2047, "m_Height": 2047}]
                    t["m_UsedGlyphRects"] = []
                    t["m_IsMultiAtlasTexturesEnabled"] = 1
                    cs = t["m_CreationSettings"]; cs["atlasWidth"] = cs["atlasHeight"] = 2048
                    o.save_typetree(t, nodes[full]); changed = True
                    fb_pid = o.path_id; st["fallback_asset"] = fn
        for o, full in later:
            if full == "TMPro.TMP_Settings" and fb_pid is not None:
                t = o.read_typetree(nodes[full])
                ref = {"m_FileID": 0, "m_PathID": fb_pid}
                if ref not in t["m_fallbackFontAssets"]:
                    t["m_fallbackFontAssets"].append(ref)
                o.save_typetree(t, nodes[full]); changed = True; st["settings"] += 1
        if changed:
            tmp = os.path.join(data_path, fn + ".zh_tmp")
            with open(tmp, "wb") as f:
                f.write(env.file.save())
            outputs[fn] = tmp
        del env
    if not st["font"] or not st["settings"]:
        for t in outputs.values():
            os.remove(t)
        raise RuntimeError("没有找到需要替换的字体资源，游戏版本可能不兼容，未做任何修改。")
    return outputs, st


def install(game, log):
    data_path = os.path.join(game, "copOS_Data")
    bdir = os.path.join(game, BACKUP_DIR)
    if is_installed(game):
        log("检测到已安装汉化，先还原原版文件再重新安装……")
        restore(game, log, quiet=True)
    with open(os.path.join(data_path, "resources.assets"), "rb") as f:
        if b"Noto Sans SC" in f.read():
            raise RuntimeError("游戏文件已经被其他方式修改过（含中文字体），无法作为原版备份。"
                               "请先在 Steam 中右键游戏 → 属性 → 已安装文件 → 验证游戏文件的完整性，再运行本程序。")
    os.makedirs(bdir, exist_ok=True)
    log("备份原版文件到 " + bdir)
    for fn in FILES + [DLL_FILE]:
        shutil.copy2(os.path.join(data_path, fn), os.path.join(bdir, os.path.basename(fn)))
    log("正在打补丁（大约需要 1~3 分钟）……")
    import tempfile
    staging = tempfile.mkdtemp(prefix="dd_zh_")
    for fn in FILES + ["globalgamemanagers.assets"]:
        shutil.copy2(os.path.join(data_path, fn), os.path.join(staging, fn))
    try:
        outputs, st = patch_game(staging, log)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    patched = {}
    for fn, tmp in outputs.items():
        dst = os.path.join(data_path, fn)
        shutil.copyfile(tmp, dst)
        patched[fn] = sha1(dst)
    import gc; gc.collect()
    shutil.rmtree(staging, ignore_errors=True)
    tr = json.load(open(os.path.join(data_dir(), "translation.json"), encoding="utf-8"))
    dll_map = tr.get("dll", {})
    if dll_map:
        dll_path = os.path.join(data_path, DLL_FILE)
        st["dll"] = patch_dll_strings(dll_path, dll_map)
        patched[DLL_FILE] = sha1(dll_path)
    json.dump({"version": VERSION, "patched": patched}, open(manifest_path(game), "w", encoding="utf-8"), indent=1)
    log(f"完成！剧情/提示 {st['text']} 个文件，界面文本 {st['ui']} 处，代码内文本 {st.get('dll', 0)} 处，手册与图片 {st['manual']} 张，中文字体已加入。")
    if st["text"] < len(tr["textassets"]) or st["manual"] < len(tr["manual"]) or st.get("dll", 0) < len(dll_map):
        log("提示：有部分内容没有匹配上（游戏可能已更新），这些地方会保持英文。")


def restore(game, log, quiet=False):
    m = load_manifest(game)
    bdir = os.path.join(game, BACKUP_DIR)
    if not m:
        log("没有找到汉化备份，无需还原。"); return
    if not is_installed(game):
        log("当前游戏文件不是本补丁安装的版本（可能游戏已更新或已在 Steam 验证过文件），不做还原以免覆盖新文件。")
        return
    for fn in m["patched"]:
        shutil.copy2(os.path.join(bdir, os.path.basename(fn)), os.path.join(game, "copOS_Data", fn))
    os.remove(manifest_path(game))
    if not quiet:
        log("已还原为英文原版。")


def main():
    print("=" * 60)
    print(f" Database Detective: Minor Crimes Division 简体中文汉化 v{VERSION}")
    print("=" * 60)
    game = find_game()
    while not is_game_dir(game):
        if game:
            print("这个目录里没有找到 copOS.exe。")
        game = input("请输入游戏安装目录（包含 copOS.exe 的文件夹）：").strip().strip('"')
    print("游戏目录：", game)
    print("当前状态：", "已安装汉化" if is_installed(game) else "未安装汉化")
    print("\n  1. 安装 / 重新安装汉化\n  2. 还原为英文原版\n  0. 退出")
    c = input("\n请选择：").strip()
    try:
        if c == "1":
            install(game, print)
        elif c == "2":
            restore(game, print)
    except Exception as e:
        print("\n出错了：", e)
        traceback.print_exc()
        print("游戏文件未被修改或已保留备份，可在 Steam 中“验证游戏文件完整性”恢复。")
    input("\n按回车键退出……")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] in ("--install", "--restore"):
        (install if sys.argv[1] == "--install" else restore)(sys.argv[2], print)
    else:
        main()
