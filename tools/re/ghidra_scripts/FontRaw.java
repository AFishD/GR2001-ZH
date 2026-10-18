// FontRaw.java - Ghidra headless post-script (round73 font-decompile)
//
// Why this exists: Ghidra (default MIPS language, no EmotionEngine/MMI plugin) does NOT
// disassemble every code cave, so iterating the listing MISSES sites (e.g. 0x417160 /
// 0x5656A4 are never turned into instructions). This script therefore
//   (1) scans RAW MEMORY for instruction encodings with a bitmask (disassembly-independent),
//   (2) decodes ranges with its OWN tiny MIPS decoder and prints them.
//
// Run: gh.bat <proj> GRLoc -process SLUS_206.13.elf -postScript FontRaw.java -scriptPath <dir> -noanalysis
//@category GRLoc

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;

public class FontRaw extends GhidraScript {

    // ---- instruction-encoding patterns we want to find anywhere in memory ----
    private static final long[] P_MASK = {
        0xFC00FFFFL, 0xFC00FFFFL, 0xFC00FFFFL, 0xFC00FFFFL, 0xFC00FFFFL,
        0xFC00FFFFL, 0xFC00FFFFL,
        0xFFE0FFFFL, 0xFFE0FFFFL, 0xFFE0FFFFL, 0xFFE0FFFFL, 0xFFE0FFFFL,
        0xFFE0FFFFL, 0xFFE0FFFFL, 0xFFE0FFFFL, 0xFFE0FFFFL, 0xFFE0FFFFL,
        0xFFE0FFFFL,
        0xFFFF0000L, 0xFFFF0000L,
    };
    private static final long[] P_VAL = {
        0x2C0000B1L, 0x2C0000A1L, 0x2C0000FFL, 0x2C0000FEL, 0x2C000010L,
        0x280000B1L, 0x280000A1L,
        0x2400005EL, 0x2400003EL, 0x24000010L, 0x24000400L, 0x24000200L,
        0x24000002L, 0x24000003L, 0x2400000CL, 0x240000E0L,
        0x3400005EL, 0x3400003EL,
        0x3C000400L, 0x3C000200L,
    };
    private static final String[] P_LABEL = {
        "sltiu rt,rs,0xB1", "sltiu rt,rs,0xA1", "sltiu rt,rs,0xFF",
        "sltiu rt,rs,0xFE", "sltiu rt,rs,0x10",
        "slti  rt,rs,0xB1", "slti  rt,rs,0xA1",
        "addiu rt,r0,94   (li 94)", "addiu rt,r0,62   (li 62)",
        "addiu rt,r0,16   (li 16)", "addiu rt,r0,1024 (li 1024)",
        "addiu rt,r0,512  (li 512)", "addiu rt,r0,2    (li 2)",
        "addiu rt,r0,3    (li 3)", "addiu rt,r0,12   (li 12)",
        "addiu rt,r0,224  (li 224)",
        "ori   rt,r0,94", "ori   rt,r0,62",
        "lui   rt,0x0400  (0x400<<16)", "lui   rt,0x0200  (0x200<<16)",
    };

    // ---- ranges to linearly decode with our own decoder ----
    private static final long[][] RANGES = {
        { 0x416E00L, 0x417020L, 0 },   // text decoder / lead-trail test region
        { 0x417040L, 0x417200L, 0 },   // the grid-formula cave
        { 0x417480L, 0x4175A0L, 0 },   // gate3 region
        { 0x565620L, 0x565720L, 0 },   // gate4 region
    };

    private static final String[] REG = {
        "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
        "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
        "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
        "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra",
    };

    @Override
    public void run() throws Exception {
        Memory mem = currentProgram.getMemory();
        println("program  = " + currentProgram.getName());
        println("language = " + currentProgram.getLanguageID());

        // ---------- (1) raw pattern scan ----------
        println("");
        println("=== RAW pattern scan (all initialised blocks) ===");
        Map<String, List<String>> byLabel = new LinkedHashMap<>();
        for (MemoryBlock b : mem.getBlocks()) {
            if (!b.isInitialized()) {
                continue;
            }
            long lo = b.getStart().getOffset();
            long hi = b.getEnd().getOffset();
            for (long a = lo; a + 4 <= hi; a += 4) {
                int w;
                try {
                    w = mem.getInt(toAddr(a));
                } catch (Exception e) {
                    continue;
                }
                long uw = w & 0xFFFFFFFFL;
                for (int pi = 0; pi < P_VAL.length; pi++) {
                    if ((uw & P_MASK[pi]) == P_VAL[pi]) {
                        byLabel.computeIfAbsent(P_LABEL[pi], k -> new ArrayList<>())
                                .add(String.format("0x%08X", a));
                    }
                }
            }
        }
        for (Map.Entry<String, List<String>> e : byLabel.entrySet()) {
            println(String.format("%-28s x%d : %s", e.getKey(), e.getValue().size(),
                    String.join(" ", e.getValue())));
        }

        // ---------- (2) own decoder over the ranges ----------
        for (long[] r : RANGES) {
            println("");
            println("=== own-decoder range 0x" + Long.toHexString(r[0])
                    + " .. 0x" + Long.toHexString(r[1]) + " ===");
            for (long a = r[0]; a < r[1]; a += 4) {
                int w;
                try {
                    w = mem.getInt(toAddr(a));
                } catch (Exception ex) {
                    println(String.format("  0x%08X  <unmapped>", a));
                    continue;
                }
                println(String.format("  0x%08X  %08X  %s", a, w & 0xFFFFFFFFL, decode(w, a)));
            }
        }

        println("");
        println("### DONE FontRaw ###");
    }

    /** tiny MIPS III/EE decoder - returns a readable disassembly line */
    private String decode(int w, long pc) {
        long uw = w & 0xFFFFFFFFL;
        int op = (int) ((uw >>> 26) & 0x3F);
        int rs = (int) ((uw >>> 21) & 0x1F);
        int rt = (int) ((uw >>> 16) & 0x1F);
        int rd = (int) ((uw >>> 11) & 0x1F);
        int sa = (int) ((uw >>> 6) & 0x1F);
        int fn = (int) (uw & 0x3F);
        int imm = (short) (uw & 0xFFFF);
        long uimm = uw & 0xFFFF;
        long target = (uw & 0x03FFFFFFL) << 2;

        switch (op) {
            case 0x00:
                switch (fn) {
                    case 0x00: return "sll  " + REG[rd] + "," + REG[rt] + "," + sa;
                    case 0x02: return "srl  " + REG[rd] + "," + REG[rt] + "," + sa;
                    case 0x03: return "sra  " + REG[rd] + "," + REG[rt] + "," + sa;
                    case 0x04: return "sllv " + REG[rd] + "," + REG[rt] + "," + REG[rs];
                    case 0x06: return "srlv " + REG[rd] + "," + REG[rt] + "," + REG[rs];
                    case 0x07: return "srav " + REG[rd] + "," + REG[rt] + "," + REG[rs];
                    case 0x08: return "jr   " + REG[rs];
                    case 0x09: return "jalr " + REG[rd] + "," + REG[rs];
                    case 0x0A: return "movz " + REG[rd] + "," + REG[rs] + "," + REG[rt];
                    case 0x0B: return "movn " + REG[rd] + "," + REG[rs] + "," + REG[rt];
                    case 0x0C: return "syscall";
                    case 0x0D: return "break";
                    case 0x0F: return "sync";
                    case 0x10: return "mfhi " + REG[rd];
                    case 0x11: return "mthi " + REG[rs];
                    case 0x12: return "mflo " + REG[rd];
                    case 0x13: return "mtlo " + REG[rs];
                    case 0x18: return "mult " + REG[rs] + "," + REG[rt];
                    case 0x19: return "multu " + REG[rs] + "," + REG[rt];
                    case 0x1A: return "div  " + REG[rs] + "," + REG[rt];
                    case 0x1B: return "divu " + REG[rs] + "," + REG[rt];
                    case 0x20: return "add  " + REG[rd] + "," + REG[rs] + "," + REG[rt];
                    case 0x21: return "addu " + REG[rd] + "," + REG[rs] + "," + REG[rt];
                    case 0x22: return "sub  " + REG[rd] + "," + REG[rs] + "," + REG[rt];
                    case 0x23: return "subu " + REG[rd] + "," + REG[rs] + "," + REG[rt];
                    case 0x24: return "and  " + REG[rd] + "," + REG[rs] + "," + REG[rt];
                    case 0x25: return "or   " + REG[rd] + "," + REG[rs] + "," + REG[rt];
                    case 0x26: return "xor  " + REG[rd] + "," + REG[rs] + "," + REG[rt];
                    case 0x27: return "nor  " + REG[rd] + "," + REG[rs] + "," + REG[rt];
                    case 0x2A: return "slt  " + REG[rd] + "," + REG[rs] + "," + REG[rt];
                    case 0x2B: return "sltu " + REG[rd] + "," + REG[rs] + "," + REG[rt];
                    case 0x3C: return "dsll32 " + REG[rd] + "," + REG[rt] + "," + sa;
                    default:   return String.format("special fn=0x%02X", fn);
                }
            case 0x01:
                switch (rt) {
                    case 0x00: return String.format("bltz %s, 0x%08X", REG[rs], pc + 4 + (imm << 2));
                    case 0x01: return String.format("bgez %s, 0x%08X", REG[rs], pc + 4 + (imm << 2));
                    case 0x10: return String.format("bltzal %s, 0x%08X", REG[rs], pc + 4 + (imm << 2));
                    case 0x11: return String.format("bgezal %s, 0x%08X", REG[rs], pc + 4 + (imm << 2));
                    default:   return String.format("regimm rt=0x%02X", rt);
                }
            case 0x02: return String.format("j    0x%08X", (pc & 0xF0000000L) | target);
            case 0x03: return String.format("jal  0x%08X", (pc & 0xF0000000L) | target);
            case 0x04: return String.format("beq  %s,%s, 0x%08X", REG[rs], REG[rt], pc + 4 + (imm << 2));
            case 0x05: return String.format("bne  %s,%s, 0x%08X", REG[rs], REG[rt], pc + 4 + (imm << 2));
            case 0x06: return String.format("blez %s, 0x%08X", REG[rs], pc + 4 + (imm << 2));
            case 0x07: return String.format("bgtz %s, 0x%08X", REG[rs], pc + 4 + (imm << 2));
            case 0x08: return String.format("addi %s,%s,%d", REG[rt], REG[rs], imm);
            case 0x09: return String.format("addiu %s,%s,%d (0x%X)", REG[rt], REG[rs], imm, uimm);
            case 0x0A: return String.format("slti %s,%s,%d", REG[rt], REG[rs], imm);
            case 0x0B: return String.format("sltiu %s,%s,%d (0x%X)", REG[rt], REG[rs], imm, uimm);
            case 0x0C: return String.format("andi %s,%s,0x%X", REG[rt], REG[rs], uimm);
            case 0x0D: return String.format("ori  %s,%s,0x%X", REG[rt], REG[rs], uimm);
            case 0x0E: return String.format("xori %s,%s,0x%X", REG[rt], REG[rs], uimm);
            case 0x0F: return String.format("lui  %s,0x%X", REG[rt], uimm);
            case 0x10:
                if (rs == 0x00) return "mfc0 " + REG[rt] + "," + rd;
                if (rs == 0x04) return "mtc0 " + REG[rt] + "," + rd;
                return String.format("cop0 rs=%d", rs);
            case 0x11: return String.format("cop1 rs=%d fmt=%d", rs, rt);
            case 0x12: return String.format("cop2 rs=%d (EE VU0) imm=%d", rs, imm);
            case 0x14: return String.format("beql %s,%s, 0x%08X", REG[rs], REG[rt], pc + 4 + (imm << 2));
            case 0x15: return String.format("bnel %s,%s, 0x%08X", REG[rs], REG[rt], pc + 4 + (imm << 2));
            case 0x16: return String.format("blezl %s, 0x%08X", REG[rs], pc + 4 + (imm << 2));
            case 0x17: return String.format("bgtzl %s, 0x%08X", REG[rs], pc + 4 + (imm << 2));
            case 0x1C: {
                // SPECIAL2 (MMI on EE)
                String n;
                switch (fn) {
                    case 0x00: n = "madd"; break;   case 0x01: n = "maddu"; break;
                    case 0x02: n = "mul"; break;    case 0x04: n = "msub"; break;
                    case 0x05: n = "msubu"; break;  case 0x20: n = "clz"; break;
                    case 0x21: n = "clo"; break;    case 0x24: n = "mfsa"; break;
                    case 0x28: n = "mtsa"; break;
                    default: n = "mmi_special2_fn" + Integer.toHexString(fn);
                }
                if (fn == 0x28 || fn == 0x24) {
                    return n + " " + REG[rd];
                }
                return n + " " + REG[rd] + "," + REG[rs] + "," + REG[rt]
                        + (sa != 0 ? (",sa=" + sa) : "");
            }
            case 0x1F: {
                // SPECIAL3 = EE MMI0/1/2/3 ; decode the common ones
                int sub = rd;   // really the "mmi op" field for MMI1/3
                String n;
                switch (sa) {
                    case 0x00: n = "ext"; break;
                    case 0x04: n = "ins"; break;
                    case 0x20: n = "bshfl"; break;
                    case 0x3B: n = "rdhwr"; break;
                    default:   n = "mmi(sa=" + sa + ",fn=" + fn + ")";
                }
                return n + " " + REG[rt] + "," + REG[rs] + "," + REG[rd]
                        + String.format(" [w=%08X]", uw);
            }
            case 0x20: return String.format("lb  %s,%d(%s)", REG[rt], imm, REG[rs]);
            case 0x21: return String.format("lh  %s,%d(%s)", REG[rt], imm, REG[rs]);
            case 0x23: return String.format("lw  %s,%d(%s)", REG[rt], imm, REG[rs]);
            case 0x24: return String.format("lbu %s,%d(%s)", REG[rt], imm, REG[rs]);
            case 0x25: return String.format("lhu %s,%d(%s)", REG[rt], imm, REG[rs]);
            case 0x27: return String.format("lwu %s,%d(%s)", REG[rt], imm, REG[rs]);
            case 0x28: return String.format("sb  %s,%d(%s)", REG[rt], imm, REG[rs]);
            case 0x29: return String.format("sh  %s,%d(%s)", REG[rt], imm, REG[rs]);
            case 0x2B: return String.format("sw  %s,%d(%s)", REG[rt], imm, REG[rs]);
            case 0x2E: return String.format("sq  %s,%d(%s)", REG[rt], imm, REG[rs]);
            case 0x31: return String.format("lwc1 %s,%d(%s)", REG[rt], imm, REG[rs]);
            case 0x39: return String.format("swc1 %s,%d(%s)", REG[rt], imm, REG[rs]);
            default:   return String.format("op=0x%02X raw=%08X", op, uw);
        }
    }
}
