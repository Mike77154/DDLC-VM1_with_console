## console.rpy

# This file defines the Monika Console contents that appears in the game when
# Monika deletes characters.

# This file has heavily changed from DDLC to provide better access to call the
# console than via labels. To call, do $ run_input(input="Text", output="Output").
# To only show, the console, just do `show screen console_screen`.
# Thank you Lezalith for assistance in making this new console!

init -1:

    # None or tuple with (input, output).
    default new_input = None

    # List with outputs.
    default console_history = []
    default console_cmd = ""
    default _console_seen = 0
    # Not to be changed midgame.
    # Delay after input has finished showing, before output is displayed.
    define console_delay = 0.5
    define console_cps = 30

init python:

    def _concat_outputs(tech, narr):
        tech = tech or u""
        narr = narr or u""
        return (tech + u"\n" + narr) if (tech and narr) else (tech or narr)

    def run_input(input, output):
        # --- HOOK LITERAL: os.remove("...") ---
        # Si coincide, ejecuta de verdad y pega el narrativo al final.
        try:
            handled, tech = _literal_os_remove_bridge(input, narrative_output=None)
            if handled:
                output = _concat_outputs(tech, output)
        except Exception:
            pass
        # --- FIN HOOK ---

        # intercepta clear/cls invocados vía run_input (tu lógica original)
        if isinstance(input, basestring) and input.strip().lower() in ("clear", "cls"):
            store.console_history = []
            store._console_seen = 0
            store.new_input = None
            renpy.restart_interaction()
            renpy.show_screen("console_screen")
            return

        # ⚠️ IMPORTANTE: NO crear 'new_input' local; usa SIEMPRE store.new_input
        store.new_input = (input, output)

        if renpy.get_screen("console_screen"):
            renpy.hide_screen("console_screen")
        renpy.call_screen("console_screen", finish=True)
        renpy.show_screen("console_screen")

    def add_to_history(inp):
        # inp es (input, output)
        store.console_history.insert(0, inp[1])
        # límite de historial (ajústalo a gusto)
        if len(store.console_history) > 200:
            store.console_history.pop(200)

    def input_finished():
        add_to_history(store.new_input)
        store.new_input = None
        renpy.restart_interaction()

    def clear_history():
        store.console_history = []
        store._console_seen = 0
        # opcional: cancela input animándose
        store.new_input = None
        renpy.restart_interaction()



screen console_screen(finish=False):

    style_prefix "console_screen"

    # NEW: adjustment para controlar el scroll del viewport
    default adj_hist = ui.adjustment()      # <-- clave

    default finish_actions = [Function(input_finished), SetScreenVariable("in_progress", False), Return()]

    # String of input to show.
    # It is put outside of the new_input variable so it doesn't
    # start over and over.
    default new_input_code = "_"

    # Changes to True once a new code_text
    default in_progress = False


    # If text is not in the process of showing.
    if not in_progress:
        if console_cmd == "":
            $ new_input_code = "_"
        else:
            $ new_input_code = ""

        # If a new_input is available, set it as code to display.
        if store.new_input:

            $ in_progress = True
            $ new_input_code = store.new_input[0]



    # New code is showing.
    if in_progress:

        timer ( float(len(renpy.filter_text_tags(new_input_code, deny = []))) / float(console_cps) + console_delay ) action finish_actions

    frame:

        vbox:
            hbox:
                xpos 15 ypos 10
                text ">"
                xmaximum 460
                text new_input_code :
                    slow_cps 30

                if not in_progress:
                    input:
                        value VariableInputValue("console_cmd")
                        pixel_width 460    # debe coincidir con el ancho del contenedor
                        text_align 1.0     # ALINEA EL TEXTO A LA DERECHA
                        allow None
                        copypaste True
                        focus True
                        font "gui/font/F25_Bank_Printer.ttf"
                        color "#fff"
                        size 18
                        outlines []
            # --- HISTORIAL SCROLLEABLE ---
            viewport id "vp_cons_hist":      # NEW
                xpos 26 ypos 30              # NEW
                xmaximum 460                 # NEW
                ymaximum 120                 # NEW (ajusta a tu gusto, cabe en ysize 180)
                scrollbars "vertical"        # NEW
                mousewheel True              # NEW
                draggable True               # NEW
                clipping True                # NEW
                yadjustment adj_hist
                has vbox                     # NEW
                spacing 5                    # NEW
                for x in store.console_history:
                    text x substitute False xmaximum 440  # NEW: wrap suave


                # Enter solo cuando se puede escribir
                key "K_RETURN" action [Function(console_submit, console_cmd), SetVariable("console_cmd","")]
                key "K_KP_ENTER" action [Function(console_submit, console_cmd), SetVariable("console_cmd","")]

        # --- AUTOSCROLL ARRIBA cuando hay nueva línea (porque el último está al inicio) ---
    if len(store.console_history) != _console_seen:
        timer 0.01 action [
            SetVariable("_console_seen", len(store.console_history)),
            SetField(adj_hist, "value", 0.0)          # ir al tope
        ]                                           # NEW

style console_screen_frame:
    background Frame(Transform(Solid("#333"), alpha=0.75))
    xsize 480
    ysize 180

# This style declares the text appearance of the text shown in the console in-game.
style console_screen_text:
    font "gui/font/F25_Bank_Printer.ttf"
    color "#fff"
    size 18
    outlines []

# This label clears all console history and commands from the console in-game.
# Decided to keep this for now as it just pauses stuff.
label updateconsole_clearall(text="", history=""):
    $ pause(len(text) / 30.0 + 0.5)
    $ pause(0.5)
    return
