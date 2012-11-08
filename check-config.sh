#!/bin/bash

##
##         //\  //\  //\  //\  //\  //\  //\
##        //  \//  \//  \//  \//  \//  \//  \
##       //    _   _   _   _   _   _   _     \
##      //    / \ / \ / \ / \ / \ / \ / \     \
##     // Ⓐ  ( E ) X ) P ) E ) R ) M ) S )  Ⓐ  \
##    //  __  \_/ \_/ \_/ \_/ \_/ \_/ \_/   __  \
##   // //  \                             //  \  \
##  // //    \  //\  //\  //\  //\  //\  //    \  \
##  \_//      \//  \//  \//  \//  \//  \//      \_//
##

##===========================================================================================================================
##
##         FILE: check-config.sh
##
##  DESCRIPTION: 1) Check if the config-file is available. If not, abort with a message.
##               2) Check if the config-file was edited. If not, abort with a message.
##               3) Check the config-file for unwanted (maybe malicious) code. If found any, write only the wanted lines
##                  to a temporary file, source it and print an error-message.
##               4) Check the variables in the config-file for accuracy and abort with a message if not satisfied.
##               5) Check - based on the config-file - what changes has to happen in which directory and remember it
##                  as an octal value.
##
##       AUTHOR: fabio@dynamix-tontechnik.ch
##
##      VERSION: 0.0.2
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
##      CREATED: 2012
##
##     REVISION: ---
##
##===========================================================================================================================

# Path to config-file
if [ "$USER" == "root" ]; then
    if [ -e "/etc/experms.conf" ]; then
        configfile="/etc/experms.conf"
    else
        echo "Was not able to find the configuration file /etc/experms.conf!" >&2
        exit 1
    fi
else
    if [ -e "/home/$USER/experms.conf" ]; then
        configfile="/home/$USER/experms.conf"
    elif [ -e "/home/$USER/.experms.conf" ]; then
        configfile="/home/$USER/.experms.conf"
    else
        echo "Was not able to find the configuration file /home/$USER/experms.conf or /home/$USER/.experms.conf!" >&2
        exit 1
    fi
fi
rm -f /tmp/experms.conf
configfile_secured="/tmp/experms.conf"

# Taken from http://wiki.bash-hackers.org/howto/conffile
# Check if the file contains something we don't want.
if egrep -v '^#|^$|^[^ ]*=[^;]*' "$configfile"
then
    echo -n "Config file is unclean, cleaning it..." >&2
    # Filter the original to a new file.
    egrep '^#|^[^ ]*=[^;&]*'  "$configfile" > "$configfile_secured"
    configfile="$configfile_secured"
    echo "Done." >&2
fi
source "$configfile"

# Check if the config-file was edited.
if [ "x$mondirname" == x ]
then
    echo """It seems you haven't edited the config-file yet or did not enter a directory to monitor!
Aborting...""" >&2
    exit 1
fi

# Check every variable from the config-file for accuracy.
if ! [ "$log_activities" == "yes" ] && ! [ "$log_activities" == "no" ]
then
    logactivitieserr=1
    conferror=1
fi
if ! [ "$use_several_dirs" == "yes" ] && ! [ "$use_several_dirs" == "no" ]
then
    useseveraldirserr=1
    conferror=1
fi
if ! [ -d "$mondirname" ]
then
    mondirnameerr=1
    conferror=1
fi
if echo "$mondirname" | egrep -vq "\/$"
then
    mondirname="$mondirname/"
fi
if ! [ "$restore_at_start" == "yes" ] && ! [ "$restore_at_start" == "no" ]
then
    restore_at_startserr=1
    conferror=1
fi

if [ "$use_several_dirs" == "yes" ]
then
    # Make arrays out of the variables from the config-file.
    IFS=","
    subdirname=($subdirname)
    subdirown=($subdirown)
    subdirgrp=($subdirgrp)
    subdirchmodoktd=($subdirchmodoktd)
    subdirchmodoktf=($subdirchmodoktf)
    unset IFS

    for item in ${subdirname[@]}
    do
        if ! [ -d "$mondirname$item" ]
        then
            subdirnameerr=1
            conferror=1
        fi
    done
    for item in ${subdirown[@]}
    do
    if ! egrep -q "^$item:" /etc/passwd && ! [ "x$item" == x ]
        then
            subdirownerr=1
            conferror=1
        fi
    done
    if [ ${#subdirown[@]} -gt ${#subdirname[@]} ]
    then
        subdirowncount=1
        conferror=1
    fi
    for item in ${subdirgrp[@]}
    do
    if ! egrep -q "^$item:" /etc/group && ! [ "x$item" == x ]
        then
            subdirgrperr=1
            conferror=1
        fi
    done
    if [ ${#subdirgrp[@]} -gt ${#subdirname[@]} ]
    then
        subdirgrpcount=1
        conferror=1
    fi
    for item in ${subdirchmodoktf[@]}
    do
    if ! echo "$item" | egrep -q "^[0-7][0-7]([0-7]|[0-7][0-7])$" && ! [ x$item == x ]
        then
            subdirchmodoktferr=1
            conferror=1
        fi
    done
    if [ ${#subdirchmodoktf[@]} -gt ${#subdirname[@]} ]
    then
        subdirchmodoktfcount=1
        conferror=1
    fi
    for item in ${subdirchmodoktd[@]}
    do
    if ! echo "$item" | egrep -q "^[0-7][0-7]([0-7]|[0-7][0-7])$" && ! [ x$item == x ]
        then
            subdirchmodoktderr=1
            conferror=1
        fi
    done
    if [ ${#subdirchmodoktd[@]} -gt ${#subdirname[@]} ]
    then
        subdirchmodoktdcount=1
        conferror=1
    fi

elif [ $use_several_dirs == "no" ]
then
    if ! egrep -q "^$onlyown:" /etc/passwd && ! [ x$onlyown == x ]
    then
        onlyownerr=1
        conferror=1
    fi
    if ! egrep -q "^$onlygrp:" /etc/group&& ! [ x$onlygrp == x ]
    then
        onlygrperr=1
        conferror=1
    fi
    if ! echo "$onlychmodoktf" | egrep -q "^[0-7][0-7]([0-7]|[0-7][0-7])$" && ! [ x$onlychmodoktf == x ]
    then
        onlychmodoktferr=1
        conferror=1
    fi
    if ! echo "$onlychmodoktd" | egrep -q "^[0-7][0-7]([0-7]|[0-7][0-7])$" && ! [ x$onlychmodoktd == x ]
    then
        onlychmodoktderr=1
        conferror=1
    fi
    # Make arrays out of the variables from the config-file.
    subdirname=( '' )
    subdirown=($onlyown)
    subdirgrp=($onlygrp)
    subdirchmodoktd=($onlychmodoktd)
    subdirchmodoktf=($onlychmodoktf)
fi

# Check if there are the necessary permissions on all monitored files. If not satisfied, abort with an error-message.
if [ $USER != root ]; then
    if [ ${#subdirown[@]} -ne 0 ]; then
        echo "chown
Based on your settings in the configuration-file you need to run experms with root-permissions.
Experms will abort now!" >&2
        exit 1
    fi
    for item in "${subdirname[@]}"; do
        if ! find "$mondirname$item" -user $USER 1>/dev/null 2>/dev/null; then
            echo "chmod
Based on your settings in the configuration-file you need to be the owner of all the monitored files.
Experms will abort now!" >&2
            exit 1
        fi
    done
fi

# Inform stderr about wrong or missing entries in the config-file.
if [ "$conferror" == 1 ]
then
    echo "There are some strange settings in the config-file:" >&2
    if [ "$logactivitieserr" == 1 ]
    then
        echo "\"log_activities\" must be set to \"yes\" or \"no\"!" >&2
    fi
    if [ "$useseveraldirserr" == 1 ]
    then
        echo "\"use_several_dirs\" must be set to \"yes\" or \"no\"!" >&2
    fi
    if [ "$mondirnameerr" == 1 ]
    then
        echo "\"mondirname\" must be an existing directory!" >&2
    fi
    if [ "$restore_at_startserr" == 1 ]
    then
        echo "\"restore_at_start\" must be set to \"yes\" or \"no\"!" >&2
    fi
    if [ "$onlyownerr" == 1 ]
    then
        echo "\"onlyown\" must be an existing user on the system!" >&2
    fi
    if [ "$onlygrperr" == 1 ]
    then
        echo "\"onlygrp\" must be an existing group on the system!" >&2
    fi
    if [ "$onlychmodoktferr" == 1 ]
    then
        echo "\"onlychmodoktf\" must be the octal permissions for files or remain empty!" >&2
    fi
    if [ "$onlychmodoktderr" == 1 ]
    then
        echo "\"onlychmodoktd\" must be the octal permissions for directories or remain empty!" >&2
    fi
    if [ "$subdirnameerr" == 1 ]
    then
        echo "\"subdirname\" must contain the subdirectory-names or remain empty (comma separated)!" >&2
    fi
    if [ "$subdirownerr" == 1 ]
    then
        echo "\"subdirown\" must contain existing users or remain empty (comma separated)!" >&2
    fi
    if [ "$subdirowncount" == 1 ]
    then
        echo "You've entered more owner-names for the sub-directories, than sub-directories itself! (subdirown)" >&2
    fi
    if [ "$subdirgrperr" == 1 ]
    then
        echo "\"subdirgrp\" must contain existing groups or remain empty (comma separated)!" >&2
    fi
    if [ "$subdirgrpcount" == 1 ]
    then
        echo "You've entered more group-names for the sub-directories, than sub-directories itself! (subdirgrp)" >&2
    fi
    if [ "$subdirchmodoktferr" == 1 ]
    then
        echo "\"subdirchmodoktf\" must contain the octal permissions for files or remain empty (comma-searated)!" >&2
    fi
    if [ "$subdirchmodoktfcount" == 1 ]
    then
        echo "You've entered more permissions for files in the sub-directories, than sub-directories itself! (chmodoktf)" >&2
    fi
    if [ "$subdirchmodoktderr" == 1 ]
    then
        echo "\"subdirchmodoktd\" must contain the octal permissions for directories or remain empty (comma-separated)!" >&2
    fi
    if [ "$subdirchmodoktdcount" == 1 ]
    then
        echo "You've entered more permissions for directories in the sub-directories, than sub-directories itself! (chmodoktd)" >&2
    fi
    echo "Experms will abort now!"
    exit 1
fi

# Check what needs to be done and remember it as octal value in $doitreally.
doitreally=()
# Count for the items in the arrays.
subdircount=0
# The obligate for-loop.
for item in "${subdirname[@]}"
do
    # Check if items are empty.
    if [ x${subdirown[$subdircount]} == x ] && [ x${subdirgrp[$subdircount]} == x ]
    then
        doitreallyraw="0"
    else
        doitreallyraw="1"
    fi
    if ! [ x${subdirchmodoktd[$subdircount]} == x ]
    then
        let doitreallyraw=$doitreallyraw+2
    fi
    if ! [ x${subdirchmodoktf[$subdircount]} == x ]
    then
        let doitreallyraw=$doitreallyraw+4
    fi
    doitreally+=($doitreallyraw)
    subdircount=$subdircount+1
done
unset subdircount

