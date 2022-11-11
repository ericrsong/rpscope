# ADC driver

import time
import machine
import rp2
import uctypes
from hal.dma import DMA


@rp2.asm_pio(
    sideset_init =(rp2.PIO.OUT_HIGH, rp2.PIO.OUT_HIGH),
    in_shiftdir  = rp2.PIO.SHIFT_LEFT,
)
def build_sm_adc08100():
    in_( pins, 8 ) .side( 0b0 )
    push( block )  .side( 0b1 )

@rp2.asm_pio(
    sideset_init =(rp2.PIO.OUT_HIGH, rp2.PIO.OUT_HIGH),
    in_shiftdir  = rp2.PIO.SHIFT_LEFT,
)
def build_sm_adc08100_trigger():
    wait( 1, irq, 4 )
    wrap_target()
    in_( pins, 8 ) .side( 0b00 )
    push( block )  .side( 0b10 )#0b11
    in_( pins, 8 ) .side( 0b00 )#0b01
    push( block )  .side( 0b10 )
    wrap()

# 100MHz
#    in_( pins, 8 ) .side( 0b0 )
#    push( block )  .side( 0b1 )
#
# 10MHz
#    in_( pins, 8 ) .side( 0b1 )
#    push( block )  .side( 0b0 )

class Adc08100:
    PIO0_BASE      = 0x50200000
    PIO0_BASE_TXF0 = PIO0_BASE + 0x10
    PIO0_BASE_RXF0 = PIO0_BASE + 0x20

    def __init__( self, sps, sck, db, use_trigger=False ):
        self.db  = db #machine.Pin( 0 ) # out
        self.sck = sck #machine.Pin( 21 ) # side 0
        
        if( use_trigger ):
            self.sm = rp2.StateMachine(
                0,
                prog        = build_sm_adc08100_trigger,
                freq        = 2*sps,
                sideset_base= self.sck,
                in_base     = self.db,
            )
        else:
            self.sm = rp2.StateMachine(
                0,
                prog        = build_sm_adc08100,
                freq        = 2*sps,
                sideset_base= self.sck,
                in_base     = self.db,
            )
        self.dma = DMA( 1 )
    
    def dma_config( self, buf, count, ring_size_pow2=0 ):
        self.dma.config(
            Adc08100.PIO0_BASE_RXF0, 
            uctypes.addressof( buf ),
            count,
            src_inc=False,
            dst_inc=True,
            trig_dreq=DMA.DREQ_PIO0_RX0,
            ring_sel=True,
            ring_size_pow2=ring_size_pow2
        )
    
    def read( self, buf, dma_config=True ):
        if( dma_config ):
            self.dma_config( buf, len(buf) )
        
        self.dma.enable()
        self.sm.active( True )
        while( self.dma.is_busy() ):
            pass
        self.sm.active( False )
        self.dma.disable()

def test_adc08100():
    db  = machine.Pin( 0 ) # out
    sck = machine.Pin( 21 ) # side 0
        
    buf = bytearray( 10_000 )

    adc = Adc08100( 1_000_000, sck, db )
    
    t0 = time.ticks_us()
    adc.read( buf )
    t1 = time.ticks_us()
    
    print( "buf", buf[0:10], "..." )

    print( "Read speed [B/s]:", len( buf )/((t1-t0)/1e-6) )
    print( "@CPU freq:", machine.freq() )

#test_adc08100()

#print("done")