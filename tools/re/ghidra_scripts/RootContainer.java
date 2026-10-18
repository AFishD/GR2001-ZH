// RootContainer.java - 反编译"容器管理器": 盘上到底挂了哪些 IMG、按什么顺序搜
// 跑法: work\tools\gh.bat work\tools\ghidra_proj_ee GRLocEE -process SLUS_206.13.elf -postScript RootContainer.java -scriptPath work\tools\ghidra_scripts -noanalysis
//@category GRLoc

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;
import ghidra.util.task.ConsoleTaskMonitor;

public class RootContainer extends GhidraScript {

    private static final String[] KEY = {
        "RSRootContainer", "RSFileData", "Mount", "mount", "RSModsFinder", "RSModsSystem",
        "AddContainer", "OpenContainer", "RSContainer",
    };

    @Override
    public void run() throws Exception {
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);

        println("########## 容器/挂载相关符号 ##########");
        SymbolIterator it = currentProgram.getSymbolTable().getAllSymbols(true);
        java.util.List<Function> todo = new java.util.ArrayList<>();
        int n = 0;
        while (it.hasNext() && n < 300) {
            Symbol s = it.next();
            String nm = s.getName();
            boolean hit = false;
            for (String k : KEY) if (nm.contains(k)) { hit = true; break; }
            if (!hit) continue;
            Address a = s.getAddress();
            Function f = getFunctionAt(a);
            if (f == null) f = getFunctionContaining(a);
            println(String.format("  %-64s @0x%08X  %s", nm, a.getOffset(),
                    f != null ? ("size=" + f.getBody().getNumAddresses()
                                 + " callers=" + f.getCallingFunctions(mon).size()) : "(非函数)"));
            if (f != null && !todo.contains(f)) todo.add(f);
            n++;
        }
        println("  命中 " + n);

        // 只反编译前 14 个最大的(信息量最大)
        todo.sort((Function a, Function b) ->
                Long.compare(b.getBody().getNumAddresses(), a.getBody().getNumAddresses()));
        int shown = 0;
        for (Function f : todo) {
            if (shown++ >= 10) break;
            println("");
            println("==================================================================");
            println("## " + f.getName() + " @0x" + Long.toHexString(f.getEntryPoint().getOffset())
                    + "  size=" + f.getBody().getNumAddresses());
            println("==================================================================");
            DecompileResults res = dec.decompileFunction(f, 300, mon);
            if (res != null && res.decompileCompleted()) {
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
