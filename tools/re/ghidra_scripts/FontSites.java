// FontSites.java - Ghidra headless post-script (Java; Ghidra compiles it on the fly)
// Purpose (round73 / font-decompile):
//   (1) print program info incl. LANGUAGE (to document the MMI/EmotionEngine gap)
//   (2) list symbols matching font/glyph/char/text/atlas/kanji/sjis/unicode/wrap
//   (3) scan every instruction in the main EXEC block for target immediates
//       (0xB1 0xA1 0x5E 0x3E 0x10 0x400 0x200 0x6C8 0x5E0 0xE0 0x410 ...)
//   (4) locate the literal strings "font.res" / "new_font_revised" /
//       "pda_counterparts" and print their references
// Run:  gh.bat <proj> GRLoc -process SLUS_206.13.elf -postScript FontSites.java -scriptPath <dir> -noanalysis
//@category GRLoc

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.scalar.Scalar;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;

public class FontSites extends GhidraScript {

    // immediates we care about, with a human label
    private static final long[][] TARGETS = {
        { 0x0B1L, 0 }, { 0x0A1L, 0 }, { 0x05EL, 0 }, { 0x03EL, 0 }, { 0x010L, 0 },
        { 0x400L, 0 }, { 0x200L, 0 }, { 0x6C8L, 0 }, { 0x5E0L, 0 },
        { 0x0E0L, 0 }, { 0x410L, 0 }, { 0x40010L, 0 }, { 0x0DFL, 0 },
        { 0x0FFL, 0 }, { 0x0FEL, 0 }, { 0x11L, 0 }, { 0x60L, 0 }, { 0x40L, 0 },
    };

    private static final String[] STRS = {
        "font.res", "new_font_revised", "pda_counterparts", "COMMON.PAK", "common.pak",
        ".rsb", "FONT.RES"
    };

    @Override
    public void run() throws Exception {
        println("############################################################");
        println("program      = " + currentProgram.getName());
        println("image base   = " + currentProgram.getImageBase());
        println("language     = " + currentProgram.getLanguageID());
        println("compiler     = " + currentProgram.getCompilerSpec().getCompilerSpecID());
        println("functions    = " + currentProgram.getFunctionManager().getFunctionCount());
        println("############################################################");

        println("");
        println("=== memory blocks ===");
        for (MemoryBlock b : currentProgram.getMemory().getBlocks()) {
            println(String.format("  %-24s %s .. %s  size=0x%X  R=%b W=%b X=%b init=%b",
                    b.getName(), b.getStart(), b.getEnd(), b.getSize(),
                    b.isRead(), b.isWrite(), b.isExecute(), b.isInitialized()));
        }

        // ---------- (2) symbols ----------
        println("");
        println("=== symbols matching font/glyph/char/text/atlas/kanji/sjis/unicode/wrap ===");
        Pattern pat = Pattern.compile(
                "(?i)(font|glyph|atlas|kanji|sjis|zenkaku|hankaku|charwidth|stringwidth|wordwrap)");
        SymbolIterator sit = currentProgram.getSymbolTable().getAllSymbols(true);
        int ns = 0;
        List<String> hits = new ArrayList<>();
        while (sit.hasNext() && ns < 20000) {
            Symbol s = sit.next();
            ns++;
            String nm = s.getName();
            if (pat.matcher(nm).find()) {
                hits.add(String.format("  0x%08X  %s  [%s]",
                        s.getAddress().getOffset(), nm, s.getSymbolType()));
            }
        }
        println("  (scanned " + ns + " symbols, " + hits.size() + " hits)");
        int cap = Math.min(hits.size(), 400);
        for (int i = 0; i < cap; i++) {
            println(hits.get(i));
        }
        if (hits.size() > cap) {
            println("  ... (" + (hits.size() - cap) + " more suppressed)");
        }

        // ---------- (3) immediate scan over the EXEC blocks ----------
        println("");
        println("=== immediate scan (main segment 0x100000..0x600000) ===");
        AddressSet scanSet = new AddressSet();
        for (MemoryBlock b : currentProgram.getMemory().getBlocks()) {
            long lo = b.getStart().getOffset();
            if (!b.isInitialized()) {
                continue;
            }
            if (lo >= 0x100000L && lo < 0x600000L) {
                scanSet.addRange(b.getStart(), b.getEnd());
            }
        }
        println("  scan set size = " + scanSet.getNumAddresses());

        List<String> out = new ArrayList<>();
        InstructionIterator iit = currentProgram.getListing().getInstructions(scanSet, true);
        long nins = 0;
        while (iit.hasNext()) {
            Instruction ins = iit.next();
            nins++;
            String mn = ins.getMnemonicString().toLowerCase();
            // only ALU-with-immediate style ops are interesting
            boolean interesting = mn.startsWith("slti") || mn.startsWith("addiu")
                    || mn.startsWith("ori") || mn.startsWith("andi") || mn.startsWith("li")
                    || mn.startsWith("slt") || mn.startsWith("subu") || mn.startsWith("lui")
                    || mn.startsWith("daddiu");
            if (!interesting) {
                continue;
            }
            int nops = ins.getNumOperands();
            for (int oi = 0; oi < nops; oi++) {
                Scalar sc = null;
                try {
                    sc = ins.getScalar(oi);
                } catch (Exception e) {
                    sc = null;
                }
                if (sc == null) {
                    continue;
                }
                long v = sc.getUnsignedValue();
                for (long[] t : TARGETS) {
                    if (v == t[0]) {
                        Function f = getFunctionContaining(ins.getAddress());
                        out.add(String.format("  0x%08X  %-46s  %-28s  imm=0x%X(%d)",
                                ins.getAddress().getOffset(), ins.toString(),
                                (f == null ? "<no-func>" : f.getName()), v, v));
                    }
                }
            }
        }
        println("  (scanned " + nins + " instructions, " + out.size() + " immediate hits)");
        int cap2 = Math.min(out.size(), 2500);
        for (int i = 0; i < cap2; i++) {
            println(out.get(i));
        }
        if (out.size() > cap2) {
            println("  ... (" + (out.size() - cap2) + " more suppressed)");
        }

        // ---------- (4) string refs ----------
        println("");
        println("=== literal strings + references ===");
        for (String s : STRS) {
            byte[] pat2 = s.getBytes("US-ASCII");
            println("--- \"" + s + "\" ---");
            Set<Long> found = new LinkedHashSet<>();
            Address searchFrom = null;
            for (MemoryBlock b : currentProgram.getMemory().getBlocks()) {
                if (!b.isInitialized() || !b.isRead()) {
                    continue;
                }
                searchFrom = b.getStart();
                while (searchFrom != null) {
                    Address hit;
                    try {
                        hit = currentProgram.getMemory().findBytes(searchFrom, b.getEnd(),
                                pat2, null, true, monitor);
                    } catch (Exception e) {
                        hit = null;
                    }
                    if (hit == null) {
                        break;
                    }
                    if (found.add(hit.getOffset())) {
                        println(String.format("  str @ 0x%08X", hit.getOffset()));
                        ghidra.program.model.symbol.ReferenceIterator rit =
                                currentProgram.getReferenceManager().getReferencesTo(hit);
                        int shown = 0;
                        while (rit.hasNext()) {
                            Reference r = rit.next();
                            Function f = getFunctionContaining(r.getFromAddress());
                            println(String.format("      <= ref from 0x%08X  %s",
                                    r.getFromAddress().getOffset(),
                                    (f == null ? "<no-func>" : f.getName())));
                            shown++;
                            if (shown > 24) {
                                println("      ... more refs suppressed");
                                break;
                            }
                        }
                        if (shown == 0) {
                            println("      (no references found by Ghidra)");
                        }
                    }
                    Address next = hit.add(1);
                    if (next.compareTo(b.getEnd()) > 0) {
                        break;
                    }
                    searchFrom = next;
                }
            }
        }

        println("");
        println("### DONE FontSites ###");
    }
}
