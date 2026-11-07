"""H.264 matrix: resolution x fps x target bitrate, received over UDP. Same env vars as udp_bench.py."""
import os, socket, subprocess, threading, time, json
HOST=os.environ["LOCAL_IP"]; PI=os.environ["PI_TARGET"]; PASS=os.environ.get("PI_PASS")
SSH=["sshpass","-p",PASS,"ssh"] if PASS else ["ssh"]
REMOTE=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"remote_bench.py")).read()
RES=[(1920,1080),(1280,720),(960,540),(640,480)]; FPS=[60,30,15]; BR=[8,4,2]   # BR in Mbit/s
print(f"{'res':10}{'req fps':>8}{'target Mb/s':>12}{'fps':>7}{'sysCPU%':>8}{'proc%':>6}{'recv Mb/s':>10}{'pkts/s':>8}",flush=True)
n=0
for w,h in RES:
  for f in FPS:
    for b in BR:
      port=5700+n; n+=1
      s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,64<<20); s.bind(("0.0.0.0",port)); s.settimeout(1)
      log=[]; stop=False
      def rx():
        buf=bytearray(70000)
        while not stop:
          try: k=s.recv_into(buf); log.append((time.monotonic(),k))
          except socket.timeout: pass
      th=threading.Thread(target=rx); th.start()
      r=subprocess.run(SSH+[PI,"python3","-","h264",str(w),str(h),str(f),HOST,str(port),"--bitrate",str(b*1000000)],input=REMOTE,capture_output=True,text=True,timeout=60)
      stop=True; th.join(); s.close()
      ln=[l for l in r.stdout.splitlines() if l.startswith("{")]; res=json.loads(ln[-1]) if ln else {"fail":"?"}
      tag=f"{f'{w}x{h}':10}{f:>8}{b:>12}"
      if "fail" in res or not log: print(tag+"  FAIL",res.get("fail",""),flush=True); continue
      t0=log[0][0]+5; win=[k for t,k in log if t0<=t<t0+8]
      print(f"{tag}{res['fps']:7.1f}{res['sys']:8.0f}{res['proc']:6.0f}{sum(win)/1e6:10.2f}{len(win)/8:8.0f}",flush=True)
