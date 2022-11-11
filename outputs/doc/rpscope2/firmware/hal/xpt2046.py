import time
import machine

class Xpt2046:
    
    CHANNEL_X = 0x90
    CHANNEL_Y = 0xD0
    
    def __init__( self, baudrate, cs, sck, mosi, miso, ax=1, bx=0, ay=1, by=0 ):
        self.buf_tx = bytearray( 3 )
        self.buf_rx = bytearray( 3 )
        
        self.sck = sck
        self.mosi= mosi
        self.miso= miso
        self.cs  = cs
        self.cs.value( 1 )

        self.ax = ax
        self.bx = bx
        self.ay = ay
        self.by = by
        
        self.baudrate = baudrate
        self.spi_init()

    
    def spi_init( self ):
        self.spi = machine.SPI( 
            1, 
            baudrate=self.baudrate, 
            polarity=0,
            phase=0,
            sck=self.sck, 
            mosi=self.mosi, 
            miso=self.miso 
        )

    def _read( self ):
        self.cs.value( 0 )
        
        self.buf_tx[0] = Xpt2046.CHANNEL_X
        self.buf_tx[1] = 0x00
        self.buf_tx[2] = 0x00
        self.spi.write_readinto( self.buf_tx, self.buf_rx )
        x = (self.buf_rx[1]<<4) | (self.buf_rx[2]>>4)

        self.buf_tx[0] = Xpt2046.CHANNEL_Y
        self.buf_tx[1] = 0x00
        self.buf_tx[2] = 0x00
        self.spi.write_readinto( self.buf_tx, self.buf_rx )
        y = (self.buf_rx[1]<<4) | (self.buf_rx[2]>>4)
        
        self.cs.value( 1 )
        
        if( x == 2047 ):
            x = 0
        
        return x, y

    def read( self ):
        xacc = 0
        yacc = 0
        for i in range( 4 ):
            x, y = self._read()
            if( x and y ):
                xacc += x
                yacc += y
            else:
                return 0, 0
        
        x = xacc/4
        y = yacc/4
        
        x = self.ax*x + self.bx
        y = self.ay*y + self.by
        
        return int( x ), int( y )

def test_tsc():    
    baudrate= 1_000_000
    #cs  = machine.Pin( 16, machine.Pin.OUT )
    #sck = machine.Pin( 10, machine.Pin.OUT )
    #mosi= machine.Pin( 11, machine.Pin.OUT )
    #miso= machine.Pin( 12, machine.Pin.OUT )

    lcd_baudrate = 24_000_000
    tsc_baudrate = 1_000_000

    lcd_cs  = machine.Pin( 9, machine.Pin.OUT )
    tsc_cs  = machine.Pin( 16, machine.Pin.OUT )
    lcd_cs.value( 1 )
    tsc_cs.value( 1 )

    sck = machine.Pin( 10, machine.Pin.OUT )
    mosi= machine.Pin( 11, machine.Pin.OUT )
    miso= machine.Pin( 12, machine.Pin.IN  )
    dc  = machine.Pin( 8, machine.Pin.OUT )

    bl  = machine.Pin( 13, machine.Pin.OUT )
    bl.value( 1 )
    
    # Calibration values
    AX = 1#0.176831
    BX = 0#-45.643
    AY = 1# 0.13084
    BY = 0#-16.191

    AX = 0.2525252525252525
    BX =-29.54545454545455
    AY =-0.1744186046511628
    BY = 335.5232558139535
    
    tsc = Xpt2046( baudrate, tsc_cs, sck, mosi, miso, ax=AX, bx=BX, ay=AY, by=BY )
    for i in range( 20 ):
        x, y = tsc.read()
        if( x and y ):
            print( True, x, y )
        else:
            print( False, x, y )
    time.sleep( 0.1 )


#test_tsc()

#print("done")