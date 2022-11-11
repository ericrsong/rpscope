import lvgl as lv

context = []
widgets = {}

def set_context( ctx ):
    global context
    context = ctx

def get_context():
    global context
    return context

def set_widgets( wgts ):
    global widgets
    widgets = wgts

def get_widgets():
    global widgets
    return widgets

style = lv.style_t()
style.init()
style.set_pad_all( 2 )
style.set_pad_gap( 2 ) 
style.set_radius( 2 )
style.set_border_width( 0 )
style.set_bg_color( lv.palette_lighten( lv.PALETTE.GREY, 3 ) )

class Cont:
    def __init__( self, x=5, y=5, w=480-10, h=320-10 ):
        self.obj = lv.obj( context[-1] )
        self.obj.add_style( style, 0 )
        #self.obj.set_flex_flow( lv.FLEX_FLOW.COLUMN )
        self.obj.set_pos( x, y )
        self.obj.set_size( w, h )
        #if( len( context ) == 3 ):
        self.obj.set_style_border_width( 0, 0 )
    
    def __enter__( self ):
        context.append( self.obj )
        return self.obj
    
    def __exit__( self, a, b, c ):
        context.pop()

class Column:
    def __init__( self ):
        self.obj = lv.obj( context[-1] )
        self.obj.add_style( style, 0 )
        self.obj.set_flex_flow( lv.FLEX_FLOW.COLUMN )
        if( len( context ) == 3 ):
            self.obj.set_style_border_width( 2, 0 )
    
    def __enter__( self ):
        context.append( self.obj )
        return self.obj
    
    def __exit__( self, a, b, c ):
        self.obj.set_size( lv.SIZE.CONTENT, lv.SIZE.CONTENT )
        context.pop()

class Row:
    def __init__( self ):
        self.obj = lv.obj( context[-1] )
        self.obj.add_style( style, 0 )
        self.obj.set_flex_flow( lv.FLEX_FLOW.ROW )
        if( len( context ) == 3 ):
            self.obj.set_style_border_width( 2, 0 )
    
    def __enter__( self ):
        context.append( self.obj )
        return self.obj
    
    def __exit__( self, a, b, c ):
        self.obj.set_size( lv.SIZE.CONTENT, lv.SIZE.CONTENT )
        context.pop()

def add_button( name, w=40, h=20, radius=5, checkable=False ):
    btn = lv.btn( context[-1] )
    btn.set_size( w, h )
    btn.set_style_radius( radius, 0 )
    btn.set_style_border_width( 1, 0 )
    btn.set_style_border_color( lv.palette_darken( lv.PALETTE.BLUE_GREY, 2 ), 0 )
    btn.set_style_bg_color( lv.palette_lighten( lv.PALETTE.BLUE_GREY, 2 ), 0 )
    btn.set_style_bg_color( lv.palette_main( lv.PALETTE.GREEN ), 1 )
    if( checkable ):
        btn_run.add_flag( lv.obj.FLAG.CHECKABLE )
    lbl = lv.label( btn )
    lbl.set_text( name.split("#")[0] )
    lbl.center()
    assert name not in widgets
    widgets[ name ] = btn
    return btn

def add_spinbox( name, w=100, h=40 ):
    spinbox = lv.spinbox( context[-1] )
    spinbox.set_range( 0, 1_000_000_000 )
    spinbox.set_digit_format( 9, 0 )
    spinbox.set_size( w, h )
    #lbl.set_style_border_width( 1, 0 )
    assert name not in widgets
    widgets[ name ] = spinbox
    return spinbox

def add_label( name, w=40, h=20 ):
    lbl = lv.label( context[-1] )
    lbl.set_text( name.split("#")[0] )
    lbl.set_size( w, h )
    assert name not in widgets
    widgets[ name ] = lbl
    return lbl

def add_line( x=0, y=0, w=40, h=1, width=1 ):
    line = lv.line( context[-1] )
    line.set_points( [{"x":x, "y":y}, {"x":x+w-1, "y":y+h-1} ], 2 ) 
    line.set_style_line_width( width, 0 )
    #assert name not in widgets
    #widgets[ name ] = line
    return line

print("done")