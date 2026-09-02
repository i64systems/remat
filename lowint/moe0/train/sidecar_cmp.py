"""Compare two W4 resume sidecars tensor by tensor.

The sidecar is NOT the G1-compared artifact (the safetensors is), but if the
step-1100 sidecars differ in bytes we say WHY, exactly, rather than waving at it.
"""
import sys
import torch

a = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
b = torch.load(sys.argv[2], map_location="cpu", weights_only=False)

print("step a=%s b=%s" % (a["step"], b["step"]))
oa, ob = a["opt"], b["opt"]
print("param_groups keys a=%s" % sorted(oa["param_groups"][0].keys()))
print("param_groups keys b=%s" % sorted(ob["param_groups"][0].keys()))
print("param_groups equal=%s" % (oa["param_groups"] == ob["param_groups"]))
ka = sorted(oa["state"].keys())
kb = sorted(ob["state"].keys())
print("state key count a=%d b=%d same_keys=%s" % (len(ka), len(kb), ka == kb))

bad = 0
checked = 0
kinds = set()
for k in ka:
    sa, sb = oa["state"][k], ob["state"][k]
    if sorted(sa.keys()) != sorted(sb.keys()):
        print("KEYSET DIFFERS at %s: %s vs %s" % (k, sorted(sa.keys()), sorted(sb.keys())))
        bad += 1
        continue
    for f in sorted(sa.keys()):
        va, vb = sa[f], sb[f]
        if torch.is_tensor(va):
            kinds.add((f, str(va.dtype), str(vb.dtype)))
            checked += 1
            if not torch.equal(va.cpu(), vb.cpu()):
                print("TENSOR DIFFERS state[%s][%s]" % (k, f))
                bad += 1
        else:
            checked += 1
            if va != vb:
                print("VALUE DIFFERS state[%s][%s]: %r vs %r" % (k, f, va, vb))
                bad += 1
print("field kinds/dtypes: %s" % sorted(kinds))
print("compared %d optimizer state fields, differences=%d" % (checked, bad))
print("cpu_rng equal=%s" % torch.equal(a["cpu_rng"], b["cpu_rng"]))
print("cuda_rng count a=%d b=%d" % (len(a["cuda_rng"]), len(b["cuda_rng"])))
for i, (x, y) in enumerate(zip(a["cuda_rng"], b["cuda_rng"])):
    print("cuda_rng[%d] equal=%s" % (i, torch.equal(x, y)))
print("SIDECAR_NUMERIC_EQUAL=%s" % (bad == 0))
