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
##                 version 0.4 - 2013
##


##===========================================================================================================================
##
##         FILE: check-config.py
##
##  DESCRIPTION: Parses the configuration file, check validity and store content to variables
##
##       AUTHOR: Fabio Rämi - fabio(a)dynamix-tontechnik.ch
##
##      VERSION: 0.4
##
##      LICENCE: GNU GPL v3.0 or later.
##               http://www.gnu.org/licenses/gpl-3.0.txt
##               Experms comes with absolutely no warranty!
##               
##      COPYING: This file is part of Experms.
##
##               Experms is free software: you can redistribute it and/or modify
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
##===========================================================================================================================

#import sys, os, string, re
import os
import pwd
import grp
import re
import sys
from ConfigParser import SafeConfigParser,MissingSectionHeaderError

# more output? make True
debugvar = False


# function to verify the given octal permissions
def checkoctalperms(octalperms, chmodfd, i):
  if chmodfd == 'chmodf':
    anrede = 'chmodf'
  else:
    anrede = 'chmodd'
  if octalperms != ['']:
    try:
      int(octalperms)
    except ValueError:
      print >> sys.stderr, "Error in section", i + ":", anrede, "is not an interger number."
      return False
    if len(octalperms) != 3 and len(octalperms) != 4:
      print >> sys.stderr, "Error in section", i + ":", anrede, "needs to be a three or four digit octal number."
      return False
    for thing in octalperms:
      if int(thing) > 7:
        print >> sys.stderr, "Error in section", i + ":", anrede, "is not an octal number."
        return False
    if debugvar == True:
      print "'" + anrede + "' is valid"
    return True

class Check(object):
  def __init__(self):
    # variable names from the configfile
    log_activities = 'log_activities'
    restore = 'restore'
    dirname = 'path'
    owner = 'owner'
    group = 'group'
    chmodf = 'chmodf'
    chmodd = 'chmodd'
    excludedir = 'excludepath'
    excludepattern = 'excludepattern'
    
    # default values for the section general
    logitdefault = 'no'
    restoredefault = 'no'
    # create the needed lists
    self.doit = []
    self.dirname = []
    self.owner = []
    self.group = []
    self.chmodf = []
    self.chmodd = []
    self.excludedir = []
    self.excludepattern = []
    
    errorsoccured = False
    
    # check for the existence of a config-file
    home = os.path.expanduser("~")
    if os.path.isfile(home + '/.experms.conf'):
      configfile = home + '/.experms.conf'
    elif os.path.isfile(home + '/experms.conf'):
      configfile = home + '/experms.conf'
    elif os.path.isfile('/etc/experms.conf'):
      configfile = '/etc/experms.conf'
    elif sys.path[0] + '/experms.conf':
      configfile = sys.path[0] + '/experms.conf'
    else:
      print >> sys.stderr, "Error: No configuration-file (experms.conf) was found."
      sys.exit(1)
    print "Using configuration-file '" + configfile + "'"
    
    # parse the config-file
    parser = SafeConfigParser()
    try:
      parser.read(configfile)
    except MissingSectionHeaderError:
      pass

    
    if parser.has_section('general'):
      if debugvar == True:
        print "'general' was found"
      if parser.has_option('general', log_activities):
        self.logit = parser.get('general', log_activities).lower()
        if self.logit == 'yes':
          if debugvar == True:
            print 'experms will write a log'
        elif self.logit == 'no' or self.logit == '':
          self.logit = logitdefault
          if debugvar == True:
            print "experms won't write a log"
        else:
          print >> sys.stderr, "Error: 'log_activities' must be either 'yes' or 'no'"
          errorsoccured = True
      else:
        self.logit = logitdefault
        if debugvar == True:
          print "experms won't write a log"
      
      if parser.has_option('general', restore):
        self.restore = parser.get('general', restore).lower()
        if self.restore == 'yes':
          if debugvar == True:
            print 'experms will restore at start'
        elif self.restore == 'no' or self.restore == '':
          self.restore = restoredefault
          if debugvar == True:
            print "experms won't restore at start"
        else:
          print >> sys.stderr, "Error: 'restore' must be either 'yes' or 'no'"
          errorsoccured = True
      else:
        self.restore = restoredefault
        if debugvar == True:
          print "experms won't restore at start"
    
      if len(parser.sections()) < 2:
        print >> sys.stderr, "Error: No directory-section was found.\nIf you have started experms for the first time, please edit the configfile first (usually /etc/experms.conf)"
        errorsoccured = True
    else:
      self.restore = restoredefault
      self.logit = logitdefault
      if len(parser.sections()) < 1:
        print >> sys.stderr, "Error: No directory-section was found.\nIf you have started experms for the first time, please edit the configfile first (usually /etc/experms.conf)"
        errorsoccured = True
    


    self.sectionname = []
    for number, i in enumerate(parser.sections()):
      if i == 'general':
        continue
      self.sectionname.append(i)
      number = number - 1
      usowchmoderr = True
      self.doit.append('')
      
      if parser.has_option(i, dirname):
        self.dirname.append('')
        if parser.get(i, dirname).rstrip('/') in self.dirname:
          print >> sys.stderr, "Error in section", i + ": 'path' already exists in another section."
          errorsoccured = True
        self.dirname[number] = parser.get(i, dirname).rstrip('/')
        if self.dirname[number] == '':
          print >> sys.stderr, "Error in section", i + ": 'path' is empty.\nIf you have started experms for the first time, please edit the configfile first (usually /etc/experms.conf)"
          errorsoccured = True
        else:
          if not os.path.isdir(self.dirname[number]):
            print >> sys.stderr, "Error in section", i + ": 'path'", self.dirname[number], "doesn't exist"
            errorsoccured = True
          else:
            if debugvar == True:
              print "'dirname' is valid"
      else:
        print >> sys.stderr, "Error in section", i + ": 'dirname' is not set."
        errorsoccured = True
      
      self.owner.append('')  
      if parser.has_option(i, owner):
        self.owner[number] = parser.get(i, owner)
        if self.owner[number] != '':
          try:
            self.owner[number] = int(self.owner[number])
          except ValueError:
            try:
              pwd.getpwnam(self.owner[number])
            except KeyError:
              print >> sys.stderr, "Error in section", i + ": User", self.owner[number], "doesn't exist."
              errorsoccured = True
            else:
              # save the user as uid
              self.owner[number] = pwd.getpwnam(self.owner[number]).pw_uid
              usowchmoderr = False
              self.doit[number] = 1
              if debugvar == True:
                print "'user' is valid"
          else:
            try:
              pwd.getpwuid(self.owner[number])
            except KeyError:
              print >> sys.stderr, "Error in section", i + ": User", self.owner[number], "doesn't exist."
              errorsoccured = True
            else:
              usowchmoderr = False
              self.doit[number] = 1
              if debugvar == True:
                print "'user' is valid"
            
        else:
          self.owner[number] = -1
          self.doit[number] = 0
      else:
        self.owner[number] = -1
        self.doit[number] = 0
      
      self.group.append('')
      if parser.has_option(i, group):
        self.group[number] = parser.get(i, group)
        if self.group[number] != '':
          try:
            self.group[number] = int(self.group[number])
          except ValueError:
            try:
              grp.getgrnam(self.group[number])
            except KeyError:
              print >> sys.stderr, "Error in section", i + ": Group", self.group[number], "doesn't exist."
              errorsoccured = True
            else:
              # save the group as gid
              self.group[number] = grp.getgrnam(self.group[number]).gr_gid
              usowchmoderr = False
              self.doit[number] = 1
              if debugvar == True:
                print "'group' is valid"
          else:
            try:
              grp.getgrgid(self.group[number])
            except KeyError:
              print >> sys.stderr, "Error in section", i + ": Group", self.group[number], "doesn't exist."
              errorsoccured = True
            else:
              usowchmoderr = False
              self.doit[number] = 1
              if debugvar == True:
                print "'group' is valid"
        else:
          self.group[number] = -1
      else:
        self.group[number] = -1
      
      self.chmodf.append('')
      if parser.has_option(i, chmodf):
        self.chmodf[number] = parser.get(i, chmodf)
        if checkoctalperms(self.chmodf[number], 'chmodf', i):
          if len(self.chmodf[number]) == 3:
            self.chmodf[number] = '0' + self.chmodf[number]
            self.chmodf[number] = int(self.chmodf[number], 8)
          elif len(self.chmodf[number]) == 4:
            self.chmodf[number] = int(self.chmodf[number], 8)
          usowchmoderr = False
          self.doit[number] = self.doit[number] + 2
        else:
          errorsoccured = True
      
      self.chmodd.append('')  
      if parser.has_option(i, chmodd):
        self.chmodd[number] = parser.get(i, chmodd)
        if checkoctalperms(self.chmodd[number], 'chmodd', i):
          if len(self.chmodd[number]) == 3:
            self.chmodd[number] = '0' + self.chmodd[number]
            self.chmodd[number] = int(self.chmodd[number], 8)
          elif len(self.chmodd[number]) == 4:
            self.chmodd[number] = int(self.chmodd[number], 8)
          usowchmoderr = False 
          self.doit[number] = self.doit[number] + 4 
        else:
          errorsoccured = True
      
      self.excludedir.append([])
      if parser.has_option(i, excludedir):
        exvalid = True
        self.excludedir[number] = parser.get(i, excludedir).split(',')
        for nr, item in enumerate(self.excludedir[number]):
          item = item.strip().rstrip('/')
          self.excludedir[number][nr] = item
          if item == '':
            self.excludedir[number].remove(item)
          else:
            if not os.path.isdir(item) and not os.path.isfile(item):
              print >> sys.stderr, "Error in section", i + ": 'excludedir'", item, "doesn't exist."
              errorsoccured = True
              exvalid = False
        if exvalid == True:
          if self.dirname[number] in self.excludedir[number]:
            print >> sys.stderr, "Error in section", i + ": 'excludedir'", item, "is the same like 'dirname'."
            errorsoccured = True
          if debugvar == True:
            print "'excludedir' is valid"
        if self.excludedir[number] == [] or self.excludedir[number] == ['']:
          self.excludedir[number] = None
      else:
        self.excludedir[number] = None
      
      self.excludepattern.append('')
      if parser.has_option(i, excludepattern):
        exvalid = True
        self.excludepattern[number] = parser.get(i, excludepattern)
        try:
          re.compile(self.excludepattern[number])
        except:
          print >> sys.stderr, "Error in section", i + ": 'excludepattern' must be a valid regular expression."
          errorsoccured = True
        else:
          if debugvar == True:
            print "'excludepattern' is valid"
        if self.excludepattern[number] == '':
          self.excludepattern[number] = None
      else:
        self.excludepattern[number] = None
      
      if usowchmoderr == True:
        print >> sys.stderr, "Error in section", i + ": With your actual configuration, experms will do exactly nothing."
        errorsoccured = True
    
    if errorsoccured == True:
      print >> sys.stderr, "Aborting!"
      sys.exit(1)