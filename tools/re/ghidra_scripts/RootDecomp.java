// RootDecomp.java - Ghidra headless post-script: decompile the texture/image-load path.
// Round85 root-cause. READ-ONLY on the project.
// Run: work\tools\gh.bat <projdir> GRLoc -process SLUS_206.13.elf -noanalysis
//        -postScript RootDecomp.java -scriptPath work\tools\ghidra_scripts
//@category GRLoc

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.util.task.ConsoleTaskMonitor;

public class RootDecomp extends GhidraScript {

    private static final long[] VAS = {
        0x0051C810L, // 记录解析 + LoadPS2Img 调用者
        0x0051D910L, // LoadPS2Img
        0x0051B660L, // LoadingTexturePak
        0x0051B900L, // LoadingTexturePak 记账 (+0x30)
        0x005181B8L, // SetTexturePkt 分块器
        0x00518828L, // SetTexturePkt TEX0 构造
        0x0051BF00L, // RefreshActive (+0x30 消费者)
        0x0051CF60L, // LoadRSBFile
        0x005176E0L, // SetTexturePkt 所在函数入口候选
    };

    @Override
    public void run() throws Exception {
        println("### program = " + currentProgram.getName());
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        java.util.HashSet<Long> done = new java.util.HashSet<Long>();

        for (long va : VAS) {
            Address addr = toAddr(va);
            Function f = getFunctionContaining(addr);
            println("");
            println("============================================================");
            if (f == null) {
                println(String.format("VA 0x%08X : (不在任何已识别函数内)", va));
                // 仍打印附近指令
                Address a = addr;
                for (int k = 0; k < 40; k++) {
                    Instruction ins = currentProgram.getListing().getInstructionAt(a);
                    println("    " + a + "  " + (ins == null ? "(无语义)" : ins.toString()));
                    a = a.add(4);
                }
                continue;
            }
            long ent = f.getEntryPoint().getOffset();
            println(String.format("VA 0x%08X -> %s @0x%08X size=%d", va, f.getName(), ent,
                    f.getBody().getNumAddresses()));
            for (Function cf : f.getCallingFunctions(mon)) {
                println(String.format("     <= caller 0x%08X %s", cf.getEntryPoint().getOffset(),
                        cf.getName()));
            }
            if (done.contains(ent)) {
                println("  (已反编译)");
                continue;
            }
            done.add(ent);
            DecompileResults res = dec.decompileFunction(f, 180, mon);
            if (res != null && res.decompileCompleted()) {
                println("  ---- C ----");
                println(res.getDecompiledFunction().getC());
            } else {
                println("  (反编译失败: " + (res == null ? "null" : res.getErrorMessage()) + ")");
                Address a = f.getEntryPoint();
                for (int k = 0; k < 300; k++) {
                    Instruction ins = currentProgram.getListing().getInstructionAt(a);
                    if (ins == null) break;
                    println("    " + a + "  " + ins.toString());
                    a = a.add(4);
                }
            }
        }
        dec.dispose();
        println("### DONE ###");
    }
}
