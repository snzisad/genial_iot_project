#include <Ethernet.h>
#include <EthernetUdp.h>
#include <SPI.h> 
#include<math.h>
#include "Wire.h" 
 
byte mac[] ={0x90, 0xA2, 0xDA, 0x10, 0xA7, 0xE1}; 
IPAddress ip(10, 42, 0, 174); 
unsigned int localPort = 5000; 
char packetBuffer[UDP_TX_PACKET_MAX_SIZE]; 
String datReq; 
int packetSize;
EthernetUDP Udp; 

const int B = 4275;               
const int R0 = 100000;            
const int pinTempSensor = A1; 
const int pinSoundSensor = A2; 
const int pinLightSensor = A3;



void setup() {
  
  Serial.begin(9600);
  Ethernet.begin( mac, ip);
  Udp.begin(localPort); 
  delay(1500); 
}


 
void loop() {

  packetSize =Udp.parsePacket();  
  if(packetSize>0) {
    
    Udp.read(packetBuffer, UDP_TX_PACKET_MAX_SIZE); 
    String datReq(packetBuffer);
    Serial.println(datReq);
    
    float x[3];

    if((packetBuffer[1]-'0')==1){
      int a = analogRead(pinTempSensor);
      float R = 1023.0/a-1.0;
      R = R0*R;
      float temperature = 1.0/(log(R/R0)/B+1/298.15)-273.15;
      x[0]=temperature;
    }else{
      x[0]=-1;
    }
    if((packetBuffer[4]-'0')==2){
      long sum = 0;
      for(int i=0; i<32; i++)
      {
          sum += analogRead(pinSoundSensor);
      }
      sum >>= 5;
      x[1]=sum;
    }else{
      x[1]=-1;
    }
    if((packetBuffer[7]-'0')==3){
      int val=analogRead(pinLightSensor);
      x[2]=val;
    }else{
      x[2]=-1;
    }

    Udp.beginPacket(Udp.remoteIP(), Udp.remotePort()); //Initialize packet send
    int xx=sizeof(x)/4;
    for(int i=0;i<xx;i++){
      Udp.print(x[i]);
      if(i!=xx-1){
        Udp.print('*');
      }
      
    }
    Udp.endPacket();//End the packet      
  }
  
  memset(packetBuffer, 0, UDP_TX_PACKET_MAX_SIZE); //clear out the packetBuffer array
}
