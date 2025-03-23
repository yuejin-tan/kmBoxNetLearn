# AK z | A4 x | A1 c | 
# MAC10 v | MP9 b | PP n | GALI m 

import threading
import time
import socket
import queue
import numpy
import sys
import functools
import datetime
import random
import struct
import kmbox_para
import keyboard
import math
import pickle

from enum import Enum

VERSION_STR = "cs2GunGod V0.2"

# 运行配置
ip = '192.168.2.188'
# ip = '127.0.0.1'
port = 32770
mac = 0xC7FF3CAB
# mac = 0x8147e04e


class Guns(Enum):
    off = 0
    AK = 1
    A4 = 2
    A1 = 3
    MAC10 = 4
    MP9 = 5
    PP = 6
    GALI = 7


moniStop = False
isLearning = False
learnFlg = 0
shootFlg = 0
recoilNo = 0
gAccMax = 40000
gGuns = Guns.AK

gunStartCheatTime = [
    1e6,    # off
    0.15,  # AK
    0.22,  # A4
    0.25,  # A1
    0.15,    # MAC10
    0.15,    # MP9
    0.15,    # PP
    0.22,    # GALI
]
gunRecord = [
    [[numpy.zeros(1), numpy.zeros(1), numpy.zeros(1)]],  # off
    [[numpy.zeros(1), numpy.zeros(1), numpy.zeros(1)]],  # AK
    [[numpy.zeros(1), numpy.zeros(1), numpy.zeros(1)]],  # A4
    [[numpy.zeros(1), numpy.zeros(1), numpy.zeros(1)]],  # A1
    [[numpy.zeros(1), numpy.zeros(1), numpy.zeros(1)]],  # MAC10
    [[numpy.zeros(1), numpy.zeros(1), numpy.zeros(1)]],  # MP9
    [[numpy.zeros(1), numpy.zeros(1), numpy.zeros(1)]],  # PP
    [[numpy.zeros(1), numpy.zeros(1), numpy.zeros(1)]],  # GALI
]

try:
    with open("ak.pkl", "rb") as f:
        gunRecord[Guns.AK.value] = pickle.load(f)
    with open("a4.pkl", "rb") as f:
        gunRecord[Guns.A4.value] = pickle.load(f)
    with open("a1.pkl", "rb") as f:
        gunRecord[Guns.A1.value] = pickle.load(f)
    with open("mac10.pkl", "rb") as f:
        gunRecord[Guns.MAC10.value] = pickle.load(f)
    with open("mp9.pkl", "rb") as f:
        gunRecord[Guns.MP9.value] = pickle.load(f)
    with open("pp.pkl", "rb") as f:
        gunRecord[Guns.PP.value] = pickle.load(f)
    with open("gali.pkl", "rb") as f:
        gunRecord[Guns.GALI.value] = pickle.load(f)
    print("gunRecord read ok")

except Exception as e:
    print("gunRecord not init")
    print(e)


class NTD():
    def __init__(self, aMax, x0, v0):
        self.r = aMax
        self.x = x0
        self.v = v0
        self.a = 0

    def initX(self, x0):
        self.x = x0
        self.v = 0
        self.a = 0

    def calc(self, xTar, dT):
        temp = min(max(-self.x + xTar - self.v*abs(self.v)/self.r*0.5, -1), 1)
        self.a = 0.5*self.a + 0.5 * self.r * temp
        self.v += dT*self.a
        self.x += dT*self.v
        return self.x


class kmboxMgr():
    def __init__(self, ip, port, mac, portMoni):
        self.pkgNo = 0
        self.ip = ip
        self.port = port
        self.mac = mac
        self.portMoni = portMoni

        self.guns = Guns.off

        self.udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_server.settimeout(0.1)

        self.moniSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.moniSocket.setblocking(False)
        self.moniSocket.bind(("", self.portMoni))

        print(datetime.datetime.now().strftime('[%H:%M:%S.%f]')
              + f" init @ ip:{self.ip};port:{self.port};portMoni:{self.portMoni};mac:{hex(self.mac)}")

        # 发送连接包
        self.sendPack(kmbox_para.CMD_connect, 0)

    def __del__(self):
        self.sendPack(kmbox_para.CMD_monitor, 0)
        self.unMaskMK(0, 0)
        self.udp_server.close()
        self.moniSocket.close()

    def sendPack(self, cmd, data1, data2=None):
        self.send_data = struct.pack("<IIII", self.mac, data1, self.pkgNo, cmd)
        if (data2):
            self.send_data += data2

        self.udp_server.sendto(self.send_data,
                               (self.ip, self.port))
        self.pkgNo += 1

        try:
            self.recv_data = self.udp_server.recvfrom(1024)
        except Exception as e:
            print(datetime.datetime.now().strftime(
                '[%H:%M:%S.%f]')+" send echo recv err! "+e.__str__(), file=sys.stderr)
        else:
            if (self.recv_data[0] != self.send_data):
                print(datetime.datetime.now().strftime('[%H:%M:%S.%f]')
                      + " send echo not match!")
                print(self.recv_data[0].hex())
                print(self.recv_data[1])

    def mouseMove(self, x, y):
        data2 = struct.pack("<IiiI", 0, x, y, 0) + 10*struct.pack("<I", 0)
        self.sendPack(kmbox_para.CMD_mouse_move, 0, data2)

    def mouseCtrl(self, x, y, button, wheel):
        data2 = struct.pack("<IiiI", button, x, y, wheel) + \
            10*struct.pack("<I", 0)
        self.sendPack(kmbox_para.CMD_mouse_wheel, 0, data2)

    def unMaskMK(self, mouse, keyBoard):
        self.sendPack(kmbox_para.CMD_unmask_all, mouse+(keyBoard << 8))

    def maskMK(self, mouse, keyBoard):
        self.sendPack(kmbox_para.CMD_mask_mouse, mouse+(keyBoard << 8))

    # 非线性跟踪微分器
    def fhan(self, xTar, x, v, dt):
        return

    def do_run(self):
        global moniStop
        global isLearning
        global learnFlg
        global shootFlg
        global recoilNo
        global gAccMax
        global gGuns

        # 开启轮询
        self.sendPack(kmbox_para.CMD_monitor, self.portMoni | 0xaa550000)
        # 屏蔽滚轮和左键
        # self.maskMK(kmbox_para.MOUSE_WHEEL | kmbox_para.MOUSE_LEFT, 0)
        self.maskMK(kmbox_para.MOUSE_WHEEL, 0)

        # 初始化参数
        self.dx = 0
        self.dy = 0
        self.mbtn = 0
        self.wheel = 0
        self.lpfCoef = 0.1

        self.xx = 0
        self.yy = 0

        self.vx = 0
        self.vy = 0

        self.meandx = 0
        self.meandy = 0

        self.minDt = 2e-3

        tNow = time.time()
        self.tmon = tNow
        self.tlearn = tNow
        self.tshoot = tNow
        self.xxlearn = self.xx
        self.yylearn = self.yy
        self.learnTList = []
        self.learnXList = []
        self.learnYList = []

        while (moniStop == False):
            tNow = time.time()

            # 监控鼠标状况
            cntRead = 0
            while (1):
                try:
                    self.recv_data2 = self.moniSocket.recvfrom(1024)
                    cntRead += 1
                except Exception as e:
                    # 读干净
                    break
                else:
                    # 有状态更新
                    # print(datetime.datetime.now().strftime('[%H:%M:%S.%f]')
                    #       + " moniRecv @ "+str(self.recv_data2[1]))
                    decodeAns = struct.unpack(
                        "<BBhhhBBBBBBBBBBBB", self.recv_data2[0])
                    # print(res[0:5], res[5:])
                    self.mbtn = decodeAns[1]
                    self.dx += decodeAns[2]
                    self.xx += decodeAns[2]
                    self.dy += decodeAns[3]
                    self.yy += decodeAns[3]
                    self.wheel += decodeAns[4]

            self.dt1 = tNow-self.tmon

            if (self.dt1 > self.minDt):
                self.tmon = tNow
                self.vx = (self.dx/self.dt1-self.vx)*self.lpfCoef+self.vx
                self.vy = (self.dy/self.dt1-self.vy)*self.lpfCoef+self.vy

                if (cntRead > 0):
                    self.meandx = self.dx/cntRead
                    self.meandy = self.dy/cntRead

                # print(
                #     f"\rself.vx, self.vy, self.wheel, self.mbtn={self.vx:.2f},{self.vy:.2f},{self.wheel},{self.mbtn}                  ", end="")

                if (self.wheel < 0):
                    self.guns = Guns.off
                    print(f"\r now:{self.guns} globalGun:{gGuns}    ", end="")
                elif (self.wheel > 0):
                    self.guns = gGuns
                    print(f"\r now:{self.guns} globalGun:{gGuns}    ", end="")

                self.dx = 0
                self.dy = 0
                self.wheel = 0

            else:
                # 堆屎，限制cpu占用率
                time.sleep(0.0005)
                continue

            if (isLearning):
                if (self.mbtn & kmbox_para.MOUSE_LEFT):
                    if (learnFlg == 0):
                        self.tlearn = tNow
                        self.xxlearn = self.xx
                        self.yylearn = self.yy
                        self.learnTList.clear()
                        self.learnXList.clear()
                        self.learnYList.clear()
                        learnFlg = 1
                    if (learnFlg == 1):
                        self.learnTList.append(tNow-self.tlearn)
                        self.learnXList.append(self.xx-self.xxlearn)
                        self.learnYList.append(self.yy-self.yylearn)
                else:
                    if (learnFlg == 1):
                        print(self.learnTList)
                        print(self.learnXList)
                        print(self.learnYList)
                        gunRecord[self.guns.value].clear()
                        gunRecord[self.guns.value].append([numpy.array(self.learnTList), numpy.array(
                            self.learnXList), numpy.array(self.learnYList)])
                        learnFlg = 0

            else:
                if (self.mbtn & kmbox_para.MOUSE_LEFT):
                    if (shootFlg == 0):
                        # 开始压枪
                        self.tshoot = tNow
                        self.xxshoot = 0
                        self.yyshoot = 0
                        self.ntdX1 = NTD(gAccMax, 0, 0)
                        self.ntdY1 = NTD(gAccMax, 0, 0)
                        self.randomPhiX = random.uniform(0, 2*math.pi)
                        self.randomPhiY = random.uniform(0, 2*math.pi)
                        self.randomOmegaX = random.uniform(1, 3)*2*math.pi
                        self.randomOmegaY = random.uniform(0.3, 2)*2*math.pi
                        self.randomAmpX = random.uniform(10, 20)
                        self.randomAmpY = random.uniform(5, 10)
                        shootFlg = 1
                    elif (shootFlg == 1):
                        tarT = tNow-self.tshoot
                        tarX = int(self.ntdX1.calc(numpy.interp(
                            tarT, gunRecord[self.guns.value][recoilNo][0], gunRecord[self.guns.value][recoilNo][1] + self.randomAmpX*math.sin(self.randomOmegaX*tarT+self.randomPhiX)), self.dt1))
                        tarY = int(self.ntdY1.calc(numpy.interp(
                            tarT, gunRecord[self.guns.value][recoilNo][0], gunRecord[self.guns.value][recoilNo][2] + self.randomAmpY*math.sin(self.randomOmegaY*tarT+self.randomPhiY)), self.dt1))
                        if (tarT > gunStartCheatTime[self.guns.value]):
                            # 保证点射手感，前面不压枪
                            self.mouseMove(tarX-self.xxshoot,
                                           tarY-self.yyshoot)
                        else:
                            self.tarY0 = tarY
                            # print("1", end="")
                        self.xxshoot = tarX
                        self.yyshoot = tarY
                else:
                    # 松开了，回正
                    if (shootFlg == 1):
                        shootFlg = 2
                        self.ntdY2 = NTD(gAccMax, self.yyshoot, 0)
                        # print(f"yyshoot={self.yyshoot}")
                        # print(f"tarY0={self.tarY0}")

                # 回正步骤是强制进行的
                if (shootFlg == 2):
                    tarY = int(self.ntdY2.calc(self.tarY0, self.dt1))
                    # if (abs(self.ntdY2.v) < 10 or tarT < gunStartCheatTime[self.guns.value]):
                    if (abs(tarY-self.tarY0) < 5 or tarT < gunStartCheatTime[self.guns.value]):
                        # 完事了
                        shootFlg = 0
                        tarY = 0
                    else:
                        self.mouseMove(0, tarY-self.yyshoot)
                        # print("2", end="")
                    self.yyshoot = tarY

            # 退出判定
            if keyboard.is_pressed('enter'):
                moniStop = True
            # 换枪判断
            if keyboard.is_pressed('z'):
                gGuns = Guns.AK
                print(f"\r now:{self.guns} globalGun:{gGuns}    ", end="")
            if keyboard.is_pressed('x'):
                gGuns = Guns.A4
                print(f"\r now:{self.guns} globalGun:{gGuns}    ", end="")
            if keyboard.is_pressed('c'):
                gGuns = Guns.A1
                print(f"\r now:{self.guns} globalGun:{gGuns}    ", end="")
            if keyboard.is_pressed('v'):
                gGuns = Guns.MAC10
                print(f"\r now:{self.guns} globalGun:{gGuns}    ", end="")
            if keyboard.is_pressed('b'):
                gGuns = Guns.MP9
                print(f"\r now:{self.guns} globalGun:{gGuns}    ", end="")
            if keyboard.is_pressed('n'):
                gGuns = Guns.PP
                print(f"\r now:{self.guns} globalGun:{gGuns}    ", end="")
            if keyboard.is_pressed('m'):
                gGuns = Guns.GALI
                print(f"\r now:{self.guns} globalGun:{gGuns}    ", end="")

        # 关闭监控
        self.sendPack(kmbox_para.CMD_monitor, 0)
        # 关闭屏蔽
        self.unMaskMK(0, 0)


# 鼠标控制器
kmbox1 = kmboxMgr(ip, port, mac, port+1)

# 提示字符
print("\n"+datetime.datetime.now().strftime('[%H:%M:%S.%f] ')
      + VERSION_STR+" starTed!\n")

kmbox1.do_run()
