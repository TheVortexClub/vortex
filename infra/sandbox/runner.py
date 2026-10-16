"""Runs the code from stdin, then saves any open matplotlib figures to /out as PNG."""

import sys
import traceback

code = sys.stdin.read()
namespace = {"__name__": "__main__"}
status = 0
try:
    exec(compile(code, "<vortex>", "exec"), namespace)
except SystemExit as e:
    status = e.code if isinstance(e.code, int) else 0
except BaseException:
    traceback.print_exc()
    status = 1
finally:
    try:
        import matplotlib.pyplot as plt

        for n, num in enumerate(plt.get_fignums(), start=1):
            plt.figure(num).savefig(f"/out/grafico-{n}.png", dpi=110, bbox_inches="tight")
    except Exception:
        pass
sys.exit(status)
