package dev.axymorrsen.mifitness;
public final class GatePolicyTest {
    private GatePolicyTest() {}
    public static void main(String[] args) {
        for (int bits=0;bits<32;bits++) {
            boolean original=(bits&1)!=0,enabled=(bits&2)!=0,provider=(bits&4)!=0,
                    capable=(bits&8)!=0,pinned=(bits&16)!=0;
            boolean expected=original || (enabled && provider && capable && pinned);
            if (GatePolicy.allow(original,enabled,provider,capable,pinned)!=expected)
                throw new AssertionError("Gate policy incorrect for "+bits);
        }
        System.out.println("GatePolicy 32 input combinations passed");
    }
}
