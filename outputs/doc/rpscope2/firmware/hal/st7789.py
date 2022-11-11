import time
import machine
import uctypes
from hal.dma import DMA

class St7789:
    HRES = 320
    VRES = 240

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
        
        self.dc.value( 1 )
        self.spi.write( buf )
        
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
        self.write_register( 0x11, b"" )
        time.sleep_ms( 100 )
        self.write_register( 0x36, b"\x60" )
        self.write_register( 0x3A, b"\x55" )
        self.write_register( 0xB2, b"\x0C\x0C\x00\x33\x33"  )
        self.write_register( 0xB7, b"\x35" )
        self.write_register( 0xBB, b"\x28" )
        self.write_register( 0xC0, b"\x3C" )
        self.write_register( 0xC2, b"\x01" )
        self.write_register( 0xC3, b"\x0B" )
        self.write_register( 0xC4, b"\x20" )
        self.write_register( 0xC6, b"\x0F" )
        self.write_register( 0xD0, b"\xA4\xA1" )
        self.write_register( 0xE0, b"\xD0\x01\x08\x0F\x11\x2A\x36\x55\x44\x3A\x0B\x06\x11\x20" )
        self.write_register( 0xE1, b"\xD0\x02\x07\x0A\x0B\x18\x34\x43\x4A\x2B\x1B\x1C\x22\x1F" )
        self.write_register( 0x55, b"\xB0" )
        self.write_register( 0x29, b"" )
        time.sleep_ms( 100 )

    def set_window( self, x, y, w, h ):
        x0 = x
        y0 = y
        x1 = x0 + w - 1
        y1 = y0 + h - 1
        self.buf4[0] = x0 >> 8
        self.buf4[1] = x0 &  0xff
        self.buf4[2] = x1 >> 8
        self.buf4[3] = x1 &  0xff
        self.write_register( St7789.CASET, self.buf4 )
        self.buf4[0] = y0 >> 8
        self.buf4[1] = y0 &  0xff
        self.buf4[2] = y1 >> 8
        self.buf4[3] = y1 &  0xff
        self.write_register( St7789.RASET, self.buf4 )
    
    def draw_bitmap_dma( self, x, y, w, h, buf, is_blocking=True ):
        self.set_window( x, y, w, h )
        self.write_register_dma( St7789.RAMWR, buf, is_blocking )

    @micropython.native
    def draw_wave( self, x, y, w, h, buf, color ):
        
        
        self.set_window( x, y, w, h )
        #self.write_register( 0x36, b"\x60" )
        self.cs.value( 0 )
        
        CASET = St7789.CASET
        RASET = St7789.RASET
        RAMWR = St7789.RAMWR
        buf1 = self.buf1
        buf2 = self.buf2
        dc = self.dc
        spi = self.spi
        
        
        CASET = b"\x2A"
        RASET = b"\x2B"
        RAMWR = b"\x2C"
        
        COLOR = bytearray(2)
        
        COLOR[0] = color >> 8
        COLOR[1] = color & 0xFF
        
        for i in range( len( buf ) ):
            x0 = x + i
            y0 = y + buf[i]        
            
            buf2[0] = x0 >> 8
            buf2[1] = x0 &  0xff
            #self.write_register( St7789.CASET, self.buf2 )
            #buf1[0] = CASET
            #self.cs.value( 0 )
            dc.value( 0 )
            spi.write( CASET )
            dc.value( 1 )
            spi.write( buf2 )
            #self.cs.value( 1 )
            
            
            
            buf2[0] = y0 >> 8
            buf2[1] = y0 &  0xff
            #self.write_register( St7789.RASET, self.buf2 )
            #buf1[0] = RASET
            #self.cs.value( 0 )
            dc.value( 0 )
            spi.write( RASET )
            dc.value( 1 )
            spi.write( buf2 )
            #self.cs.value( 1 )


            #self.write_register( St7789.RAMWR, self.buf2 )
            #buf1[0] = RAMWR
            #self.cs.value( 0 )
            dc.value( 0 )
            spi.write( RAMWR )
            dc.value( 1 )
            spi.write( COLOR )
            #self.cs.value( 1 )
        self.cs.value( 1 )
            
            
    def clear( self, color ):
        self.buf2[0] = color >> 8
        self.buf2[1] = color &  0xff
        
        self.set_window( 0, 0, St7789.HRES, St7789.VRES  )
        self.write_register( St7789.RAMWR, b"" )

        self.cs.value( 0 )
        self.dc.value( 1 )
        for i in range( St7789.HRES ):
            for j in range( St7789.VRES ):
                self.spi.write( self.buf2 )
        self.cs.value( 1 )

def build_square_buf( w, h ):
    top = b"\xFF\xFF"*w
    body=(b"\xFF\xFF" + b"\x00\x00"*(w-2) + b"\xFF\xFF")*(h-2)
    bot = b"\xFF\xFF"*w
    return top + body + bot
    
def test_lcd():
    baudrate = 2_000_000
    print( "baudrate", baudrate )
    cs  = machine.Pin( 13, machine.Pin.OUT )
    sck = machine.Pin( 10, machine.Pin.OUT )
    mosi= machine.Pin( 11, machine.Pin.OUT )
    miso= machine.Pin( 12, machine.Pin.IN  )
    dc  = machine.Pin( 14, machine.Pin.OUT )

    bl  = machine.Pin( 15, machine.Pin.OUT )
    bl.value( 1 )

    lcd = St7789( baudrate, cs, sck, mosi, miso, dc )
    #lcd.clear( 0x001F )

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
    #lcd.draw_bitmap_dma( 50, 50, w, h, bmp )
    #lcd.draw_bitmap_dma( 250, 50, w, h, bmp )
    #lcd.draw_bitmap_dma( 250, 200, w, h, bmp )
    #lcd.draw_bitmap_dma( 50, 200, w, h, bmp )
    
    
def test_lcd2():
    baudrate = 24_000_000
    cs  = machine.Pin( 13, machine.Pin.OUT )
    sck = machine.Pin( 10, machine.Pin.OUT )
    mosi= machine.Pin( 11, machine.Pin.OUT )
    miso= machine.Pin( 12, machine.Pin.IN  )
    dc  = machine.Pin( 14, machine.Pin.OUT )

    bl  = machine.Pin( 15, machine.Pin.OUT )
    bl.value( 1 )

    lcd = St7789( baudrate, cs, sck, mosi, miso, dc )
    
    import math
    bufa = bytearray( 256 )
    bufb = bytearray( 256 )
    for i in range( len( bufa ) ):
        bufa[i] = int( 128 + (2*50+0)/100*60*math.sin( 2*math.pi*i/len( bufa ) ) )
    for i in range( len( bufb ) ):
        bufb[i] = int( 128 + (2*100+1)/100*60*math.sin( 2*math.pi*i/len( bufb ) ) )
        
    
    for j in range( 100//2 ):
        t0 = time.ticks_us()

        lcd.draw_wave( 0, 0, 128, 240, bufb, 0xFFFF )
        t1 = time.ticks_us()
        lcd.draw_wave( 0, 0, 128, 240, bufa, 0x0000 )
        t2 = time.ticks_us()
        
        t0 = time.ticks_us()
        lcd.draw_wave( 0, 0, 128, 240, bufa, 0xFFFF )
        t1 = time.ticks_us()
        lcd.draw_wave( 0, 0, 128, 240, bufb, 0x0000 )
        t2 = time.ticks_us()
        
        #print( t1-t0, t2-t1 )

#test_lcd()


#print( "done" )