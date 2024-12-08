#ifndef ARDUINO_DSHOT_H
#define ARDUINO_DSHOT_H

void disableMotor();
void printResponse();
void UpdateDShot(uint16_t dshotValue);
void UpdatePWM(uint16_t pwmValue);
void dshotSetup();
void pwmSetup();

#endif