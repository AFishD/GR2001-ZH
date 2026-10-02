# PS2《Ghost Recon》字体系统机制逆向报告（SLUS_206.13）

> 纯静态逆向（capstone + Metrowerks 专有调试段手工解码 + font_rsfb_engine.bin 实证交叉验证）。
> 证据文件在 `C:\gr_build\tmp\slus_scan\`（dis_*.txt 反汇编、xref_font.txt 调用点、dis4.py EE 反汇编器）。
> 所有地址均为 ELF 虚拟地址（main 段 0x100000 起）。

---

## 0. 总览

```
IkeUIMgr::PreInit(0x274F20) / Create(0x2751xx)
  └─ RSFontMgr::Create(0x21A5B0)          new RSFontMgr(0x74B) → 全局单例指针 g_pFontMgr@0x5E70D8
  └─ RSFontMgr::Initialize(this, 0x500)   mMaxNumCharacters = 0x500+128 = 1408（0x21A450）
  └─ RSFontMgr::ReadResourceFile(0x219380)  ← 解析 \data\shell\fonts\font.res（=我们的 FONT.RES 解压体 font_rsfb_engine.bin）
       ├─ 3 个 FontDefinition（large / default / huge），各含 224 条 10 字节记录（mKerningData）
       └─ 8 个 RSFont 样式（mFonts[0..7]），按名字字符串绑定到 3 个 FontDefinition
运行时：
  UI → RSFontMgr::GetFont(idx)（0x3A17D0，返回 &mFonts[idx]）
     → RSFontMgr::DrawString(0x219A70 / 0x219E00 / 0x219EB0)
        ├─ RSFont::CharWidth(0x21AD10) / CharHeight(0x21ACD0) / StringWidth(0x21AC00)
        ├─ RSFont::ComputeCharTextureCoords(0x21ADE0)  ← 10 字节记录 → UV
        └─ RSFontMgr::AddOneWord(0x219F50) → UISpriteModel(mModel/mBtnModel) 收集四边形
           → RSFontMgr::BeginFrame/Draw(0x219F00/0x21A290) → 全局 UIPacket(0x637AF0) 提交 GS
```

---

## 1. face 体系（问题 1）

**两层结构：3 个 FontDefinition「字面」+ 8 个 RSFont「样式」。**

### 1.1 类布局（来自 .debug 专有调试段，记录 tag 0x02/0x0d，成员偏移属性 0x23）

```
class FontDefinition {            // sizeof = 0x48（无 vtable，POD）
 0x00 int    mColumns             // ┐
 0x04 int    mRows                // │ 记录数 = mColumns × mRows（224 = 32×7 或 16×14）
 0x08 int    mCharWidth           // │
 0x0C int    mCharHeight          // │ 基准字高（large/default=26，huge=42），单位=半像素
 0x10 int    mGridWidth           // │ ┐ 运行时渲染路径未使用
 0x14 int    mGridHeight          // │ │
 0x18 int    mTextureOffsetX      // │ │
 0x1C int    mTextureOffsetY      // │ │
 0x20 int    mStartChar           // │ │ 字符索引基（=32）
 0x24 int    mLineHeight          // │ │
 0x28 float  mTextureWidth        // │ │（=512.0，读入但渲染路径未使用）
 0x2C float  mTextureHeight       // │ │
 0x30 float  mTextureStartX       // │ │
 0x34 float  mTextureStartY       // │ ┘
 0x38 void*  mKerningData         // ★ 指向 cols×rows 条 10 字节字符记录数组（堆上）
 0x3C RSUIString mID              // face 名（"large"/"default"/"huge"，8 字节字符串对象）
 0x44 int    mSize                // ★ 记录数（= mColumns×mRows，索引上界）
}

class RSFont {                    // sizeof = 0x2C
 0x00 vtable
 0x04 RSUIString mFontDefinitionID // 所属 face 名
 0x0C int  mCharWidth              // ┐固定宽模式才用（本项目全部 fixedWidth=0，无效）
 0x10 int  mCharHeight             // ┘
 0x14 int  mSpaceWidth             // 空格宽（3）
 0x18 int  mKerningOffset          // 附加字距（1 或 2），StringWidth 逐字累加
 0x1C float mScaleX                // 横向缩放（1.0 / 1.64 / 0.80 / 1.63）
 0x20 float mScaleY                // 纵向缩放
 0x24 u8   mFixedWidth             // 0
 0x25 u8   mDBFont                 // 
 0x28 FontDefinition* mFontDefinition // ← 按 mID 字符串匹配绑定
}

class RSFontMgr {                 // sizeof = 0x74
 0x00 vtable(__vt__9RSFontMgr@0x597780)
 0x04 RSArray<RSFont>        mFonts            // {RSFont* mArray; int mSize} — RSFont 按值存储，步长 44
 0x0C RSArray<FontDefinition*> mFontDefinitions // 按值存储，步长 72（0x48）
 0x14 RSUIString mFindPath
 0x1C RSFilename mFontFilename    // = font.res 内嵌的纹理名 "new_font_revised.rsb"
 0x28 UISpriteModel mModel        // 正文字形四边形收集器（28 字节，内嵌）
 0x44 int  mNumQuads
 0x48 bool mInitialized
 0x4C UISpriteModel mBtnModel     // 按钮图标四边形（纹理=pda_counterparts.rsb）
 0x68 int  mNumBtnQuads
 0x6C int  mMaxNumCharacters      // Initialize(arg): = arg+128
 0x70 float fOrientation          //（DrawString 里与 mCharWidth 相乘后传给 AddOneWord 的 float 实参，AddOneWord 未使用）
}
```

### 1.2 ReadResourceFile（0x219380，1292 字节）逐段注释

完整反汇编见 `tmp\slus_scan\dis_ReadResourceFile.txt`。文件格式**已用 font_rsfb_engine.bin（7222B）逐字节实证**（解析脚本见 `tmp\slus_scan\parse_font_rsfb.py`）：

```
流式 wire format（全部小端，std::istream::read 顺序）:
  u32  strlen          ; 纹理文件名长度
  char name[strlen]    ; "new_font_revised.rsb"  → RSFontMgr::mFontFilename（0x1C）
  u32  faceCount       ; = 3                     （face 循环）
  ┌─ 每个 face:
  │  u32 len; char name[len]                     ; face 名（"large"/"default"/"huge"）
  │  u32 mCharWidth;  u32 mCharHeight;           ; ← 注意顺序：charWidth, charHeight 在前
  │  u32 mGridWidth;  u32 mGridHeight;
  │  u32 mColumns;    u32 mRows;                 ; 32,7（huge 为 16,14）
  │  f32 mTextureStartX; f32 mTextureStartY;
  │  f32 mTextureWidth;  f32 mTextureHeight;     ; 512.0, 512.0
  │  u32 mTextureOffsetX; u32 mTextureOffsetY;
  │  u32 mStartChar;     u32 mLineHeight;
  │  u8  rec[mColumns*mRows][10]                 ; 224 条字符记录（见 §2）
  └─
  u32  styleCount      ; = 8（RSFont 循环）
  ┌─ 每条 RSFont 记录（0x21AB50 RSFont::ReadResource）:
  │  u32 len; char id[len]      ; face 名 → 与 mFontDefinitions[i].mID 逐一 __eq__ 匹配
  │  i32 charWidth; i32 charHeight; i32 spaceWidth; i32 kerningOffset
  │  u8  fixedWidth
  │  f32 scaleX; f32 scaleY
  └─
```

反汇编关键步骤（RA=$ra，流=sp+0xC0 的 idistream）：

| 地址 | 动作 |
|---|---|
| 0x2193B8 | `diSearchFile(a0=文件名)` —— a0 = $a1（文件名实参，`paddub` 拷贝），s5 = this |
| 0x2193C8 | `idistream(路径, 1)` 打开流 |
| 0x2193D4 | 构造临时 RSUIString(sp+0xA8) 并 `Read(RSUIString)`（0x53FE40：`{u32 len; char[len]}`） |
| 0x2193EC | `ConvertToRSString` → 0x2193FC `RSFilename(rsstring)` → 0x21940C `operator=` 存入 **this+0x1C (mFontFilename)** |
| 0x219438 | `read(&faceCount@sp+0xBC, 4)` |
| 0x219440 | `b 0x2196B8` 进 face 循环（fp = face 序号，条件 `fp < faceCount`） |
| 0x219448 | 循环体：`RSUIString(sp+0x829C)` 构造 + `Read`（face 名） |
| 0x219470-0x219578 | 14 次 `read(istream, sp+0x8260+off, 4)`：目的偏移依次 0x8268,0x826C,0x8270,0x8274,0x8260,0x8264,0x8290,0x8294,0x8288,0x828C,0x8278,0x827C,0x8280,0x8284 —— 即 FD 的 0x08,0x0C,0x10,0x14,0x00,0x04,0x30,0x34,0x28,0x2C,0x18,0x1C,0x20,0x24（临时 FontDefinition@sp+0x8260） |
| 0x219588 | `lw v0,(s0)`(=mRows) `lw v1`(=mColumns) → 0x219590 `mult $s6, $v1, $v0`（**EE 专有：MULT rd≠0 时 rd=乘积**，即 `s6 = mColumns×mRows`）——字符记录条数 |
| 0x219594-0x2195A0 | `sll×2/addu/sll×1` 算出 `s6×10+0x10` → `__nwa__` 分配记录数组；0x2195B8 取 `0x2199E0`（`__dt__6RSFontFv`）作 `__construct_new_array(块, dtor, 0, s6)` 参数 |
| 0x2195D0-0x2195E4 | s4 = sp+0x8298：`[0x8298]=数组指针`（→临时 FD+0x38 **mKerningData**）、`[sp+0x82A4]=s6`（→FD+0x44 **mSize**） |
| 0x2195F8-0x219668 | **字符记录循环**（i < s6）：`read(rec+off, 1)`, `read(rec+off+1, 1)`, `read(rec+off+2, 2)` ×4（off 每轮 +10）——即每字 **{u8, u8, u16, u16, u16, u16} 10 字节** |
| 0x219670-0x21969C | `IncreaseToSize_Array<FontDefinition>(this+0xC, size+1)`（步长 72），临时 FD `operator=` 拷入 `mFontDefinitions[i]` |
| 0x2196C8 | face 循环退出后：`read(&styleCount@sp+0xBC, 4)` |
| 0x2196E0-0x2196F4 | RSFont 循环（s0 < styleCount）：临时 RSFont(sp+0x82B0) 构造 → `RSFont::ReadResource(0x21AB50)`（读 {id, charWidth, charHeight, spaceWidth, kerningOffset, fixedWidth:u8, scaleX:f32, scaleY:f32}，注意 a2 尺寸在各自 jal 延迟槽里：1 字节的是 fixedWidth） |
| 0x219704-0x21974C | **名字绑定**：`for j < mFontDefinitions.mSize: if mFontDefinitions[j].mID(0x3C) == font.mFontDefinitionID: font.mFontDefinition = &mFontDefinitions[j]`（RSUIString `__eq__` @0x541640） |
| 0x219758-0x21978C | `IncreaseToSize_Array<RSFont>(this+4, size+1)`，`RSFont::operator=(0x219890)` 拷入 `mFonts[i]`（44 字节步长） |
| 0x2197B8-0x2197D8 | `mModel.SetTexture(UITextureMgr::GetTexture(mFontFilename))`；`mBtnModel.SetTexture(GetTexture("pda_counterparts.rsb"@0x578650))` |
| 0x2197D8 | `Initialize` 式收尾后返回 |

实证解析结果（font_rsfb_engine.bin，7222B 全部消费）：

| face | cols×rows | 记录数 | charHeight | texStart | 纹理 |
|---|---|---|---|---|---|
| large | 32×7 | 224 | 26 | (0,0) | 512.0×512.0 |
| default | 32×7 | 224 | 26 | (0,208) | 512.0×512.0 |
| huge | 16×14 | 224 | 42 | (0,416) | 512.0×512.0 |

8 条 RSFont 样式（GetFont 索引 → 样式参数）：

| idx | id | scaleX=scaleY | spaceWidth | kerningOffset | 已证实用途 |
|---|---|---|---|---|---|
| 0 | default | 1.000 | 3 | 1 | （CommandMap 用 1） |
| 1 | default | 1.000 | 3 | 1 | CommandMapFrameModel 字号（小字） |
| 2 | large | 1.000 | 3 | 2 | |
| 3 | large | 1.000 | 4 | 2 | CommandMapFrameModel（地图标注） |
| 4 | large | 1.000 | 3 | 2 | HUD 击杀/时间（UpdateTimeAndKillsDisplay、DrawResPawn） |
| 5 | large | 1.640 | 6 | 1 | HUD 计时大字（DrawSurTime） |
| 6 | huge | 0.800 | 3 | 1 | SimHuman 黑屏字幕（TriggleForBlackCamera） |
| 7 | huge | 1.630 | 3 | 1 | （大标题类，未在直接调用点出现） |

### 1.3 face 查询接口与调用点（问题 3）

- `RSFontMgr::Get()`（0x3A17E0）= `return *(RSFontMgr**)0x5E70D8`（全局单例指针）。
- `RSFontMgr::GetFont(int i)`（0x3A17D0）= `j RSArray<RSFont>::operator[](i)`（0x2007E0，44B 步长乘法）+ 延迟槽 `addiu a0,a0,4` → **返回 &mFonts[i]，参数是整数下标（0..7），不是字符串**。字符串只在 font.res 内部匹配 face 时使用。
- DrawString 三个重载：
  - `0x219A70` (PCc, float x, float y, RSColor&, RSFont*, PCi, PCi, int) —— 主浮点版
  - `0x219E00` (PCc, float x, float y, RSColor&, **int fontIdx**, PCi, PCi) —— 直接传样式下标
  - `0x219EB0` (PCc, int x, int y, RSColor&, RSFont*, PCi, PCi, int) —— 整数坐标版

直接 jal 调用点统计（见 `tmp\slus_scan\xref_font.txt`，含延迟槽取参）：

| 调用者符号 | 用途 | GetFont 下标 |
|---|---|---|
| DrawSurTime__16IkeSimulationMgr | HUD 计时（大字） | **5**（large×1.64） |
| UpdateTimeAndKillsDisplay__16IkeSimulationMgr | HUD 击杀/时间 | **4**（large×1.0） |
| DrawResPawn__16IkeSimulationMgr | 重生提示 | **4** |
| TriggleForBlackCamera__8SimHuman | 任务简报黑屏字幕 | **6**（huge×0.8） |
| Draw__20CommandMapFrameModel | 指挥地图 | DrawString_v2 的 int 下标 = **3** 和 **1** |
| DrawRollovers__14CommandMapView | 地图悬停 | 同 v2 |

其余文字都通过 DrawString v1/v3 并传入**组件缓存的 RSFont\***（IkeButton3/IkeKeyMapButton/IkeBaseButton 的 `DrawText`：字体指针来自按钮对象 +0x9C 处的字体句柄 +4；RSTextComponent 的 `DrawTheString/DrawOneLine`：来自组件 +0x98 一带的字体句柄），即所有按钮标签、文本框、帮助条、制作名单（Draw__7Credits）、加载屏（LoadingLoagoThread）、聊天（ChatDisplay）、调试信息（DrawDebugInfo）、快捷键条（NewPS2Shortcut::DrawNN）都走同一个 8 样式表。推断（供重排工程参考）：菜单按钮标签用 default 系（idx 0/1），正文/帮助条用 large 系（idx 2/3/4），大标题用 huge 系（idx 6/7）。

---

## 2. 记录 → 运行时字格（问题 2）

### 2.1 10 字节记录的真实语义（font_rsfb_engine.bin 实证）

```
rec[10] = { u8 pad;        // 恒为 0（全 224 条 b0=0），运行时未读
            u8 advance;    // ★ 推进量 b1（半像素单位）；'large' 1..19，'default' 1..17，'huge' 1..35
            u16 u0;        // 字格左缘   ┐
            u16 v0;        // 字格上缘   │ 半像素单位（2 单位 = 1 纹理 texel）
            u16 u1;        // 字格右缘   │
            u16 v1; }      // 字格下缘   ┘
```
- 之前扫描命名的 {x0,y0,x1,y1,tag} 对应：x0=u0、y0=v0、x1=u1、y1=v1、tag=advance(b1)（第一个 u8 是 pad，不是数据）。
- 记录按**紧打包**存储：相邻记录 u0 连续（0,13,17,23,…,290…），每个字格宽 = u1-u0 ≈ advance+1（+1 单位即半 texel 边缘余量），v 方向按 26（或 42）单位一条行带。
- 三 face 共用同一张 512×512 纹理（large: v 0..130、default: v 104..208、huge: v 182..476，单位半像素）。

### 2.2 引擎读取（ComputeCharTextureCoords 0x21ADE0，反汇编见 dis_ComputeCharTextureCoords.txt）

```
ComputeCharTextureCoords(this, char c, float *u0, float *v0, float *u1, float *v1):
  t2 = this->mFontDefinition                       ; lw 0x28(this)
  idx  = (int8)c                                   ; andi 0xff; dsll32 24; dsra32 24 —— 字节【符号扩展】
  idx -= (int8)FD->mStartChar                      ; lb 0x20(fd)（有符号字节加载，=32）
  idx &= 0xff
  if (idx < 0) idx = 0                             ; bltzl
  if (idx >= FD->mSize /*[fd+0x44]*/) idx = 0      ; 越界回退到记录 0（空格）
  rec  = FD->mKerningData + idx*10                 ; sll2/addu/sll1 —— 10 字节步长
  *u0 = (float)((u16)rec[2] >> 1)                  ; lhu +2; srl 1; mtc1; cvt.s.w
  *v0 = (float)((u16)rec[4] >> 1)                  ; +4
  *u1 = (float)((u16)rec[6] >> 1)                  ; +6
  *v1 = (float)((u16)rec[8] >> 1)                  ; +8
```

**结论：**
- **u0/v0/u1/v1 是半像素（半 texel）单位：引擎 `>>1` 除以 2 换成 512×512 纹理的 texel 坐标。** 1 记录单位 = 0.5 texel = 1 个基准显示像素（即纹理按 2× 超采样显示：large 的 13-texel 字面显示为 26px）。
- **y0/y1（v0/v1）直接成为纵向 UV**，无任何重排/重映射；引擎完全按文件里的 u0/v0/u1/v1 原样采样（只做 /2）。
- advance(b1) 的换算在 `CharWidth`（0x21AD10）：`return (int)(mScaleX * (float)rec[1])`（`lbu rec+1; cvt; mul.s mScaleX; fptosi`）——**b1 与 charHeight 同为"半像素=基准显示像素"单位，乘以样式 scaleX 后直接作为推进量**，不再除 2。
- `CharHeight`（0x21ACD0）：`mFixedWidth(0x24)!=0 ? RSFont.mCharHeight : (int)(mScaleY * (float)FD->mCharHeight)`。本资源全部 fixedWidth=0，实际走后者。
- 特殊返回：`CharWidth(' ')=mSpaceWidth`、`CharWidth(0xB5)=CharWidth(0xB1)=字面量 20`（这两个码位是 PS 按钮图标字，见 §4）。
- `StringWidth`（0x21AC00）= `Σ CharWidth(c) + (strlen-1) × mKerningOffset`（0x21AC98 `mult(=mul) v0, (len-1), mKerningOffset`，EE rd 写回）。

### 2.3 UV 进入渲染器的路径

`UISpriteModel::SetTextureCoordinate(idx, vec4 uv)`（0x515960）：把 4 个 float 各 `fptosi(x*16)` 成 **Q12.4 定点 u16** 写进顶点（+8/+0xA/+0x18/…），由 GS 打包层按纹理尺寸归一化。即：文件半像素 → /2 texel → ×16 定点 → /512 归一化（纹理尺寸来自 .rsb 头，见 §4）。

---

## 3. 渲染管线（问题 5）

`DrawString`（0x219A70，dis_DrawString.txt）：

1. `s7 = strlen(s)`；`f20=x, f23=y`（`mov.s f20,f12 / f23,f13`）；`f21 = (float)CharHeight(font)`。
2. `w = (float)StringWidth(font, s)`；裁剪：`x+w < 0 → 返回`、`x ≥ 640 → 返回`、`y+ch < 0 → 返回`、`y ≥ 480 → 返回`（常量 640.0=0x4420、480.0=0x43F0）。
3. 逐字符循环：
   - `cw = CharWidth(c)`（存 f20）；`c==' '` → 只推进光标。
   - 检查 `mNumQuads < mMaxNumCharacters`（`lw 0x44(s5) / lw 0x6c(s5) / slt`）。
   - 普通字符：`ComputeCharTextureCoords(c, &uv0,&uv1,&uv2,&uv3)`（栈 0xB0..0xBC）。
   - **码位 0xB5 / 0xB1：UV 用硬编码常量**（不走 font.res 记录）：
     - 0xB5 → (u0,v0,u1,v1) = (1.0, 200.0, 21.0, 218.0)
     - 0xB1 → (25.0, 200.0, 45.0, 218.0)
     单位是像素（SetTextureCoordinate 直接 ×16 定点），纹理是 **pda_counterparts.rsb**（按钮图标纹理，mBtnModel 专用）；v 方向对行中心做 `2.0/(y0+y1)` 归一插值。
   - 字形四边形：`pos = {x0=x, y0=y, x1=x+cw, y1=y+ch}`（栈 0xC0..0xCC；`add.s f0,f20,f0 → [fp]` 即 x1=x+advance）。
   - `AddOneWord(this, pos, uv, color, fOrientation*mCharWidth, is_special)`：
     - 普通字 → `mModel.SetVertex(mNumQuads,pos)/SetTextureCoordinate(mNumQuads,uv)/SetColor(mNumQuads,color)`，`mNumQuads++`（vtable+0x1C/+0x24）。
     - 0xB5/0xB1 → 写入 **mBtnModel**（上限 2 条，`slti v1, n, 2`）。
     - `mNumQuads ≥ 0x500(1280)` 时**中途 FLUSH**（SetAlpha(1) → SetLinearSampling(true) → AddModel(mModel/mBtnModel) → 复位）。
   - 光标 `x += cw`；若非 fixedWidth 再 `x += mKerningOffset`（`lwc1 0x18` 即 mKerningOffset，cvt 后加）。
4. 帧末 `RSFontMgr::Draw(0x21A290)`：`SetLinearSampling(true)` → `AddModel(mModel)`（若 mNumQuads>0）→ `AddModel(mBtnModel)`（若 mNumBtnQuads>0）→ 恢复采样设置 → 复位计数。`BeginFrame(0x219F00)` 每帧清零两个模型。

**采样与缩放结论：**
- 引擎按 `1 记录单位 = 1 显示像素 = 0.5 texel` 渲染（纹理 2× 超采样）。
- **开启线性采样**（SetLinearSampling(true)）→ 放大字格时是双线性插值，不是 1:1 硬像素；没有逐字符的额外缩放/插值变换，四边形严格等于 `advance×scaleX × charHeight×scaleY`。
- 因此重排时只要让 **texel 内容 = 目标显示尺寸的一半**（或让 UV/字格成对放大），渲染就会按约定放大；若希望字面 1:1 像素，应把字面画成当前纹理分辨率、并保持 `charHeight/scale` 与 UV 带高一致（现在 large：13 texel → 26 px）。

---

## 4. 图集纹理（问题 4）

- 纹理文件名**存于 font.res 内**（第一条字符串 `"new_font_revised.rsb"` → `mFontFilename`），经 `UITextureMgr::GetTexture(RSFilename)`（0x51B040）：WaitSema → `FindSurface`(小写名查缓存) → miss 则 **`LoadIndexedRSB`(0x51B230)** → `UITexture::LoadRSBFile`(0x51C810) → 载入后链入 UI 纹理链表。按钮图标纹理独立：`pda_counterparts.rsb`。
- `LoadRSBFile` 头部（以 han_v2/artifacts/Chinese0.rsb 实测）：`u32 mode(=6); u32 width; u32 height;`（宽高取各自 u32 的低 16 位，存 `UITexture+0x10/+0x12`）——**纹理尺寸是引擎从 .rsb 头读取的，不是硬编码 512**（font.res 里的 mTextureWidth/Height=512.0 浮点在渲染路径中未被读取，属描述性字段）。
  - 之后 4 个 u32（实测 4,4,4,4）为格式/mip 参数，经组合分支选择子格式（→ s0/s1 选择器）：其中 `s1==4` 分支读 **1024 字节 = 256×RGBA32 CLUT** 并逐项转成 GS 序（B,G,R 通道重排 + **alpha 减半** (a+1)/2），`s1==1/2/3/5` 走其它子格式；mode<4 走旧 `LoadPS2Img`。
  - 即：8bpp 索引纹理 + 独立 256 色 CLUT，**CLUT 在 .rsb 文件内部（紧跟头/参数区），不是 PAK 条目**。
- **texel→透明度：纯 CLUT 查表**。引擎对 texel 值 31/0 无任何特殊处理；「背景 31=透明、0=实心」完全由 CLUT 内容决定（CLUT[31].A=0、CLUT[0].A=不透明白），载入时 alpha 统一减半后交给 GS（UI 管线 alpha 语义为 0..128）。重排字库时沿用该 CLUT 约定即可，改变 texel 排布不需要改引擎。

---

## 5. 字符索引与约束确认（问题 6）

### 5.1 char 符号扩展（ComputeCharTextureCoords / CharWidth 完全一致）

```
idx = ((int8)c - (int8)mStartChar) & 0xFF        // 两处均为 lb + dsll32/dsra32 符号扩展 + subu + andi 0xff
if (idx < 0 || idx >= mSize) idx = 0
```
- **是同一张 224 条记录表，不存在负偏移第二张表。** 由于先符号扩展再减 32 再 `&0xFF` 回绕：
  - `0x20..0x7F` → 记录 0..95
  - `0x80..0xFF`（int8 为负）→ 回绕映射到记录 96..223（例：0xA1 → (0xA1-32)&0xFF？不 —— (int8)0xA1=-95，-95-32=-127，-127&0xFF=0x81=**129**）
  - `0x00..0x1F` → 224..255 → ≥mSize(224) → **回退记录 0（空格）**
- 这与实测「0xA1–0xFF 能渲染」吻合：它们落在记录 129..223（即原拉丁高区 á..ÿ 的格子），重排中文字形时直接占用这一区间即可，无需改引擎。

### 5.2 记录数 224 是可变的

- 记录数 = `mColumns × mRows`（`mult(=mul)` EE 三操作数乘法算出，0x219590），存入 `FD.mSize`，读取循环与索引上界都用它——**没有任何硬编码 224**。
- 另一个相关常数：`AddOneWord` 的溢出 FLUSH 阈值 `0x500`（1280 条四边形）是**硬编码**；`mMaxNumCharacters`（=Initialize 参数+128，PreInit 传 0x500→1408，Create 传 0x580→1536）只在 DrawString 里做预检查（`lw 0x44 / lw 0x6c / slt`）。单帧超 1280 字会中途提交。

---

## 6. 字库重排工程约束清单

### 6.1 可以自由修改（引擎无不变量）
1. **10 字节记录的 u0/v0/u1/v1 全部内容**——引擎按原值 /2 采样，只要与 .rsb 纹理内容一致即可。
2. **advance(b1)**——自由改；影响 CharWidth/StringWidth/光标推进。
3. **pad 字节（b0）**——引擎不读。
4. **纹理内容与排布**——只要 UV 对应；CLUT 约定（31=透明背景）保持即可。
5. **.rsb 的宽高字段**——引擎从头读取（但 UV 是绝对半像素坐标，改纹理尺寸必须同步改 UV，否则错位）。
6. **face 名字符串**——只要 font.res 内 RSFont.id 与 FontDefinition.mID 一致（引擎做字符串匹配），可加 face。
7. **每 face 记录条数**（cols×rows 与 mSize）——可变；bounds 检查用 mSize。
8. **8 条 RSFont 样式的 scale/spaceWidth/kerningOffset**——自由调（影响整体大小与字距）。
9. font.res 里的 mGridWidth/mGridHeight/mTextureOffsetX/Y/mTextureStartX/Y/mTextureWidth/mTextureHeight/mLineHeight —— **渲染路径未读取**（占位即可，但建议填合理值以防其它工具/调试路径使用）。

### 6.2 引擎不变量（必须遵守）
1. **索引模型**：`(int8)ch - (int8)mStartChar` 后 `&0xFF`、越界回 0。GBK 双字节首/尾字节 0xA1-0xFE 只能落在记录 129..223（若 mStartChar=32 且 mSize=224）；**要显示更多汉字必须：增大 mSize（改 cols×rows）+ 相应增大纹理/UV**，或改 mStartChar 语义（引擎支持任意有符号字节）。
2. **记录数 = mColumns × mRows = mSize**，且文件流中紧接 14 个 u32 字段后逐条 10 字节，不可加长度字段。
3. **wire 顺序不可变**：纹理名 → faceCount → {face 名,14 字段,记录[]}× → styleCount → RSFont 记录×（含 u8 fixedWidth 与两个 f32 scale 的确切顺序）。
4. **UV 单位 = 半 texel（/2 后为 512 空间 texel 坐标）**；advance 与 charHeight 单位 = 同一"半像素=基准显示像素"。
5. **3 face 共用一张 .rsb**；v 带不要互相覆盖（large 0-130 / default 104-208 / huge 182-476，单位半像素——注意现有文件 default 与 large 在 104-130 有交叠，系各自 x 区间不同所致，重排时建议彻底分离）。
6. **code 0xB5/0xB1 是按钮图标字**：UV 硬编码（指向 pda_counterparts.rsb），不占用 font 记录；重排时这两个码位无需提供字形（但 CharWidth 返回字面量 20，布局会为其留位）。
7. **text 全部经 mModel（≤0x500 条/帧）**；HUD/地图/字幕引用样式 idx 4/5/6、地图 3/1——样式表顺序（font.res 中 8 条 RSFont 的排列）不可打乱，否则全部 UI 字号错位。
8. CLUT alpha 载入时减半：若需要 alpha=255 的不透明色，CLUT 里应写 A=255（引擎 /2 → 128 满量程）。

### 6.3 face ↔ UI 对照表

| face/style | 引用者（符号名） | 典型内容 |
|---|---|---|
| style0/1 = default ×1.0 | CommandMapFrameModel（地图小字）、按钮/文本组件缓存句柄 | 菜单按钮标签、地图注记 |
| style2/3/4 = large ×1.0 | CommandMapFrameModel、UpdateTimeAndKillsDisplay、DrawResPawn、RSTextComponent（帮助/正文/自动换行 DoWordWrap）、IkeButton3/IkeBaseButton/IkeKeyMapButton（按钮文字） | HUD 数字、菜单/帮助条正文 |
| style5 = large ×1.64 | DrawSurTime | HUD 计时大字 |
| style6 = huge ×0.8 | TriggleForBlackCamera（SimHuman） | 简报/黑屏字幕 |
| style7 = huge ×1.63 | （缓存句柄路径：Credits/Loading 等大标题） | 标题 |

> 证据：GetFont 延迟槽立即数（4/5/6）与 CommandMap v2 调用的 a3 立即数（3/1）；按钮/文本组件的字体来自创建期缓存的 RSFont*（+0x9C/+0x98 成员），其下标由 UI 定义数据决定，未在调用点出现。

---

## 附：证据文件索引（C:\gr_build\tmp\slus_scan\）

- `dis4.py` —— PS2 EE 手写反汇编器（支持 EE MULT-rd 写回、MMI、LQ/SQ、COP1 fs/ft/fd 正确字段）
- `dis_ReadResourceFile.txt` / `dis_RSFont_ReadResource.txt` —— 0x219380 / 0x21AB50
- `dis_ComputeCharTextureCoords.txt` —— 0x21ADE0
- `dis_StringWidth_CharW_H.txt` —— 0x21AC00 / 0x21AD10 / 0x21ACD0
- `dis_DrawString.txt` —— 0x219A70；`dis_AddOneWord.txt` —— 0x219F50
- `dis_LoadRSBFile.txt` / `dis_LoadRSBFile2.txt` —— 0x51C810（.rsb 解析）
- `xref_font.txt` —— 全部字体 API 的 jal 调用点汇总
- `font_parse.py` —— font_rsfb_engine.bin 解析脚本（3 face×224 记录 + 8 style，7222B 全消费验证）
