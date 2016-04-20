#!/usr/bin/python
# LICENSE: GPL2
# (c) 2015 Kamil Wartanowicz
# (c) 2015 Szymon Mielczarek

import os, sys
import Tkinter as tk
import subprocess as sub

# Note: python-tk package needs to be installed on Linux machine

RESOURCE_DIR = 'res'
MIM_DIR = 'mim'
FGCOLOR = '#FFFFFF'
BGCOLOR = '#1F67B1'
HIGHLIGHT_BGCOLOR = '#3E7BBC'
TITLE_FONT = "Verdana 16"
LABEL1_FONT = "Verdana 10 bold"
LABEL2_FONT = "Verdana 7"

MIM_OPTIONS = [
    {'script': 'mim_live.py',
     'text1': 'Live',             'text2': 'USIM Live',  'icon': "live.gif"},
    {'script': 'mim_soft.py',
     'text1': 'Soft',             'text2': 'USIM Soft with SAT',  'icon': "soft.gif"},
    {'script': 'mim_live_live.py',
     'text1': 'Live, Live',       'text2': 'USIM Live, USIM Live with AUTH',  'icon': "live_live.gif"},
    {'script': 'mim_live_soft_sat.py',
     'text1': 'Live, Soft SAT',   'text2': 'USIM Live, SAT Soft',  'icon': "live_soft.gif"},
    {'script': 'mim_soft_live_reg.py',
     'text1': 'Soft, Live',       'text2': 'USIM Soft with SAT, USIM Live with AUTH and REG',  'icon': "soft_live.gif"},
    {'script': 'mim_soft_live_auth.py',
     'text1': 'Soft, Live',       'text2': 'USIM Soft with SAT, USIM Live with AUTH ins',  'icon': "soft_live.gif"},
    {'script': 'mim_live_live_soft_sat.py',
     'text1': 'Live, Live, Soft SAT','text2': 'USIM Live, USIM Live, SAT Soft', 'icon': "live_live_soft.gif"}
]

def runScript(event, root, scriptName):
    print scriptName
    root.destroy() # close Tk window and mainloop
    absPath = os.path.abspath(scriptName)
    sub.call(['python', absPath], shell=False)

def retag(tag, *args):
    '''Add the given tag as the first bindtag for every widget passed in'''
    for widget in args:
        widget.bindtags((tag,) + widget.bindtags())

def on_enter(event, widgets, color):
    event.widget.configure(bg=color)
    for w in widgets:
        w.configure(bg=color)

def on_leave(event, widgets, color):
    event.widget.configure(bg=color)
    for w in widgets:
        w.configure(bg=color)

def main():
    root = tk.Tk()

    lbl = tk.Label(root, text="Choose an option", fg=FGCOLOR, bg=BGCOLOR, font=TITLE_FONT)
    lbl.pack(pady=(10,0))

    # Main frame
    fraMain = tk.Frame(root)
    fraMain.pack(padx=10, pady=10)

    optionsNum = len(MIM_OPTIONS)
    imgIcons = [None] * optionsNum
    lblImages = [None] * optionsNum
    lblText1 = [None] * optionsNum
    lblText2 = [None] * optionsNum
    fraFields = [None] * optionsNum
    i = 0
    for r in MIM_OPTIONS:
        fraFields[i] = tk.Frame(fraMain, bg=BGCOLOR)
        # Images
        imgIcons[i] = tk.PhotoImage(file=(os.path.join(RESOURCE_DIR, r['icon'])))
        lblImages[i] = tk.Label(fraFields[i], image=imgIcons[i], bg=BGCOLOR)
        lblImages[i].pack(side=tk.LEFT, padx=5, pady=5)
        # Labels
        lblText1[i] = tk.Label(fraFields[i], text=r['text1'], fg=FGCOLOR, bg=BGCOLOR, font=LABEL1_FONT)
        lblText1[i].pack(pady=(10,0), anchor=tk.W) #side=tk.LEFT,
        lblText2[i] = tk.Label(fraFields[i], text=r['text2'], fg=FGCOLOR, bg=BGCOLOR, font=LABEL2_FONT)
        lblText2[i].pack(anchor=tk.W, padx=(0,3)) #side=tk.BOTTOM,
        # Frames
        fraFields[i].bind("<Enter>", lambda event, i=i: on_enter(event, [lblImages[i], lblText1[i], lblText2[i]], HIGHLIGHT_BGCOLOR))
        fraFields[i].bind("<Leave>", lambda event, i=i: on_leave(event, [lblImages[i], lblText1[i], lblText2[i]], BGCOLOR))
        fraFields[i].pack(fill=tk.BOTH)

        name = r['script']
        tag = "special" + str(i)
        retag(tag, fraFields[i], lblImages[i], lblText1[i], lblText2[i])
        root.bind_class(tag, "<Button-1>", lambda event, name=name: runScript(event, root, os.path.join(MIM_DIR, name)))
        i = i + 1

    root.configure(bg=BGCOLOR)
    root.resizable(width=tk.FALSE, height=tk.FALSE)
    if os.name != 'posix':
    #workaround, do not load icon on unix
        try:
            root.iconbitmap(os.path.join(RESOURCE_DIR, 'live.ico'))
        except tk.TclError:
            print 'No ico file found'
    root.title("simLAB")
    root.mainloop()

if __name__ == '__main__':
    main()
