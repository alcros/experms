#!/bin/bash

##===========================================================================================================================
##
##         FILE: cronexperms.sh
##
##  DESCRIPTION: This is the experms-script for cron. It checkes if Experms is running. If not it starts it.
##
##        NOTES: You can let cron run this script (e.g. every 5 minutes) in order to make sure Experms is running permanentely.
##               Example for crontab:
##               */5 * * * * /your/path/to/cronexperms.sh
##
##===========================================================================================================================


if ! ps -Ao fname | egrep -q experms
then
    experms start
fi
exit 0

