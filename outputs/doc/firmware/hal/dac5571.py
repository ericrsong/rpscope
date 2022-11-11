import machine

class Dac5571:
    DEV_ADDR   = 0x4D
        
    def __init__( self, i2c ):
        self.i2c = i2c
        self.buf = bytearray( 1 )
        self.set_output( 0x00 )
    
    def set_output( self, value ):
        self.buf[0] = (value<<4)&0xFF
        self.i2c.writeto_mem( self.DEV_ADDR, (value>>4)&0xFF, self.buf )