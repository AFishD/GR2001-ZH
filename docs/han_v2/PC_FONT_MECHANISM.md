# Ghost Recon (PC, ike 引擎 v1.4.0.0 中文版) 中文字库机制 — 指令级还原报告

> 目标:`GhostRecon.exe`(PE i386,ImageBase 0x400000,7,999,848 字节)中的中文 DBCS 字库机制。
> 方法:纯静态逆向(capstone 线性反汇编 + 字符串 xref + 相对调用扫描 + 文件字节实证)。
> 所有中间产物(反汇编 dump、扫描脚本)在 `C:\gr_build\tmp\pcfont\dis\`。
> 本文所有 VA 均为虚拟地址(默认基址 0x400000 下)。

---

## 0. 总览:一条调用链看懂全部机制

```
CRT 启动 _initterm(0x8B0000, 0x8B201C)         ; C++ 静态初始化函数表(2054 项)
  └─ 表项 0x8B1420 → 0x657DB0 (thunk) → 0x657DC0 (mov ecx,0x91C734) → 0x657DD0
       字库管理器构造函数(在 main() 之前执行!)
       ├─ __try: GB2312 分支 0x657DD0..0x657EFD
       │    new 0x54 字节管理器 → [mgr+0]=512(页宽)
       │    mgr+0x04 = 串 "Data\Shell\Art\"   (0x434610 = append)
       │    mgr+0x14 = 串 "GB"
       │    mgr+0x34 = std::map(按字号 12/16/24 → 页资源)   ctor 0x658E90
       │    mgr+0x44 = std::map(GBK 码 → 格位序号)          ctor 0x658ED0
       │    0x658010: GetModuleFileNameA 拼绝对路径
       │    0x6581A0: 读 "Data\Shell\Art\" + "GB" + "text.def" → 建 code→slot 映射
       │    0x658340: sprintf("%s%s%02d%02d.TGA") + GetFileAttributesA → 逐页注册
       │    OutputDebugStringA("Chinese GB2312 Texture Loaded\n")
       │    全局模式标志 [0x8D353C] = 1   (1=GB, 0=BIG5)
       │    全局管理器指针 [0x91C738] = mgr
       └ __except: BIG5 分支 0x657F04..0x658004  (GB 文件缺失/异常时才走)
            同上,但前缀串 = "BIG5" → big5text.def / BIG5*.TGA
            [0x8D353C] = 0;OutputDebugStringA("Chinese BIG5 Texture Loaded\n")

SXM 拉丁字模初始化 0x7BC990(同样在启动期):
  按模式标志选 "IDR_SXM12/16/24"(GB) 或 "IDR_SXM12B/16B/24B"(BIG5)
  FindResourceA(0, name, "SXM") → LoadResource → LockResource   ; RT_RCDATA!
  外加三张 SXME 度量表(IDR_SXME12/16/24),描述符表 0xA4E1E0,步距 0x30

运行期文本渲染(UI 文本,宽字符串):
  0x655A10(主入口,ret 0x20,栈帧 0x400DC) → DBCS 扫描循环 0x655D46
    ├─ 查宽 0x658970(=0x7BCC80 校验 + SXM 度量 / 汉字=整格宽)
    └─ 画字 0x658760(= mgr+0x44 映射找 slot → slot→页/行/列 → UV → 交给 mesh)
         缺字 → slot 0;非 DBCS → SXM 拉丁字形(10 字节/字形记录)
```

**六个问题逐一回答如下。**

---

## 1. DBCS 扫描器(文本渲染循环)

### 1.1 前导/后续字节判定函数(全引擎共享)

```
0x7BCC10  IsLeadByte(b)  — 前导字节判定
0x7BCC40  IsTrailByte(b) — 后续字节判定
0x7BCC80  IsDBCS(code16) — 组合校验:IsLead(code 高字节) && IsTrail(code 低字节)
```
反汇编(0x7BCC10/0x7BCC40 全文,关键路径):

```asm
0x7BCC10  mov  al, [0x8d353c]      ; 模式标志: 1=GB2312/GBK, 0=BIG5
          test al, al
          mov  al, [esp+4]
          je   0x7bcc2b            ; 标志==0 → BIG5 范围
          cmp  al, 0xa1            ; 标志!=0 → GB 分支:
          jb   fail
          cmp  al, 0xfe            ; lead ∈ [0xA1, 0xFE]   ← GBK 全范围
          ja   fail
          mov  eax, 1 ; ret
0x7bcc2b: cmp  al, 0xa1            ; BIG5 分支:
          jb   fail
          cmp  al, 0xf9            ; lead ∈ [0xA1, 0xF9]   ← BIG5 lead 范围
          ja   fail

0x7BCC40  mov  al, [0x8d353c]      ; IsTrailByte:
          test al, al / mov al,[esp+4] / je 0x7bcc5b
          ; GB 分支(标志!=0):  trail ∈ [0x40,0x7E] ∪ [0xA1,0xFE]  ← GBK trail 全范围
          cmp al, 0x40 / jb / cmp al, 0x7e / jbe ok
          cmp al, 0xa1 / jb / cmp al, 0xfe / ja fail
          ; BIG5 分支(标志==0): trail ∈ [0xA1, 0xFE]
```

**结论:**
- **判定不是 0x81–0xFE,而是 `lead ∈ [0xA1,0xFE]` + `trail ∈ [0x40,0x7E]∪[0xA1,0xFE]`(GBK)**;BIG5 模式下 `lead ∈ [0xA1,0xF9]`、`trail ∈ [0xA1,0xFE]`。
- 模式标志 `[0x8D353C]`(BYTE):**1=GB、0=BIG5**,仅由字库初始化器写入(见 §4)。
- ASCII 分流点:凡 `IsDBCS` 不成立的元素一律走 SXM 拉丁路径(见 §5)。空格是显式特判:`cmp word[esi], 0x20`(0x655DA1)。

### 1.2 渲染主循环(0x655A10 框架内的 0x655D46 循环)

输入是**宽字符串(2 字节/元素)**,其中文本层已把 GBK 字节串"零扩展"成宽元素:汉字 = 两个连续元素 `[0x00lead, 0x00trail]`,ASCII = 一个元素 `0x00XX`,换行 = `0x000A`(显式终止符,0x655AB3 处写入 `0x0A` + `0x00`)。

循环体(每轮一个元素;`esi`=当前元素,`edi`=下一元素=esi+2):

```asm
; ---- 测宽 ----
0x655D54  mov cl,[esi]; push; call 0x7BCC10     ; IsLead(当前元素低字节)
0x655D63  mov dl,[edi]; push; call 0x7BCC40     ; IsTrail(下一元素低字节)
0x655D72  mov ax,[esi]
0x655D77  shl ax,8                              ; (lead)<<8
0x655D7B  add ax,[edi]                          ; + (trail)  →  key = (lead<<8)|trail
0x655D7F  push eax; call 0x658970               ; GetCharWidth: DBCS→整格宽; 否则 SXM 宽
          ; 失败(非 DBCS)路径 0x655D8E: 直接 push word[esi] 调 0x658970
0x655DA1  cmp word[esi], 0x20                   ; 空格特判
; ---- 画字 ----
0x655DB3  mov dl,[esi]; call 0x7BCC10           ; 同样两个测试再做一遍
0x655DC9  call 0x7BCC40
0x655DD9  mov bx,[esi] / shl bx,8 / add bx,[edi]  ; 同一个 key 合成
0x655E39  call 0x657620                          ; std::map<u16,u16>(mgr+0x44) 按 key 找 slot
          ; 节点布局: +0xC=u16 key, +0xE=u16 value(slot 序号); 找不到 → slot 保持 0
0x655EF4  call 0x658760                          ; slot → 页/行/列 → UV → 建四边形
; ---- 步进(0x6561AD..0x656485, DBCS 专属加跳) ----
0x6561AD  mov esi,[esp+0x20]      ; 字符计数器
0x6561C5  inc esi                 ; DBCS: 计数器额外 +1(共 +2, 元素计数口径)
0x6561C6  add edx,2               ; 保存的 edi 额外 +2(共 +4 = 两个元素)
0x6561C8  add ecx,2               ; 保存的 esi 额外 +2
0x6561DA  jmp 0x656468            ; 公共步进: 计数器再 +1, esi/edi 再 +2, jl 0x655D46
```

**要点:**
- **key 合成公式:`key = (lead << 8) | trail`(GBK 自然码/大端序)**。宽元素形式下就是 `(elem[k]<<8) + elem[k+1]`。
- **DBCS 汉字一轮迭代消费两个元素**:计数器 +2(以元素总数为上限 `[esp+0x4C]`),指针 +4——这就是"跳过 trail 元素"的实现(计数器口径 + 指针双 +2,0x6561C5–0x6561C8)。
- **空格/换行**:`元素==0x0020` 走空格步进;源串以 `0x000A` 结尾。
- 同一组校验函数 0x7BCC10/40/80 还被脚本系统复用(如 0x569CC5 的"跳过 DBCS 字符再把 a-z 转大写"循环、0x56CEB9、0x57D442–0x57D819 等)——PS2 端若要移植 DBCS,应把这些调用点一并考虑。

---

## 2. 查表(gbtext.def → 内存映射)

### 2.1 文件格式(经字节级实证)

`Data\Shell\Art\gbtext.def`(BIG5 版为 `big5text.def`),2,576 字节 = **1,288 条 × 2 字节**:

- **每条记录 2 字节 = [lead, trail](GBK 自然字节序)**。例:'。'(0xA1A3) 存为 `A1 A3`;'！'(0xA3A1) 存为 `A3 A1`;任(0xC8CE) 存为 `C8 CE`。
- 把整个文件按 **little-endian u16** 读出来的值 = `(trail<<8)|lead`(交换序);**全部 1,288 个值严格升序**(排序主键是 trail、次键 lead——生成工具的排序产物,运行期无意义)。
- 表覆盖 `strings.txt` 中出现的全部 522 个不同汉字 + 全角标点(实证 522/522 命中;缺字 fallback 见 §2.3)。

### 2.2 加载器 0x6581A0(逐指令关键路径)

```asm
0x6581CB  call 0x65A550          ; out = mgr+0x04("Data\Shell\Art\") + mgr+0x14("GB")
0x6581D0  push "text.def"        ; 0x8C7EA8
0x6581E1  call 0x65A680          ; fullpath = out + "text.def"   → "Data\Shell\Art\GBtext.def"
0x658249  push "rb" (0x8C7EA4); push fullpath; call 0x6FA93E   ; fopen
0x658259  test eax,eax / jne     ; fopen 失败 → push 0x896FB8; call 0x6F7BC3  → 抛 C++ 异常!
                                   ; ← 这就是 GB→BIG5 回退链的触发点(见 §4)
0x658278  mov al,[edi+0xC]       ; FILE 标志位
; --- 循环: 每次 fread(buf, 2, 1, f) 读一条 ---
0x658297  mov ecx,[esp+0x10]     ; ecx = *(u16*)buf = b0 | b1<<8
0x65829D  and eax,0xffff / and eax,0x800000ff / jns   ; eax = b0(第一字节=lead)
0x6582B7  shl eax,8              ; lead<<8
0x6582BA  mov dl,ch              ; dl = b1(trail)
0x6582C0  add eax,edx            ; key = (lead<<8)|trail      ← 自然码
0x6582C6  mov [esp+0x14],ax      ; key 作为 u16
0x6582D1  lea ecx,[ebp+0x44]     ; mgr+0x44 的 map
0x6582D4  call 0x6598E0          ; map.insert(key, 序号i)  — i = 记录顺序号(0..1287)
0x6582DD  mov word [edx+0xE], si ; map 节点 +0xE 处 = u16 slot 值
```

### 2.3 查找方式与缺字 fallback

- **查找 = std::map 平衡树(key=u16),不是线性也不是二分数组**。查找函数 0x657620(节点 +0/+4/+8 = 左/父/右指针,+0xC=key,+0xE=value),比较指令 `cmp word[eax+0xC], di`(0x65763D);插入 0x6598E0 同构。**比较时 key 按自然码原值比较,无任何交换。**
- **缺字 fallback:`slot = 0`**(0x6587DC 处默认 `[esp+0x40]=0`,find 命中 end 哨兵 `[mgr+0x48]` 时保持 0)——即渲染**表内第 0 格**(当前发行表里是 '！' 所在格;实际显示为固定字形,不是空格也不是动态豆腐)。 渲染测宽侧(0x658970)对不在表内的 DBCS 码同样按"整格宽"计(只要通过 0x7BCC80 校验)。

---

## 3. UV / 网格(0x658760,逐指令还原)

### 3.1 字号三档的选择(0x6586E0)

```asm
0x6586E0  mov eax,[esp+4]     ; 请求字号
          cmp eax,0x12 ; jg   ; ≤ 18 → 12
          mov eax,0xc ; ret
          cmp eax,0x18 / setg cl / dec ecx / and ecx,0xfffffff8 / add ecx,0x18
          ; 19..24 → 24;  >24 → 16  (0xFFFFFFFF&0xfffffff8+0x18 = 0x10)
```
**量化规则:`size ≤ 18 → 12;18 < size ≤ 24 → 24;size > 24 → 16`。** 每次取字形前都会调 0x658A80(当前字号)→ 0x6586E0 量化,且 0x658760 内还有保险:`if size ∉ {12,16,24} → 12`(0x6587FC)。

### 3.2 slot → (页号, 列, 行) 精确公式

0x658760 找到 slot 后(0x658848 起):

```
S        = 量化字号 ∈ {12, 16, 24}
perRow   = 512 / S                 ; 12→42, 16→32, 24→21   (idiv esi, 0x6587E5)
perPage  = perRow * perRow         ; 1764, 1024, 441       (imul ebp,edi, 0x6587F5)
page     = slot / perPage          ;                       (idiv ebp, 0x658852)
cell     = slot % perPage
row      = cell / perRow           ;                       (idiv edi, 0x658859)
col      = cell % perRow
X        = col * S   (像素)        ; 0x658861 imul edx,esi
Y        = row * S   (像素)        ; 0x658874 imul eax,esi
U0 = X / 512 ; V0 = Y / 512 ; U1 = (X+S)/512 ; V1 = (Y+S)/512   ; 0x65889B..0x6588B3 (fild/fdiv 512)
```
两处 idiv 用的除数分别来自 `[mgr]`(=0x200,构造时写入,0x657E1C)与 `perRow`。

**与发行文件的互证**:1,288 字 → 12px 每页 42²=1764 ≥ 1288 → 1 页(GB1200.tga ✓);16px 每页 32²=1024 → 2 页(GB1600+GB1601 ✓);24px 每页 21²=441 → ⌈1288/441⌉=3 页(GB2400/2401/2402 ✓)。**公式与磁盘文件完全吻合。**

### 3.3 页纹理的加载与 alpha 处理(0x658340)

```asm
0x658398  push "%s%s%02d%02d.TGA"; call 0x6F7F35      ; sprintf: dir + 前缀 + %02d(字号12/16/24) + %02d(页号) + ".TGA"
0x6583AB  call [0x859144]                              ; GetFileAttributesA(文件存在性)
          ; 失败(-1) → 0x6584C2; 成功 → OutputDebugStringA(文件名 + "\n")
0x6583FE  call 0x6591C0                                ; 注册进 mgr+0x34 的按字号 map(页向量)
```
文件名实例:`Data\Shell\Art\` + `GB` + `12` + `00` + `.TGA` → `GB1200.TGA`。TGA 为 32bpp(1,048,594 = 512²×4+18)。引擎随后经自身的 RSFILE/RSB 缓存系统转成 16bpp(R5G6B5)缓存——`Data\Shell\Art\gb1200.rsb` 等 524,397 字节 = 512×512×2 + 109 字节头,**转换后无 alpha 通道**,字形为黑底白笔画,渲染时应是加色/亮度混合(黑=透明)。原 32bpp TGA 的 alpha 在该管线下未被保留,PS2 端可直接用"亮度即 alpha"的近似。

---

## 4. 模式触发(GB2312 / BIG5)

**本 exe 的模式判定是"文件驱动 + 异常回退",与 GetACP/注册表/命令行无关**(GetACP 仅被 CRT 内部 wrapper `jmp [0x859250]` 引用一次,不参与字体):

1. CRT 静态初始化器表(0x8B0000..0x8B201C,`_initterm` 于 0x6FD2F3/0x6FD30C 调用)中,0x8B1420 项 → 字库初始化器 0x657DD0。
2. 初始化器是 `__try/__except`(MSVC EH4,作用域表 0x896EA8,handler 链中 `mov eax,0x657F04; ret` = 进入 BIG5 体的续接 thunk,`mov eax,0x657EEA; ret` = 跳到公共收尾):
   - `__try` 体 = **GB 分支**:拼 `GBtext.def`、`GB%02d%02d.TGA` 并加载;任一步失败(最典型:gbtext.def 或 GB*.TGA 缺失 → fopen 返回 NULL → 0x6581A0 内 0x65825B 处抛异常)→
   - `__except` 体 = **BIG5 分支**(0x657F04):同样流程换 `BIG5` 前缀。若 BIG5 也失败,再由外层续接 `0x657FFE → 0x657EEA` 收尾(无中文字库继续运行)。
3. 模式标志 `[0x8D353C]`:GB 成功 → 1(0x657EE3);BIG5 成功 → 0(0x657FF2)。数据段初值 = 1。
4. SXM 拉丁资源同样按标志分两组:`IDR_SXM12/16/24`(GB)vs `IDR_SXM12B/16B/24B`(BIG5)(0x7BC9BD/0x7BC9C6 处 `test [0x8D353C]`)。

> 附带发现:发行目录根下的 `Chinese.dat`(2,202 字节)是 GBK 编码的 UI 词条集("胜利！火并当场消灭所有敌人…"等),exe 内**没有**引用该文件名字符串——它应是本地化工具的语料/参考文件,不是引擎运行期数据。`Data\Shell\Art\Chinese0-4.rsb`(各 524,381B=512²×2bpp)为早期字库页缓存残留,exe 中同样无引用。

---

## 5. SXM 拉丁字模

### 5.1 资源与描述符表

SXM = exe 内 **RT_RCDATA 资源,类型名 "SXM"**(0x7BC950:`FindResourceA(0, name, "SXM")` → LoadResource → LockResource;任一步失败 → `malloc(0x100000)` 兜底零缓冲)。字体初始化 0x7BC990 建立三档描述符表(0xA4E1E0,步距 0x30):

| 档 | 基址 | +00 | +04 | +08/+0C | +10 资源 | +14 | +18 | +1C 度量表(SXME,大小) |
|---|---|---|---|---|---|---|---|---|
| 0(小) | 0xA4E1E0 | 12 | 12 | 1,1 | IDR_SXM12(GB)/SXM12B(BIG5) | 7 | 12 | 0xA4E1FC ← IDR_SXME12(2688B) |
| 1(中) | 0xA4E210 | 16 | 16 | 1,1 | IDR_SXM16/SXM16B | 11 | 19 | 0xA4E22C ← IDR_SXME16(6688B) |
| 2(大) | 0xA4E240 | 24 | 24 | 1,1 | IDR_SXM24/SXM24B | 18 | 29 | 0xA4E25C ← IDR_SXME24(16704B) |

- `+14/+18` 为上下沿/基线类排版常数(12px:7/12,16px:11/19,24px:18/29)。
- SXME 度量表结构(0x7C15C0):`{+4: 数据指针, +8: size*8, +0xC: size}`——8 字节/字形的度量记录数组。
- **GB 与 BIG5 的 SXM 是不同资源**(B 后缀),即拉丁字形也随编码分套。

### 5.2 与中文字库的组合(混排)

字体对象(vtable 0x866FD0,0x658710 构造)的 `[obj+0x28]` 指向当前档 SXM 字形集,关键字段:
- `+0x20` 首字符码,`+0x44` 字形数(索引 = code − 首字符,越界钳 0);
- `+0x38` 字形数组,**10 字节/字形**:`[+1]`=advance(u8),`[+2..+9]`=4×u16(x0,y0,x1,y1 像素坐标);
- `+0x28/+0x2C` 纹理宽/高(UV 归一化分母),`+0x14`=空格宽,`+0x1C`=全局缩放(1.0)。

**混排规则(0x658760 渲染、0x658970 测宽同一套逻辑):**
1. 对每个元素先做 `IsDBCS` 校验(0x7BCC80);
2. DBCS ✓ → 走 mgr+0x44 映射 → 中文纹理页 UV,advance = **整格宽**(0x6586E0 量化值,0x658A35);
3. DBCS ✗ → 走 SXM 字形:索引钳位后取 10 字节记录的 UV 与 advance(0x6588C0..0x658969);
4. 字库未就绪时(`[0x91C728]==0`,0x658970 的 je 0x6589E8 分支)退化为纯 SXM 度量。

基线对齐:宽字符串中汉字/拉丁共用同一行高推进,行进 `+= 当前字 advance × [esp+0x28] 缩放`;`[esp+0x48]` 累计 x 偏移(0x655DA5 `fmul`、0x65644A `fadd`)。混排无独立的"中西文间距"调整——汉字天然占满整格,视觉间距由格尺寸决定。

> 备注:0x658970 的 DBCS/ASCII 两分支分别引用串字面量 0x8C7ECC("\xCA\xC7")与 0x8C7EC8("A")再调 0x7BD400(分档取代表宽),该辅助函数未完全展开,但不影响上述主链结论。

---

## 6. 副产品:ike 引擎 PC/PS2 共享代码指纹

为判断 PS2 ELF 中同类函数的可移植性,提炼以下"编译指纹"(均在本 exe 实测):

1. **异常驱动的资源回退**:本地化代码大量使用 `fopen==NULL → 抛 C++ 异常 → __except 换参数重试`(MSVC EH4:push -1/push handler/mov fs:[0],esp 序言 + 状态字节 [ebp-4] + `mov eax,续接地址; ret` 续接 thunk)。PS2 端(通常无 EH)应改为**显式 if/else**——回退顺序本身就是配置语义。
2. **侵入式 std::map<u16,u16>**(Dinkumware 风格):节点 `{+0 左, +4 父, +8 右, +0xC key, +0xE value}`,红色黑色位在父指针低位域;查找/插入为平尾树walk。PS2 移植时可换成定长数组 + 二分(表本身有序),语义等价、代码量更小。
3. **字符串类**:16 字节 SSO(`{char buf[4]; char* heap; len; cap}`,堆块前置引用计数 `[ptr-1]`,0xFF 为特殊值),append=0x434610,clear=0x402D40,析构 funclet 统一跳 0x402B00。PS2 端直接用定长 char 数组即可。
4. **度量/UV 惯用式**:`and eax,0x800000ff; jns; dec; or 0xffffff00; inc` = (signed char) 扩展(0x6582A2/0x658777/0x6589A0/0x658A13 共 4 处);整数→float 一律 `fild`,除法 `fdiv`。PS2(MIPS)对应 `sll/sra` 与 `lwc1/cvt.s.w`。
5. **网格常量指纹**:页宽 512 写死在对象 +0;`perRow=512/S`、`perPage=perRow²`、slot 三段 idiv——PS2 端若同样用 512×512 页,可直接复用公式(注意 MIPS 无 32 位除法指令,用整乘 magic 或查表)。
6. **日志/存在性检查**:`OutputDebugStringA`([0x8590E8],所以 Ike.log 里看不到 "Chinese ... Texture Loaded")与 `GetFileAttributesA`([0x859144]);PS2 端对应换成 printf/`fopen` 探测即可。
7. **共享函数识别特征**(同源代码在 PS2 ELF 中的样子):三函数簇 `IsLead/IsTrail/IsDBCS` 常量对 (0xA1,0xFE)/(0xA1,0xF9)/(0x40,0x7E) 非常独特;`shl ax,8; add ax,[edi]` 的 key 合成;42/32/21 三档步进;`"%s%s%02d%02d"` 命名式。PS2 版若带本地化,大概率有同样的常量对可 grep。

---

## 7. 对 PS2 ELF DBCS 补丁的借鉴要点

**可直接移植的设计(建议照抄):**

1. **编码方案**:查表键 = `(lead<<8)|trail` 自然码;`text.def` 式"字表文件"与字形页分离——补丁可以在不改 ELF 数据段的情况下扩字。若想省一次转换,PS2 端也可直接采用**交换序键 `(trail<<8)|lead`**(即把文件当 LE u16 读的视角),只要全链一致即可;PC 版的真实选择是"文件字节=[lead,trail]、运行键=自然码"。
2. **lead/trail 范围**:GB 用 `lead[0xA1,0xFE] + trail([0x40,0x7E]∪[0xA1,0xFE])`(GBK);若目标盘只有 GB2312 字表,收窄到 PC 版表内实际覆盖(本项目表内无 trail<0xA1 的字,因此引擎实际只要 `trail∈[A1,FE]` 就够——两套范围在 PC 上靠 0x7BCC40 的双区间兼容了 GBK 扩展区)。
3. **缺字 fallback**:固定 slot 0(表内第 0 格)。比"空白"更好的是**预留一个可辨识字形**(如全角空格/方框)放在 0 号格——PC 表 0 号是 '！',属于历史巧合,补丁不必模仿。
4. **字号量化**:`≤18→12、≤24→24、>24→16` 的三档 + "非三档值回退 12" 的保险,UI 侧只需给一个期望字号。
5. **混排**:DBCS=整格宽、拉丁=字形自带 advance、空格特判;不需要额外间距参数。
6. **页组织**:`slot → page=slot/(512/S)² → row,col`,页文件名 `%s%02d%02d.TGA` 式编号;补丁若沿用 512×512 页,GB1600(2 页)/GB2400(3 页) 的页数公式可直接算。

**需要绕开/重做的:**

1. **宽字符串"字节零扩展"中间表示**:PC 版把 GBK 串扩成假宽串再在渲染器里重组——PS2 端建议直接在 MBCS 字节串上扫描(跳过 trail 字节即可),省掉两次转换,也避免“元素计数 vs 字符计数”两套步进并存带来的坑(PC 用 `计数器+2/指针+4` 同时消化,见 0x6561C5-0x6561C8 与底部 0x656471-74)。
2. **异常驱动回退**:换显式探测(`GetFileAttributes` → `fopen`),顺序保持"先查表文件再加载页纹理"即可完整复刻 GB→BIG5 语义(在 PS2 上即"中文简体→中文繁术→无中文"三级)。
3. **std::map**:用有序数组二分(文件天然按 (trail<<8)|lead 升序——注意这是 LE-u16 视角,做二分比较时要把键同样转成交换序,或加载时顺手字节交换)。
4. **alpha**:PS2 纹理若走 4bpp/8bpp CLUT 或 16bpp,黑底白字 + 加色混合最省事;不要指望 TGA 的 alpha 通道(PC 自己都没保留)。
5. **SXM 拉丁字模**:PS2 端可沿用"10 字节/字形(1 advance + 4×u16 坐标)"的紧凑度量记录与"首字符+数量"的索引钳位法;中英混排只需在扫描器里把非 DBCS 元素转发给拉丁字形集。

---

## 附:关键 VA 速查

| VA | 内容 |
|---|---|
| 0x657DD0 / 0x657F04 | 字库初始化器 GB 分支 / BIG5 分支(EH4 回退) |
| 0x6581A0 | text.def 加载器(fopen→2 字节记录→map 插入;失败即抛异常) |
| 0x658340 | TGA 页纹理加载(sprintf "%s%s%02d%02d.TGA" + GetFileAttributesA) |
| 0x6586E0 | 字号量化(≤18→12,≤24→24,>24→16) |
| 0x658760 | slot→UV 核心(含 SXM fallback 渲染路径) |
| 0x658970 | 字符测宽(DBCS=整格宽/拉丁=SXM advance) |
| 0x657620 / 0x6598E0 | map 查找 / 插入(节点 key+0xC, value+0xE) |
| 0x7BCC10 / 0x7BCC40 / 0x7BCC80 | IsLead / IsTrail / IsDBCS(GB[1]/BIG5[0] 由 [0x8D353C] 切换) |
| 0x655A10 / 0x655D46 | 文本渲染主函数 / DBCS 扫描循环 |
| 0x658010 | GetModuleFileNameA 路径解析 |
| 0x7BC990 / 0x7BC950 / 0x7C15C0 / 0x7BCBB0 | SXM 初始化 / RCDATA 查找 / SXME 度量挂接 / 字号分档(0/1/2) |
| 0xA4E1E0(步距 0x30) | SXM 三档描述符表 |
| 0x8D353C | 模式标志(1=GB,0=BIG5) |
| 0x91C738 | 字库管理器单例指针(0x54 字节对象;+0x34 字号 map,+0x44 编码 map,[+0]=512) |
| 0x8B0000..0x8B201C | CRT 静态初始化器表(0x8B1420 = 字库初始化器) |

**中间产物**:`C:\gr_build\tmp\pcfont\dis\`(fontload_full.asm=初始化器全文、fm_658760.asm=UV 全文、render_trace.asm=渲染循环全程带 esp 跟踪、tga_658340.asm、cdis.py/callx.py/trace.py=逆向工具)。
