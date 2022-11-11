import time
import machine
import rp2
import uctypes
from hal.dma import DMA

@rp2.asm_pio()
def build_sm_trigger_rising():
    label( "prog_trigger" )
    pull( block )
    mov( y, osr )
    pull( block )
    mov( x, osr )
    irq( 4 )
    
    label( "loop_y_dec" )
    nop()
    jmp( y_dec, "loop_y_dec" )
    
    wait( 0, pin, 0 )
    wait( 1, pin, 0 )
    
    label( "loop_x_dec" )
    nop()
    jmp( x_dec, "loop_x_dec" )
    
    push( block )
    nop()[4]
    irq( block, 1 )
    
    jmp( "prog_trigger" )

@rp2.asm_pio()
def build_sm_trigger_falling():
    label( "prog_trigger2" )
    pull( block )
    mov( y, osr )
    pull( block )
    mov( x, osr )
    irq( 4 )
    
    label( "loop_y_dec2" )
    nop()
    jmp( y_dec, "loop_y_dec2" )
    
    wait( 1, pin, 0 )
    wait( 0, pin, 0 )
    
    label( "loop_x_dec2" )
    nop()
    jmp( x_dec, "loop_x_dec2" )
    
    push( block )
    nop()[4]
    irq( block, 1 )
    
    jmp( "prog_trigger2" )

class Trigger:
    def __init__( self, sps, trig, rising ):
        self.trig = trig
        
        if( rising ):
            build_sm_trigger = build_sm_trigger_rising
        else:
            build_sm_trigger = build_sm_trigger_falling
        
        self.sm = rp2.StateMachine(
            1,
            prog        = build_sm_trigger,
            freq        = 2*sps,
            in_base     = trig
        )

        self.dma = DMA( 2 )
        self.src = b"\x00"
    
    def read( self, pre, post, addr_stop ):
        self.dma.config( 
            src_addr=uctypes.addressof( self.src ),
            dst_addr=addr_stop,
            count=1,
            src_inc=False,
            dst_inc=False,
            ring_sel=False, 
            ring_size_pow2=0, 
            trig_dreq=DMA.DREQ_PIO0_RX1
        )  
        
        self.sm.put( pre )
        self.sm.put( post )
        
        self.dma.enable()
        self.sm.active( True )
        
        while( self.dma.is_busy() ):
            pass
        
        self.sm.active( False )
        self.dma.disable()
        
def test_trigger( ccc ):
    sps = 10_000_000
    
    db  = machine.Pin( 0 ) # out
    sck = machine.Pin( 21 ) # side 0
    trig = machine.Pin( 7 )#, machine.Pin.IN ) # trigger
        
    buf = bytearray( 512 )
    buf_addr_aligned = (uctypes.addressof( buf )+0xFF)&0xFFFFFF00
    buf_offset_aligned = buf_addr_aligned - uctypes.addressof( buf )
    print( "# uctypes.addressof( buf ) 0x{:08X}".format( uctypes.addressof( buf ) ) )
    print( "# buf_addr_aligned 0x{:08X}".format( buf_addr_aligned ) )
    print( "# buf_offset_aligned 0x{:08X}".format( buf_offset_aligned ) )
    
    t0 = time.ticks_us()
    adc = Adc08100( sps, sck, db, use_trigger=True )
    t1 = time.ticks_us()
    print( "#Adc08100 t1-t0", t1-t0 )
    #adc.dma_config( buf, 0x0FFFFFFF, ring_size_pow2=8 )
    t0 = time.ticks_us()
    adc.dma.config(
        Adc08100.PIO0_BASE_RXF0, 
        buf_addr_aligned,
        0xFFFFFFFF,
        src_inc=False,
        dst_inc=True,
        trig_dreq=DMA.DREQ_PIO0_RX0,
        ring_sel=True,
        ring_size_pow2=8
    )
    t1 = time.ticks_us()
    print( "#dma.config t1-t0", t1-t0 )
    

    t0 = time.ticks_us()
    adc.dma.enable()
    adc.sm.active( True )
    t1 = time.ticks_us()
    print( "#dma&sm.enable t1-t0", t1-t0 )
    
    t0 = time.ticks_us()    
    trigger = Trigger( sps, trig )
    t1 = time.ticks_us()
    print( "#Trigger t1-t0", t1-t0 )
    
    DMA1_TRIG = 0x50000000 + 1 * 0x40 + 0x0C

    t0 = time.ticks_us()    
    trans_count0 = machine.mem32[ adc.dma.CHx_TRANS_COUNT ]
    trigger.read( 1024, 128, DMA1_TRIG )
    trans_count1 = machine.mem32[ adc.dma.CHx_TRANS_COUNT ]
    t1 = time.ticks_us()
    print( "#trigger.read t1-t0", t1-t0 )
    
    t0 = time.ticks_us()    
    adc.dma.disable()
    adc.sm.active( False )
    t1 = time.ticks_us()
    print( "#dma&sm.disable t1-t0", t1-t0 )
    
    
    trans_count_diff = trans_count0 - trans_count1 # - 1
    print( "#trans_count", trans_count0, trans_count1, trans_count0-trans_count1 )
    print( "#trans_count_diff", trans_count_diff, trans_count_diff&0xFF )
    
    cnt0 = 0
    for i in range( len( buf ) ):
        if( buf[i] == 0 ):
            cnt0 += 1
    
    #print( "buf[ buf_offset_aligned ]", hex( buf[ buf_offset_aligned ] ), chr( buf[ buf_offset_aligned ] ), buf[ buf_offset_aligned ] )
    print( "#len(buf)-cnt0", len(buf) - cnt0 )
    #print( buf )
    
    buf2 = buf[ buf_offset_aligned : buf_offset_aligned+0x100 ]
    buf2 = buf2+buf2
    
    trans_count_diff = trans_count_diff&0xFF
    print( "#buf[ buf_offset_aligned + trans_count_diff ]", buf2[ trans_count_diff ] )

    #print( "buf" + str(ccc) + " = ", buf2[trans_count_diff : trans_count_diff + 0x100] )
    
    bufA = buf[ buf_offset_aligned + trans_count_diff : buf_offset_aligned + 0x100 ]
    bufB = buf[ buf_offset_aligned : buf_offset_aligned + trans_count_diff ]
    print( "buf" + str(ccc) + " = ", bufA + bufB )
    
    
#for i in range( 10 ):
#    print( "# i", i )
#    test_trigger( i )
#
#import gc
#gc.collect()

#print( "done" )