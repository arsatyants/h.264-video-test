"""Runs on the Pi. Estimates clock offset to the host (UDP ping-pong), runs rpicam-vid -> udp, returns JSON
with per-frame sensor timestamps converted to the HOST clock, plus fps/CPU."""
import subprocess, time, os, sys, json, socket, struct
HZ=os.sysconf('SC_CLK_TCK')
codec,w,h,f,host,port,echo=sys.argv[1:8]; extra=sys.argv[8:]
# --- clock offset: host_time - pi_time, taken from the lowest-RTT sample
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.settimeout(0.5); best=None
for _ in range(60):
    t0=time.time(); s.sendto(b'x',(host,int(echo)))
    try: ht=struct.unpack('d',s.recv(8))[0]
    except socket.timeout: continue
    t1=time.time()
    if best is None or t1-t0<best[0]: best=(t1-t0, ht-(t0+t1)/2)
rtt,off=best
def stat():
    v=list(map(int,open('/proc/stat').readline().split()[1:])); return sum(v), v[3]+v[4]
def proc(pid):
    x=open(f'/proc/{pid}/stat').read().rsplit(')',1)[1].split(); return int(x[11])+int(x[12])
meta='/tmp/m.json'
if os.path.exists(meta): os.remove(meta)
p=subprocess.Popen(["rpicam-vid","-n","-t","15000","--codec",codec,"--width",w,"--height",h,"--framerate",f,"--metadata",meta,"-o",f"udp://{host}:{port}"]+extra,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
time.sleep(5)
if p.poll() is not None:
    err=[l for l in p.stderr.read().decode().splitlines() if 'rror' in l]; print(json.dumps({"fail":err[-1] if err else "exit"})); sys.exit()
t0,i0=stat(); c0=proc(p.pid); w0=time.time(); time.sleep(8)
t1,i1=stat(); c1=proc(p.pid); w1=time.time(); p.wait()
d=json.load(open(meta)); ts=[x["SensorTimestamp"]/1e9 for x in d]
wall_minus_boot=time.time()-time.clock_gettime(time.CLOCK_BOOTTIME)
caps=[t+wall_minus_boot+off for t in ts]          # capture time on the host clock
fps=(len(ts)-1)/(ts[-1]-ts[0])
print(json.dumps({"off_ms":off*1000,"rtt_ms":rtt*1000,"caps":caps,"fps":fps,"sys":100*(1-(i1-i0)/(t1-t0)),"proc":100*(c1-c0)/HZ/(w1-w0)}))
