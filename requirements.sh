set -e
pip3 install --upgrade "pip>=26.2.2"
pip3 install --upgrade "certifi>=2026.10.19"
pip3 install -r /apps/requirements.txt
python3 - <<'EOF'
# eMudhra/emSign CA incident (Oct 2026): fail the build on unpatched TLS stack
import sys
from importlib.metadata import version
from pip._vendor.packaging.version import Version

min_py = {(3, 11): (3, 11, 18), (3, 12): (3, 12, 16), (3, 13): (3, 13, 18),
          (3, 14): (3, 14, 10), (3, 15): (3, 15, 2)}
py = sys.version_info[:3]
errors = []
if py < min_py.get(py[:2], (99,)):
    errors.append(f"python {py} unpatched")
if Version(version("pip")) < Version("26.2.2"):
    errors.append(f"pip {version('pip')} < 26.2.2")
if Version(version("certifi")) < Version("2026.10.19"):
    errors.append(f"certifi {version('certifi')} < 2026.10.19")
if errors:
    sys.exit("TLS check failed: " + ", ".join(errors))
print("TLS check ok:", ".".join(map(str, py)), "pip", version("pip"), "certifi", version("certifi"))
EOF
