// Crash2Probe.java - probe program language + symbol table around the crash PCs.
//@category GRLoc

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;

public class Crash2Probe extends GhidraScript {

    private static final long[] VAS = {
        0x0025E86CL,
        0x00101D10L,
        0x00101DD8L,
        0x00101DE4L,
        0x00101E08L,
        0x00101E34L,
        0x00101E6CL,
    };

    @Override
    public void run() throws Exception {
        println("### PROBE START ###");
        println("program    = " + currentProgram.getName());
        println("exe path   = " + currentProgram.getExecutablePath());
        println("language   = " + currentProgram.getLanguageID());
        println("imageBase  = " + currentProgram.getImageBase());
        println("minAddr    = " + currentProgram.getMinAddress());
        println("maxAddr    = " + currentProgram.getMaxAddress());
        println("funcs      = " + currentProgram.getFunctionManager().getFunctionCount());
        println("symbols    = " + currentProgram.getSymbolTable().getNumSymbols());
        println("mem blocks:");
        for (var b : currentProgram.getMemory().getBlocks()) {
            println(String.format("   %-20s %s - %s  size=0x%X  r=%b w=%b x=%b",
                b.getName(), b.getStart(), b.getEnd(), b.getSize(),
                b.isRead(), b.isWrite(), b.isExecute()));
        }

        println("");
        println("=== function containing each crash PC ===");
        for (long va : VAS) {
            Address a = toAddr(va);
            Function f = getFunctionContaining(a);
            println(String.format("0x%08X -> %s", va,
                f == null ? "(none)" : String.format("%s @0x%08X size=%d",
                    f.getName(), f.getEntryPoint().getOffset(),
                    f.getBody().getNumAddresses())));
        }

        println("");
        println("=== symbols whose name contains interesting keywords ===");
        String[] keys = {"chunk", "malloc", "free", "arena", "heap", "IkeObjectMgr",
                         "Awareness", "SaveGame", "GameState", "LoadGame"};
        SymbolIterator sit = currentProgram.getSymbolTable().getAllSymbols(true);
        int shown = 0;
        while (sit.hasNext() && shown < 400) {
            Symbol s = sit.next();
            String n = s.getName();
            for (String k : keys) {
                if (n.contains(k)) {
                    println(String.format("   0x%08X  %s", s.getAddress().getOffset(), n));
                    shown++;
                    break;
                }
            }
        }
        println("(matched " + shown + " symbols)");
        println("### PROBE DONE ###");
    }
}
