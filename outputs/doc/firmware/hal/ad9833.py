import time
import machine

class Ad9833:
    SHAPE_SIN = 0x2000
    SHAPE_TRI = 0x2002
    SHAPE_SQU = 0x2020
    
    MCLK = 25_000_000
    
    SPI_BAUDRATE = 100_000
    
    def __init__( self, cs, sck, mosi, miso ):
        self.buf = bytearray( 2 )
        
        self.cs  = cs
        self.sck = sck
        self.mosi= mosi
        self.miso= miso
        
        self.sck.high()
        
        self.cs.value( 1 )
        
        self.spi_init()
        self.reset()
    
    def reset( self ):
        self.send( 0x0100 )
        time.sleep_ms( 1 )
        self.send( 0x0000 )
        time.sleep_ms( 10 )
        
    def spi_init( self ):
        self.spi = machine.SPI( 
            1, 
            baudrate=Ad9833.SPI_BAUDRATE, 
            polarity=1,
            phase=1,
            sck=self.sck, 
            mosi=self.mosi, 
            miso=self.miso,
            firstbit=machine.SPI.MSB
        )
    
    def send( self, data ):
        self.buf[0] = data >> 8
        self.buf[1] = data & 0xFF
        
        self.sck.high()
        time.sleep_ms(1)
        self.cs.low()
        time.sleep_ms(1)
        self.spi.write( self.buf )
        time.sleep_ms(1)
        self.cs.high()
    
    def config( self, freq_hz, shape ):
        word = (freq_hz<<28)//Ad9833.MCLK

        MSB =(word & 0xFFFC000) >> 14
        LSB = word & 0x3FFF

        # Set control bits DB15 = 0 and DB14 = 1; for frequency register 0
        MSB |= 0x4000
        LSB |= 0x4000

        self.send( 0x2100 )
        self.send( LSB )  # lower 14 bits
        self.send( MSB )  # Upper 14 bits
        self.send( 0xC000 )
        self.send( shape )

def test_ad9983():
    lcd_cs = machine.Pin( 13, machine.Pin.OUT )
    tsc_cs = machine.Pin( 16, machine.Pin.OUT )
    dds_cs = machine.Pin( 17, machine.Pin.OUT )

    lcd_cs.value( 1 )
    tsc_cs.value( 1 )
    dds_cs.value( 1 )

    sck  = machine.Pin( 10, machine.Pin.OUT )
    mosi = machine.Pin( 11, machine.Pin.OUT )
    miso = machine.Pin( 12, machine.Pin.IN  )
    dc   = machine.Pin( 14, machine.Pin.OUT )

    sck.high()

    bl  = machine.Pin( 15, machine.Pin.OUT )

    """
    # Calibration values
    AX, BX = 0.176831, -45.643
    AY, BY = 0.130840, -16.191
    tsc = Xpt2046( tsc_baudrate, tsc_cs, sck, mosi, miso, ax=AX, bx=BX, ay=AY, by=BY )

    # Init lcd last one to start lvgl with SPI LCD baudrate
    lcd = St7789( lcd_baudrate, lcd_cs, sck, mosi, miso, dc )
    lcd.clear( 0x0000 )

    adc = Adc08100( 10_000_000 )
    """

    dds = Ad9833( dds_cs, sck, mosi, miso )


    dds.config( 1_000_000, Ad9833.SHAPE_SQU )
    time.sleep_ms( 1 )
    dds.config( 500_000, Ad9833.SHAPE_SQU )

    print( "done" )

#test_ad9983()

#print( "done" )