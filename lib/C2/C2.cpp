/**
 * C2 implementation according to SiLabs Application Note 127:
 * https://www.silabs.com/documents/public/application-notes/AN127.pdf
 */

#include "C2.h"
#include "../../src/arduino_dshot.h"

C2::C2(volatile uint8_t *port, volatile uint8_t *ddr, volatile uint8_t *pin, uint8_t pinCk, uint8_t pinD, uint8_t pinLed) {
  _port = port;
  _ddr = ddr;
  _pin = pin;

  _pinCk_num = 0;
  _pinCk = pinCk;
  _pinD = pinD;
  _pinLed = pinLed;

  device.id = 0x00;
  device.revision = 0x00;
}

void C2::setup() {
  // Serial.begin(1000000);

  *_ddr = 0x00 | (1 << _pinD) | (1 << _pinCk);
  *_port = 0x00 | (1 << _pinCk);
  
  pinMode(_pinLed, OUTPUT);
  digitalWrite(_pinLed, LOW);
}

/**
 * Programming interface initialization sequence
 *
 * Page 15
 */
void C2::init() {
  reset();

  // Enable programming
  writeAddress(FPCTL);
  writeData(0x02);
  if (flag_error_comunication) return;
  writeData(0x04);
  if (flag_error_comunication) return;
  writeData(0x01);
  if (flag_error_comunication) return;

  // Wait at lesat 20ms
  delayMicroseconds(30);
}

/**
 * Device reset
 *
 * Page 10
 */
void C2::reset() {
  // Force CK LOW for at least 20us
  *_port &= ~(1 << _pinCk);
  delayMicroseconds(30);

  //Force CK HIGH
  *_port |= (1 << _pinCk);

  // Wait at least 2us
  delayMicroseconds(5);
}

void C2::deviceInfo() {
  writeAddress(C2Addresses::DEVICEID);
  device.id = readData();
  if (flag_error_comunication) return;

  writeAddress(C2Addresses::REVID);
  device.revision = readData();
  if (flag_error_comunication) return;
}

void C2::writeAddress(uint8_t address) {
  sendAddressWriteInstruction();
  sendByte(address);
  sendStopBit();
}

void C2::writeSfr(uint8_t address, uint8_t data) {
  writeAddress(address);
  writeData(data);
  if (flag_error_comunication) return;
}

uint8_t C2::readBits(uint8_t length) {
  uint8_t mask = 0x01 << (length - 1);
  uint8_t data = 0;

  *_ddr &= ~(1 << _pinD);
  *_pin &= (1 << _pinD);
  for (uint8_t i = 0; i < length; i += 1) {
    clockPulse();

    data >>= 1;
    if (*_pin & (1 << _pinD)) {
      data = data | mask;
    }
  }
  *_ddr |= (1 << _pinD);

  return data;
}

void C2::sendStopBit() {
  sendBits(0x00, 1);
}

void C2::sendAddressReadInstruction() {
  uint8_t data = 0x00 | (0x00 << 0) | (ADDRESS_READ << 1);
  sendBits(data, 3);
}

void C2::sendDataReadInstruction(uint8_t byte) {
  uint8_t data = 0x00 | (0x00 << 0) | (DATA_READ << 1) | ((byte - 1) << 3);
  sendBits(data, 5);
}

void C2::sendAddressWriteInstruction() {
  uint8_t data = 0x00 | (0x00 << 0) | (ADDRESS_WRITE << 1);
  sendBits(data, 3);
}

void C2::sendDataWriteInstruction(uint8_t byte) {
  uint8_t data = 0x00 | (0x00 << 0) | (DATA_WRITE << 1) | ((byte - 1) << 3);
  sendBits(data, 5);
}

void C2::sendBits(uint8_t data, uint8_t length) {
  for(uint8_t i = 0; i < length; i += 1) {
    if(data >> i & 0x01) {
      *_port |= (1 << _pinD);
    } else {
      *_port &= ~(1 << _pinD);
    }

    clockPulse();
  }
}

/**
 * Clock strobe
 *
 * Page 10
 */
void C2::clockPulse() {
  noInterrupts();

  // Force low for 80ns - 5000ns
  *_port &= ~(1 << _pinCk);
  delayMicroseconds(2);

  // Force high for at least 120ns
  *_port |= (1 << _pinCk);

  interrupts();
}

uint8_t C2::readByte() {
  return readBits(8);
}

void C2::sendByte(uint8_t byte) {
  sendBits(byte, 8);
}

uint8_t C2::readAddress() {
  sendAddressReadInstruction();
  uint8_t retval = readByte();
  sendStopBit();

  return retval;
}

void C2::writeData(uint8_t data) {
  sendDataWriteInstruction(1);
  sendByte(data);
  unsigned long startTime = millis();
  while (readBits(1) == 0) {
    if (millis() - startTime >= 100) {
      flag_error_comunication = true;
      return;
    }
  }
  sendStopBit();
}

/**
 * Response for the C2 interface is indicated by a one bit after an arbitary number
 * of 0 bits. The next 8 bit after the first one are the response byte.
 */
uint8_t C2::waitForResponse() {
  unsigned long startTime = millis();
  while(readBits(1) == 0) {
    if (millis() - startTime >= 100) {
      flag_error_comunication = true;
      return 0;
    }
  }
  return readBits(8);
}

uint8_t C2::readData() {
  sendDataReadInstruction(1);
  uint8_t response = waitForResponse();
  if (flag_error_comunication) return 0;
  sendStopBit();

  return response;
}

uint8_t C2::pollBitHigh(uint8_t mask) {
  uint8_t retval;

  unsigned long startTime = millis();
  do {
    if (millis() - startTime >= 100) {
      flag_error_comunication = true;
      break;
    }
    retval = readAddress();
  } while ((retval & mask) == 0);

  return retval;
}

uint8_t C2::pollBitLow(uint8_t mask) {
  uint8_t retval;

  unsigned long startTime = millis();
  do {
    if (millis() - startTime >= 100) {
      flag_error_comunication = true;
      break;
    }
    retval = readAddress();
  } while (retval & mask);

  return retval;
}

uint8_t C2::readFlashBlock(uint16_t address, uint8_t *data, uint8_t bytes) {
  writeAddress(C2Addresses::FPDAT);
  writeData(BLOCK_READ);
  if (flag_error_comunication) return 0;

  pollBitLow(_inBusy);
  if (flag_error_comunication) return 0;
  pollBitHigh(_outReady);
  if (flag_error_comunication) return 0;

  uint8_t value = readData();
  if (flag_error_comunication) return 0;
  if(value != 0x0D) {
    return EXIT_FAILURE;
  }

  // Write high byte of address
  writeData(address >> 8);
  if (flag_error_comunication) return 0;
  pollBitLow(_inBusy);
  if (flag_error_comunication) return 0;

  // Write low byte of address
  writeData(address & 0xFF);
  if (flag_error_comunication) return 0;
  pollBitLow(_inBusy);
  if (flag_error_comunication) return 0;

  writeData(bytes);
  if (flag_error_comunication) return 0;
  pollBitLow(_inBusy);
  if (flag_error_comunication) return 0;
  pollBitHigh(_outReady);
  if (flag_error_comunication) return 0;

  readData();
  if (flag_error_comunication) return 0;

  for(uint8_t i = 0; i < bytes; i += 1) {
    pollBitHigh(_outReady);
  if (flag_error_comunication) return 0;
    data[i] = readData();
    if (flag_error_comunication) return 0;
  }

  return EXIT_SUCCESS;
}

uint8_t C2::writeFlashBlock(uint16_t address, uint8_t *data, uint8_t length) {
  writeAddress(FPDAT);
  writeData(BLOCK_WRITE);
  if (flag_error_comunication) return 0;

  pollBitLow(_inBusy);
  if (flag_error_comunication) return 0;
  pollBitHigh(_outReady);
  if (flag_error_comunication) return 0;

  uint8_t value = readData();
  if (flag_error_comunication) return 0;
  if(value != 0x0D) {
    return EXIT_FAILURE;
  }

  // Write high byte of address
  writeData(address >> 8);
  if (flag_error_comunication) return 0;
  pollBitLow(_inBusy);
  if (flag_error_comunication) return 0;

  // Write low byte of address
  writeData(address & 0xFF);
  if (flag_error_comunication) return 0;
  pollBitLow(_inBusy);
  if (flag_error_comunication) return 0;

  writeData(length);
  if (flag_error_comunication) return 0;
  pollBitLow(_inBusy);
  if (flag_error_comunication) return 0;

  for(uint8_t i = 0; i < length; i += 1) {
    writeData(data[i]);
    if (flag_error_comunication) return 0;
    pollBitLow(_inBusy);
  if (flag_error_comunication) return 0;
  }
  pollBitHigh(_outReady);
  if (flag_error_comunication) return 0;

  value = readData();
  if (flag_error_comunication) return 0;
  if(value != 0x0D) {
    return EXIT_FAILURE;
  }

  return EXIT_SUCCESS;
}

uint8_t C2::eraseDevice() {
  writeAddress(FPDAT);
  writeData(DEVICE_ERASE);
  if (flag_error_comunication) return 0;

  pollBitLow(_inBusy);
  if (flag_error_comunication) return 0;
  pollBitHigh(_outReady);
  if (flag_error_comunication) return 0;

  uint8_t value = readData();
  if (flag_error_comunication) return 0;
  if(value != 0x0D) {
    return EXIT_FAILURE;
  }

  writeData(0xDE);
  if (flag_error_comunication) return 0;
  pollBitLow(_inBusy);
  if (flag_error_comunication) return 0;

  writeData(0xAD);
  if (flag_error_comunication) return 0;
  pollBitLow(_inBusy);
  if (flag_error_comunication) return 0;

  writeData(0xA5);
  if (flag_error_comunication) return 0;
  pollBitLow(_inBusy);
  if (flag_error_comunication) return 0;
  pollBitHigh(_outReady);
  if (flag_error_comunication) return 0;

  value = readData();
  if (flag_error_comunication) return 0;
  if(value != 0x0D) {
    return EXIT_FAILURE;
  }

  return EXIT_SUCCESS;
}

uint8_t C2::getState() {
  return _state;
}

void C2::resetState() {
  _state = 0;
  flag_error_comunication = false;
}

uint8_t C2::updateState(uint8_t data) {
  switch(_state) {
    case 0x00: {
      _messagePtr = 0;
      _message[_messagePtr++] = data;

      _state = 1;
    } break;

    case 0x01: {
      _bytesLeft = data;
      _message[_messagePtr++] = data;

      if(_bytesLeft == 0) {
        _state = 3;

        break;
      }

      _state = 2;
    } break;

    case 0x02: {
      _message[_messagePtr++] = data;
      _bytesLeft--;

      if(_bytesLeft == 0) {
        _state = 3;
      }
    } break;
  }

  return _state;
}

volatile uint8_t *C2::getMessage() {
  return _message;
}

void C2::loop() {
  unsigned char crc;
  unsigned char newcrc;
  unsigned long address;

  if(Serial.available()) {
    uint8_t data = Serial.read();
    updateState(data);

    if(_state == 3) {
      switch(_message[0]) {
        case Actions::ACK: {
          Serial.write(0x80);
          resetState();
        } break;

        case Actions::INIT: {
          Serial.write(0x81);
          init();
          if (flag_error_comunication) {
            Serial.write(0x44);
            resetState();
            break;
          }
          deviceInfo();
          if (flag_error_comunication) {
            Serial.write(0x44);
            resetState();
            break;
          }

          switch(device.id) {
            case C2Devices::EFM8BB1:
            case C2Devices::EFM8BB2: {
              writeSfr(0xFF, 0x80);
              if (flag_error_comunication) {
                Serial.write(0x44);
                resetState();
                break;
              }
              delayMicroseconds(5);
              writeSfr(0xEF, 0x02);
              if (flag_error_comunication) {
                Serial.write(0x44);
                resetState();
                break;
              }
            } break;
          }

          digitalWrite(_pinLed, HIGH);

          resetState();
        } break;

        case Actions::RESET: {
          reset();
          resetState();

          Serial.write(0x82);
          digitalWrite(_pinLed, LOW);
        } break;

        case Actions::WRITE: {
          address = (((unsigned long)(_message[4]))<<8) + (((unsigned long)(_message[5]))<<0);
          crc = _message[6];
          newcrc = _message[5] + _message[4];
          for(uint8_t i = 0; i < _message[2]; i+= 1) {
            _flashBuffer[i] = _message[i+7];
          }

          for(uint8_t i = 0; i < _message[2]; i += 1) {
            newcrc += _flashBuffer[i];
          }

          if(crc != newcrc) {
            Serial.write(0x43);
            resetState();
            break;
          }

          uint8_t ch = _message[2];
          writeFlashBlock(address, _flashBuffer, ch);
          if (flag_error_comunication) {
            Serial.write(0x44);
            resetState();
            break;
          }
          
          Serial.write(0x83);

          resetState();
        } break;

        case Actions::ERASE: {
          eraseDevice();
          if (flag_error_comunication) {
            Serial.write(0x44);
            resetState();
            break;
          }
          resetState();

          Serial.write(0x84);
        } break;

        case Actions::READ: {
          uint8_t byteCount = _message[2];
          unsigned long addressPart1 = ((unsigned long)(_message[3])) << 16;
          unsigned long addressPart2 = ((unsigned long)(_message[4])) << 8;
          unsigned long addressPart3 = ((unsigned long)(_message[5])) << 0;

          address = addressPart1 | addressPart2 | addressPart3;
          readFlashBlock(address, _flashBuffer, byteCount);
          if (flag_error_comunication) {
            Serial.write(0x44);
            resetState();
            break;
          }
          resetState();

          Serial.write(0x85);
          for(uint8_t i = 0; i < byteCount; i += 1) {
            Serial.write(_flashBuffer[i]);
          }
        } break;

        /*
        case 0x06: {
          writeAddress(_message[3]);
          writeData(_message[4]);
          resetState();

          Serial.write(0x86);
        } break;

        case 0x07: {
          writeAddress(_message[3]);
          data = readData();
          resetState();

          Serial.write(data);
          Serial.write(0x87);
        } break;
        */

        case Actions::INFO: {
          resetState();

          Serial.write(0x88);
          Serial.write(device.id);
          Serial.write(device.revision);
        } break;

        case Actions::CHANGE_CLK: {
          _pinCk_num = _message[2];
          if (_pinCk_num>3) _pinCk_num = 0;
          switch(_pinCk_num) {
            case 0:
              _pinCk = C2CK_PIN1;
              break;
            case 1:
              _pinCk = C2CK_PIN2;
              break;
            case 2:
              _pinCk = C2CK_PIN3;
              break;
            case 3:
              _pinCk = C2CK_PIN4;
              break;
          }
          
          *_ddr = 0x00 | (1 << _pinD) | (1 << _pinCk);
          *_port = 0x00 | (1 << _pinCk);
          resetState();

          Serial.write(0x89);
          Serial.write(_pinCk_num);
        } break;

        case Actions::IPWM: {
          pwmSetup();
          Serial.write(0x91);
          resetState();
        } break;

        case Actions::IDSHOT: {
          dshotSetup();
          Serial.write(0x92);
          resetState();
        } break;

        case Actions::PWM: {
          uint16_t pwmValue = 0;
          Serial.write(0x93);
    
          for (int i = 0; i < _message[1]; i++) 
          {
              pwmValue = pwmValue * 10 + (_message[2+i] - '0');
          }

          UpdatePWM(pwmValue);
          // Serial.write(_message[0]);
          // Serial.write(_message[1]);
          // Serial.write(_message[2]);
          // Serial.write(_message[3]);
          // Serial.write(_message[4]);
          // Serial.write(_message[5]);
          // Serial.write(_message[6]);
          // Serial.write(pwmValue);
          resetState();
        } break;

        case Actions::DSHOT: {
          uint16_t dshotValue = 0;
          Serial.write(0x94);
          
          for (int i = 0; i < _message[1]; i++) 
          {
              dshotValue = dshotValue * 10 + (_message[2+i] - '0');
          }
          UpdateDShot(dshotValue);
          // Serial.write(_message[0]);
          // Serial.write(_message[1]);
          // Serial.write(_message[2]);
          // Serial.write(_message[3]);
          // Serial.write(_message[4]);
          // Serial.write(_message[5]);
          // Serial.write(_message[6]);
          // Serial.write(dshotValue);
          resetState();
        } break;

        case Actions::RESPONSE: {
          printResponse();
          Serial.write(0x95);
          resetState();
        } break;

        case Actions::C2MODE: {
          disableMotor();
          Serial.write(0x90);
          resetState();
        } break;
      }
    }
  }
}
