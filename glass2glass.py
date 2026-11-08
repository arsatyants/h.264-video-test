#!/usr/bin/env python3
"""Glass-to-glass latency test, runs on the DISPLAY host (e.g. a Pi 5 with a screen).
Shows a big millisecond stopwatch plus the live camera video next to it. Point the camera at this screen: the video then
contains the stopwatch as it was when the frame was captured; latency = clock now - clock seen inside the video.
The app saves a PNG once per second and logs the exact clock value at that moment, so only the nested clock has to be read.

LOCAL_IP=<this host> PI_TARGET=user@pi [PI_PASS=..] python3 glass2glass.py TAG SECONDS [rpicam-vid extra args...]
Needs: pygame, ffmpeg. Under Wayland run with WAYLAND_DISPLAY / XDG_RUNTIME_DIR set."""
import os, sys, time, subprocess, threading
os.environ.setdefault("SDL_VIDEODRIVER", "wayland")
import pygame
HOST=os.environ["LOCAL_IP"]; PI=os.environ["PI_TARGET"]; PASS=os.environ.get("PI_PASS")
tag=sys.argv[1]; secs=int(sys.argv[2]); extra=sys.argv[3:]
TS=os.environ.get("FMT")=="ts"; PORT=5990; VW,VH=480,270; OUT="g2g_out"; os.makedirs(OUT,exist_ok=True)
SSH=["sshpass","-p",PASS,"ssh"] if PASS else ["ssh"]
dec=subprocess.Popen(["ffmpeg","-loglevel","error","-fflags","nobuffer","-flags","low_delay",*(["-threads",os.environ["FF_THREADS"]] if os.environ.get("FF_THREADS") else []),"-probesize","32768","-analyzeduration","0",
    *(["-f","mpegts"] if TS else ["-f","h264"]),"-i",f"udp://0.0.0.0:{PORT}?fifo_size=5000000&overrun_nonfatal=1","-vf",f"scale={VW}:{VH}","-f","rawvideo","-pix_fmt","rgb24","-"],
    stdout=subprocess.PIPE,stderr=open(f"{OUT}/{tag}_ffmpeg.log","w"),bufsize=0)
cam=subprocess.Popen(SSH+[PI,"pkill -x rpicam-vid; sleep 1; rpicam-vid -n -t %d --codec %s --framerate 60 --width 1280 --height 720 --bitrate 8000000 -o udp://%s:%d%s %s"%(secs*1000,"libav --libav-format mpegts" if TS else "h264",HOST,PORT,"?pkt_size=1316" if TS else""," ".join(extra))],
    stdout=subprocess.DEVNULL,stderr=open(f"{OUT}/{tag}_cam.log","w"))
latest=[None,0.0,0]
def reader():
    n=VW*VH*3
    while True:
        buf=b""
        while len(buf)<n:
            c=dec.stdout.read(n-len(buf))
            if not c: return
            buf+=c
        latest[0]=buf; latest[1]=time.perf_counter(); latest[2]+=1
threading.Thread(target=reader,daemon=True).start()
pygame.init(); scr=pygame.display.set_mode((960,544),pygame.FULLSCREEN); pygame.mouse.set_visible(False)
big=pygame.font.SysFont("dejavusansmono,monospace",118,bold=True); mid=pygame.font.SysFont("dejavusansmono,monospace",84,bold=True); small=pygame.font.SysFont("dejavusansmono,monospace",22)
tile=pygame.font.SysFont("dejavusansmono,monospace",44,bold=True); TILE=os.environ.get("TILE","1")!="0"
clk=pygame.time.Clock(); t_start=time.perf_counter(); last_shot=0; shots=0; log=open(f"{OUT}/{tag}.csv","w"); log.write("png,clock_now\n")
while time.perf_counter()-t_start<secs-1:
    for e in pygame.event.get(): pass
    now=time.perf_counter(); scr.fill((0,0,0))
    cv="%06.3f"%(now%100)
    if TILE:                                  # small clock copies over the whole screen: readable whatever part the camera sees
        ts=tile.render(cv,True,(255,255,255))
        for yy in range(0,544,56):
            for xx in range(0,960,168): scr.blit(ts,(xx+(yy//56%2)*40,yy))
    # motion: sweeping stripes (top-left strip) and a bouncing ball (bottom-left strip)
    off=int(now*400)%80
    for x in range(-80+off,480,80): pygame.draw.rect(scr,(0,160,255),(x,10,40,150))
    bx=60+abs((now*500)%840-420)*1.0; by=380+abs((now*300)%240-120)*0.9
    pygame.draw.circle(scr,(255,200,0),(int(min(bx,470)),int(by)),38)
    scr.blit(big.render(cv,True,(255,255,255)),(8,200))
    for yy in (25,425): scr.blit(mid.render(cv,True,(255,255,255)),(500,yy))   # copies where the camera sees the right half
    scr.blit(small.render(f"{tag}  frames:{latest[2]}",True,(160,160,160)),(8,520))
    if latest[0]:
        scr.blit(pygame.image.frombuffer(latest[0],(VW,VH),"RGB"),(480,137))
        scr.blit(small.render("pipe age %3.0f ms"%((now-latest[1])*1000),True,(120,200,120)),(8,490))
    pygame.draw.rect(scr,(255,0,0),(480,137,VW,VH),2)
    pygame.display.flip()
    if now-t_start>6 and now-last_shot>=1.0:
        name=f"{tag}_{shots:02d}.png"; pygame.image.save(scr,f"{OUT}/{name}"); log.write(f"{name},{cv}\n"); log.flush(); last_shot=now; shots+=1
    clk.tick(60)
log.close(); pygame.quit(); cam.terminate(); dec.kill(); dec.wait()
subprocess.run(SSH+[PI,"pkill -x rpicam-vid"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
