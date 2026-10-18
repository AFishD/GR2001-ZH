# 精确换算：p2 里「失败路径出口」到「坏跳转」之间隔了多少 cycle
fail_exit = 65029607910      # hook 0051C05C (s0=0, frame 44)
last_vec  = 65030656737      # hook 80000180（进入分派器，随后 jr 到 0x7E7E7E7E）
print("p2: 0x51C05C(fail exit) -> 0x80000180(分派器) = %d cycles" % (last_vec - fail_exit))
print("p2: 第2次解压 malloc 返回0 = 65029607850 -> 分派器 = %d cycles" % (last_vec - 65029607850))
