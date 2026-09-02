#!/usr/bin/env python3
# OB5B-S1 leg C, limb 1: re-hash from raw bytes.
# Hashes every artifact either runlog claims a digest for, and prints
# CLAIM / ACTUAL / verdict. No number here is taken from a runlog's prose;
# the claims are transcribed into the table below and the bytes are re-read.
import hashlib, os, sys

def sha(p):
    h = hashlib.sha256()
    try:
        with open(p, 'rb') as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                h.update(b)
    except Exception as e:
        return "ERR:" + str(e)
    return h.hexdigest()

REPO = "/mnt/f/f32/openbob-wt/research-2"

# (path, claimed sha256, source of the claim)
CLAIMS = [
 # ---- leg A, RUNLOG-1 section 10, in repo ----
 (REPO+"/research/ob5b1/gate0_top8.py","ec0d533db241f8950f9b0070bddd385d3c3f5720c8c8bb6d5e29061acde93e36","R1 s10"),
 (REPO+"/research/ob5b1/gate0_window.py","73dd84c2c26166840b7662f1db026170624bf23ae5f4726824b036526bc471ba","R1 s10"),
 (REPO+"/research/ob5b1/gate0_project.py","77dff29c5228310c62f734f506c8ba6fadde62b46dcc60fbf334846938fd2c5c","R1 s10"),
 (REPO+"/research/ob5b1/gate0-run.sh","859405d7b538b401bf3059197ee92970d9de387cf6a976003b238129a005a2dd","R1 s10"),
 (REPO+"/research/ob5b1/gate0-derive.sh","defb2263c95a85535c65a5d7117f46a0d02a9bb861a829d2ddbb077a5eeb2f03","R1 s10"),
 (REPO+"/research/ob5b1/build-ob5b1.sh","34cbf093624076011e024fea62f8c413ff74b6b691a278f1b443baf9442cdb38","R1 s10"),
 (REPO+"/research/ob5b1/ob5b1-gen.cpp","01a2dc56de4e6fae9c28b5a3139cbaeef3fa35190b5c329fe59d8d1b8436aad5","R1 s10/s4.2"),
 (REPO+"/research/ob5b1/make-prompt.sh","b105f08cab36431c13a409e644311576b6173cb25e73ee7699eae80b7c43fbc0","R1 s10"),
 (REPO+"/research/ob5b1/smoke-20b.sh","2d11b088d4e810bc55689d1ce78dfb439de125c1577a5961218ac8e6eed6d95a","R1 s10"),
 (REPO+"/research/ob5b1/gate1-120b.sh","2baa66ae95ae49ecea92edc14f88aa7c3b58e56b4a688812a86c72abbaffcf0e","R1 s10"),
 (REPO+"/research/ob5b1/gate1_route_check.py","62aad75690a789ca244efdd74afa8a58edffb8018e456535c0d862484fcbfc9b","R1 s10"),
 (REPO+"/research/ob5b1/gate1-analyze.sh","82aab8af252f1d8bbf36b05ef5996ca3d6193b3a06eefab4f36e705a3336a6b0","R1 s10"),
 (REPO+"/research/ob5b1/gate1-ctl-ubatch.sh","f594178f933fece43864a016ddef0a73743852262023b5c6ad52a59c3ff95926","R1 s10"),
 (REPO+"/research/ob5b1/gate1-ctl-harness.sh","9389a9bf1b4e624f16dcc21a0e4b2dcb514cfd9feff5100eae014f9f1c14cb14","R1 s10"),
 (REPO+"/research/ob5b1/sha-artifacts.sh","8d5e4d198a6b139cba8c8404b8e2d5f7553ebfa823fb2d83dfc1bf2e60889f85","R1 s10"),
 (REPO+"/research/ob5b1/verify-runlog-arith.py","029924f446a6dc13fb217beeb967acac93b20a889c4656af3722b377b83ce90e","R1 s10"),
 (REPO+"/research/ob5b1/check-lf.sh","0215412f273b3137cab2b1ffcb3dd8da6ba55dce095d13b83039d6070a9ff0ee","R1 s10"),
 # ---- leg B, RUNLOG-2 section 11, in repo ----
 (REPO+"/research/ob5b1/gate2_sets.py","05ff0efa330029d8e20fb444ab78cb12b92480cd1c837d16bd17921e5886afc6","R2 s11"),
 (REPO+"/research/ob5b1/gate2-prompts.sh","7cd56914fa3e2e1536932836f4b0237bea2aa843553ce202178846993752190f","R2 s11"),
 (REPO+"/research/ob5b1/gate2-sweep.sh","38557059f1c0291da4636c5f5a42be88ab6a45bfa6f99b182e1341f3a6cfcd97","R2 s11"),
 (REPO+"/research/ob5b1/gate2_decode_acct.py","cea830d4c7f86e0ac4a74f8261ef6b351537a33739fff9604826eabd516663b6","R2 s11"),
 (REPO+"/research/ob5b1/gate2_window_mass.py","1d33f429f9acc18232e6f2f862c047179faf6ace14bcdafd7f51a58a694654f1","R2 s11"),
 (REPO+"/research/ob5b1/gate2-analyze.sh","446cb0b85e3f62128a61b5cdb31eb119602b7f93b4a54fda28a631e69e867ff4","R2 s11"),
 (REPO+"/research/ob5b1/br1-region.rs","4f4a5a008f667b419b8c5bce120a890fb3178648ae75581de337aaca2c7d3645","R2 s11/s5.1"),
 (REPO+"/research/ob5b1/gate3-patch.py","e1046bfc84d8222497f795c11cb0b2bf5e5bf99e487169f61118e84014035671","R2 s11/s5.1"),
 (REPO+"/research/ob5b1/gate3-fabric-build.sh","4e6e597aefb888e297335623e16d948ccbd0d7a48f61e92aa5fbef62efd8adb2","R2 s11"),
 (REPO+"/research/ob5b1/gate3-devhome.sh","b4d30a9207994347f31895f7098433f3d8fb597d581d4b231054eeb4c8218391","R2 s11"),
 (REPO+"/research/ob5b1/ob5b2-worker.py","9d78d8f4aab7d6dbd6edbd08f8ec11d7852ce6623b022b3de77c00611b322643","R2 s11"),
 (REPO+"/research/ob5b1/gate3-seam.sh","a83b6bea07c285822998ab024c9fffd098b8f7caa4bff9fcea3cd4e22182cc59","R2 s11"),
 (REPO+"/research/ob5b1/gate3-install.sh","966715c56bb1718a50c94bcdb2b978311742e86439f4ab2d8e76b00e41674b1b","R2 s11"),
 (REPO+"/research/ob5b1/gate3-h1-rider.sh","6572c8e8c22f71251c169e3a6c2fab814b516e0f6fb5f2703fe98e3c1e7ee732","R2 s11"),
 (REPO+"/research/ob5b1/verify-runlog2-arith.py","3bd5ce3bd13f550a54d8420c44f2799039578b3a8db6fe4ceac6066cb5b33b4c","R2 s11"),
 # ---- pinned inputs, in repo ----
 (REPO+"/research/ob1b/RESIDENT-SETS-120B-K8.json","8053f18a70030ad2ac2e59fe220a064ee26f35ad4eb3876bbb7c65f6e994530b","R1 s1 / R2 s1"),
 (REPO+"/research/ob1b/EXPERT-MANIFEST-120B.sha256","c71ce2ceec07db8932c8bbb3155029ca5f6b49b940dc46066240b2a47dbf1c80","R1 s1 / R2 s1"),
 # ---- gate 1 identity artifacts, off repo ----
 ("/root/ob5b1/runs/gen-120b-k8-a/gen-ids.txt","5855bcebe6b98f73879a79527b2a9e32fc7b8e43ca8808ac48e6d17634e993e4","R1 s0"),
 ("/root/ob5b1/runs/gen-120b-k8-b/gen-ids.txt","5855bcebe6b98f73879a79527b2a9e32fc7b8e43ca8808ac48e6d17634e993e4","R1 s0 (A/A)"),
 ("/root/ob5b1/runs/gen-120b-k8-c/gen-ids.txt","5855bcebe6b98f73879a79527b2a9e32fc7b8e43ca8808ac48e6d17634e993e4","R1 s0 (A/A)"),
 ("/root/ob5b1/runs/gen-120b-k8-a/gen-text.txt","99417b7488e53ca611f5d9a9e1211ea3491ec0e34e38c4353520ed8f7fe805b4","R1 s0"),
 ("/root/ob5b1/runs/gen-120b-k8-b/gen-text.txt","99417b7488e53ca611f5d9a9e1211ea3491ec0e34e38c4353520ed8f7fe805b4","R1 s0 (A/A)"),
 ("/root/ob5b1/runs/gen-120b-k8-c/gen-text.txt","99417b7488e53ca611f5d9a9e1211ea3491ec0e34e38c4353520ed8f7fe805b4","R1 s0 (A/A)"),
 ("/root/ob5b1/runs/gen-120b-k8-a/prompt-ids.txt","a5e714dacc907126af664f8d512a3bed55a54a325692e4e44cd5eef2c21715d5","R1 s0"),
 ("/root/ob5b1/runs/gen-120b-k8-b/prompt-ids.txt","a5e714dacc907126af664f8d512a3bed55a54a325692e4e44cd5eef2c21715d5","R1 s0 (A/A)"),
 ("/root/ob5b1/runs/gen-120b-k8-c/prompt-ids.txt","a5e714dacc907126af664f8d512a3bed55a54a325692e4e44cd5eef2c21715d5","R1 s0 (A/A)"),
 ("/root/ob5b1/runs/gen-120b-k8-a/route.log","50b8554c38627be594c5ab4314f680380e43fb9f60aaf5e42bc30a742cad5b32","R1 s0"),
 ("/root/ob5b1/runs/gen-120b-k8-b/route.log","50b8554c38627be594c5ab4314f680380e43fb9f60aaf5e42bc30a742cad5b32","R1 s0 (A/A)"),
 ("/root/ob5b1/runs/gen-120b-k8-c/route.log","50b8554c38627be594c5ab4314f680380e43fb9f60aaf5e42bc30a742cad5b32","R1 s0 (A/A)"),
 ("/root/ob5b1/runs/gen-120b-k8-a/alloc-journal.txt","0beefc532904765a029f2ab8dee6ddf72e2b6ebd87fa3b58cb4caaaaef14b6f0","R1 s0"),
 ("/root/ob5b1/runs/gen-120b-k8-b/alloc-journal.txt","0beefc532904765a029f2ab8dee6ddf72e2b6ebd87fa3b58cb4caaaaef14b6f0","R1 s0 (A/A)"),
 ("/root/ob5b1/runs/gen-120b-k8-c/alloc-journal.txt","0beefc532904765a029f2ab8dee6ddf72e2b6ebd87fa3b58cb4caaaaef14b6f0","R1 s0 (A/A)"),
 ("/root/ob5b1/runs/gen-120b-k8-ub32/route.log","e10b5a1c58647324c959df3b56870764afda9d85a2901509d3874cef5d8c9dbd","R1 s4.6 ctl"),
 # ---- prompts ----
 ("/mnt/f/f32/stage/research/ob5b1/PROMPT-1.txt","51cb66644b3c513381d6fc641b4d7c89f1c5b9fccfb10f339e8cfde8a1549ffb","R1 s1 / R2 s1"),
 ("/mnt/f/f32/stage/research/ob5b1/PROMPT-2.txt","f0a0d166b595120d57a88ef118f4abdbbedc0e2457e65d8a3c14b1abdadf4be2","R2 s1"),
 ("/mnt/f/f32/stage/research/ob5b1/PROMPT-3.txt","a5cc358f36ac7e4636115c08a3f7c7eb28345ab50f94d5a3cdb95e5ced62ded3","R2 s1"),
 ("/mnt/f/f32/stage/research/ob5b1/PROMPT-4.txt","b9776d7ddf459c9ad5b0e1d6ac61e27befb5e99fd62446677600d7cacef544d0","R2 s1"),
 # ---- gate 0 inputs, the banked RS053 route logs ----
 ("/mnt/f/f32/stage/research/rs053/runs/120b-prose-a/route.log","5aa8464d3c71a73648c2323456d656cd40cfcf9dc88b603e1f10da69f9efa129","R1 s1"),
 ("/mnt/f/f32/stage/research/rs053/runs/120b-prose-b/route.log","5aa8464d3c71a73648c2323456d656cd40cfcf9dc88b603e1f10da69f9efa129","R1 s1"),
 ("/mnt/f/f32/stage/research/rs053/runs/120b-code-a/route.log","114db00490a2346ddedb84b10c9c8348521d58c0c260e55fa4a6ff641ed19d87","R1 s1"),
 ("/mnt/f/f32/stage/research/rs053/runs/120b-code-b/route.log","114db00490a2346ddedb84b10c9c8348521d58c0c260e55fa4a6ff641ed19d87","R1 s1"),
 # ---- gate 0 outputs ----
 ("/mnt/f/f32/stage/research/ob5b1/gate0/120b-prose-a.json","914048cbf48d466ae7328bb0d342bc1cd800750d8ccad89dc380a1a0e7f93533","R1 s10"),
 ("/mnt/f/f32/stage/research/ob5b1/gate0/120b-prose-a.det2.json","914048cbf48d466ae7328bb0d342bc1cd800750d8ccad89dc380a1a0e7f93533","R1 s10 A/A"),
 ("/mnt/f/f32/stage/research/ob5b1/gate0/120b-prose-b.json","fe1caecc5f0a4f4352ae21651316951e0b28e241e345e3f809b77dd4a80ec374","R1 s10"),
 ("/mnt/f/f32/stage/research/ob5b1/gate0/120b-code-a.json","9c12ceebc59218852b0c2f59c7cf89ea32edf30aadaedc21ac5996e49ba23407","R1 s10"),
 ("/mnt/f/f32/stage/research/ob5b1/gate0/120b-code-b.json","357744f8efdf0ed5e0309b358645a7cea473d8529305e0d0017f1851148dcbeb","R1 s10"),
 ("/mnt/f/f32/stage/research/ob5b1/gate0/window64.json","c1a816b779c5c640d7901234b31e2dbd64aea05d356824074c6a52b40f1b935c","R1 s10"),
 # ---- engine binaries ----
 ("/root/ob5b1/llama.cpp/build/bin/ob5b1-gen","daca8fb74f626c186950c2882dfd1fdfe191056ca5feacccd51201db3e625740","R1 s4.2 / R2 s1"),
 ("/root/ob5b1/llama.cpp/build/bin/llama-perplexity","63007d58a53a31de9a4e140469eb0bede3e4b2a1f98e801bc906a800381dc9bf","R1 s4.1"),
 ("/root/ob5b1/llama.cpp/build/bin/libggml-base.so.0","6f1ba2c7a215c8c33594afdce199530138272697b7d6d29aa677bd4a3c27318d","R1 s4.1"),
 ("/root/ob5b1/llama.cpp/build/bin/libggml-cpu.so.0","41773bf9edcd89ccaaece7a1b7a2897e61ab07689f81073e8febed09a2f5fc86","R1 s4.1"),
 ("/root/ob5b1/llama.cpp/build/bin/libllama.so.0","9a3e448c4331ebbc09c5c4feef7f39f83ac649b6d77e9de07c5a4884583b876e","R1 s4.1"),
 ("/root/ob5a/llama.cpp/build/bin/llama-perplexity","f9965806c98f5dce6cc7f4f44e52dd57e8d9b51cf27826ad4608db4599e23249","R1 s4.1 / OB5A"),
 ("/root/ob5a/llama.cpp/build/bin/libllama.so.0","5e2c4a1b34606ffe1d9cc7e563345b74426d3b8de836b4176d712916a5aced00","R1 s4.1"),
 ("/root/ob5a/llama.cpp/build/bin/libggml-base.so.0","6f1ba2c7a215c8c33594afdce199530138272697b7d6d29aa677bd4a3c27318d","R1 s4.1"),
 ("/root/ob5a/llama.cpp/build/bin/libggml-cpu.so.0","41773bf9edcd89ccaaece7a1b7a2897e61ab07689f81073e8febed09a2f5fc86","R1 s4.1"),
 # ---- gate 2 identity ----
 ("/root/ob5b2/runs/g2-k8-p1-a/gen-ids.txt","5b751861465660a73ec9e895f03f01d81f0522e5ef27c713efb44746c38b7686","R2 s4.2"),
 ("/root/ob5b2/runs/g2-k8-p1-b/gen-ids.txt","5b751861465660a73ec9e895f03f01d81f0522e5ef27c713efb44746c38b7686","R2 s4.2 A/A"),
 ("/root/ob5b2/runs/g2-k8-p1-a/gen-text.txt","539e71d138c3c7b15e379b0b6f0729a691d7569884182a9617fabf462ea5da55","R2 s4.2"),
 ("/root/ob5b2/runs/g2-k8-p1-b/gen-text.txt","539e71d138c3c7b15e379b0b6f0729a691d7569884182a9617fabf462ea5da55","R2 s4.2 A/A"),
 # ---- gate 3 ----
 ("/root/ob5b2/worker/WORKER-LOG-1.jsonl","021b0dddc3e867ad4002a1f6b56562074c0a95135be069f428abb293326b7719","R2 s0/s11"),
 # ---- gatekeeper artifact ----
 ("/root/openbob-l2s2/in/qwen3-4b-openbob-q1.bin","6a617f7af6e75b342d3040e3d3175001108806622fe10dd8597ef2a6a29915c3","R2 s1"),
 # ---- fabric source ----
 ("/root/k4b/src/openbob_s11_cpu.rs","7fc600b9f354dffcb606b112793523937f6b3cf2c3dbfa34b97f0681a3f1d80d","R2 s1/s5.1"),
]

ok = 0
bad = 0
missing = 0
print("PATH | CLAIM(R1/R2) | ACTUAL | VERDICT")
for p, claim, src in CLAIMS:
    a = sha(p)
    if a.startswith("ERR:"):
        v = "MISSING"
        missing += 1
    elif a == claim:
        v = "MATCH"
        ok += 1
    else:
        v = "*** MISMATCH ***"
        bad += 1
    print("%s | %s | %s | %s | %s" % (p, claim, a, v, src))
print("")
print("HASH_CHECKS %d  MATCH %d  MISMATCH %d  MISSING %d" % (len(CLAIMS), ok, bad, missing))
