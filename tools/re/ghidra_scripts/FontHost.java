// FontHost.java - 反编译"贴图/字体资源查找链", 回答: 字形贴图能不能搬到别的容器?
// 用 r5900 工程跑: work\tools\gh.bat work\tools\ghidra_proj_ee GRLocEE -process SLUS_206.13.elf -postScript FontHost.java -scriptPath work\tools\ghidra_scripts -noanalysis
//@category GRLoc

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;
import ghidra.util.task.ConsoleTaskMonitor;

public class FontHost extends GhidraScript {

    // 名称关键词: 找出所有相关的函数(按符号名)
    private static final String[] NAME_KEYS = {
        "RSFontMgr", "UITextureMgr", "UITexture", "LoadIndexedRSB", "LoadRSBFile",
        "LoadingTexturePak", "ReadResourceFile", "SetTexture", "GetTexture",
        "FindSurface", "new_font_revised", "pda_counterparts", "COMMON",
        "RSFilename", "LoadTexture",
    };

    private static final long[] VAS = {
        0x0051B660L, // UITextureMgr::LoadingTexturePak
        0x0051B230L, // LoadIndexedRSB
        0x0051C810L, // UITexture::LoadRSBFile
        0x0051B8F0L, // (报告提到的区域, 未知也打印)
        0x0051C000L,
    };

    @Override
    public void run() throws Exception {
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);

        println("########## 符号名匹配的函数 ##########");
        SymbolIterator it = currentProgram.getSymbolTable().getAllSymbols(true);
        int n = 0;
        while (it.hasNext() && n < 400) {
            Symbol s = it.next();
            String nm = s.getName();
            boolean hit = false;
            for (String k : NAME_KEYS) {
                if (nm.contains(k)) {
                    hit = true;
                    break;
                }
            }
            if (hit) {
                Address a = s.getAddress();
                Function f = getFunctionAt(a);
                if (f == null) f = getFunctionContaining(a);
                println(String.format("  %-58s @0x%08X  %s", nm, a.getOffset(),
                        f != null ? ("func=0x" + Long.toHexString(f.getEntryPoint().getOffset())
                                     + " size=" + f.getBody().getNumAddresses()
                                     + " callers=" + f.getCallingFunctions(mon).size()) : "(非函数)"));
                n++;
            }
        }
        println("  命中 " + n + " 个符号");

        println("");
        println("########## 指定地址的反编译 ##########");
        for (long va : VAS) {
            Address addr = toAddr(va);
            Function f = getFunctionContaining(addr);
            println("");
            println("===== VA 0x" + Long.toHexString(va) + " =====");
            if (f == null) {
                println("  (不在任何已知函数内)");
                continue;
            }
            println(String.format("  函数 %s 入口 0x%08X 大小 %d",
                    f.getName(), f.getEntryPoint().getOffset(), f.getBody().getNumAddresses()));
            for (Function cf : f.getCallingFunctions(mon)) {
                println(String.format("     <= 被 0x%08X %s 调用",
                        cf.getEntryPoint().getOffset(), cf.getName()));
            }
            DecompileResults res = dec.decompileFunction(f, 300, mon);
            if (res != null && res.decompileCompleted()) {
                println("  ---- C ----");
                println(res.getDecompiledFunction().getC());
            } else {
                println("  (反编译未完成: " + (res == null ? "null" : res.getErrorMessage()) + ")");
            }
        }
        dec.dispose();
        println("");
        println("### DONE ###");
    }
}
