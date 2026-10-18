// Crash2EE.java - decompile the round-74 crash chain using the r5900 (EmotionEngine)
// project, which DOES decode SPECIAL2/MMI.  Run against project GRLocEE.
//@category GRLoc

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.util.task.ConsoleTaskMonitor;

public class Crash2EE extends GhidraScript {

    private void dis(Address start, int count) {
        Address a = start;
        for (int k = 0; k < count; k++) {
            Instruction ins = currentProgram.getListing().getInstructionAt(a);
            println("    " + a + "  " + (ins == null ? "(no instruction)" : ins.toString()));
            a = a.add(4);
        }
    }

    private void decomp(DecompInterface dec, ConsoleTaskMonitor mon, long va, String why, boolean showCallers) {
        println("");
        println("============================================================");
        Address addr = toAddr(va);
        println(String.format("VA 0x%08X   (%s)", va, why));
        Function f = getFunctionContaining(addr);
        if (f == null) {
            println("  (no function)");
            return;
        }
        println(String.format("  FUNC %s   entry=0x%08X  size=%d",
                f.getName(), f.getEntryPoint().getOffset(), f.getBody().getNumAddresses()));
        if (showCallers) {
            for (Function cf : f.getCallingFunctions(mon)) {
                println(String.format("      <= called by 0x%08X  %s",
                        cf.getEntryPoint().getOffset(), cf.getName()));
            }
        }
        DecompileResults res = dec.decompileFunction(f, 180, mon);
        if (res != null && res.decompileCompleted()) {
            println("  ---- decompiled ----");
            println("  /* signature: " + res.getDecompiledFunction().getSignature() + " */");
            println(res.getDecompiledFunction().getC());
        } else {
            println("  (decompile failed: " + (res == null ? "null" : res.getErrorMessage()) + ")");
        }
    }

    @Override
    public void run() throws Exception {
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);

        println("### CRASH2 EE ###");
        println("program=" + currentProgram.getName());
        println("language=" + currentProgram.getLanguageID());
        println("funcs=" + currentProgram.getFunctionManager().getFunctionCount());

        // 1. the 492.88s crash: IkeSoundMgr::SetPause
        decomp(dec, mon, 0x0025E86CL, "lw $25,0x14($2) with $2==NULL  -- the fatal call", true);
        println("");
        println("  ---- SetPause instructions at the crash site ----");
        dis(toAddr(0x0025E84CL), 30);

        // 2. the two callers of SetPause
        for (long c : new long[]{0x0025E494L, 0x0025E614L}) {
            decomp(dec, mon, c, "caller of IkeSoundMgr::SetPause", true);
        }

        // 3. who supplies the sound object at this+820 (0x334)
        println("");
        println("============================================================");
        println("=== all IkeSoundMgr methods (to identify the object layout) ===");
        var it = currentProgram.getFunctionManager().getFunctions(true);
        while (it.hasNext()) {
            Function f = it.next();
            String n = f.getName();
            if (n.contains("IkeSoundMgr")) {
                println(String.format("   0x%08X  %-58s size=%d",
                        f.getEntryPoint().getOffset(), n, f.getBody().getNumAddresses()));
            }
        }

        // 4. the 434.15s heap-corruption site
        decomp(dec, mon, 0x00101D10L, "chunk_free(arena*, malloc_chunk*)", false);
        println("");
        println("  ---- chunk_free instructions 0x101D10..0x101E90 ----");
        dis(toAddr(0x00101D10L), 96);

        println("");
        println("=== dlmalloc helpers called by chunk_free ===");
        for (long va : new long[]{0x00101B00L, 0x00101C00L, 0x00102000L, 0x00102018L,
                                  0x00102200L, 0x00102400L}) {
            Function f = getFunctionContaining(toAddr(va));
            println(String.format("   0x%08X -> %s", va,
                    f == null ? "(none)" : String.format("0x%08X %s", f.getEntryPoint().getOffset(), f.getName())));
        }

        dec.dispose();
        println("");
        println("### CRASH2 EE DONE ###");
    }
}
