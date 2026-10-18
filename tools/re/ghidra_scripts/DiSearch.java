// DiSearch.java - 反编译 diSearchFile (资源查找总入口): 决定"大贴图能放哪"
// 跑法: work\tools\gh.bat work\tools\ghidra_proj_ee GRLocEE -process SLUS_206.13.elf -postScript DiSearch.java -scriptPath work\tools\ghidra_scripts -noanalysis
//@category GRLoc

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;
import ghidra.util.task.ConsoleTaskMonitor;

public class DiSearch extends GhidraScript {

    @Override
    public void run() throws Exception {
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);

        // 1) 按符号名找 diSearchFile 及其家族
        println("########## di* / Search 符号 ##########");
        SymbolIterator it = currentProgram.getSymbolTable().getAllSymbols(true);
        int n = 0;
        java.util.List<Function> todo = new java.util.ArrayList<>();
        while (it.hasNext() && n < 200) {
            Symbol s = it.next();
            String nm = s.getName();
            if (nm.startsWith("diSearch") || nm.startsWith("diOpen") || nm.contains("SearchFile")
                || nm.startsWith("diMount") || nm.startsWith("diFind")
                || nm.contains("LoadIndexedRSB") || nm.contains("GetTexture__12UITextureMgr")) {
                Address a = s.getAddress();
                Function f = getFunctionAt(a);
                if (f == null) f = getFunctionContaining(a);
                println(String.format("  %-60s @0x%08X  %s", nm, a.getOffset(),
                        f != null ? ("size=" + f.getBody().getNumAddresses()
                                     + " callers=" + f.getCallingFunctions(mon).size()) : "(非函数)"));
                if (f != null && !todo.contains(f)) todo.add(f);
                n++;
            }
        }
        println("  命中 " + n);

        // 2) 逐个反编译
        for (Function f : todo) {
            println("");
            println("==================================================================");
            println("## " + f.getName() + " @0x" + Long.toHexString(f.getEntryPoint().getOffset()));
            println("==================================================================");
            println(String.format("  大小 %d  调用者 %d", f.getBody().getNumAddresses(),
                    f.getCallingFunctions(mon).size()));
            for (Function cf : f.getCallingFunctions(mon)) {
                println(String.format("     <= 被 0x%08X %s 调用",
                        cf.getEntryPoint().getOffset(), cf.getName()));
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
