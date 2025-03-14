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

VERSION_STR = "cs2GunGod V0.2"

# 语法提示
if False:
    ip = '127.0.0.1'
    port = 32770
    mac = 0x8147e04e

moniStop = False


class kmboxMgr():
    def __init__(self, ip, port, mac, portMoni):
        self.pkgNo = 0
        self.ip = ip
        self.port = port
        self.mac = mac
        self.portMoni = portMoni

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

    def do_run(self):
        global moniStop

        # 开启轮询
        self.sendPack(kmbox_para.CMD_monitor, self.portMoni | 0xaa550000)

        # 初始化参数
        self.dx = 0
        self.dy = 0
        self.mbtn = 0
        self.wheel = 0

        while (moniStop == False):

            # 监控鼠标状况
            while (1):
                try:
                    self.recv_data2 = self.moniSocket.recvfrom(1024)
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
                    self.mbtn |= decodeAns[1]
                    self.dx += decodeAns[2]
                    self.dy += decodeAns[3]
                    self.wheel += decodeAns[4]

            # 得到结果
            print(f"\rself.dx, self.dy, self.wheel, self.mbtn=",
                  self.dx, self.dy, self.wheel, self.mbtn, "                    ", end="")
            self.dx = 0
            self.dy = 0
            self.mbtn = 0
            self.wheel = 0

            if (self.mbtn & kmbox_para.MOUSE_MID):
                moniStop = True

            time.sleep(0.5)

        # 关闭轮询
        self.sendPack(kmbox_para.CMD_monitor, 0)


# 鼠标控制器
kmbox1 = kmboxMgr(ip, port, mac, port+1)

# 提示字符
print("\n"+datetime.datetime.now().strftime('[%H:%M:%S.%f] ')
      + VERSION_STR+" started!\n")

kmbox1.do_run()
