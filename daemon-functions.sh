#!/bin/bash

## ################################ ##
##                                  ##
## daemon-functions.sh VERSION 0.1a ##
## experms VERSION 0.2              ##
##                                  ##
## ################################ ##

## Distrubuted under the GPL
## http://www.gnu.org/licenses/gpl-3.0.txt

## BEWARE: This is a hardly modified version for Experms. You will find the original file here: http://blog.apokalyptik.com/2008/05/09/as-close-to-a-real-daemon-as-bash-scripts-get/

## No warranty of any kind... May run 
## off with your daughter. May explode
## in a ball of smoke and fire. Might
## work. Use at your own risk

## #!/bin/bash
##
## # Example Usage: datelogger.sh
## #    A sample daemon which simply logs the
## #    date and time once per second.
##
## function payload() {
##   while [ true ]; do
##     checkforterm
##     date
##     sleep 1
##   done
## }
##
## source /path/to/daemon-functions.sh

function daemonize() {
    echo $MY_PID > $MY_PIDFILE
    exec 3>&-           # close stdin
    exec 2>>$MY_ERRFILE # redirect stderr
    exec 1>>$MY_LOGFILE # redirect stdout
    echo $(date)" Daemonizing" >> $MY_ERRFILE
}

function checkforterm() {
    if [ -f $MY_KILLFILE ]; then
        echo $(date)" Terminating gracefully" >> $MY_ERRFILE
        rm $MY_PIDFILE
        rm $MY_KILLFILE
        inotifypid=$(cat /tmp/perms_pid.sfhsfhi)
        rm -f /tmp/experms.conf
        rm -f /tmp/perms_pid.sfhsfhi
        kill $inotifypid
        echo "done!"
        kill $MY_PID
        exit 0
    fi
}

MY_PID=$$
# MY_PATH=$(readlink -f $0)
# MY_ROOT=$(dirname $MY_PATH)
MY_NAME=$(basename $MY_PATH)
MY_PIDFILE="$MY_ROOT/.$MY_NAME.pid"
MY_KILLFILE="$MY_ROOT/.$MY_NAME.kill"
MY_ERRFILE="$MY_ROOT/.$MY_NAME.err"
MY_LOGFILE="$MY_ROOT/.$MY_NAME.log"
MY_WAITFILE="$MY_ROOT/.$MY_NAME.wait"
MY_BLOCKFILE="$MY_ROOT/.$MY_NAME.block"

CR="
"
SP=" "
OIFS=$IFS

case $1 in
#    pause)
#        touch $MY_WAITFILE
#        ;;
#    resume)
#        rm $MY_WAITFILE
#        ;;
    restart)
        $0 stop
        $0 start
        ;;
    start)
        if [ -f $MY_BLOCKFILE ]; then
            echo "Experms execution has been disabled"
            exit 0
        fi
        if [ -f $MY_PIDFILE ]; then
            if ps -Ao pid,fname | egrep "^$(cat $MY_PIDFILE) " | egrep -q "$MY_NAME"; then
                echo "Experms is already running"
                exit 0
            else
                rm $MY_PIDFILE
                rm -f /tmp/experms.conf
                rm -f /tmp/perms_pid.sfhsfhi
            fi
        fi
        if [ "$restore_at_start" == "yes" ]
        then
            func_restore
        fi
        $0 run &
        echo "Experms started"
        exec 3>&- # close stdin
        exec 2>&- # close stderr
        exec 1>&- # close stdout
        exit 0
        ;;
    disable)
        touch $MY_BLOCKFILE
        $0 stop
        ;;
    enable)
        if [ -f $MY_BLOCKFILE ]; then rm $MY_BLOCKFILE; fi
        ;;
    stop)
        echo -n "Terminating daemon... "
        $0 stat 1>/dev/null 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "process is not running"
            exit 0
        fi
        touch $MY_KILLFILE
        checkforterm
        ;;
    stat)
        if [ -f $MY_BLOCKFILE ]; then
            echo "Experms execution disabled"
        fi
        if [ ! -f $MY_PIDFILE ]; then
            echo "$MY_NAME is not running"
            exit 1
        fi
        pgrep -l -f "$MY_NAME run" | grep -q -E "^$(cat $MY_PIDFILE) " 
        if [ $? -eq 0 ]; then
            echo "$MY_NAME is running with PID "`cat $MY_PIDFILE`
            if [ -f /tmp/perms_pid.sfhsfhi ]; then
                inotifypid=$(cat /tmp/perms_pid.sfhsfhi)
                echo "inotifywait is running with PID $inotifypid"
            fi
            exit 0
        else
            echo "$MY_NAME is not running"
            exit 1
        fi
        ;;
    log|stdout)
        if [ -f $MY_LOGFILE ] && [ -s "$MY_LOGFILE" ]; then
            tail -f $MY_LOGFILE
        else
            echo "No stdout output yet"
        fi
        ;;
    
    err|stderr)
        if [ -f $MY_ERRFILE ] && [ -s "$MY_ERRFILE" ]; then
            tail -f $MY_ERRFILE
        else
            echo "No stderr output yet"
        fi
        ;;
    run)
        daemonize
        payload
        ;;
    restore)
        if [ -f $MY_BLOCKFILE ]; then
            echo "Experms execution has been disabled"
            exit 0
        fi
        func_restore
        ;;
    help|?|--help|-h)
                echo """
Usage: $0 [ start | stop | restart | stat | disable | enable | (log|stdout) | (err|stderr) | restore | help ]

Experms runs as daemon and monitors file-changes happened in the directory set in experms.conf.
If changes happened, it adjusts the file-permissions and ownership/group.
You can either define one directory, or several sub-directories with different ownerships and permissions.
Further it is able to restore all the ownerships and permissions of all files based on the config-file.
"""
        exit 0
        ;;
    *)
        echo "Invalid argument"
        echo
        $0 help
        ;;
esac

