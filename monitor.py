import re
import sys
import json
import time
import psutil
import socket
import datetime
import subprocess

import threading

from websocket import create_connection

hostname = socket.gethostname()

NvidiaDriverInfoRE = re.compile(
    r"""NVIDIA-SMI\s(?P<Smiversion>[0-9\.]*)\s*
        Driver\sVersion:\s(?P<DriverVersion>[0-9\.]*)
     """,
    re.X|re.S)

NvidiaHardwareInfoRE = re.compile(
    r"""\|\s+(?P<Index>\d+)\s+(?P<Name>.*?)\s{4}.*?
        \|\s+(?P<Fan>\d+%)\s+(?P<Temp>\d+C).*?
             (?P<Pwr>\d+W\s+/\s+\d+W).*?
             (?P<Memory>[\d\.]+MiB\s+/\s+[\d\.]+MiB).*?
             (?P<Percent>\d+%).*?\|
     """,
    re.X|re.S)

NvidiaJobInfoRE = re.compile(
    r"""\|\s+(?P<GPU>\d+)\s+(?P<PID>\d+)\s+\S+\s+(?P<Process>\S+)\s+(?P<Name>\S+)?\s(?P<Memory>\d+MiB)\s+\|""")

def getCPU():
    return [{
        'name':    'Cpu',
        'total':   psutil.cpu_count(logical=False),
        'percent': str(psutil.cpu_percent()) + '%',
    }]

def getRAM():
    tmp = psutil.virtual_memory()
    return [{
        'name':      'Ram',
        'total':     '%.2f GB' %(tmp.total/1024.0/1024.0/1024.0),
        'percent':   str(tmp.percent) + '%',
        'available': tmp.available,
    }]

def getDISK():
    tmp    = psutil.disk_partitions()
    result = []
    for t in tmp:
        if '/osd/'     in t.mountpoint: continue
        if '/docker/'  in t.mountpoint: continue
        if '/kubelet/' in t.mountpoint: continue
        if '/private/' in t.mountpoint: continue
        info = psutil.disk_usage(t.mountpoint)
        result.append({
            'name':    'Disk-%s' %t.mountpoint,
            'total':   '%.2f GB' %(info.total/1024.0/1024.0/1024.0),
            'percent': str(info.percent) + '%',
        })
    return result

def getNVIDIA():
    cmd = 'nvidia-smi 2>&1'
    proc = subprocess.Popen(cmd, stdout = subprocess.PIPE, shell = True)
    try:
        outs, errs = str(proc.communicate(timeout = 10)[0]), ''
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, errs = '', 'timeout error'
    except:
        proc.kill()
        outs, errs = '', 'other error'
    NvidiaDriverInfo   = NvidiaDriverInfoRE.findall(outs)
    NvidiaHardwareInfo = NvidiaHardwareInfoRE.findall(outs)
    NvidiaJobInfo      = NvidiaJobInfoRE.findall(outs)
    if NvidiaDriverInfo and NvidiaHardwareInfo and NvidiaJobInfo:
        return {
            'driver': NvidiaDriverInfo[0][1],
            'jobs': mergeDriverJobInfo(NvidiaHardwareInfo, NvidiaJobInfo)
        }
    else:
        return {}

def mergeDriverJobInfo(drivers, jobs):
    p_cpu_t = {}
    tmp = []
    for job in jobs:
        pid   = int(job[1])
        index = job[0]
        p = psutil.Process(pid)
        if not p_cpu_t.get(pid, None): p_cpu_t[pid] = p.cpu_percent(interval = 0.1)
        d = [x for x in drivers if index == x[0]][0]
        tmp.append({
            'name':         pid,
            'cpu':          '%.2f %%' %(p_cpu_t[pid]),
            'memory':       '%.2f GB' %(p.memory_info().rss/1024.0/1024/1024),
            'drivers_name': d[1],
            'drivers_temp': d[3],
            'drivers_pwr':  d[4],
            'drivers_mem':  d[5],
            'drivers_util': d[6],
            'create_time':  datetime.datetime.fromtimestamp(p.create_time()).strftime('%Y%m%d %H:%M:%S'),
        })
    return tmp

def main():
    if len(sys.argv) != 2:
        print("Miss Flag.")
        sys.exit(1)

    while 1:
        try:
            ws = create_connection(sys.argv[1])
            ws.settimeout(3)
        except:
            print("ERROR >> Connection WebSocket Server Error")
            time.sleep(3)
            continue

        try:
            while 1:
                tmp = {
                    'updateTime': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'hostname':   hostname,
                    'hw':         getCPU() + getRAM() + getDISK(),
                    'nvidia':     getNVIDIA()
                }
                ws.send(json.dumps(tmp))
                time.sleep(2)
        except Exception as e:
            print(e)
            print("ERROR >> Send Data To WebSocket Server Error")
            time.sleep(2)
        finally:
            ws.close()

if __name__ == '__main__':
    t = threading.Thread(target = main)
    t.setDaemon(True)
    t.start()
    t.join()