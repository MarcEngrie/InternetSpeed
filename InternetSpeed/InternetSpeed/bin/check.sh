#! /bin/bash
#------------------------------------------------------------------------------
# Main
#------------------------------------------------------------------------------

clear
black=`tput setaf 0`
red=`tput setaf 1`
green=`tput setaf 2`
yellow=`tput setaf 3`
blue=`tput setaf 4`
magenta=`tput setaf 5`
cyan=`tput setaf 6`
white=`tput setaf 7`
bold=`tput bold`
underline=`tput smul`
reset=`tput sgr0`

#------------------------------------------------------------------------------
# check if load is OK < 1.5
echo
echo "Checking load (15 minute)"
LOAD=`uptime | awk '{print $NF}'`
LOADCOMP=`echo $LOAD \> 1.5 | bc -l`
if [ $LOADCOMP -eq 0 ]; then 
    echo "${green}${bold}>>> load OK  = $LOAD <<<${reset}"
else
    echo "${red}${bold}>>> load NOT OK = $LOAD <<<${reset}"
fi

#------------------------------------------------------------------------------
# check if InternetSpeed is running
echo
echo "Checking if InternetSpeed is running"
ps auxw | grep -v grep | grep -i InternetSpeed.py
if [ $? == 0 ]; then
    echo "${green}${bold}>>> running <<<$(tput sgr 0)"
else
    echo "${red}${bold}!!! not running !!!$(tput sgr 0)"
fi

#------------------------------------------------------------------------------
# check if network is accessible
echo
echo "Checking network connectivity ..."
ping -c5 -4 192.168.1.1
if [ $? -eq 0 ]; then
    echo "${green}${bold}>>> Access to network OK <<<${reset}"
else
    echo "${red}${bold}!!! Access to network FAILED - Reboot !!!${reset}"
fi
#------------------------------------------------------------------------------

echo
echo
