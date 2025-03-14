import threading
import time
import socket
import queue
import numpy
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
import functools
import datetime
import random
import struct
import kmbox_para

import cs2GG_ui

VERSION_STR = "cs2GunGod V0.1"

# 语法提示
if False:
    ip = '127.0.0.1'
    port = 32770
    mac = 0x8147e04e

moniStop = False

lock1 = threading.Lock()
recv = queue.Queue()


def minitorThread(port):
    global moniStop

    moniSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    moniSocket.settimeout(1)
    moniSocket.bind(("", port))

    recv_data = None

    while (moniStop == False):
        try:
            recv_data = moniSocket.recvfrom(1024)

        except Exception as e:
            if (moniStop == False):
                print(datetime.datetime.now().strftime(
                    '[%H:%M:%S.%f]')+" moni recv err! "+e.__str__(), file=sys.stderr)

        else:
            print(datetime.datetime.now().strftime('[%H:%M:%S.%f]')
                  + " moniRecv @ "+str(recv_data[1]))
            res=struct.unpack("<BBhhhBBBBBBBBBBBB", recv_data[0])
            print(res[0:5],res[5:])

    moniSocket.close()


class kmboxSendMgr():
    def __init__(self, ip, port, mac):
        self.pkgNo = 0
        self.ip = ip
        self.port = port
        self.mac = mac

        self.moniThread = None

        self.udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.udp_server.bind(("", self.port))
        self.udp_server.settimeout(0.1)

        print(datetime.datetime.now().strftime('[%H:%M:%S.%f]')
              + f" init @ ip:{ip};port:{port};mac:{hex(mac)}")

        # 发送连接包
        self.sendPack(kmbox_para.CMD_connect, 0)

    def __del__(self):
        self.udp_server.close()

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

    def monitorCtrl(self, port):
        global moniStop

        if (port > 0):
            self.sendPack(kmbox_para.CMD_monitor, port | 0xaa550000)
            if (self.moniThread):
                moniStop = True
                self.moniThread.join()
                self.moniThread = None

            moniStop = False
            self.moniThread = threading.Thread(
                target=minitorThread, args=(port,))
            self.moniThread.start()

        else:
            self.sendPack(kmbox_para.CMD_monitor, port)
            if (self.moniThread):
                moniStop = True
                self.moniThread.join()
                self.moniThread = None

    def unMaskMK(self, mouse, keyBoard):
        self.sendPack(kmbox_para.CMD_unmask_all, mouse+(keyBoard << 8))

    def maskMK(self, mouse, keyBoard):
        self.sendPack(kmbox_para.CMD_mask_mouse, mouse+(keyBoard << 8))


class mainWindow(QtWidgets.QMainWindow, cs2GG_ui.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.setWindowTitle(VERSION_STR)

        self.actioncs2GunGod.triggered.connect(functools.partial(
            QtWidgets.QMessageBox.aboutQt, None, "about "+VERSION_STR))

        self.statusBar().showMessage(VERSION_STR, 2000)

        # self.pushButton_fft.clicked.connect(self.fftSlot)

    def timerSlot(self):
        pass


############## main ##############
if __name__ == "__main__":
    # 窗口
    app = QtWidgets.QApplication(sys.argv)
    fontx = QtGui.QFont()
    fontx.setPixelSize(14)
    app.setFont(fontx)

    w = mainWindow()
    w.show()

    # 鼠标控制器
    kmbox1 = kmboxSendMgr(ip, port, mac)

    # 提示字符
    print("\n"+datetime.datetime.now().strftime('[%H:%M:%S.%f] ')
          + VERSION_STR+" started!\n")
