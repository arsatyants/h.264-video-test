import socket, subprocess, threading, time, json, sys
import os
HOST=os.environ["LOCAL_IP"]                      # this machine's IP, receiver of the UDP stream
PI=os.environ["PI_TARGET"]                       # e.g. admin@192.168.10.85
PASS=os.environ.get("PI_PASS")                   # optional; otherwise ssh keys are used
SSH=["sshpass","-p",PASS,"ssh"] if PASS else ["ssh"]
tests=[("yuv420",1536,864,120,["--mode","1536:864"]),("yuv420",2304,1296,56,["--mode","2304:1296"]),("yuv420",4608,2592,14,["--mode","4608:2592"]),
("h264",1280,720,60,[]),("h264",1728,972,30,[]),("h264",1920,1080,30,[]),("h264",1920,1080,60,[]),
("mjpeg",1536,864,120,[]),("mjpeg",2304,1296,56,[]),("mjpeg",4608,2592,14,[])]
print(f"{'codec':7}{'res':11}{'req':>4} {'fps':>6} {'sysCPU%':>8} {'proc%':>6} {'recv Mbit/s':>12} {'pkts/s':>8}",flush=True)
for n,(codec,w,h,f,extra) in enumerate(tests):
    port=5600+n
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,128<<20); s.bind(("0.0.0.0",port)); s.settimeout(1)
    log=[]; stop=False
    def rx():
        buf=bytearray(70000)
        while not stop:
            try: k=s.recv_into(buf); log.append((time.monotonic(),k))
            except socket.timeout: pass
    th=threading.Thread(target=rx); th.start()
    cmd=SSH+[PI,"python3","-","%s"%codec,str(w),str(h),str(f),HOST,str(port)]+extra
    r=subprocess.run(cmd,input=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"remote_bench.py")).read(),capture_output=True,text=True,timeout=60)
    stop=True; th.join(); s.close()
    line=[l for l in r.stdout.splitlines() if l.startswith("{")]
    res=json.loads(line[-1]) if line else {"fail":r.stderr[-100:]}
    if "fail" in res: print(f"{codec:7}{f'{w}x{h}':11}{f:>4}  FAIL {res['fail']}",flush=True); continue
    if not log: print(f"{codec:7}{f'{w}x{h}':11}{f:>4} {res['fps']:6.1f}  no packets received",flush=True); continue
    t0=log[0][0]+5; win=[k for t,k in log if t0<=t<t0+8]
    print(f"{codec:7}{f'{w}x{h}':11}{f:>4} {res['fps']:6.1f} {res['sys']:8.0f} {res['proc']:6.0f} {sum(win)*8/8/1e6:12.1f} {len(win)/8:8.0f}",flush=True)
