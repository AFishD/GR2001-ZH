// TextureHost.java - decompile the texture-name resolution chain:
//   GetTexture / LoadIndexedRSB / LoadingTexturePak / LoadRSBFile / ReadResourceFile / diSearchFile(Ex)
// Goal: decide whether FONT.RES's texture-name can point at a NEWLY ADDED top-level IMG entry.
// (historical experiment F4 pointed it at an EXISTING top-level entry LOAD_NEW_1.RSB and saw
//  zero cdvd reads => concluded "resolution domain = PAK internal directory")
// run: work\tools\gh.bat work\tools\ghidra_proj_ee GRLocEE -process SLUS_206.13.elf -postScript TextureHost.java -scriptPath work\tools\ghidra_scripts -noanalysis
//@category GRLoc

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.util.task.ConsoleTaskMonitor;

public class TextureHost extends GhidraScript {

    private static final long[] TARGETS = {
        0x0051B040L,  // UITextureMgr::GetTexture(const RSFilename&)
        0x0051B230L,  // UITextureMgr::LoadIndexedRSB(const RSFilename&)
        0x0051B660L,  // UITextureMgr::LoadingTexturePak(int, const char*)
        0x0051C810L,  // UITexture::LoadRSBFile(istream&)
        0x00219380L,  // RSFontMgr::ReadResourceFile(const char*)
        0x004D1290L,  // diSearchFile
        0x004D11D0L   // diSearchFileEx
    };

    @Override
    public void run() throws Exception {
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);

        for (long va : TARGETS) {
            Address a = toAddr(va);
            Function f = getFunctionAt(a);
            if (f == null) f = getFunctionContaining(a);
            println("");
            println("==================================================================");
            if (f == null) {
                println("## 0x" + Long.toHexString(va) + "  (no function)");
                println("==================================================================");
                continue;
            }
            println("## " + f.getName() + " @0x" + Long.toHexString(f.getEntryPoint().getOffset())
                    + "  size=" + f.getBody().getNumAddresses()
                    + " callers=" + f.getCallingFunctions(mon).size());
            println("==================================================================");
            DecompileResults res = dec.decompileFunction(f, 600, mon);
            if (res != null && res.decompileCompleted()) {
                println(res.getDecompiledFunction().getC());
            } else {
                println("  (incomplete: " + (res == null ? "null" : res.getErrorMessage()) + ")");
            }
        }
        dec.dispose();
        println("");
        println("### DONE ###");
    }
}
