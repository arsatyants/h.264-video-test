"""Run on the receiving host. Per-frame latency = UDP receive time on host - sensor timestamp (host clock, NTP + ping-pong offset).
LOCAL_IP=... PI_TARGET=user@pi [PI_PASS=...] python3 latency_test.py"""
import os, socket, struct, subprocess, threading, time, json, statistics as st
HOST=os.environ["LOCAL_IP"]; PI=os.environ["PI_TARGET"]; PASS=os.environ.get("PI_PASS")
SSH=["sshpass","-p",PASS,"ssh"] if PASS else ["ssh"]
REMOTE=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"remote_latency.py")).read()
LOWLAT=["--flush","--buffer-count","3","--denoise","cdn_off","--intra","30","--inline","--profile","baseline"]
SETS={"main":{"default":[],"flush":["--flush"],"lowlat":LOWLAT},
 "flags":{"bc2":["--flush","--buffer-count","2"],"bc3":["--flush","--buffer-count","3"],"bc4":["--flush","--buffer-count","4"],
          "bc3+dn":["--flush","--buffer-count","3","--denoise","cdn_off"],"bc3+gop":["--flush","--buffer-count","3","--intra","30","--inline","--profile","baseline"]}}
CFG=SETS[os.environ.get("LAT_SET","main")]
RES=[(1920,1080,30),(1920,1080,60),(1280,720,60)] if os.environ.get("LAT_SET")=="flags" else [(1920,1080,30),(1920,1080,60),(1280,720,60),(640,480,60)]; BR="8000000"
def slices(b):
    n=0; i=b.find(b'\x00\x00\x01')
    while i!=-1 and i+3<len(b):
        if b[i+3]&0x1f in (1,5): n+=1
        i=b.find(b'\x00\x00\x01',i+3)
    return n
print(f"{'res@fps':12}{'config':9}{'fps':>6}{'lat med':>9}{'p95':>7}{'max':>7}{'drift':>7}{'rx/tx fr':>10}{'Mb/s':>6}{'CPU%':>5}{'off ms':>7}",flush=True)
n=0
for w,h,f in RES:
  for name,extra in CFG.items():
    port=5800+n; echo=5900+n; n+=1
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,64<<20); s.bind(("0.0.0.0",port)); s.settimeout(1)
    e=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); e.bind(("0.0.0.0",echo)); e.settimeout(1)
    log=[]; stop=False
    def rx():
        buf=bytearray(70000)
        while not stop:
            try: k=s.recv_into(buf); log.append((time.time(),k,slices(bytes(buf[:k]))))
            except socket.timeout: pass
    def ec():
        while not stop:
            try: _,a=e.recvfrom(16); e.sendto(struct.pack('d',time.time()),a)
            except socket.timeout: pass
    ths=[threading.Thread(target=rx),threading.Thread(target=ec)]; [t.start() for t in ths]
    r=subprocess.run(SSH+[PI,"python3","-","h264",str(w),str(h),str(f),HOST,str(port),str(echo),"--bitrate",BR]+extra,input=REMOTE,capture_output=True,text=True,timeout=90)
    stop=True; [t.join() for t in ths]; s.close(); e.close()
    ln=[l for l in r.stdout.splitlines() if l.startswith("{")]; res=json.loads(ln[-1]) if ln else {"fail":r.stderr[-120:]}
    tag=f"{f'{w}x{h}@{f}':12}{name:9}"
    if "fail" in res or not log: print(tag+" FAIL",res.get("fail",""),flush=True); continue
    starts=[t for t,k,c in log for _ in range(c)]       # receive time of each frame's first slice datagram
    caps=res["caps"]; m=min(len(starts),len(caps))
    pairs=[(starts[i],(starts[i]-caps[i])*1000) for i in range(m)]
    t0=starts[0]+5; win=[(t,l) for t,l in pairs if t0<=t<t0+8]
    lat=[l for _,l in win]; a=[l for t,l in win if t<t0+3]; b=[l for t,l in win if t>=t0+5]
    mb=sum(k for t,k,c in log if t0<=t<t0+8)*8/8/1e6
    drift=(st.median(b)-st.median(a)) if a and b else float('nan')
    lat.sort()
    print(f"{tag}{res['fps']:6.1f}{st.median(lat):9.0f}{lat[int(.95*len(lat))]:7.0f}{lat[-1]:7.0f}{drift:7.0f}{f'{len(starts)}/{len(caps)}':>10}{mb:6.1f}{res['sys']:5.0f}{res['off_ms']:7.1f}",flush=True)
