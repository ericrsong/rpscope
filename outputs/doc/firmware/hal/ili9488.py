import time
import machine
import uctypes
from hal.dma import DMA

class Ili9488:
    HRES = 480
    VRES = 320

    CASET = 0x2A
    RASET = 0x2B
    RAMWR = 0x2C 
    def __init__( self, baudrate, cs, sck, mosi, miso, dc, rst, bl ):
        self.buf1 = bytearray( 1 )
        self.buf2 = bytearray( 2 )
        self.buf4 = bytearray( 4 )
        
        self.baudrate = baudrate
        self.cs  = cs
        self.sck = sck
        self.mosi= mosi
        self.miso= miso
        self.dc  = dc
        self.rst = rst
        self.bl = bl
        
        self.rst.value( 0 )
        self.cs.value( 1 )
        self.bl.value( 1 )
        
        self.dma = DMA( 0 )
        self.spi_init()
        self.reset()
        self.config()
    
    def reset( self ):
        self.rst.value( 0 )
        time.sleep_ms( 10 )
        self.rst.value( 1 )
        time.sleep_ms( 100 )
    
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
    
    def write_register( self, reg, buf ):
        self.buf1[0] = reg
        self.cs.value( 0 )

        self.dc.value( 0 )
        self.spi.write( self.buf1 )
        time.sleep_us( 5 )
        self.cs.value( 1 )
        
        for i in range( len( buf )//2 ):
            self.cs.value( 0 )
            self.dc.value( 1 )
            self.spi.write( buf[2*i:2*i+2] )
            time.sleep_us( 5 )
            self.cs.value( 1 )

        self.cs.value( 1 )

    # Note: if is_blocking is False, user should call to wait_dma explicitly
    def write_register_dma( self, reg, buf, is_blocking=True ):    
        SPI1_BASE = 0x40040000
        SSPDR     = 0x008
        self.dma.config(
            src_addr = uctypes.addressof( buf ),
            dst_addr = SPI1_BASE + SSPDR,
            count    = len( buf ),
            src_inc  = True,
            dst_inc  = False,
            trig_dreq= DMA.DREQ_SPI1_TX
        )
        
        self.buf1[0] = reg
        self.cs.value( 0 )

        self.dc.value( 0 )
        self.spi.write( self.buf1 )
        
        self.cs.value( 1 )
        self.cs.value( 0 )
        
        self.dc.value( 1 )
        self.dma.enable()
        
        if( is_blocking ):
            self.wait_dma()

    def wait_dma( self ):
        while( self.dma.is_busy() ):
            pass
        self.dma.disable()
        
        # Note: wait to send last byte. It should take < 1uS @ 10MHz 
        time.sleep_us( 1 )
        
        self.cs.value( 1 )
    
    def config( self ):
        print("config")
        self.write_register( 0x21, b"" )
        self.write_register( 0xc2, b"\x00\x33" )
        self.write_register( 0xc5, b"\x00\x00\x00\x1e\x00\x80" )
        self.write_register( 0xb1, b"\x00\xb0" )
        self.write_register( 0x36, b"\x00\x28" )
        self.write_register( 0xe0, b"\x00\x00\x00\x13\x00\x18\x00\x04\x00\x0f\x00\x06\x00\x3a\x00\x56\x00\x4d\x00\x03\x00\x0a\x00\x06\x00\x30\x00\x3e\x00\x0f" )
        self.write_register( 0xe1, b"\x00\x00\x00\x13\x00\x18\x00\x01\x00\x11\x00\x06\x00\x38\x00\x34\x00\x4d\x00\x06\x00\x0d\x00\x0b\x00\x31\x00\x37\x00\x0f" )
        self.write_register( 0x3a, b"\x00\x55" )
        self.write_register( 0x11, b"" )
        time.sleep_ms( 120 )
        self.write_register( 0x29, b"" )
        self.write_register( 0xB6, b"\x00\x00\x00\x62" )
        self.write_register( 0x36, b"\x00\x28" )

    def set_window( self, x, y, w, h ):
        x0 = x
        y0 = y
        x1 = x0 + w - 1
        y1 = y0 + h - 1
        
        buf8 = bytearray( 8 )

        buf8[0] = 0x00
        buf8[1] = x0 >> 8
        buf8[2] = 0x00
        buf8[3] = x0 & 0xFF
        buf8[4] = 0x00
        buf8[5] = x1 >> 8
        buf8[6] = 0x00
        buf8[7] = x1 & 0xFF
        self.write_register( Ili9488.CASET, buf8 )

        buf8[0] = 0x00
        buf8[1] = y0 >> 8
        buf8[2] = 0x00
        buf8[3] = y0 & 0xFF
        buf8[4] = 0x00
        buf8[5] = y1 >> 8
        buf8[6] = 0x00
        buf8[7] = y1 & 0xFF
        self.write_register( Ili9488.RASET, buf8 )
        
        
    def draw_bitmap_dma( self, x, y, w, h, buf, is_blocking=True ):
        self.set_window( x, y, w, h )
        self.write_register_dma( Ili9488.RAMWR, buf, is_blocking )
            
    def clear( self, color ):
        self.buf2[0] = color >> 8
        self.buf2[1] = color &  0xff
        
        self.set_window( 0, 0, Ili9488.HRES, Ili9488.VRES  )
        self.write_register( Ili9488.RAMWR, b"" )

        self.cs.value( 0 )
        self.dc.value( 1 )
        for i in range( Ili9488.HRES ):
            for j in range( Ili9488.VRES ):
                self.spi.write( self.buf2 )
        self.cs.value( 1 )

def build_square_buf( w, h ):
    top = b"\xFF\xFF"*w
    body=(b"\xFF\xFF" + b"\x00\x00"*(w-2) + b"\xFF\xFF")*(h-2)
    bot = b"\xFF\xFF"*w
    return top + body + bot

def test_lcd():
    baudrate = 25_000_000
    print( "baudrate", baudrate )  

    rst = machine.Pin( 15, machine.Pin.OUT )
    #cs  = machine.Pin( 13, machine.Pin.OUT )
    cs  = machine.Pin( 9, machine.Pin.OUT )
    sck = machine.Pin( 10, machine.Pin.OUT )
    mosi= machine.Pin( 11, machine.Pin.OUT )
    miso= machine.Pin( 12, machine.Pin.IN  )
    #dc  = machine.Pin( 14, machine.Pin.OUT )
    dc  = machine.Pin( 8, machine.Pin.OUT )

    #bl  = machine.Pin( 15, machine.Pin.OUT )
    bl  = machine.Pin( 13, machine.Pin.OUT )
    bl.value( 1 )

    cs.value( 1 )

    rst.value(1)
    time.sleep_ms( 100 )
    rst.value(0)
    time.sleep_ms( 100 )
    rst.value(1)
    time.sleep_ms( 100 )

    lcd = Ili9488( baudrate, cs, sck, mosi, miso, dc )
    lcd.clear( 0x001F )

    # 1/4 screen pixels square with white border red backgorund 
    w, h = 320//4, 240//4
    bmp = build_square_buf( w, h )
    
    t0 = time.ticks_us()
    lcd.draw_bitmap_dma( 100, 100, w, h, bmp )
    t1 = time.ticks_us()

    print( "Maximum FPS @24MHz:", 24e6/( 320*240*16 ) ) # FPS = F/(W*H*BPP)
    print( "Achieved FPS:", 1/(16*(t1-t0)*1e-6) )       # Note: Test only draws 1/16 of the sreen area
    
    print( "Draw TSC calibration pattern")
    w, h = 10, 10
    bmp = build_square_buf( w, h )
    lcd.draw_bitmap_dma( 50, 50, w, h, bmp )
    lcd.draw_bitmap_dma( 250, 50, w, h, bmp )
    lcd.draw_bitmap_dma( 250, 200, w, h, bmp )
    lcd.draw_bitmap_dma( 50, 200, w, h, bmp )

#test_lcd()

#print("done")