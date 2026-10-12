import os
import pwd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
user = pwd.getpwuid(os.getuid()).pw_name
print(f'''[Unit]
Description=Jarvis offline Raspberry Pi companion
After=sound.target
StartLimitIntervalSec=120
StartLimitBurst=3

[Service]
Type=simple
User={user}
SupplementaryGroups=audio
WorkingDirectory={ROOT}
ExecStart={ROOT}/.venv/bin/python -m jarvis.app
Environment=PYTHONUNBUFFERED=1
Environment=OMP_NUM_THREADS=1
Environment=OPENBLAS_NUM_THREADS=1
Environment=ONNX_NUM_THREADS=1
Restart=on-failure
RestartSec=5
KillMode=control-group
TimeoutStopSec=8
MemoryAccounting=yes
MemoryHigh=2100000000
MemoryMax=2300000000
MemorySwapMax=0
OOMPolicy=stop
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths={ROOT}/data {ROOT}/run
# Runtime can reach only loopback: GUI tunnel and local llama.cpp.
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
IPAddressDeny=any
IPAddressAllow=localhost
UMask=0077

[Install]
WantedBy=multi-user.target
''')
