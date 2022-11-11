import time
import machine
import uctypes

class DMA:
    DMA_BASE  = 0x50000000
    
    DMA_EN    = 0x01 << 0
    HIGH_PRIO = 0x01 << 1
    INCR_READ = 0x01 << 4
    INCR_WRITE= 0x01 << 5
    DREQ_PIO0_RX0 = 0x04 << 15
    DREQ_PIO0_RX1 = 0x05 << 15
    DREQ_SPI1_TX  = 0x12 << 15
    DREQ_PERMANENT= 0x3F << 15
    IRQ_QUIET = 0x01 << 21
    BUSY      = 0x01 << 24
    
    CHAIN_TO_POS = 0x0B
    RING_SEL_POS = 0x0A
    RING_SIZE_POS= 0x06
    
    def __init__( self, channel_number ):
        self.channel_number = channel_number
        
        offset = self.channel_number * 0x40
        self.CHx_READ_ADDR     = DMA.DMA_BASE + 0x00 + offset
        self.CHx_WRITE_ADDR    = DMA.DMA_BASE + 0x04 + offset
        self.CHx_TRANS_COUNT   = DMA.DMA_BASE + 0x08 + offset
        self.CHx_CTRL_TRIG     = DMA.DMA_BASE + 0x0C + offset
    
    def config( self, src_addr, dst_addr, count, src_inc, dst_inc, trig_dreq, ring_sel=False, ring_size_pow2=0 ):
        machine.mem32[ self.CHx_CTRL_TRIG ]   = 0
        machine.mem32[ self.CHx_READ_ADDR ]   = src_addr
        machine.mem32[ self.CHx_WRITE_ADDR ]  = dst_addr
        machine.mem32[ self.CHx_TRANS_COUNT ] = count
        
        trig_val = 0
        if( src_inc ):
            trig_val |= DMA.INCR_READ
        if( dst_inc ):
            trig_val |= DMA.INCR_WRITE
        
        trig_val |= self.channel_number << DMA.CHAIN_TO_POS
        
        trig_val |= ring_sel << DMA.RING_SEL_POS
        trig_val |= ring_size_pow2 << DMA.RING_SIZE_POS
        
        trig_val |= trig_dreq
        
        machine.mem32[ self.CHx_CTRL_TRIG ]   = trig_val
    
    def enable( self ):
        machine.mem32[ self.CHx_CTRL_TRIG ] |= DMA.DMA_EN
    
    def disable( self ):
        machine.mem32[ self.CHx_CTRL_TRIG ] = 0
    
    def is_busy( self ):
        if( machine.mem32[ self.CHx_CTRL_TRIG ] & DMA.BUSY ):
            return True
        else:
            return False

def test_dma():
    dma = DMA(0)
    src_buf = b"Hello World!"*10
    dst_buf = bytearray( 512 )
    scr_addr = uctypes.addressof( src_buf )
    dst_addr = uctypes.addressof( dst_buf )
    print( "0x{:08X}".format( scr_addr ) )
    print( "0x{:08X}".format( dst_addr ) )
    dma.config( 
        src_addr = scr_addr, 
        dst_addr = (dst_addr+0x100)&0xFFFFFF00,
        count = len( src_buf ), 
        src_inc = True, 
        dst_inc = True, 
        trig_dreq = DMA.DREQ_PERMANENT,
        ring_sel =True,
        ring_size_pow2=8
    )
    
    t0 = time.ticks_us()
    dma.enable()
    while( dma.is_busy() ):
        pass
    dma.disable()
    t1 = time.ticks_us()
    
    for i in range( len( dst_buf ) ):
        if( dst_buf[i] != 0 ):
            print( "i", i )
            print( "0x{:08X}".format( dst_addr+i ) )
            break
    
    cnt = 0
    for i in range( len( dst_buf ) ):
        if( dst_buf[i] == 0 ):
            cnt += 1
    
    print( "wrt", len(dst_buf)-cnt )
    print( "dst", dst_buf, "..." )

    print( "Transfer speed [B/s]:", len( src_buf )/((t1-t0)*1e-6) )
    print( "@CPU freq:", machine.freq() )

#test_dma()

#print( "done" )