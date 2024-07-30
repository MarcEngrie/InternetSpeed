#!/bin/sh

export TERM=linux

#myoutput=/home/pi/InternetSpeed/Log/relaunch.log
myoutput=/dev/null

#------------------------------------------------------------------------------
# check if load is OK < 150
echo                                               >> $myoutput
echo --------------------------------------------- >> $myoutput
date                                               >> $myoutput
echo Checking load 15 minute                       >> $myoutput
LOAD=`uptime | awk '{print $NF}'`
LOADCOMP=`echo $LOAD \> 150 | bc -l`
if [ $LOADCOMP -eq 1 ]; then 
    echo    load NOT OK = $LOAD - rebooting        >> $myoutput
    sudo reboot now
else
    echo    load OK = $LOAD                        >> $myoutput
fi
echo --------------------------------------------- >> $myoutput

#------------------------------------------------------------------------------
# check if ramdisk are not running out of space. If so cleanup

df -H | grep -i '/var/log' | awk '{ print $5 " " $6 }' | while read output;
do
  #echo $output
  usedspace=$(echo $output | awk '{ print $1}' | cut -d'%' -f1  )
  if [ $usedspace -ge 80 ]; then
    echo "/var/log running out of space" 
	rm /var/log/*.log        > /dev/null
	rm /var/log/syslog*      > /dev/null
	rm /var/log/messages*    > /dev/null
	rm /var/log/btmp         > /dev/null
	rm /var/log/wtmp         > /dev/null
	rm /var/log/debug        > /dev/null
	rm /var/log/apache2/*.gz > /dev/null
  fi
done

#------------------------------------------------------------------------------
# check if InternetSpeed is running
echo                                                     >> $myoutput
echo ---------------------------------------------       >> $myoutput
date                                                     >> $myoutput
echo test InternetSpeed restart                   >> $myoutput
ps auxw | grep -v grep | grep -i InternetSpeed.py >> $myoutput
ps auxw | grep -v grep | grep -i InternetSpeed.py  > /dev/null
if [ $? != 0 ]; then
    echo InternetSpeed restart                    >> $myoutput
    systemctl restart InternetSpeed.service
fi    
echo ---------------------------------------------       >> $myoutput
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# check if network is accessible
echo                                                >> $myoutput
echo ---------------------------------------------  >> $myoutput
ping -c5 -4 192.168.1.1                             >> $myoutput
if [ $? -eq 0 ]; then
    echo Access to network OK                       >> $myoutput
else
    echo Access to network FAILED - Rebooting       >> $myoutput
    sudo reboot
fi
#------------------------------------------------------------------------------
