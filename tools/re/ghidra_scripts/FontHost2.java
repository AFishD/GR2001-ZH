// FontHost2.java - 反编译"字体资源加载 + 贴图绑定"的真实函数(用上一轮挖到的真实地址)
// 跑法: work\tools\gh.bat work\tools\ghidra_proj_ee GRLocEE -process SLUS_206.13.elf -postScript FontHost2.java -scriptPath work\tools\ghidra_scripts -noanalysis
//@category GRLoc

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.Symbol;
import ghidra.util.task.ConsoleTaskMonitor;

public class FontHost2 extends GhidraScript {

    // 上一轮从符号表挖到的真实地址
    private static final Object[][] FNS = {
        { "RSFontMgr::ReadResourceFile", 0x219380L },
        { "RSFontMgr::Create",           0x21A5B0L },
        { "RSFontMgr::Initialize",       0x21A450L },
        { "RSFontMgr::ReallocateSize",   0x21A3B0L },
        { "RSFontMgr::AddOneWord",       0x219F50L },
        { "RSFontMgr::Flush",            0x21A190L },
        { "RSFontMgr::Draw",             0x21A290L },
        { "UITextureMgr::LoadingTexturePak", 0x51B660L },
        { "LoadIndexedRSB",              0x51B230L },
        { "UITexture::LoadRSBFile",      0x51C810L },
    };

    @Override
    public void run() throws Exception {
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);

        for (Object[] row : FNS) {
            String want = (String) row[0];
            long va = (Long) row[1];
            Address addr = toAddr(va);
            Function f = getFunctionContaining(addr);
            if (f == null) f = getFunctionAt(addr);
            println("");
            println("################################################################");
            println("## " + want + "  (期望 0x" + Long.toHexString(va) + ")");
            println("################################################################");
            if (f == null) {
                println("  ✗ 该地址不在任何已知函数内 —— 打印该处指令与相邻函数:");
                Address a = addr.subtract(0x40);
                for (int k = 0; k < 40; k++) {
                    ghidra.program.model.listing.Instruction ins =
                        currentProgram.getListing().getInstructionAt(a);
                    println("     " + a + "  " + (ins == null ? "(无语义)" : ins.toString()));
                    a = a.add(4);
                }
                // 找最近的函数
                Function c = getFunctionAfter(addr);
                if (c != null) println("  其后最近的函数: " + c.getName() + " @0x"
                        + Long.toHexString(c.getEntryPoint().getOffset()));
                continue;
            }
            println(String.format("  实际函数 %s 入口 0x%08X 大小 %d 调用者 %d",
                    f.getName(), f.getEntryPoint().getOffset(),
                    f.getBody().getNumAddresses(), f.getCallingFunctions(mon).size()));
            for (Function cf : f.getCallingFunctions(mon)) {
                println(String.format("     <= 被 0x%08X %s 调用",
                        cf.getEntryPoint().getOffset(), cf.getName()));
            }
            DecompileResults res = dec.decompileFunction(f, 420, mon);
            if (res != null && res.decompileCompleted()) {
                println("  ---- C ----");
                println(res.getDecompiledFunction().getC());
            } else {
                println("  (反编译未完成: " + (res == null ? "null" : res.getErrorMessage()) + ")");
            }
            // 该函数引用到的字符串(找 rsb/COMMON/纹理名)
            println("  ---- 该函数引用到的数据/字符串 ----");
            ReferenceIterator ri = currentProgram.getReferenceManager()
                    .getReferencesTo(f.getEntryPoint());
            int n = 0;
            for (Reference r : ri) {
                if (n++ > 4) break;
                println("      " + r.getFromAddress() + " " + r.getReferenceType());
            }
        }
        dec.dispose();
        println("");
        println("### DONE ###");
    }
}
