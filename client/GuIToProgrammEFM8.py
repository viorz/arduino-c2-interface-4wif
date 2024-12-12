from PyQt5 import QtWidgets, uic
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt5.QtCore import QIODevice, QPointF, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QAbstractItemView, QMessageBox
import sys
from time import sleep

from hashlib import new
import serial
import time
import sys
import argparse
from tokenize import String

# class mylogger(object):
# 	def __init__(self, fn='', tofile=False):
# 		self.fn = fn
# 		self.tofile = tofile
# 		return
# 	def printml(self, *args):
# 		toprint = ''
# 		for v in args:
# 			toprint = toprint + str(v) + ' '
# 		if self.tofile:
# 			f = open(self.fn, 'w')
# 			f.write(toprint + "\n")
# 			f.close()
# 		else: print(toprint)
# 		return

# LOGFILE = 'log.txt'
# PRINT_TO_FILE = True
# # создаем экземпляр объекта
# # указываем имя лога и 
# # PRINT_TO_FILE = True - вывод в файл, 
# # иначе - на консоль
# log = mylogger(LOGFILE, PRINT_TO_FILE)

# # переопределяем адрес функции print()
# # на адрес метода нашего логгера
# print = log.printml


class ProgrammingInterface:
  def __init__(self, port, baudrate = 1000000):
    # self.serial.close()
    self.serial = serial.Serial(port, baudrate, timeout = 1)

    # Give Arduino some time
    time.sleep(2)

  def closeSerial(self):
     self.serial.close()

  def openSerial(self):
     self.serial.open()

  def changeSerial(self, port, baudrate = 1000000):
     self.serial.close()
     self.serial = serial.Serial(port, baudrate, timeout = 1)

  def getReadRequest(slef, address, amount):
    return [
        0x05, 0x05,
        amount,
        (address >> 16) & 0xFF,
        (address >> 8) & 0xFF,
        address & 0xFF,
        0x00,
    ]
  
  def initialize(self):
    done = False
    while not done:
      try:
        self.serial.read_all()
        self.serial.write(b"\x01\x00")
        result = self.serial.read(1)
        if result != b"\x81": print("Error: ", result)
        assert result == b"\x81"
        done = True
      except:
        print("Error: Could not establish connection - try resetting your Arduino")
        msg = QMessageBox()
        msg.setWindowTitle("Error")
        msg.setText("Could not establish connection - try resetting your Arduino")
        msg.setIcon(QMessageBox.Warning)

        msg.exec_()
        sys.exit(1)

    print("Connected to interface")
    return True

  def read(self, file, start=0x00, size=0x3FFF, chunksize=0x10):
    self.serial.read_all()
    for address in range(start, start + size, chunksize):
      # Write request and wait for response
      request = self.getReadRequest(address, chunksize)
      self.serial.write(request)

      # Response has to be at least 2 bytes long, otherwise something went wrong
      response = self.serial.read(chunksize + 1)
      if len(response) > 1:
        status = response[0]
        body = response[1:]

        print("===============================================")
        print("address: %s" % hex(address))
        print("request: %s" % bytes(request).hex())
        print("response code: %s" % hex(status))
        print("response body: %s" % body.hex())

        line = bytearray([chunksize, (address >> 8) & 0xFF, address & 0xFF, 0x00]) + body
        crc = 0
        for nextbyte in line:
            crc = crc + nextbyte

        crc = (~crc + 1) & 0xFF
        line.append(crc)
        file.write(":%s\n" % line.hex())

      else:
        break
    return True

  def sendValue(self, value):
    self.serial.read_all()
    b = bytearray()
    print("b", b)
    b.extend(map(ord, value))
    self.serial.write(b)

  def sendValueMotor(self, mode, value):
    self.serial.read_all()
    if mode == "dShot":
      self.serial.write(b"\x0D")
    elif mode == "PWM":
      self.serial.write(b"\x0C")
    num = len(value)
    b = num.to_bytes(1, 'big')
    self.serial.write(b)
    b = bytearray()
    b.extend(map(ord, value))
    self.serial.write(b)
    print("send b ", b)
    print(self.serial.read(1))
    
    # print(self.serial.read(1))
    # print(self.serial.read(1))
    # print(self.serial.read(1))
    # print(self.serial.read(1))
    # print(self.serial.read(1))
    # print(self.serial.read(1))
    # print(self.serial.read(1))
    # print(int.from_bytes(self.serial.read_all(), "big"))
  
  def setC2Mode(self):
    self.serial.read_all()
    self.serial.write(b"\x0F\x00")
    rxdataa = self.serial.read(1)
    print("C2 mode ", rxdataa)
    # assert rxdataa == b"\x89"
    if rxdataa != b"\x90": return False
    print("C2 mode is enable")
    return True

  def setDShotMode(self):
    self.serial.read_all()
    self.serial.write(b"\x0B\x00")
    rxdataa = self.serial.read(1)
    print("dShot mode is set ", rxdataa)
    # assert rxdataa == b"\x02"
    if rxdataa != b"\x92": return False
    return True

  def setPWMMode(self):
    self.serial.read_all()
    self.serial.write(b"\x0A\x00")
    rxdataa = self.serial.read(1)
    print("PWM mode is set ", rxdataa)
    # assert rxdataa == b"\x03"
    if rxdataa != b"\x91": return False
    return True
  
  def changeClk(self, i):
    self.serial.read_all()
    self.serial.write(b"\x09\x01")
    iList = bytes([i])
    self.serial.write(iList)
    rxdataa = self.serial.read(1)
    print("Change CLK pin ", rxdataa)
    # assert rxdataa == b"\x89"
    if rxdataa != b"\x89": return False
    iChange = self.serial.read(1)
    print("Clk is set to", iChange)
    return True

  def erase(self):
    self.serial.read_all()
    self.serial.write(b"\x04\x00")
    # assert self.serial.read(1) == b"\x84"
    if self.serial.read(1) != b"\x84": return False
    print("Device erased")
    return True

  def reset(self):
    self.serial.read_all()
    self.serial.write(b"\x02\x00")
    # assert self.serial.read(1) == b"\x82"
    if self.serial.read(1) != b"\x82": return False
    return True

  def write(self, file):
    self.serial.read_all()
    lines = file.readlines()
    for line in lines:
      # assert line[0] == ":"
      if line[0] != ":": return False
      if line[7:9] != "00":
        continue

      length = int(line[1:3], 16)
      # assert length + 4 < 256
      if length + 4 >= 256: return False

      addressHi = int(line[3:5], 16)
      addressLo = int(line[5:7], 16)
      data = bytearray.fromhex(line[9 : 9 + length * 2])
      # assert len(data) == length
      if len(data) != length: return False
      crc = addressHi + addressLo
      for i in range(len(data)):
        crc += data[i]
      crc = crc & 0xFF
      print(
        "0x{:04X}, Bytes: {:02X}, Data: {}".format(
          (addressLo + (addressHi << 8)), len(data), data.hex()
        )
      )
      self.serial.write([0x3, len(data) + 5, len(data), 0, addressHi, addressLo, crc])
      self.serial.write(data)
      response = self.serial.read(1)
      if response != b"\x83":
          print("Error: Failed writing data: ", response)
          return None
    self.reset()
    return True


  def deviceInfo(self):
    self.serial.read_all()
    self.serial.write(b"\x08\x00")
    # assert self.serial.read(1) == b"\x88"
    if self.serial.read(1) != b"\x88": return False
    deviceId = self.serial.read(1)
    revision = self.serial.read(1)
    print("Device:   0x%s" % deviceId.hex())
    print("Revision: 0x%s" % revision.hex())
    return True


# # __________________PROGRAMM:__________________

# def run(action, destination, port):
# #   parser = argparse.ArgumentParser(description='Interact with the Arduino based EFM8 C2 interface')
# #   parser.add_argument('action', metavar='ACTION', type=str,
# #                       help='Action to perform: read, write or erase',
# #                       choices=['read', 'write', 'erase', 'info'],)
# #   parser.add_argument('port', metavar='PORT', type=str,
# #                       help='Port to use')
# #   parser.add_argument('destination', metavar='DESTINATION', type=str, nargs='?', default=None,
# #                       help='Destination to write to or read from')
# #   #parser.add_argument('-m', '--mcu', type=str, default='BB2', choices=['BB1', 'BB2', 'BB51'],
# #   #                    help='MCU - important to read full space, including bootloader')

# #   args = parser.parse_args()
#   interface = ProgrammingInterface(port)
#   string_status = {0:"Succes",1:"Succes",2:"Succes",3:"Succes"}

#   if interface.setC2Mode():
#     for i in range(4):
#       if not interface.changeClk(i):
#         string_status[i] = "Arduino can not change CLK"
#         continue
#       if not interface.reset():
#         string_status[i] = "Arduino can not reset mc"
#         continue
#       if not interface.initialize():
#         string_status[i] = "Arduino can not initialize mc"
#         continue
#       if not interface.deviceInfo():
#         string_status[i] = "Arduino can not send device Info"
#         continue
      
#       if action == 'read':

#         file = open(destination + str(i) + ".hex", "w")

#         # Fetch the flash segment
#         if not interface.read(file, 0, 0x3FFF):
#           string_status[i] = "Arduino can not read mc"
#           continue

#         # Reading the bootloader on BB51 does not seem to bepossible since we are not
#         # getting a response from this address space
#         # TODO: Fetch the bootloader on BB51
#         # if args.mcu == 'BB51':
#         #  interface.read(file, 0xF000, 0x0800)

#         file.write(":00000001FF\n")

#       if action == 'erase':
#         if not interface.erase():
#           string_status[i] = "Arduino can not erase mc"
#           continue

#       if action == 'write':
#         file = open(destination, "r")

#         # for i in range(4):
#         if not interface.erase():
#           string_status[i] = "Arduino can not erase mc"
#         if not interface.write(file):
#           string_status[i] = "Arduino can not programm mc"
#   else:
#     interface.closeSerial()
#     string_status = {0:"Arduino not answered right",1:"Arduino not answered right",2:"Arduino not answered right",3:"Arduino not answered right"}
#     return string_status
#   print("interface.reset()",interface.reset())
#   interface.closeSerial()
#   return string_status

# def startMotor(mode, value, port):
#   interface = ProgrammingInterface(port)
#   if mode == "dShot":
#      interface.setDShotMode()
#   elif mode == "PWM":
#      interface.setPWMMode()
  
#   print("sleep start")
#   sleep(4)
#   print("sleep stop")
  
#   interface.sendValue(value)
#   interface.closeSerial()

# def stopMotor(port):
#   interface = ProgrammingInterface(port)
#   print("sleep start")
#   sleep(1)
#   print("sleep stop")
#   interface.closeSerial()




class ApplicationWindow(QtWidgets.QMainWindow):
    
    serialRxBufer = ""

    def __init__(self, *args, **kwargs):
      super(ApplicationWindow, self).__init__(*args, **kwargs)
      self.ui = uic.loadUi("GuIToProgrammEFM8.ui", self)
      self.ui.setWindowTitle("GuIToProgrammEFM8")
      # self.ui.setGeometry(300, 250, 1000, 1200)

      parametersApp = {}
      #Serial port:
      # serial = QSerialPort()
      # serial.setBaudRate(1000000)
      portList = []
      ports = QSerialPortInfo.availablePorts()
      for port in ports:
          portList.append(port.portName())
          if port.description() == "Arduino Uno":
              parametersApp["port"] = port.portName()
          if port.description() == "USB-SERIAL CH340":
              parametersApp["port"] = port.portName()
      self.ui.comboBox.addItems(portList)

      #Read parameters from file
      f = open("save.txt", "r")
      stringF = f.readlines()
      f.close()
      for S in stringF:
          newS = S.split(":", 1)
          if newS[0] == "port":
              if parametersApp.get("port") == None:
                parametersApp[newS[0]] = newS[1].strip("\n ")
          else:
              parametersApp[newS[0]] = newS[1].strip("\n ")

      # if parametersApp.get("port") != None:
      if parametersApp.get("port") in portList:
          for i in range(len(portList)):
              if portList[i] == parametersApp.get("port"):
                  self.ui.comboBox.setCurrentIndex(self.ui.comboBox.findText(parametersApp.get("port")))
      if parametersApp.get("mode") == "dShot":
          self.ui.radioButton_dShot.setChecked(True)
      elif parametersApp.get("mode") == "PWM":
          self.ui.radioButton_PWM.setChecked(True)
      self.ui.spinBox_dShot.setValue(int(parametersApp.get("dShot")))
      self.ui.spinBox_PWM.setValue(int(parametersApp.get("PWM")))
      self.ui.horizontalSlider_dShot.setValue(int(parametersApp.get("dShot")))
      self.ui.horizontalSlider_PWM.setValue(int(parametersApp.get("PWM")))
      self.ui.lineEdit.setText(parametersApp.get("name"))

      self.interface = ProgrammingInterface(parametersApp.get("port"))


      # def onRead():
      #     rx = serial.readAll()
      #     rxs = str(rx, 'utf-8')
      #     serialRxBufer = serialRxBufer + rxs
      #     print("rx",rx)
      #     print("rxs",rxs)

      
      # __________________PROGRAMM:__________________

      def run(action, destination, port):
      #   parser = argparse.ArgumentParser(description='Interact with the Arduino based EFM8 C2 interface')
      #   parser.add_argument('action', metavar='ACTION', type=str,
      #                       help='Action to perform: read, write or erase',
      #                       choices=['read', 'write', 'erase', 'info'],)
      #   parser.add_argument('port', metavar='PORT', type=str,
      #                       help='Port to use')
      #   parser.add_argument('destination', metavar='DESTINATION', type=str, nargs='?', default=None,
      #                       help='Destination to write to or read from')
      #   #parser.add_argument('-m', '--mcu', type=str, default='BB2', choices=['BB1', 'BB2', 'BB51'],
      #   #                    help='MCU - important to read full space, including bootloader')

      #   args = parser.parse_args()
        # interface = ProgrammingInterface(port)
        string_status = {0:"Succes",1:"Succes",2:"Succes",3:"Succes"}

        if self.interface.setC2Mode():
          for i in range(4):
            if not self.interface.changeClk(i):
              string_status[i] = "Arduino can not change CLK"
              continue
            if not self.interface.reset():
              string_status[i] = "Arduino can not reset mc"
              continue
            if not self.interface.initialize():
              string_status[i] = "Arduino can not initialize mc"
              continue
            if not self.interface.deviceInfo():
              string_status[i] = "Arduino can not send device Info"
              continue
            
            if action == 'read':

              file = open(destination + str(i) + ".hex", "w")

              # Fetch the flash segment
              if not self.interface.read(file, 0, 0x3FFF):
                string_status[i] = "Arduino can not read mc"
                continue

              # Reading the bootloader on BB51 does not seem to bepossible since we are not
              # getting a response from this address space
              # TODO: Fetch the bootloader on BB51
              # if args.mcu == 'BB51':
              #  interface.read(file, 0xF000, 0x0800)

              file.write(":00000001FF\n")

            if action == 'erase':
              if not self.interface.erase():
                string_status[i] = "Arduino can not erase mc"
                continue

            if action == 'write':
              file = open(destination, "r")

              # for i in range(4):
              if not self.interface.erase():
                string_status[i] = "Arduino can not erase mc"
              if not self.interface.write(file):
                string_status[i] = "Arduino can not programm mc"
        else:
          # self.interface.closeSerial()
          string_status = {0:"Arduino not answered right",1:"Arduino not answered right",2:"Arduino not answered right",3:"Arduino not answered right"}
          onPushButton_reset()
          return string_status
        print("interface.reset()",self.interface.reset())
        # self.interface.closeSerial()
        succes_prgrm = True
        for i in range(4):
          if string_status[i] != "Succes":
            succes_prgrm = False
        # if not succes_prgrm:
        #   onPushButton_reset()
        return string_status

      def setModeMotor(mode):
        if mode == "dShot":
          self.interface.setDShotMode()
        elif mode == "PWM":
          self.interface.setPWMMode()

      def startMotor(mode, value):
        # if mode == "dShot":
        #   self.interface.setDShotMode()
        # elif mode == "PWM":
        #   self.interface.setPWMMode()
        # sleep(1)
        self.interface.sendValueMotor(mode, value)

      def stopMotor(mode):
        if mode == "dShot":
          self.interface.sendValueMotor(mode, "0")
        elif mode == "PWM":
          self.interface.sendValueMotor(mode, "0")



      def onPushButton_change():
          parametersApp["name"] = self.ui.lineEdit.text()
          parametersApp["port"] = self.ui.comboBox.currentText()
          parametersApp["dShot"] = str(self.ui.spinBox_dShot.value())
          parametersApp["PWM"] = str(self.ui.spinBox_PWM.value())
          if self.ui.radioButton_dShot.isChecked():
              parametersApp["mode"] = "dShot"
          else: parametersApp["mode"] = "PWM"
          self.interface.changeSerial(parametersApp["port"])
          setModeMotor(parametersApp.get("mode"))
          # self.interface.__init__(parametersApp["port"])
          # serial.setPortName(self.ui.comboBox.currentText())
          # # serial.open(QIODevice.ReadWrite)
          # print("serial.open",serial.open(QIODevice.ReadOnly))


      def onPushButton_save():
          f = open("save.txt", "w")
          newS = ""
          for s in parametersApp:
              newS = newS + s + ": "+ parametersApp[s] + "\n"
          f.write(newS)
          f.close()
          # # serial.close()
          # print("serial.close",serial.close())

      def onPushButton_reset():
          self.interface.closeSerial()
          print("serial.close")
          self.interface.openSerial()
          print("serial.open")
          sleep(2)
          setModeMotor(parametersApp.get("mode"))

      def onPushButton_1():
          self.ui.label_1.setText("Прошивка")
          self.ui.label_1.setStyleSheet("background-color: yellow; border: 1px solid black;")
          self.ui.label_2.setText("Прошивка")
          self.ui.label_2.setStyleSheet("background-color: yellow; border: 1px solid black;")
          self.ui.label_3.setText("Прошивка")
          self.ui.label_3.setStyleSheet("background-color: yellow; border: 1px solid black;")
          self.ui.label_4.setText("Прошивка")
          self.ui.label_4.setStyleSheet("background-color: yellow; border: 1px solid black;")
          print("onPushButton_1")
          sleep(0.001)
          status = run(action = "write", destination = parametersApp.get("name"), port = parametersApp.get("port"))
          print(status)
          if status.get(0) == "Succes":
              self.ui.label_1.setText("Прошито")
              self.ui.label_1.setStyleSheet("background-color: green; border: 1px solid black;")
          else:
              self.ui.label_1.setText("Проблема")
              self.ui.label_1.setStyleSheet("background-color: red; border: 1px solid black;") 
          if status.get(1) == "Succes":
              self.ui.label_2.setText("Прошито")
              self.ui.label_2.setStyleSheet("background-color: green; border: 1px solid black;")
          else:
              self.ui.label_2.setText("Проблема")
              self.ui.label_2.setStyleSheet("background-color: red; border: 1px solid black;") 
          if status.get(2) == "Succes":
              self.ui.label_3.setText("Прошито")
              self.ui.label_3.setStyleSheet("background-color: green; border: 1px solid black;")
          else:
              self.ui.label_3.setText("Проблема")
              self.ui.label_3.setStyleSheet("background-color: red; border: 1px solid black;") 
          if status.get(3) == "Succes":
              self.ui.label_4.setText("Прошито")
              self.ui.label_4.setStyleSheet("background-color: green; border: 1px solid black;")
          else:
              self.ui.label_4.setText("Проблема")
              self.ui.label_4.setStyleSheet("background-color: red; border: 1px solid black;") 
          setModeMotor(parametersApp.get("mode"))


      def onPushButton_2():
          if self.ui.pushButton_2.isChecked():
              print("onPushButton_2: ", parametersApp.get("mode"), "  ", parametersApp.get(parametersApp.get("mode")))
              setModeMotor(parametersApp.get("mode"))
              startMotor(parametersApp.get("mode"), parametersApp.get(parametersApp.get("mode")))
          else:
              print("offPushButton_2: ", parametersApp.get("mode"))
              stopMotor(parametersApp.get("mode"))

      def changeSpinBox_dShot():
          self.ui.horizontalSlider_dShot.setValue(self.ui.spinBox_dShot.value())

      def changeSpinBox_PWM():
          self.ui.horizontalSlider_PWM.setValue(self.ui.spinBox_PWM.value())

      def changehorizontalSlider_dShot():
          self.ui.spinBox_dShot.setValue(self.ui.horizontalSlider_dShot.value())

      def changehorizontalSlider_PWM():
          self.ui.spinBox_PWM.setValue(self.ui.horizontalSlider_PWM.value())

      # serial.readyRead.connect(onRead)
      self.ui.pushButton_change.clicked.connect(onPushButton_change)
      self.ui.pushButton_save.clicked.connect(onPushButton_save)
      self.ui.pushButton_reset.clicked.connect(onPushButton_reset)
      self.ui.pushButton_1.clicked.connect(onPushButton_1)
      self.ui.pushButton_2.clicked.connect(onPushButton_2)
      
      self.ui.spinBox_dShot.valueChanged.connect(changeSpinBox_dShot)
      self.ui.spinBox_PWM.valueChanged.connect(changeSpinBox_PWM)
      self.ui.horizontalSlider_dShot.valueChanged.connect(changehorizontalSlider_dShot)
      self.ui.horizontalSlider_PWM.valueChanged.connect(changehorizontalSlider_PWM)

      setModeMotor(parametersApp.get("mode"))

        




























def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("Oбнаружена ошибка !:", tb)
#    QtWidgets.QApplication.quit()             # !!! если вы хотите, чтобы событие завершилось




if __name__ == "__main__":
    # Check whether there is already a running QApplication (e.g., if running
    # from an IDE).
    qapp = QtWidgets.QApplication.instance()
    if not qapp:
        qapp = QtWidgets.QApplication(sys.argv)

    app = ApplicationWindow()
    app.show()
    app.activateWindow()
    app.raise_()
    qapp.exec()
