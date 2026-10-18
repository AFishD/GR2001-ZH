// Crash2Bytes.java - read Ghidra's ACTUAL loaded bytes at the crash PCs, disassemble
// the undefined region 0x25E84C..0x25E8B0 by force, and dump .text-window hex.
//@category GRLoc

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.Memory;

public class Crash2Bytes extends GhidraScript {

    private byte[] bytesAt(long va, int n) throws Exception {
        Address a = toAddr(va);
        byte[] buf = new byte[n];
        currentProgram.getMemory().getBytes(a, buf);
        return buf;
    }

    private String hex(byte[] b) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < b.length; i++) {
            sb.append(String.format("%02x ", b[i]));
            if ((i % 8) == 7) sb.append(" ");
        }
        return sb.toString();
    }

    @Override
    public void run() throws Exception {
        println("### CRASH2 BYTES ###");
        Memory mem = currentProgram.getMemory();
        println("memory blocks:");
        for (var b : mem.getBlocks()) {
            println(String.format("   %-12s %s - %s size=0x%X", b.getName(), b.getStart(), b.getEnd(), b.getSize()));
        }

        // 1. raw bytes Ghidra has for the key PCs
        long[] keys = {0x0025E84CL, 0x0025E85CL, 0x0025E860L, 0x0025E864L, 0x0025E868L,
                       0x0025E86CL, 0x0025E870L, 0x0025E874L, 0x0025E878L,
                       0x00101D10L, 0x00101DD8L, 0x00101E6CL};
        println("");
        println("=== Ghidra loaded bytes ===");
        for (long va : keys) {
            byte[] b = bytesAt(va, 24);
            // little-endian words
            StringBuilder w = new StringBuilder();
            for (int k = 0; k + 3 < b.length; k += 4) {
                long v = (b[k] & 0xFFL) | ((b[k+1] & 0xFFL) << 8) | ((b[k+2] & 0xFFL) << 16) | ((b[k+3] & 0xFFL) << 24);
                w.append(String.format("%08x ", v));
            }
            println(String.format("  0x%08X  %s | words: %s", va, hex(b), w.toString()));
        }

        // 2. force-disassemble the whole 0x25E700..0x25E900 window by *decoding* manually
        //    (Ghidra's listing has nothing there, so we decode from bytes ourselves)
        println("");
        println("=== manual MIPS decode of 0x25E840..0x25E8A0 (non-destructive) ===");
        // We cannot easily call the decoder, so instead: clear+disassemble is destructive.
        // Use the instruction prototype via DisassemblerContext? Simpler: print words + our own decode.
        for (long va = 0x0025E840L; va < 0x0025E8A4L; va += 4) {
            byte[] b = bytesAt(va, 4);
            long insn = (b[0] & 0xFFL) | ((b[1] & 0xFFL) << 8) | ((b[2] & 0xFFL) << 16) | ((b[3] & 0xFFL) << 24);
            int op = (int) ((insn >>> 26) & 0x3F);
            int rs = (int) ((insn >>> 21) & 0x1F);
            int rt = (int) ((insn >>> 16) & 0x1F);
            int rd = (int) ((insn >>> 11) & 0x1F);
            int sa = (int) ((insn >>> 6) & 0x1F);
            int fn = (int) (insn & 0x3F);
            int imm = (short) (insn & 0xFFFF);
            String d;
            if (op == 0x23) d = String.format("lw $%d, %d($%d)", rt, imm, rs);
            else if (op == 0x2B) d = String.format("sw $%d, %d($%d)", rt, imm, rs);
            else if (op == 0x0F) d = String.format("lui $%d, 0x%04X", rt, imm & 0xFFFF);
            else if (op == 0x09) d = String.format("addiu $%d, $%d, %d", rt, rs, imm);
            else if (op == 0x0C) d = String.format("andi $%d, $%d, 0x%04X", rt, rs, imm & 0xFFFF);
            else if (op == 0x04) d = String.format("beq $%d, $%d, %+d (->0x%08X)", rs, rt, imm * 4 + 4, va + 4 + imm * 4);
            else if (op == 0x05) d = String.format("bne $%d, $%d, %+d (->0x%08X)", rs, rt, imm * 4 + 4, va + 4 + imm * 4);
            else if (op == 0x02) d = String.format("j 0x%08X", ((insn & 0x3FFFFFF) << 2) | (va & 0xF0000000L));
            else if (op == 0x03) d = String.format("jal 0x%08X", ((insn & 0x3FFFFFF) << 2) | (va & 0xF0000000L));
            else if (op == 0) {
                switch (fn) {
                    case 0x08: d = String.format("jr $%d", rs); break;
                    case 0x09: d = String.format("jalr $%d", rs); break;
                    case 0x21: d = String.format("addu $%d, $%d, $%d", rd, rs, rt); break;
                    case 0x27: d = String.format("nor $%d, $%d, $%d", rd, rs, rt); break;
                    case 0x25: d = String.format("or $%d, $%d, $%d", rd, rs, rt); break;
                    case 0x2B: d = String.format("sltu $%d, $%d, $%d", rd, rs, rt); break;
                    case 0x00: d = String.format("sll $%d, $%d, %d", rd, rt, sa); break;
                    case 0x02: d = String.format("srl $%d, $%d, %d", rd, rt, sa); break;
                    case 0x03: d = String.format("sra $%d, $%d, %d", rd, rt, sa); break;
                    case 0x18: d = String.format("mult $%d, $%d", rs, rt); break;
                    case 0x1A: d = String.format("div $%d, $%d", rs, rt); break;
                    case 0x10: d = String.format("mfhi $%d", rd); break;
                    case 0x12: d = String.format("mflo $%d", rd); break;
                    default:   d = String.format("special fn=0x%02X", fn); break;
                }
            }
            else if (op == 0x1F) d = String.format("special2?(0x1F) 0x%08X", insn);
            else if (op == 0x01) d = String.format("regimm rt=%d %+d", rt, imm * 4 + 4);
            else d = String.format("op=0x%02X 0x%08X", op, insn);
            println(String.format("  %08x  %08x  %s", va, insn, d));
        }

        // 3. does Ghidra think 0x25E86C is initialized?
        println("");
        Address a = toAddr(0x0025E86CL);
        println("  isInitialized(0x25E86C) = " + mem.getBlock(a).isInitialized());
        println("  block(0x25E86C) = " + mem.getBlock(a).getName());
        CodeUnit cu = currentProgram.getListing().getCodeUnitContaining(a);
        println("  codeUnit at 0x25E86C = " + (cu == null ? "null" : cu.toString()));
        Instruction ins = currentProgram.getListing().getInstructionAt(a);
        println("  instruction at 0x25E86C = " + (ins == null ? "null" : ins.toString()));

        println("");
        println("### CRASH2 BYTES DONE ###");
    }
}
