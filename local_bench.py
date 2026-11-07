import subprocess, time, os
HZ=os.sysconf('SC_CLK_TCK')
def stat():
    v=list(map(int,open('/proc/stat').readline().split()[1:]))
    return sum(v), v[3]+v[4]   # total, idle+iowait
def proc(pid):
    f=open(f'/proc/{pid}/stat').read().rsplit(')',1)[1].split()
    return int(f[11])+int(f[12])
def rss(pid):
    for l in open(f'/proc/{pid}/status'):
        if l.startswith('VmRSS'): return int(l.split()[1])//1024
tests=[]
for w,h,f in [(1536,864,120),(2304,1296,56),(4608,2592,14)]: tests.append(("yuv420",w,h,f,["--mode",f"{w}:{h}"]))
for w,h,f in [(1280,720,60),(1728,972,30),(1920,1080,30),(1920,1080,60)]: tests.append(("h264",w,h,f,[]))
for w,h,f in [(1536,864,120),(2304,1296,56),(4608,2592,14)]: tests.append(("mjpeg",w,h,f,[]))
print(f"{'codec':7}{'res':11}{'req':>4} {'fps':>6} {'sysCPU%':>8} {'proc%(of 400)':>14} {'RSS MB':>7} {'temp':>6}")
for codec,w,h,f,extra in tests:
    pts='/tmp/p.pts'
    if os.path.exists(pts): os.remove(pts)
    p=subprocess.Popen(["rpicam-vid","-n","-t","15000","--codec",codec,"--width",str(w),"--height",str(h),"--framerate",str(f),"--save-pts",pts,"-o","/dev/null"]+extra,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    time.sleep(5)
    if p.poll() is not None:
        print(f"{codec:7}{w}x{h:<6}{f:>4}  FAIL: "+[l for l in p.stderr.read().decode().splitlines() if 'ERROR' in l][-1:].__str__()); continue
    t0,i0=stat(); c0=proc(p.pid); w0=time.time()
    time.sleep(8)
    t1,i1=stat(); c1=proc(p.pid); w1=time.time(); r=rss(p.pid)
    temp=subprocess.run(["vcgencmd","measure_temp"],capture_output=True,text=True).stdout.strip().replace("temp=","")
    p.wait()
    sys_cpu=100*(1-(i1-i0)/(t1-t0))
    proc_cpu=100*(c1-c0)/HZ/(w1-w0)
    ts=[float(l) for l in open(pts) if l.strip() and not l.startswith("#")]
    ts=[x for x in ts if x>=ts[0]+5000]   # steady-state window after 5 s
    fps=(len(ts)-1)*1000/(ts[-1]-ts[0])
    print(f"{codec:7}{f'{w}x{h}':11}{f:>4} {fps:6.1f} {sys_cpu:8.0f} {proc_cpu:14.0f} {r:7} {temp:>6}",flush=True)
print(subprocess.run(["vcgencmd","get_throttled"],capture_output=True,text=True).stdout.strip())
