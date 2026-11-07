import subprocess, time, os, sys, json
HZ=os.sysconf('SC_CLK_TCK')
codec,w,h,f,host,port=sys.argv[1:7]; extra=sys.argv[7:]
def stat():
    v=list(map(int,open('/proc/stat').readline().split()[1:])); return sum(v), v[3]+v[4]
def proc(pid):
    x=open(f'/proc/{pid}/stat').read().rsplit(')',1)[1].split(); return int(x[11])+int(x[12])
pts='/tmp/p.pts'
if os.path.exists(pts): os.remove(pts)
p=subprocess.Popen(["rpicam-vid","-n","-t","15000","--codec",codec,"--width",w,"--height",h,"--framerate",f,"--save-pts",pts,"-o",f"udp://{host}:{port}"]+extra,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
time.sleep(5)
if p.poll() is not None:
    err=[l for l in p.stderr.read().decode().splitlines() if 'ERROR' in l or 'rror' in l]
    print(json.dumps({"fail":err[-1] if err else "exit"})); sys.exit()
t0,i0=stat(); c0=proc(p.pid); w0=time.time()
time.sleep(8)
t1,i1=stat(); c1=proc(p.pid); w1=time.time()
p.wait()
ts=[float(l) for l in open(pts) if l.strip() and not l.startswith('#')]
ts=[x for x in ts if x>=ts[0]+5000]
print(json.dumps({"fps":(len(ts)-1)*1000/(ts[-1]-ts[0]),"sys":100*(1-(i1-i0)/(t1-t0)),"proc":100*(c1-c0)/HZ/(w1-w0)}))
