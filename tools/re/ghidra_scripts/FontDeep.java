// FontDeep.java - Ghidra headless post-script (round73): decompile ONLY the VAs given as
// arguments, with a long timeout, and report the C length + error so a silent empty result
// is visible.
// Usage: gh.bat <proj> GRLocEE -process SLUS_206.13.elf -postScript FontDeep.java \
//              -scriptPath <dir> -noanalysis 0x51B660 0x219380 ...
//@category GRLoc

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.util.task.ConsoleTaskMonitor;

public class FontDeep extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args == null || args.length == 0) {
            println("no VAs given");
            return;
        }
        println("language = " + currentProgram.getLanguageID());
        DecompInterface dec = new DecompInterface();
        dec.toggleCCode(true);
        dec.toggleSyntaxTree(false);
        dec.openProgram(currentProgram);
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();

        for (String s : args) {
            long va;
            try {
                va = Long.parseLong(s.replace("0x", "").replace("0X", ""), 16);
            } catch (Exception e) {
                println("bad VA: " + s);
                continue;
            }
            Address addr = toAddr(va);
            println("");
            println("=== VA 0x" + String.format("%08X", va) + " ===");
            Function f = getFunctionContaining(addr);
            if (f == null) {
                println("  (no function)");
                continue;
            }
            println(String.format("  func %s entry=0x%08X size=%d",
                    f.getName(), f.getEntryPoint().getOffset(),
                    f.getBody().getNumAddresses()));
            for (Function cf : f.getCallingFunctions(mon)) {
                println(String.format("     <= caller 0x%08X %s",
                        cf.getEntryPoint().getOffset(), cf.getName()));
            }
            DecompileResults res = dec.decompileFunction(f, 900, mon);
            if (res == null) {
                println("  (res == null)");
                continue;
            }
            if (!res.decompileCompleted()) {
                println("  (not completed: " + res.getErrorMessage() + ")");
            }
            String c = (res.getDecompiledFunction() == null) ? null
                    : res.getDecompiledFunction().getC();
            println("  C length = " + (c == null ? -1 : c.length()));
            if (c != null && c.length() > 0) {
                for (String line : c.split("\n", -1)) {
                    println("  | " + line);
                }
            }
        }
        dec.dispose();
        println("");
        println("### DONE FontDeep ###");
    }
}
