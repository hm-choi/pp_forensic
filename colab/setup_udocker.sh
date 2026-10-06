#!/usr/bin/env bash
# One-time setup on a fresh Colab GPU runtime: udocker + HEaaN GPU image + sanity test.
set -e
command -v udocker >/dev/null || pip -q install udocker
U="udocker --allow-root"
$U install >/dev/null
if ! $U ps | grep -q heaan; then
  $U pull cryptolabinc/heaan-stat:1.0.0-gpu
  $U create --name=heaan cryptolabinc/heaan-stat:1.0.0-gpu
  $U setup --nvidia heaan
fi
echo "== GPU inside the container"
$U run --entrypoint=nvidia-smi heaan --query-gpu=name,memory.total --format=csv
cat > /content/heaan_sanity.py <<'PY'
import heaan as hn, numpy as np
ctx = hn.make_context(hn.ParameterPreset.FGb, {0})
dev = hn.Device(hn.DeviceType.GPU, 0)
sk = hn.SecretKey(ctx)
kg = hn.KeyGenerator(ctx, sk); kg.gen_common_keys(); pk = kg.keypack
sk.to(dev); pk.to(dev)
enc, dec, ev = hn.Encryptor(ctx), hn.Decryptor(ctx), hn.HomEvaluator(ctx, pk)
m = hn.Message(np.full(2**15, 0.5)); m.to(dev)
c = hn.Ciphertext(ctx); enc.encrypt(m, pk, c)
ev.mult(c, c, c)
r = hn.Message(15); dec.decrypt(c, sk, r); r.to_host()
v = np.array(r, dtype=np.complex128)[0].real
print("SANITY", "OK" if abs(v - 0.25) < 1e-6 else "FAIL", "0.5*0.5 =", v)
PY
echo "== HEaaN on GPU"
$U run --volume=/content:/content --entrypoint=python3 heaan /content/heaan_sanity.py
