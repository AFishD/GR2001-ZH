// FontDecomp.java - Ghidra headless post-script (round73 font-decompile)
// Purpose: decompile + disassemble the font loading / char addressing / glyph table
//          chain of SLUS_206.13.elf, and list callers of each site.
// Usage : gh.bat <proj> GRLoc -process SLUS_206.13.elf -postScript FontDecomp.java
//                 -scriptPath <dir> -noanalysis  [extra VAs as hex args]
//@category GRLoc

import java.util.ArrayList;
import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.util.task.ConsoleTaskMonitor;

public class FontDecomp extends GhidraScript {

    // default sites (font chain) ; extra sites may be appended on the command line
    private static final long[] DEFAULT_VAS = {
        0x416E80L,  // gate site 1 region + the cave that computes the grid
        0x417050L,  // cave entry (grid formula)
        0x417140L,  // gate site 2
        0x4174F0L,  // gate site 3
        0x565680L,  // gate site 4
        0x219380L,  // RSFontMgr::ReadResourceFile
        0x21A450L,  // RSFontMgr::Initialize
        0x21A5B0L,  // RSFontMgr::Create
        0x219A70L,  // DrawString v1
        0x21AB50L,  // RSFont::ReadResource
        0x21AC00L,  // StringWidth
        0x21AD10L,  // CharWidth
        0x21CC10L,  // DoWordWrap
        0x51B140L,  // FindSurface
        0x51B660L,  // UITextureMgr::LoadingTexturePak
        0x3A17D0L,  // RSFontMgr::GetFont
    };

    private static final String[] WHY = {
        "gate1", "cave/grid", "gate2", "gate3", "gate4",
        "ReadResourceFile", "Initialize", "Create", "DrawString",
        "RSFont::ReadResource", "StringWidth", "CharWidth", "DoWordWrap",
        "FindSurface", "LoadingTexturePak", "GetFont",
    };

    @Override
    public void run() throws Exception {
        println("program   = " + currentProgram.getName());
        println("language  = " + currentProgram.getLanguageID());
        println("imagebase = " + currentProgram.getImageBase());

        List<long[]> sites = new ArrayList<>();
        for (int i = 0; i < DEFAULT_VAS.length; i++) {
            sites.add(new long[] { DEFAULT_VAS[i], i });
        }
        String[] extra = getScriptArgs();
        if (extra != null) {
            for (String s : extra) {
                try {
                    long v = Long.parseLong(s.replace("0x", "").replace("0X", ""), 16);
                    sites.add(new long[] { v, -1 });
                } catch (Exception e) {
                    println("(bad VA arg ignored: " + s + ")");
                }
            }
        }

        DecompInterface dec = new DecompInterface();
        dec.toggleCCode(true);
        dec.toggleSyntaxTree(false);
        dec.openProgram(currentProgram);
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();

        for (long[] s : sites) {
            long va = s[0];
            int idx = (int) s[1];
            Address addr = toAddr(va);
            println("");
            println("==================================================================");
            println(String.format("VA 0x%08X   %s", va,
                    (idx >= 0 && idx < WHY.length) ? WHY[idx] : "(extra)"));

            Function f = getFunctionContaining(addr);
            if (f == null) {
                println("  (not inside a defined function)");
                // try to make one
                Function nf = createFunction(addr, null);
                if (nf != null) {
                    println("  -> created function " + nf.getName());
                    f = nf;
                }
            }
            if (f != null) {
                println(String.format("  func %s entry=0x%08X size=%d",
                        f.getName(), f.getEntryPoint().getOffset(),
                        f.getBody().getNumAddresses()));
                for (Function cf : f.getCallingFunctions(mon)) {
                    println(String.format("     <= caller 0x%08X %s",
                            cf.getEntryPoint().getOffset(), cf.getName()));
                }
                ReferenceIterator rit = currentProgram.getReferenceManager()
                        .getReferencesTo(f.getEntryPoint());
                while (rit.hasNext()) {
                    Reference r = rit.next();
                    Function rf = getFunctionContaining(r.getFromAddress());
                    println(String.format("     <= ref   0x%08X %s",
                            r.getFromAddress().getOffset(),
                            (rf == null ? "<no-func>" : rf.getName())));
                }
                DecompileResults res = dec.decompileFunction(f, 120, mon);
                if (res != null && res.decompileCompleted()) {
                    println("  ---- C ----");
                    println(res.getDecompiledFunction().getC());
                } else {
                    println("  (decompile failed: " + (res == null ? "null" : res.getErrorMessage()) + ")");
                }
            }

            println("  ---- instructions (VA-0x40 .. VA+0x90) ----");
            Address a = addr.subtract(0x40);
            for (int k = 0; k < 0x40 / 4 + 0x90 / 4 + 1; k++) {
                Instruction ins = currentProgram.getListing().getInstructionAt(a);
                println(String.format("    %s  %s", a,
                        (ins == null ? "(no instr)" : ins.toString())));
                a = a.add(4);
            }
        }

        dec.dispose();
        println("");
        println("### DONE FontDecomp ###");
    }
}
