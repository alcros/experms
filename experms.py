#!/usr/bin/env python2
# -*- coding: utf-8 -*-

##
##         //\  //\  //\  //\  //\  //\  //\
##        //  \//  \//  \//  \//  \//  \//  \
##       //    _   _   _   _   _   _   _     \
##      //    / \ / \ / \ / \ / \ / \ / \     \
##     //    ( E ) X ) P ) E ) R ) M ) S )     \
##    //  __  \_/ \_/ \_/ \_/ \_/ \_/ \_/   __  \
##   // //  \                             //  \  \
##  // //    \  //\  //\  //\  //\  //\  //    \  \
##  \_//      \//  \//  \//  \//  \//  \//      \_//
##
##                 version 0.3 - 2013
##

##=================================================================================================================================
##
##         FILE: experms.py
##
##        USAGE: experms.py [start|stop|restart|restore|status|log|err|dircount|-h|foreground]
##
##  DESCRIPTION: Runs as daemon and monitors file-changes happened in the directory/directories set in experms.conf.
##               If changes happened, it adjusts the file-permissions and ownership/group.
##               Further it is able to restore all the ownerships and permissions of all files based on the config-file.
##
##       CONFIG: experms.conf
##
## REQUIREMENTS: python2, python2-pyinotify
##
##        NOTES: Experms uses inotify to monitor the directories.
##               Inotify allows only a limited number of directories to watch per user. Per default this is set to 8192.
##               You can increase this number by writing to /proc/sys/fs/inotify/max_user_watches.
##               You can check the number of directories recursively with:
##               'experms.py dircount'
##
##       AUTHOR: Fabio Rämi - fabio(a)dynamix-tontechnik.ch
##
##      VERSION: 0.3
##
##      LICENCE: GNU GPL v3.0 or later.
##               http://www.gnu.org/licenses/gpl-3.0.txt
##               Experms comes with absolutely no warranty!
##               
##      COPYING: Experms is free software: you can redistribute it and/or modify
##               it under the terms of the GNU General Public License as published by
##               the Free Software Foundation, either version 3 of the License, or
##               (at your option) any later version.
##           
##               Experms is distributed in the hope that it will be useful,
##               but WITHOUT ANY WARRANTY; without even the implied warranty of
##               MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##               GNU General Public License for more details.
##           
##               You should have received a copy of the GNU General Public License
##               along with Experms.  If not, see <http://www.gnu.org/licenses/>.
##
##      CREATED: 2013
##
##=================================================================================================================================

# bold: "\033[1m"
# normal: "\033[0m"

import sys
import time
import os
import re
from sys import stdout
from time import localtime, strftime
from daemon import Daemon
import check_config
try:
  import pyinotify
except ImportError:
  print >> sys.stderr, "Error: Module pyinotify not found. Please install the package 'python2-pyinotify'.\nMaybe this package is called differently in your distribution (e.g. python2.7-pyinotify)."
  sys.exit(1)

pidfile = '/tmp/experms.pid'
stdoutfile = sys.path[0] + '/experms.log'
stderrfile = sys.path[0] + '/experms.err'

## Taken from Sander Marechal
## (http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/)
class MyDaemon(Daemon):
  def start(self):
    """
    Start the daemon
    """
    # Check for a pidfile to see if the daemon already runs
    try:
      pf = file(self.pidfile,'r')
      pid = int(pf.read().strip())
      pf.close()
    except IOError:
      pid = None

    if pid:
      if checkpid(pid) == True:
        message = "pidfile %s already exist. Experms already running?\n"
        sys.stderr.write(message % self.pidfile)
        sys.exit(1)
      os.remove(self.pidfile)
    # load the configuration
    config = self.loadconfig()
    if config.restore == 'yes':
      stdout.write("Restore is in progress...")
      restore()
      stdout.write(" Done.\n")
      stdout.flush()
      restorelogcount = saferestorelog()
      print restorelogcount, 'files have been changed.'
    print "Experms daemon started."
    # Start the daemon
    self.daemonize()
    self.run()

  def loadconfig(self):
    global config
    config = check_config.Check()
    return config
    #sys.exit(0)
    
  def run(self):
    # do not use IN_MOVED_SELF! It will burn down your house!
    mask = pyinotify.IN_CREATE | pyinotify.IN_MODIFY | pyinotify.IN_ATTRIB | pyinotify.IN_MOVED_TO # watched events
    
    # watch manager
    wm = pyinotify.WatchManager()
    notifier = pyinotify.ThreadedNotifier(wm, MyEventHandler())
    
    # Start the notifier from a new thread, without doing anything as no
    # directory or file are currently monitored yet.
    notifier.start()
    # Start watching a path
    wdd = wm.add_watch(config.dirname, mask, rec=True, auto_add=True)
    
    # user input
    try:
      while True:
        time.sleep(0.05)
    except KeyboardInterrupt:
      # happens when the user presses ctrl-c
      print("\nBye-bye!")
      wm.rm_watch(wdd.values())
      notifier.stop()
      sys.exit(0)
    except EOFError:
      # happens when the user presses ctrl-d
      print("\nBye-bye!")
      wm.rm_watch(wdd.values())
      notifier.stop()
      
      sys.exit(0)

# Taken from http://www.saltycrane.com/blog/2010/04/monitoring-filesystem-python-and-pyinotify/
class MyEventHandler(pyinotify.ProcessEvent):
    def process_IN_ACCESS(self, event):
        print "ACCESS event:", event.pathname

    def process_IN_ATTRIB(self, event):
        prepare(event.pathname, "ATTRIB")

    def process_IN_CLOSE_NOWRITE(self, event):
        print "CLOSE_NOWRITE event:", event.pathname

    def process_IN_CLOSE_WRITE(self, event):
        prepare(event.pathname, "IN_CLOSE_WRITE")

    def process_IN_CREATE(self, event):
        self.olddir = event.pathname
        prepare(event.pathname, "CREATE")

    def process_IN_DELETE(self, event):
        print "DELETE event:", event.pathname

    def process_IN_MODIFY(self, event):
        prepare(event.pathname, "MODIFY")

    def process_IN_OPEN(self, event):
        print "OPEN event:", event.pathname

    def process_IN_MOVE_SELF(self, event):
        prepare(event.pathname, "IN_MOVE_SELF")
        
    def process_IN_MOVED_TO(self, event):
        prepare(event.pathname, "IN_MOVED_TO")

def prepare(directory, event=None, restore=False):
  #print 'directory:', directory
  #print 'event:', event
  dirhighest = 0
  for nr, item in enumerate(config.dirname):
    #if item == directory:
      #continue
    tempdirhighest = 0
    if not item in directory:
      continue
    for count, thing in enumerate(directory.split('/')):
      #if thing == directory:
        #continue
      try:
        item.split('/')[count]
      except IndexError:
        break
      if thing == item.split('/')[count]:
        tempdirhighest = tempdirhighest + 1
    if tempdirhighest > dirhighest:
      dirhighest = tempdirhighest
      ruledir = nr

  # check if the file is excluded or what rules have to take effect
  if not config.excludepattern[nr] == None:
    if os.path.isfile(directory):
      p = re.compile(config.excludepattern[nr])
      if p.search(os.path.basename(directory)):
        return
  if config.excludedir[nr] == None:
    highest = 0
  else:
    highest = 0
    for item in config.excludedir[nr]:
      if not item in directory:
        continue
      temphighest = 0
      for nr, thing in enumerate(directory.split('/')):
        try:
          item.split('/')[nr]
        except IndexError:
          break
        if thing == item.split('/')[nr]:
          temphighest = temphighest + 1
      if temphighest > highest:
        highest = temphighest
  
  if highest > dirhighest:
    return

  action(directory, event, ruledir, restore)

# collects all the filenames in the monitored directories
# returns a list: [[filenames],[dirnames],[allnames],count]
def collect_filenames():
  realdirs = []
  for item in config.dirname:
    doappend = True
    for thing in config.dirname:
      if not item == thing:
        p = re.compile('^' + thing)
        if p.search(item):
          doappend = False
          break
    if doappend == True:
      realdirs.append(item)
  
  for item in realdirs:
    matchesfile = []
    matchesdir = []
    matchesall = []
    for root, dirnames, filenames in os.walk(item):
      for filename in filenames:
        filenamewrite = os.path.join(root, filename)
        matchesfile.append(filenamewrite)
        matchesall.append(filenamewrite)
      for dirname in dirnames:
        dirnamewrite = os.path.join(root, dirname)
        matchesdir.append(dirnamewrite)
        matchesall.append(dirnamewrite)
  # Add the watched dirs to the lists
  for thing in realdirs:
    matchesdir.append(thing)
    matchesall.append(thing)
  return [matchesfile,matchesdir,matchesall,len(matchesdir)]

def restore():
  allcounts = collect_filenames()
  for item in allcounts[2]:
    prepare(item, None, True)

def action(directory, event, ruledir, restore):
  
  try:
    actpermsraw = os.stat(directory)
  except OSError, e:
    if e.errno == 13:
      print >> sys.stderr, strftime("%Y-%m-%d_%H:%M:%S", localtime()), "Permission denied for '" + directory + "'."
      return
    elif e.errno == 2:
      return
      #print >> sys.stderr, directory, " doesn't exist."

  actperms = [actpermsraw.st_uid, actpermsraw.st_gid, oct(actpermsraw.st_mode & 0777)]
  # change owner and group
  changed = False
  # if owner or group is not set in the config, use the actual ones
  if config.doit[ruledir] == 1 or config.doit[ruledir] == 3 or config.doit[ruledir] == 5 or config.doit[ruledir] == 7:
    if config.owner[ruledir] == -1:
      config.owner[ruledir] = actperms[0]
    if config.group[ruledir] == -1:
      config.group[ruledir] = actperms[1]
    if not actperms[0] == config.owner[ruledir] or not actperms[1] == config.group[ruledir]:
      try:
        os.lchown(directory, config.owner[ruledir], config.group[ruledir])
      except OSError, e:
        if e.errno == 13:
          print >> sys.stderr, strftime("%Y-%m-%d_%H:%M:%S", localtime()), "Permission denied for '" + directory + "'."
          return
        elif e.errno == 2:
          return
          #print >> sys.stderr, directory, " doesn't exist."
      else:
        changed = True

  if config.doit[ruledir] == 2 or config.doit[ruledir] == 3 or config.doit[ruledir] == 6 or config.doit[ruledir] == 7:
    if os.path.isfile(directory):
      if not int(actperms[2], 8) == config.chmodf[ruledir]:
        try:
          os.chmod(directory, config.chmodf[ruledir])
        except OSError, e:
          if e.errno == 13:
            print >> sys.stderr, strftime("%Y-%m-%d_%H:%M:%S", localtime()), "Permission denied for '" + directory + "'."
            return
          elif e.errno == 2:
            return
            #print >> sys.stderr, directory, " doesn't exist."
        else:
          changed = True
        changed = True

  if config.doit[ruledir] == 4 or config.doit[ruledir] == 5 or config.doit[ruledir] == 6 or config.doit[ruledir] == 7:
    if os.path.isdir(directory):
      if not int(actperms[2], 8) == config.chmodd[ruledir]:
        try:
          os.chmod(directory, config.chmodd[ruledir])
        except OSError:
          if e.errno == 13:
            print >> sys.stderr, strftime("%Y-%m-%d_%H:%M:%S", localtime()), "Permission denied for '" + directory + "'."
            return
          elif e.errno == 2:
            return
            #print >> sys.stderr, directory, " doesn't exist."
        else:
          changed = True
        
  if changed == True:
    if config.logit == 'yes':
      logging(directory, restore, ruledir)
    else:
      if 'foreground' == sys.argv[1]:
        logging(directory, restore, ruledir)
    
  sys.stdout.flush()

def logging(directory, restore, ruledir):
  logtext = strftime("%Y-%m-%d_%H:%M:%S", localtime()) + ' ' + 'Section: ' + config.sectionname[ruledir] + ' ' + directory
  if restore == False:
    if not os.path.isfile(stdoutfile) or not os.path.isfile(stderrfile):
      daemon.mknewlog()
    print logtext
  else:
    with open(stdoutfile, "a") as logfile:
      logfile.write(logtext + '\n')
    global restorelogcount
    try:
      restorelogcount
    except NameError:
      restorelogcount = 1
    else:
      restorelogcount = restorelogcount + 1
    saferestorelog(restorelogcount)

# safe the count of processed files by the restore function
# to call it from daemon.start()
def saferestorelog(count = None):
  if not count == None:
    global givecountback
    givecountback = count
  else:
    try:
      givecountback
    except NameError:
      givecountback = 0
    return givecountback

# if PID-file exists, check with ps if experms is really running
def checkpid(pid):
  import subprocess
  p = subprocess.Popen(["ps", "-Ao", "pid,fname"], stdout=subprocess.PIPE)
  out, err = p.communicate()
  for item in out.split('\n'):
    tempps = item.strip().split(' ')
    if tempps == ['PID', 'COMMAND'] or tempps == ['']:
      continue
    if tempps[1] == 'experms' and int(tempps[0]) == pid:
      return True
  return False

def usage(command):
  print "usage: %s [start|stop|restart|restore|status|log|err|dircount|(help|-h|--help)|foreground]" % command
  print "See 'man experms' or the README file for more information."

# from http://blog.abhijeetr.com/2010/10/changing-process-name-of-python-script.html
def set_procname(newname):
    from ctypes import cdll, byref, create_string_buffer
    libc = cdll.LoadLibrary('libc.so.6')    #Loading a 3rd party library C
    buff = create_string_buffer(len(newname)+1) #Note: One larger than the name (man prctl says that)
    buff.value = newname                 #Null terminated string as it should be
    libc.prctl(15, byref(buff), 0, 0, 0) #Refer to "#define" of "/usr/include/linux/prctl.h" for the misterious value 16 & arg[3..5] are zero as the man page says.

if __name__ == "__main__":
  set_procname('experms')
  daemon = MyDaemon(pidfile, '/dev/null', stdoutfile, stderrfile)
  if len(sys.argv) == 2:
    if 'start' == sys.argv[1]:
      daemon.start()
    elif 'stop' == sys.argv[1]:
      stoped = daemon.stop()
      if not stoped == False:
        print "Experms stopped."
    elif 'restart' == sys.argv[1]:
      print "Experms is restarting."
      daemon.restart()
    elif 'restore' == sys.argv[1]:
      config = daemon.loadconfig()
      stdout.write("Restore is in progress...")
      restore()
      stdout.write(" Done.\n")
      stdout.flush()
      try:
        restorelogcount
      except NameError:
        restorelogcount = 0
      print restorelogcount, 'files have been changed.'
    elif 'status' == sys.argv[1]:
      # Check for a pidfile to see if the daemon already runs
      try:
        pf = file(daemon.pidfile,'r')
        pid = int(pf.read().strip())
        pf.close()
      except IOError:
        pid = None
      if pid:
        if checkpid(pid):
          print "Experms is running with the PID " + str(pid) + "."
        else:
          print "Experms is not running."
      else:
        print "Experms is not running."
    elif 'log' == sys.argv[1]:
      if not os.path.isfile(stdoutfile):
        print "There is no logfile to show."
        sys.exit(0)
      elif os.stat(stdoutfile)[6] == 0:
        print "There is no logfile to show."
        sys.exit(0)
      from subprocess import call
      print "\033[32;1mCalling 'tail -F", stdoutfile + "':\033[0m"
      try:
        call(["tail", "-F", stdoutfile])
      except KeyboardInterrupt:
        sys.exit(0)
    elif 'err' == sys.argv[1]:
      if not os.path.isfile(stderrfile):
        print "There is no logfile to show."
        sys.exit(0)
      elif os.stat(stderrfile)[6] == 0:
        print "There is no logfile to show."
        sys.exit(0)
      from subprocess import call
      print "\033[32;1mCalling 'tail -F", stderrfile + "':\033[0m\n"
      try:
        call(["tail", "-F", stderrfile])
      except KeyboardInterrupt:
        sys.exit(0)
    elif 'dircount' == sys.argv[1]:
      config = daemon.loadconfig()
      allcounts = collect_filenames()
      print "Total count of directories (including subdirectories) you have configured to monitor:"
      print allcounts[3]
    elif '-h' == sys.argv[1] or '--help' == sys.argv[1] or 'help' == sys.argv[1]:
      usage(sys.argv[0])
      sys.exit(0)
    elif 'foreground' == sys.argv[1]:
      config = daemon.loadconfig()
      if config.restore == 'yes':
        stdout.write("Restore is in progress...")
        restore()
        stdout.write(" Done.\n")
        stdout.flush()
      try:
        restorelogcount
      except NameError:
        restorelogcount = 0
      print restorelogcount, 'files have been changed.'
      print "Experms started in foreground.\nPress ctrl+c to exit."
      daemon.run()
    else:
      print >> sys.stderr, "Unknown command"
      usage(sys.argv[0])
      sys.exit(2)
    sys.exit(0)
  else:
    usage(sys.argv[0])
    sys.exit(2)
else:
  usage(sys.argv[0])
  sys.exit(2)
