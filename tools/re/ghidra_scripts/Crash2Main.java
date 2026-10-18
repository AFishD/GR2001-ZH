// Crash2Main.java - main decompile pass for the "round 74" crash chain.
//
// Chain A (heap corruption, 434.15s):
//   pc=0x101D10 addr=0x22D1624 [load]     <- chunk_free(arena*, malloc_chunk*)
//   pc=0x101DD8 addr=0x4154536F [store]   <- stores into a bogus "chunk" that is ASCII text
//   ...
//   pc=0x101E6C addr=0x22D161C [store]
// Chain B (null deref, 492.88s):
//   pc=0x25E86C addr=0x14 [load]          <- *(...)= NULL[0x14]
//   pc=0x0      addr=0x0    [load] x3
//
//@category GRLoc

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;
import ghidra.util.task.ConsoleTaskMonitor;

public class Crash2Main extends GhidraScript {

    private void dumpInstructions(Address start, int count) {
        Address a = start;
        for (int k = 0; k < count; k++) {
            Instruction ins = currentProgram.getListing().getInstructionAt(a);
            println(String.format("    %s  %s", a, ins == null ? "(no instruction)" : ins.toString()));
            a = a.add(4);
        }
    }

    private void dumpFunction(DecompInterface dec, ConsoleTaskMonitor mon, Address addr, String why) {
        println("");
        println("============================================================");
        println(String.format("VA 0x%08X  (%s)", addr.getOffset(), why));
        Function f = getFunctionContaining(addr);
        if (f == null) {
            println("  (not inside any defined function)");
            return;
        }
        println(String.format("  function %s  entry=0x%08X  size=%d",
                f.getName(), f.getEntryPoint().getOffset(), f.getBody().getNumAddresses()));
        for (Function cf : f.getCallingFunctions(mon)) {
            println(String.format("      <= called by 0x%08X %s",
                    cf.getEntryPoint().getOffset(), cf.getName()));
        }
        DecompileResults res = dec.decompileFunction(f, 120, mon);
        if (res != null && res.decompileCompleted()) {
            println("  ---- decompiled (" + res.getDecompiledFunction().getSignature() + ") ----");
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

        println("### CRASH2 MAIN ###");
        println("program=" + currentProgram.getName() + " lang=" + currentProgram.getLanguageID());

        // ---------------------------------------------------------------
        // 1. Who owns 0x25E86C?  List every function whose body precedes it.
        // ---------------------------------------------------------------
        println("");
        println("=== 1. functions nearest BELOW 0x25E86C ===");
        Address target = toAddr(0x0025E86CL);
        FunctionIterator fit = currentProgram.getFunctionManager().getFunctions(target, false);
        int n = 0;
        while (fit.hasNext() && n < 8) {
            Function f = fit.next();
            println(String.format("   next func after target: 0x%08X %s size=%d",
                    f.getEntryPoint().getOffset(), f.getName(), f.getBody().getNumAddresses()));
            n++;
        }
        FunctionIterator pit = currentProgram.getFunctionManager().getFunctions(target, true);
        n = 0;
        while (pit.hasNext() && n < 8) {
            Function f = pit.next();
            println(String.format("   prev func before target: 0x%08X %s size=%d",
                    f.getEntryPoint().getOffset(), f.getName(), f.getBody().getNumAddresses()));
            n++;
        }

        println("");
        println("=== 1b. raw instructions at/around 0x25E86C (32 insns from 0x25E800) ===");
        dumpInstructions(toAddr(0x0025E800L), 80);

        println("");
        println("=== 1c. any symbol whose address is within 0x25E700..0x25EA00 ===");
        SymbolIterator sit = currentProgram.getSymbolTable().getAllSymbols(true);
        while (sit.hasNext()) {
            Symbol s = sit.next();
            long o = s.getAddress().getOffset();
            if (o >= 0x0025E700L && o <= 0x0025EA00L) {
                println(String.format("   0x%08X  %s  (%s)", o, s.getName(), s.getSymbolType()));
            }
        }

        println("");
        println("=== 1d. references TO 0x25E86C and to nearby function starts ===");
        for (long va : new long[]{0x0025E86CL, 0x0025E800L, 0x0025E700L, 0x0025E900L}) {
            Reference[] refs = getReferencesTo(toAddr(va));
            println(String.format("   -> 0x%08X : %d refs", va, refs.length));
            for (Reference r : refs) {
                println(String.format("         from 0x%08X (%s)", r.getFromAddress().getOffset(), r.getReferenceType()));
            }
        }

        // ---------------------------------------------------------------
        // 2. chunk_free and friends
        // ---------------------------------------------------------------
        dumpFunction(dec, mon, toAddr(0x00101D10L), "chunk_free(arena*, malloc_chunk*) -- chain A entry");
        println("");
        println("  ---- chunk_free instructions 0x101D10..0x101E80 ----");
        dumpInstructions(toAddr(0x00101D10L), 96);

        println("");
        println("=== 2b. all symbols with 'chunk' / 'arena' / 'malloc' in the name ===");
        SymbolIterator sit2 = currentProgram.getSymbolTable().getAllSymbols(true);
        while (sit2.hasNext()) {
            Symbol s = sit2.next();
            String nm = s.getName();
            if (nm.contains("chunk") || nm.contains("arena") || nm.contains("malloc")
                    || nm.contains("_malloc") || nm.contains("sbrk") || nm.contains("memalign")) {
                println(String.format("   0x%08X  %s  (%s)", s.getAddress().getOffset(), nm, s.getSymbolType()));
            }
        }

        // ---------------------------------------------------------------
        // 3. what calls 0x25E86C region?  Look for jal targets landing there
        // ---------------------------------------------------------------
        println("");
        println("=== 3. disassemble a window before 0x25E86C to find the function prologue ===");
        println("(looking for 'addiu sp,sp,-N' pattern in the 0x25E600..0x25E870 range)");
        for (long a = 0x0025E600L; a < 0x0025E8A0L; a += 4) {
            Instruction ins = currentProgram.getListing().getInstructionAt(toAddr(a));
            if (ins == null) continue;
            String t = ins.toString();
            if (t.startsWith("addiu") && t.contains("sp,sp,-") && t.contains("0x")) {
                println(String.format("   possible prologue 0x%08X  %s", a, t));
            }
        }

        dec.dispose();
        println("");
        println("### CRASH2 MAIN DONE ###");
    }
}
