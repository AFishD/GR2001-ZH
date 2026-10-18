// FileRegistry.java - 反编译 RS 引擎的文件注册表: 决定"哪些容器被搜、什么顺序、能否注册新文件"
// 跑法: work\tools\gh.bat work\tools\ghidra_proj_ee GRLocEE -process SLUS_206.13.elf -postScript FileRegistry.java -scriptPath work\tools\ghidra_scripts -noanalysis
//@category GRLoc

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;
import ghidra.util.task.ConsoleTaskMonitor;

public class FileRegistry extends GhidraScript {

    // 上一轮已确认的调用者地址(有真实符号名)
    private static final long[] VAS = {
        0x005475B0L, // RSFileData::FindFile(const RSString&)
        0x00547640L, // RSFileData::FileHandle(const RSString&)
        0x00546E00L, // RSFileData::Found(const RSString&)
        0x005476A0L, // RSFileData::RegisterFullPath(const RSFilename&)
        0x005476D0L, // RSFileData::Register(const RSString&)
        0x00511300L, // RSRootContainer::ReadResourceFile(const char*, bool)
        0x0050DF90L, // RSContainer::ReadResource(istream&)
        0x00169D20L, // RSFileData::Get()
        0x00548C20L, // RSModsSystem::LoadModsSettings(const RSFilename&)
        0x00547E30L, // RSModsFinder::LoadModsContents(const RSFilename&)
    };

    @Override
    public void run() throws Exception {
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);

        for (long va : VAS) {
            Address addr = toAddr(va);
            Function f = getFunctionContaining(addr);
            if (f == null) f = getFunctionAt(addr);
            println("");
            println("################################################################");
            println("## 0x" + Long.toHexString(va) + (f != null ? ("  = " + f.getName()) : "  (无函数)"));
            println("################################################################");
            if (f == null) {
                println("  ✗ 不在任何函数内");
                continue;
            }
            println(String.format("  入口 0x%08X 大小 %d 调用者 %d",
                    f.getEntryPoint().getOffset(), f.getBody().getNumAddresses(),
                    f.getCallingFunctions(mon).size()));
            // 该函数调用了谁(看它找文件时用了哪些 API)
            println("  ---- 它调用的函数 ----");
            int n = 0;
            for (Function cf : f.getCalledFunctions(mon)) {
                if (n++ >= 14) { println("     …"); break; }
                println(String.format("     -> 0x%08X %s", cf.getEntryPoint().getOffset(), cf.getName()));
            }
            DecompileResults res = dec.decompileFunction(f, 300, mon);
            if (res != null && res.decompileCompleted()) {
                println("  ---- C ----");
                println(res.getDecompiledFunction().getC());
            } else {
                println("  (未完成: " + (res == null ? "null" : res.getErrorMessage()) + ")");
            }
        }
        dec.dispose();
        println("");
        println("### DONE ###");
    }
}
