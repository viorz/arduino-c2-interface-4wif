from hashlib import new
import serial
import time
import sys
import argparse
from tokenize import String

class ProgrammingInterface:
  def __init__(self, port, baudrate = 1000000):
    self.serial = serial.Serial(port, baudrate, timeout = 1)

    # Give Arduino some time
    time.sleep(2)

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
        self.serial.write(b"\x01\x00")
        result = self.serial.read(1)
        if result != b"\x81": print("Error: ", result)
        assert result == b"\x81"
        done = True
      except:
        print("Error: Could not establish connection - try resetting your Arduino")
        sys.exit(1)

    print("Connected to interface")
    return True

  def read(self, file, start=0x00, size=0x3FFF, chunksize=0x10):
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

  def setC2Mode(self):
    self.serial.write(b"\x01")
    rxdataa = self.serial.read(1)
    print("C2 mode is set ", rxdataa)
    # assert rxdataa == b"\x01"
    if rxdataa != b"\x01": return False
    return True
  
  def changeClk(self, i):
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
    self.serial.write(b"\x04\x00")
    # assert self.serial.read(1) == b"\x84"
    if self.serial.read(1) != b"\x84": return False
    print("Device erased")
    return True

  def reset(self):
    self.serial.write(b"\x02\x00")
    # assert self.serial.read(1) == b"\x82"
    if self.serial.read(1) != b"\x82": return False
    return True

  def write(self, file):
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
          print("Error: Failed writing data")
          return None
    return True

    self.reset()

  def deviceInfo(self):
    self.serial.write(b"\x08\x00")
    # assert self.serial.read(1) == b"\x88"
    if self.serial.read(1) != b"\x88": return False
    deviceId = self.serial.read(1)
    revision = self.serial.read(1)
    print("Device:   0x%s" % deviceId.hex())
    print("Revision: 0x%s" % revision.hex())
    return True


# __________________PROGRAMM:__________________

def run():
  parser = argparse.ArgumentParser(description='Interact with the Arduino based EFM8 C2 interface')
  parser.add_argument('action', metavar='ACTION', type=str,
                      help='Action to perform: read, write or erase',
                      choices=['read', 'write', 'erase', 'info'],)
  parser.add_argument('port', metavar='PORT', type=str,
                      help='Port to use')
  parser.add_argument('destination', metavar='DESTINATION', type=str, nargs='?', default=None,
                      help='Destination to write to or read from')
  #parser.add_argument('-m', '--mcu', type=str, default='BB2', choices=['BB1', 'BB2', 'BB51'],
  #                    help='MCU - important to read full space, including bootloader')

  args = parser.parse_args()
  interface = ProgrammingInterface(args.port)

  string_status = {0:"Succes",1:"Succes",2:"Succes",3:"Succes"}
  # status = True
  if interface.setC2Mode():
    for i in range(4):
      if not interface.changeClk(i):
        string_status[i] = "Arduino can not change CLK"
        continue
      if not interface.reset():
        string_status[i] = "Arduino can not reset mc"
        continue
      if not interface.initialize():
        string_status[i] = "Arduino can not initialize mc"
        continue
      if not interface.deviceInfo():
        string_status[i] = "Arduino can not send device Info"
        continue

      if args.action == 'read':
        if not args.destination:
          parser.print_usage()
          parser.exit()

        file = open(args.destination + str(i) + ".hex", "w")

        # Fetch the flash segment
        if not interface.read(file, 0, 0x3FFF):
          string_status[i] = "Arduino can not read mc"
          continue

        # Reading the bootloader on BB51 does not seem to bepossible since we are not
        # getting a response from this address space
        # TODO: Fetch the bootloader on BB51
        # if args.mcu == 'BB51':
        #  interface.read(file, 0xF000, 0x0800)

        file.write(":00000001FF\n")

      if args.action == 'erase':
        if not interface.erase():
          string_status[i] = "Arduino can not erase mc"
          continue

      if args.action == 'write':
        if not args.destination:
          parser.print_usage()
          parser.exit()

        file = open(args.destination, "r")

        # for i in range(4):
        if not interface.erase():
          string_status[i] = "Arduino can not erase mc"
        if not interface.write(file):
          string_status[i] = "Arduino can not programm mc"
  else:
    status = False
    string_status = {0:"Arduino not answered right",1:"Arduino not answered right",2:"Arduino not answered right",3:"Arduino not answered right"}
    return string_status
  return string_status

if __name__ == "__main__":
  status =  run()
  print(status)