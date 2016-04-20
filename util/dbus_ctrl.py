#!/usr/bin/python
# LICENSE: GPL2
# (c) 2016 Janusz Kuszczynski
"""
DBus service made as separate process, as GLib.MainLoop() is a blocking loop, interfering with gevent module.
"""

import logging
import time
import multiprocessing
import Queue
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
import gevent
from gevent import select as geventSelect
import sys

from sim import sim_shell

def startDbusProcess(self):
    gevent.spawn(privateInterpreter, self) # plac.interpreter.interact is blocking, overriding
    taskQueue = multiprocessing.Queue()
    resultQueue = multiprocessing.Queue()
    dbusProcess = DbusProcess(taskQueue, resultQueue)
    dbusProcess.daemon = True
    dbusProcess.start()
    dbusReceiveTask(self, taskQueue, resultQueue)  # acts as mainloop
    gevent.sleep(0.01)  # freeze main loop  for given amount of time
    dbusProcess.join(0.5)  # try gentle
    dbusProcess.terminate()

def getChar():
    if geventSelect.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):  # non blocking raw_input, unix only
        return sys.stdin.read(1)

def privateInterpreter(self):
    """Trivial interpreter implementation, sends command to plac interpreter"""
    logging.info("Starting plain interpreter")
    char = line = ''
    try:
        while char != '\x1b':  # \x1b = escape character
            char = getChar()
            if char:
                line += char
                line += sys.stdin.readline()
            if '\n' in line:
                self.interpreter.execute([line[:-1]], verbose=True)  # '[:-1]' to omit '\n' char
                line = ''
                sys.stdout.write(">")
                sys.stdout.flush()
            gevent.sleep(0.1)
    except KeyboardInterrupt:
        pass

def dbusReceiveTask(self, taskQueue, resultQueue):
    """Loop to execute tasks from queue"""
    try:
        while True:
            try:
                task = taskQueue.get(timeout=0.1)
                logging.info("Received task from dbus: " + str(task))
                with self.interpreter:
                    result = self.interpreter.send(task)
                    resultQueue.put(result.str)
            except Queue.Empty:
                pass  # nothing in receive task queue
            gevent.sleep(1)
    except KeyboardInterrupt:
        pass

class DbusProcess(multiprocessing.Process):
    def __init__(self, taskQueue, resultQueue):
        multiprocessing.Process.__init__(self)
        self.taskQueue = taskQueue
        self.resultQueue = resultQueue

    @staticmethod
    def _idleQueueSync():
        time.sleep(0.01)  # just to synchronize queue, otherwise task can be dropped
        return True

    def run(self):
        logging.info('D-Bus process started')
        GLib.threads_init()  # allow threads in GLib
        GLib.idle_add(self._idleQueueSync)

        DBusGMainLoop(set_as_default=True)
        dbusService = SessionDBus(self.taskQueue, self.resultQueue)

        try:
            GLib.MainLoop().run()
        except KeyboardInterrupt:
            logging.debug("\nThe MainLoop will close...")
            GLib.MainLoop().quit()
        return


class SessionDBus(dbus.service.Object, sim_shell.SimShell):
    def __init__(self, taskQueue, resultQueue):
        self.taskQueue = taskQueue
        self.resultQueue = resultQueue
        bus_name = dbus.service.BusName('org.sim.simlab', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/org/sim/simlab')

    """
    Dynamically create functions, based on sim_shell.SimShell.commands. They are exported to D-Bus.
    """
    functionTemplate = "" \
                       "def command_name(self,args=None): \n" \
                       "    self.taskQueue.put('command_name ' + args) \n" \
                       "    return self.resultQueue.get() \n" \
                       "command_name = dbus.service.method('org.sim.simlab')(command_name)   "
    for command in sim_shell.SimShell.commands:
        functionCode = functionTemplate.replace('command_name', command)
        # check how many parameters takes original function
        argumentCount = getattr(sim_shell.SimShell, command).func_code.co_argcount
        if argumentCount == 1:
            functionCode = functionCode.replace(',args=None', '')
            functionCode = functionCode.replace('+ args',     '')
        exec functionCode


