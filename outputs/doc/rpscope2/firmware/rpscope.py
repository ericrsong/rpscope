import os
import time
import machine
import rp2
import array
import uctypes

import lvgl as lv
from gui.dear_lvgl import *
#from gui.asm_set_pixel import asm_set_pixel
from gui.asm_set_pixel2 import asm_set_pixel2

from hal.dma import DMA
from hal.adc08100 import Adc08100
from hal.trigger import Trigger


def capture( sps, buf, rising, pre, post ):

    db  = machine.Pin( 0 ) # out
    sck = machine.Pin( 21 ) # side 0
    mux = machine.Pin( 20 ) # side 0
    trig = machine.Pin( 7, machine.Pin.IN, machine.Pin.PULL_DOWN ) # trigger
    #trig = machine.Pin( 19, machine.Pin.IN, machine.Pin.PULL_DOWN ) # trigger

    buf_addr_aligned = (uctypes.addressof( buf )+0xFF)&0xFFFFFF00
    buf_offset_aligned = buf_addr_aligned - uctypes.addressof( buf )

    t0 = time.ticks_us()
    adc = Adc08100( sps, mux, db, use_trigger=True )
    t1 = time.ticks_us()

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

    t0 = time.ticks_us()
    adc.dma.enable()
    adc.sm.active( True )
    t1 = time.ticks_us()

    t0 = time.ticks_us()    
    trigger = Trigger( sps, trig, rising )
    t1 = time.ticks_us()

    DMA1_TRIG = 0x50000000 + 1 * 0x40 + 0x0C

    t0 = time.ticks_us()    
    trans_count0 = machine.mem32[ adc.dma.CHx_TRANS_COUNT ]
    trigger.read( pre, post, DMA1_TRIG )
    trans_count1 = machine.mem32[ adc.dma.CHx_TRANS_COUNT ]
    t1 = time.ticks_us()

    t0 = time.ticks_us()    
    adc.dma.disable()
    adc.sm.active( False )
    t1 = time.ticks_us()

    trans_count_diff = trans_count0 - trans_count1 # - 1

    
    trans_count_diff = trans_count_diff&0xFF

    return buf_offset_aligned, trans_count_diff


class Scope:
    def __init__( self, parent, adc, trig, display_driver, len_sample, point_count ):
        self.parent = parent
        self.adc = adc
        self.trig = trig
        self.display_driver = display_driver
        
        self.run = False
        self.single = False

        self.horizontal_scale = 1
        self.horizontal_position = 0

        self.channel1_scale = 1
        self.channel1_position = 0
        self.channel2_scale = 1
        self.channel2_position = 0
        self.channel1_selected = True

        self.trigger_channel1 = True
        self.trigger_edge = False
        self.trigger_auto = False
        self.trigger_position = 0

        self.chart = None
        
        self.context = []
        self.widgets = {}
        print( "build_ui" )
        self.build_ui( self.parent )
        
        self.len_sample = len_sample
        self.point_count = point_count
        self.buf_adc_a = bytearray( 512 )#self.len_sample + self.point_count )
        self.buf_adc_b = bytearray( 512 )#self.len_sample + self.point_count )
        self.adc_used = 0
        self.trigger_pos_a = 0
        self.trigger_pos_b = 0
        self.buf_adc_a_align = 0
        self.buf_adc_b_align = 0
        
        self.count_start = 0
        self.count_end = 0

        self.params = array.array( "I", [0 for n in range( 13 )] )
        print( "build_ui done" )
    
    def test_init( self, dst_buf, only_dma=False ):
        pass
    
    def test( self, dst_buf, delay_pre, delay_post, cb_enable=False ):
        pass
    
    def process( self ):
        if( self.display_driver.dma_running == True ):
            self.display_driver.lcd.wait_dma()
            self.display_driver.dma_running = False
        
        scope_run = self.widgets["Run#M"].get_state() & lv.STATE.CHECKED
        trigger_edge = self.widgets["Edge#T"].get_state() & lv.STATE.CHECKED
        hs = self.horizontal_scale
        hp = self.horizontal_position
        sps = [
            1_000_000,
            2_000_000,
            5_000_000,
            10_000_000,
            20_000_000,
            50_000_000,
            100_000_000,
        ][hs]
        
        if( scope_run or self.single ):
            self.single = False
            if( self.adc_used == 0 ):
                self.adc_used = 1
                t0 = time.ticks_us()
                #sps = 1_000_000
                self.buf_adc_a_align, self.trigger_pos_a = capture( sps, self.buf_adc_a, trigger_edge, 1024, hp+128 )
                t1 = time.ticks_us()
                print( "aaaa", t1-t0 )
                #time.sleep_ms( 100 )
                t0 = time.ticks_us()

                self.params[0] = 10+32
                self.params[1] = 32
                
                addr_a = uctypes.addressof( self.buf_adc_a )
                align_a = ((addr_a+0xFF)&0xFFFFFF00)-addr_a
                self.params[2] = addr_a
                self.params[3] = align_a
                self.params[4] = self.trigger_pos_a
                self.params[5] = 0x001F
                
                addr_b = uctypes.addressof( self.buf_adc_b )
                align_b = ((addr_b+0xFF)&0xFFFFFF00)-addr_b
                self.params[6] = addr_b
                self.params[7] = align_b
                self.params[8] = self.trigger_pos_b
                self.params[9] = 0xFFFF
                
                self.params[10] = 256
                self.params[11] = 0xFF
                
                self.params[12] = 12
                asm_set_pixel2( uctypes.addressof( self.params ) )
                t1 = time.ticks_us()
                print( "bbbb", t1-t0 )
            else:
                self.adc_used = 0

                t0 = time.ticks_us()
                #sps = 1_000_000
                self.buf_adc_b_align, self.trigger_pos_b = capture( sps, self.buf_adc_b, trigger_edge, 1024, hp+128 )
                t1 = time.ticks_us()
                print( "cccc", t1-t0 )

                t0 = time.ticks_us()
                self.params[0] = 10+32
                self.params[1] = 32
                
                addr_b = uctypes.addressof( self.buf_adc_b )
                align_b = ((addr_b+0xFF)&0xFFFFFF00)-addr_b
                self.params[2] = addr_b
                self.params[3] = align_b
                self.params[4] = self.trigger_pos_b
                self.params[5] = 0x001F
                
                addr_a = uctypes.addressof( self.buf_adc_a )
                align_a = ((addr_a+0xFF)&0xFFFFFF00)-addr_a
                self.params[6] = addr_a
                self.params[7] = align_a
                self.params[8] = self.trigger_pos_a
                self.params[9] = 0xFFFF
                
                self.params[10] = 256
                self.params[11] = 0xFF
                
                self.params[12] = 12
                asm_set_pixel2( uctypes.addressof( self.params ) )
                t1 = time.ticks_us()
                print( "dddd", t1-t0 )
    
    def cb_run( self, evt ):
        if( self.widgets["Run#M"].get_state() & lv.STATE.CHECKED ):
            self.widgets["#Status"].set_text( "Running" )
            self.widgets["Run#M"].get_child(0).set_text( lv.SYMBOL.STOP )
        else:
            self.widgets["#Status"].set_text( "Stop" )  
            self.widgets["Run#M"].get_child(0).set_text( lv.SYMBOL.PLAY )
    
    def cb_single( self, evt ):
        self.single = True
        self.widgets["Run#M"].clear_state( lv.STATE.CHECKED )
        self.widgets["Run#M"].get_child(0).set_text( lv.SYMBOL.PLAY )
        #print( "sinlge", self.single )
        self.widgets["#Status"].set_text( "Single" )
    
    def cb_save( self, evt ):
        idx = len( [name for name in os.listdir() if "data" in name] )
        fl_name = "data{}.txt".format( idx )
        
        if( self.adc_used == 1 ):
            buf_adc = self.buf_adc_a
            addr = uctypes.addressof( self.buf_adc_a )
            align = ((addr+0xFF)&0xFFFFFF00)-addr
            trigger = self.trigger_pos_a
        else:
            buf_adc = self.buf_adc_b
            addr = uctypes.addressof( self.buf_adc_b )
            align = ((addr+0xFF)&0xFFFFFF00)-addr
            trigger = self.trigger_pos_b
        
        with open( fl_name, "w" ) as fl:
            for i in range( 256 ):
                fl.write( "{}\n".format( buf_adc[ align + ((trigger + i)&0xFF) ] ) )
        
        self.widgets["#Status"].set_text( fl_name )

    def cb_horizontal_scale_inc( self, evt ):
        if( self.horizontal_scale < 6 ):
            self.horizontal_scale += 1
        sps = [ "1 M", "2 M", "5 M", "10 M", "20 M", "50 M", "100 M" ][self.horizontal_scale]
        self.widgets[ "#lHS" ].set_text( "HS {} Sps".format( sps ) )

    def cb_horizontal_scale_set( self, evt ):
        self.widgets[ "#lHS" ].set_text( "HS {} S/D".format( self.horizontal_scale ) )
        sps = [ "1 M", "2 M", "5 M", "10 M", "20 M", "50 M", "100 M" ][self.horizontal_scale]
        self.widgets[ "#lHS" ].set_text( "HS {} Sps".format( sps ) )

    def cb_horizontal_scale_dec( self, evt ):
        if( self.horizontal_scale > 0 ):
            self.horizontal_scale -= 1
        sps = [ "1 M", "2 M", "5 M", "10 M", "20 M", "50 M", "100 M" ][self.horizontal_scale]
        self.widgets[ "#lHS" ].set_text( "HS {} Sps".format( sps ) )

    def cb_horizontal_position_inc( self, evt ):
        if( self.horizontal_position < 1024 ):
            self.horizontal_position += 1
        self.widgets[ "#lHP" ].set_text( "HP {} S".format( self.horizontal_position ) )

    def cb_horizontal_position_set( self, evt ):
        self.horizontal_position = 0
        self.widgets[ "#lHP" ].set_text( "HP {} S".format( self.horizontal_position ) )

    def cb_horizontal_position_dec( self, evt ):
        if( self.horizontal_position > -127 ):
            self.horizontal_position -= 1
        self.widgets[ "#lHP" ].set_text( "HP {} S".format( self.horizontal_position ) )

    def cb_channel_select( self, evt ):
        self.channel1_selected = not self.channel1_selected
        self.widgets["CHS#VS"].get_child(0).set_text( "CH1" if self.channel1_selected else "CH2" )
        #print( "channel1_selected", self.channel1_selected )
    
    def cb_vertical_scale_inc( self, evt ):
        if( self.channel1_selected ):
            self.channel1_scale += 1
            self.widgets[ "#lVS1" ].set_text( "VS1 {} V/D".format( self.channel1_scale ) )
        else:
            self.channel2_scale += 1
            self.widgets[ "#lVS2" ].set_text( "VS2 {} V/D".format( self.channel2_scale ) )
        
    def cb_vertical_scale_set( self, evt ):
        if( self.channel1_selected ):
            self.channel1_scale = 1
            self.widgets[ "#lVS1" ].set_text( "VS1 {} V/D".format( self.channel1_scale ) )
        else:
            self.channel2_scale = 1
            self.widgets[ "#lVS2" ].set_text( "VS2 {} V/D".format( self.channel2_scale ) )

    def cb_vertical_scale_dec( self, evt ):
        if( self.channel1_selected ):
            self.channel1_scale -= 1
            self.widgets[ "#lVS1" ].set_text( "VS1 {} V/D".format( self.channel1_scale ) )
        else:
            self.channel2_scale -= 1
            self.widgets[ "#lVS2" ].set_text( "VS2 {} V/D".format( self.channel2_scale ) )

    def cb_vertical_position_inc( self, evt ):
        if( self.channel1_selected ):
            self.channel1_position += 1
            self.widgets[ "#lVP1" ].set_text( "VP1 {} V".format( self.channel1_position ) )
        else:
            self.channel2_position += 1
            self.widgets[ "#lVP2" ].set_text( "VP2 {} V".format( self.channel2_position ) )

    def cb_vertical_position_set( self, evt ):
        if( self.channel1_selected ):
            self.channel1_position = 1
            self.widgets[ "#lVP1" ].set_text( "VP1 {} V".format( self.channel1_position ) )
        else:
            self.channel2_position = 1
            self.widgets[ "#lVP2" ].set_text( "VP2 {} V".format( self.channel2_position ) )

    def cb_vertical_position_dec( self, evt ):
        if( self.channel1_selected ):
            self.channel1_position -= 1
            self.widgets[ "#lVP1" ].set_text( "VP1 {} V".format( self.channel1_position ) )
        else:
            self.channel2_position -= 1
            self.widgets[ "#lVP2" ].set_text( "VP2 {} V".format( self.channel2_position ) )

    def cb_trigger_position_inc( self, evt ):
        self.trigger_position += 1
        self.widgets[ "#lTP" ].set_text( "TP {} V".format( self.trigger_position ) )
        self.trig.duty_u16( int( 0xFFFF*1.024/3.3 ) + self.trigger_position*256 )

    def cb_trigger_position_set( self, evt ):
        self.trigger_position = 0
        self.widgets[ "#lTP" ].set_text( "TP {} V".format( self.trigger_position ) )
        self.trig.duty_u16( int( 0xFFFF*1.024/3.3 ) + self.trigger_position*256 )

    def cb_trigger_position_dec( self, evt ):
        self.trigger_position -= 1
        self.widgets[ "#lTP" ].set_text( "TP {} V".format( self.trigger_position ) )
        self.trig.duty_u16( int( 0xFFFF*1.024/3.3 ) + self.trigger_position*256 )

    def build_ui( self, parent ):
        width = 160
        point_count = 480-width
        
        self.context.append( parent )
        set_context( self.context )
        set_widgets( self.widgets )
        
        with Cont():
            with Cont( 0, 0, 480-width, 320-15 ):
                with Column():
                    lblw= 74
                    with Row():
                        #add_label( "SCOPY", w=60 ).set_style_text_font( lv.font_montserrat_16, 0 )
                        #cont = lv.obj( self.context[-1] )
                        #cont.add_style( style, 0 )
                        #cont.set_size( 40, 20 )
                        #img = lv.img( cont )
                        #img.set_src( img_scopy_png )
                        #img.center()
                        #img.set_size( 60, 40 )
                        add_label( "#Status", w=lblw )
                        add_label( "#lHS", w=lblw ).set_text( "1 S/D" )
                        add_label( "#lHP", w=lblw ).set_text( "0 S" )
                        add_label( "#lTP", w=lblw ).set_text( "0 V" )

                    self.chart = lv.chart( self.context[-1] )
                    self.chart.set_size( 480-160-12, 300-5-50-10 )
                    #self.chart.set_style_bg_color( lv.palette_main( 0 ), 0 )
                    self.chart.set_div_line_count( 8, 10 )
                    with Row():
                        add_label( "#lVS1", w=lblw ).set_text( "1 V/D" )
                        add_label( "#lVP1", w=lblw ).set_text( "0 V" )
                        add_label( "#lVS2", w=lblw ).set_text( "1 V/D" )
                        add_label( "#lVP2", w=lblw ).set_text( "0 V" )
            with Cont( 480-width, 0, width-15, 320-15 ):
                with Column():
                    with Row():
                        add_button( "Run#M" ).add_event_cb( self.cb_run, lv.EVENT.VALUE_CHANGED, None )
                        self.widgets["Run#M"].add_flag( lv.obj.FLAG.CHECKABLE )
                        self.widgets["Run#M"].get_child(0).set_text( lv.SYMBOL.PLAY )
                        add_button( "Sing#M" ).add_event_cb( self.cb_single, lv.EVENT.CLICKED, None )
                        self.widgets["Sing#M"].get_child(0).set_text( lv.SYMBOL.NEXT )
                        add_button( "#Save" ).add_event_cb( self.cb_save, lv.EVENT.CLICKED, None )
                        self.widgets["#Save"].get_child(0).set_text( lv.SYMBOL.SAVE )
                    add_line( 0, 2, 120+2*4, 1 )

                    add_label( "Horizontal", w=100 )
                    with Row():
                        add_button( "+#HT" ).add_event_cb( self.cb_horizontal_scale_inc, lv.EVENT.CLICKED, None )
                        self.widgets["+#HT"].get_child(0).set_text( lv.SYMBOL.PLUS )
                        add_button( "Time" ).add_event_cb( self.cb_horizontal_scale_set, lv.EVENT.CLICKED, None )
                        add_button( "-#HT" ).add_event_cb( self.cb_horizontal_scale_dec, lv.EVENT.CLICKED, None )
                        self.widgets["-#HT"].get_child(0).set_text( lv.SYMBOL.MINUS )
                    with Row():
                        add_button( "+#HP" ).add_event_cb( self.cb_horizontal_position_inc, lv.EVENT.CLICKED, None )
                        self.widgets["+#HP"].get_child(0).set_text( lv.SYMBOL.PLUS )
                        add_button( "Pos#H").add_event_cb( self.cb_horizontal_position_set, lv.EVENT.CLICKED, None )
                        add_button( "-#HP" ).add_event_cb( self.cb_horizontal_position_dec, lv.EVENT.CLICKED, None )
                        self.widgets["-#HP"].get_child(0).set_text( lv.SYMBOL.MINUS )
                        self.widgets["+#HP"].add_event_cb( self.cb_horizontal_position_inc, lv.EVENT.LONG_PRESSED_REPEAT, None )
                        self.widgets["-#HP"].add_event_cb( self.cb_horizontal_position_dec, lv.EVENT.LONG_PRESSED_REPEAT, None )
                    add_line( 0, 2, 120+2*4, 1 )

                    add_label( "Vertical", w=80 )
                    with Row():
                        add_button( "CH1#V" ).add_flag( lv.obj.FLAG.CHECKABLE )
                        add_button( "CH2#V" ).add_flag( lv.obj.FLAG.CHECKABLE )
                        self.widgets["CH1#V"].set_style_bg_color( lv.palette_lighten( lv.PALETTE.RED, 1 ), 1 )
                        self.widgets["CH2#V"].set_style_bg_color( lv.palette_lighten( lv.PALETTE.BLUE, 1 ), 1 )
                        
                        add_button( "CHS#VS" ).add_flag( lv.obj.FLAG.CHECKABLE )
                        self.widgets["CHS#VS"].set_style_bg_color( lv.palette_lighten( lv.PALETTE.RED, 1 ), 0 )
                        self.widgets["CHS#VS"].set_style_bg_color( lv.palette_lighten( lv.PALETTE.BLUE, 1 ), 1 )
                        self.widgets["CHS#VS"].add_event_cb( self.cb_channel_select, lv.EVENT.CLICKED, None )
                        self.widgets["CHS#VS"].get_child(0).set_text( "CH1" )
                        
                    with Row():
                        add_button( "+#VV" ).add_event_cb( self.cb_vertical_scale_inc, lv.EVENT.CLICKED, None )
                        self.widgets["+#VV"].get_child(0).set_text( lv.SYMBOL.PLUS )
                        add_button( "Volt" ).add_event_cb( self.cb_vertical_scale_set, lv.EVENT.CLICKED, None )
                        add_button( "-#VV" ).add_event_cb( self.cb_vertical_scale_dec, lv.EVENT.CLICKED, None )
                        self.widgets["-#VV"].get_child(0).set_text( lv.SYMBOL.MINUS )
                    with Row():
                        add_button( "+#VP" ).add_event_cb( self.cb_vertical_position_inc, lv.EVENT.CLICKED, None )
                        self.widgets["+#VP"].get_child(0).set_text( lv.SYMBOL.PLUS )
                        add_button( "Pos#V").add_event_cb( self.cb_vertical_position_set, lv.EVENT.CLICKED, None )
                        add_button( "-#VP" ).add_event_cb( self.cb_vertical_position_dec, lv.EVENT.CLICKED, None )
                        self.widgets["-#VP"].get_child(0).set_text( lv.SYMBOL.MINUS )
                    add_line( 0, 2, 120+2*4, 1 )

                    add_label( "Trigger", w=80 )
                    with Row():
                        add_button( "CH12#T"  ).add_flag( lv.obj.FLAG.CHECKABLE )
                        self.widgets["CH12#T"].get_child(0).set_text( "CH1" )
                        self.widgets["CH12#T"].set_style_bg_color( lv.palette_lighten( lv.PALETTE.RED, 1 ), 0 )
                        self.widgets["CH12#T"].set_style_bg_color( lv.palette_lighten( lv.PALETTE.BLUE, 1 ), 1 )
                        add_button( "Edge#T" ).add_flag( lv.obj.FLAG.CHECKABLE )
                        add_button( "Auto#T" ).add_flag( lv.obj.FLAG.CHECKABLE )
                    with Row():
                        add_button( "+#TP" ).add_event_cb( self.cb_trigger_position_inc, lv.EVENT.CLICKED, None )
                        self.widgets["+#TP"].get_child(0).set_text( lv.SYMBOL.PLUS )
                        add_button( "Pos#T").add_event_cb( self.cb_trigger_position_set, lv.EVENT.CLICKED, None )
                        add_button( "-#TP" ).add_event_cb( self.cb_trigger_position_dec, lv.EVENT.CLICKED, None )
                        self.widgets["-#TP"].get_child(0).set_text( lv.SYMBOL.MINUS )
                        self.widgets["+#TP"].add_event_cb( self.cb_trigger_position_inc, lv.EVENT.LONG_PRESSED_REPEAT, None )
                        self.widgets["-#TP"].add_event_cb( self.cb_trigger_position_dec, lv.EVENT.LONG_PRESSED_REPEAT, None )
                        
                        


