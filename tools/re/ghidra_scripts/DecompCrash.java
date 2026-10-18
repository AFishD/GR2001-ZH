// DecompCrash.java - Ghidra headless post-script (Java; Ghidra compiles it on the fly)
// Purpose: decompile the recLUT crash chain in SLUS_206.13.elf and print function
//          names, callers, decompiled C, and the surrounding instructions.
// Run:  gh.bat <proj> GRLoc -process SLUS_206.13.elf -postScript DecompCrash.java -scriptPath <dir>
//@category GRLoc

import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.util.task.ConsoleTaskMonitor;

public class DecompCrash extends GhidraScript {

    private static final long[] VAS = {
        0x00193E90L, // 访问器: 查表查不到时如实返回 0
        0x00193EA4L, // lw $2,192($4) / sll / addu / lw $2,0($2)
        0x00193EBCL, // beq $0,$0,00193ECC (命中: 返回 0)
        0x00193ECCL, // jr $31
        0x003F5FD0L, // 虚函数入口 (开火后 5 帧进入)
        0x003F602CL, // beq $2,$0,003F6038 (v0==0 成立)
        0x003F6038L, // ★ lw $25,0($2) -- 不判空就解引用
        0x003F6044L, // lw $25,792($25) -- 虚表槽 0x318
        0x003F6048L, // ★ jalr $31,$25 -- 跳到 0
        0x0012BD00L, // 读垃圾指针 0xdb770d05 / 0x74d7432f
        0x0012BD2CL, // 读垃圾指针 0x02020202 / 0xc
        0x00101DE4L, // 从 0x10b2bf00 load
        0x00101E6CL, // store 到 0x10b2bef8
        0x00102220L, // 反复 store 到 0x10b2bef8 (主循环)
        0x001024E8L, // 同一循环的另一入口
    };

    private static final String[] WHY = {
        "访问器: 查表查不到时如实返回 0",
        "lw $2,192($4) / sll / addu / lw $2,0($2)",
        "beq $0,$0,00193ECC (命中: 返回 0)",
        "jr $31",
        "虚函数入口 (开火后 5 帧进入)",
        "beq $2,$0,003F6038 (v0==0 成立)",
        "★ lw $25,0($2) -- 不判空就解引用",
        "lw $25,792($25) -- 虚表槽 0x318",
        "★ jalr $31,$25 -- 跳到 0",
        "读垃圾指针 0xdb770d05 / 0x74d7432f",
        "读垃圾指针 0x02020202 / 0xc",
        "从 0x10b2bf00 load",
        "store 到 0x10b2bef8",
        "反复 store 到 0x10b2bef8 (主循环)",
        "同一循环的另一入口",
    };

    @Override
    public void run() throws Exception {
        println("############################################################");
        println("program      = " + currentProgram.getName());
        println("image base   = " + currentProgram.getImageBase());
        println("language     = " + currentProgram.getLanguageID());
        println("functions    = " + currentProgram.getFunctionManager().getFunctionCount());
        println("############################################################");

        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();

        // 主段函数总览(前 80)
        println("");
        println("=== 主段函数总览 (0x100000..0x600000, 前 80) ===");
        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        int n = 0;
        while (it.hasNext() && n < 80) {
            Function f = it.next();
            long a = f.getEntryPoint().getOffset();
            if (a >= 0x100000L && a < 0x600000L) {
                println(String.format("  0x%08X  %-32s size=%d", a, f.getName(),
                        f.getBody().getNumAddresses()));
                n++;
            }
        }

        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);

        for (int i = 0; i < VAS.length; i++) {
            long va = VAS[i];
            Address addr = toAddr(va);
            println("");
            println("============================================================");
            println(String.format("VA 0x%08X   (%s)", va, WHY[i]));

            Function f = getFunctionContaining(addr);
            if (f == null) {
                println("  (不在任何已知函数内)");
            } else {
                println(String.format("  函数 %s  入口 0x%08X  大小 %d",
                        f.getName(), f.getEntryPoint().getOffset(),
                        f.getBody().getNumAddresses()));
                for (Function cf : f.getCallingFunctions(mon)) {
                    println(String.format("      <= 被 0x%08X %s 调用",
                            cf.getEntryPoint().getOffset(), cf.getName()));
                }
                DecompileResults res = dec.decompileFunction(f, 90, mon);
                if (res != null && res.decompileCompleted()) {
                    println("  ---- 反编译 (" + res.getDecompiledFunction().getSignature() + ") ----");
                    println(res.getDecompiledFunction().getC());
                } else {
                    println("  (反编译未完成: " + (res == null ? "null" : res.getErrorMessage()) + ")");
                }
            }

            println("  ---- 附近 22 条指令 ----");
            Address a = addr;
            for (int k = 0; k < 22; k++) {
                Instruction ins = currentProgram.getListing().getInstructionAt(a);
                println("    " + a + "  " + (ins == null ? "(无语义)" : ins.toString()));
                a = a.add(4);
            }
        }
        dec.dispose();
        println("");
        println("### DONE ###");
    }
}
