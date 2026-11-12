# Database Detective: Minor Crimes Division 简体中文汉化

《[Database Detective: Minor Crimes Division](https://store.steampowered.com/app/3950130/)》非官方简体中文汉化补丁。

> Unofficial Simplified Chinese fan translation patch for *Database Detective: Minor Crimes Division*.

## 汉化内容

- 全部剧情对白、结局、证词、结尾字幕
- 破案思路提示、SQL 写法提示
- 界面、按钮、桌面应用，以及游戏内各个网站的内容
- 游戏内《使用手册》全部 24 页（重新排版）
- 加入中文字体（Noto Sans SC）

**为了不影响解谜**：数据库里的数据、人名、用户名、公会/公司/网站名、物品名、地名、表名和列名都保留英文。可能需要拿去查询的普通词写作“中文（英文）”，例如 `菠萝（pineapple）`。写 SQL 时请使用英文原值。

## 安装

1. 到 [Releases](../../releases) 下载 `DatabaseDetective_简体中文汉化.exe`。
2. 双击运行。程序会自动找到 Steam 里的游戏目录（找不到时会让你手动输入），选择 `1` 安装。
3. 安装前会自动把原版文件备份到游戏目录下的 `zh_backup` 文件夹。

适配的游戏版本：Unity 6000.5.5f1 构建（2026 年 11 月版本）。

## 卸载 / 还原

- 再次运行程序，选择 `2` 还原；或
- 在 Steam 中右键游戏 → 属性 → 已安装文件 → 验证游戏文件的完整性。

**游戏更新后**：Steam 更新会覆盖汉化，重新运行程序安装即可。如果新版本改动较大，部分内容可能会保持英文。

## 常见问题

- **出现方框或乱码**：请确认安装时程序提示“中文字体已加入”，然后重新安装一次。
- **第一次显示某些汉字时稍有卡顿**：中文字形是运行时动态生成的，属于正常现象。
- **杀毒软件报毒**：exe 是用 PyInstaller 打包的 Python 程序，有时会被误报。介意的话可以按下面的步骤从源码运行。

## 从源码运行 / 构建

```bash
pip install UnityPy fonttools pillow
python src/zh_patcher.py
```

打包 exe：

```bash
pip install pyinstaller
pyinstaller --onefile --console --name DatabaseDetective_zh --add-data "src/data;data" --collect-all UnityPy --collect-all fmod_toolkit --collect-all pyfmodex --collect-all texture2ddecoder --collect-all etcpak --collect-all archspec --collect-all astc_encoder --collect-all tpk_ar --collect-data fontTools src/zh_patcher.py
```

### 原理

补丁程序在玩家本地的游戏文件上修改，不分发任何游戏原始资源：

- 剧情、提示（TextAsset）：按原文 SHA-1 匹配后替换；
- 界面文本（TextMeshPro）：按英文原文匹配后替换；
- 手册贴图：按贴图名和尺寸匹配后替换为中文版图片；
- 字体：把游戏自带的动态备用字体换成 Noto Sans SC，并加入 TMP 全局 fallback。

`src/data/translation.json` 是全部译文，欢迎提交 Issue 或 PR 修正翻译。

### 目录结构

```
src/zh_patcher.py            安装 / 还原程序
src/data/translation.json    全部译文（textassets 按原文 SHA-1 索引，ui 按英文原文索引）
src/data/typetrees.json      TextMeshPro 组件的类型树（免去运行时依赖 .NET）
src/data/manual/             手册中文版图片
src/data/NotoSansSC-Regular.ttf, OFL.txt   中文字体及许可
tools/manual/                手册重新排版工具：render.py + 每页排版规格 specs/*.json
build.bat                    打包 exe
```

修改手册：先从自己的游戏里导出英文原图（贴图名 `COVER`、`1-1` … `8-3`），以 `NN_名字.png` 命名放到 `tools/manual/`，修改 `specs/` 中对应的 JSON 后运行 `python render.py render <页名>`，再把 `zh/` 里的结果复制到 `src/data/manual/`。仓库不包含英文原图。

## 许可

- 补丁程序代码：MIT License（见 `LICENSE`）。
- 中文字体 Noto Sans SC：SIL Open Font License 1.1（见 `src/data/OFL.txt`）。
- 游戏及其原文、美术素材版权归开发者所有。本项目的译文和手册图片仅供已购买正版游戏的玩家免费使用，不得用于商业用途。如开发者提出要求，本项目将配合修改或下架。
