import machine


class Tca9554:
    DEV_ADDR   = 0x20
    REG_OUTPUT = 0x01
    REG_CONFIG = 0x03
        
    def __init__( self, i2c ):
        self.i2c = i2c
        self.buf = bytearray( 1 )
        self.set_output( 0x00 )
        self.set_config( 0x00 )
    
    def set_config( self, value ):
        # Output = 0, Input = 1
        self.buf[0] = value
        self.i2c.writeto_mem( self.DEV_ADDR, self.REG_CONFIG, self.buf )
    
    def set_output( self, value ):
        self.buf[0] = value
        self.i2c.writeto_mem( self.DEV_ADDR, self.REG_OUTPUT, self.buf )
