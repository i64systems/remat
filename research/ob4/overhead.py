import subprocess, time
N = 200
t0 = time.perf_counter()
for _ in range(N):
    subprocess.run(["zstd", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
dt = time.perf_counter() - t0
print("avg subprocess spawn+exit overhead (zstd --version) sec:", dt / N)
