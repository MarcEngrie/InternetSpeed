#------------------------------------------------------------------------------
# Init
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# set colors
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

clear

# check if root is used
if [ "$(id -u)" != 0 ]; then
  echo "${red}${bold}"
  echo "Sorry, you need to run this script as root"
  echo "type sudo -i     on the command line and then"
  echo "type cd /home/pi on the command line"
  echo "${reset}"
  echo
  echo
  exit 1
fi

#------------------------------------------------------------------------------
# Main
#------------------------------------------------------------------------------
echo
echo
NOW=$( date '+%F %H:%M:%S' )
echo "${NOW} - Starting install InternetSpeed"
echo

#------------------------------------------------------------------------------
echo
echo
echo "${green}${bold}Installing or Updating Python modules${reset}"
echo
#pip version
tmp=`pip --version | sed -r 's/^pip //'`
IFS=' .'
read -r -a array <<< "$tmp"
IFS=''
PipVersion=$((${array[0]}+0))

if [ $PipVersion -ge 23 ]; then
    pipparam1="--root-user-action=ignore"
    pipparam2="--break-system-packages"
else
    pipparam1=""
    pipparam2=""
fi

pip install --upgrade $pipparam1 $pipparam2 netifaces
if [[ $? -gt 0 ]]; then
    echo "Install or upgrade of netifaces failed !!!"
    exit 1
fi

pip install --upgrade $pipparam1 $pipparam2 dnspython
if [[ $? -gt 0 ]]; then
    echo "Install or upgrade of dnspython failed !!!"
    exit 1
fi

pip install --upgrade $pipparam1 $pipparam2 pyyaml
if [[ $? -gt 0 ]]; then
    echo "Install or upgrade of dnspython failed !!!"
    exit 1
fi
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
echo
echo
echo "${green}${bold}Making sure scripts are executable${reset}"
echo
if ls /home/pi/InternetSpeed/*.sh > /dev/null 2>&1; then
   chmod +x /home/pi/InternetSpeed/*.sh
fi
if ls /home/pi/InternetSpeed/bin/*.sh > /dev/null 2>&1; then
   chmod +x /home/pi/InternetSpeed/bin/*.sh
fi
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Add application into run control (rc?.d)
#------------------------------------------------------------------------------

# #------------------------------------------------------------------------------
echo
echo
echo "${green}${bold}Configuring InternetSpeed service${reset}"
echo
cp "/home/pi/InternetSpeed/bin/InternetSpeed.service" "/usr/lib/systemd/system/InternetSpeed.service"
systemctl daemon-reload
systemctl enable InternetSpeed.service
systemctl start InternetSpeed.service

#------------------------------------------------------------------------------
# Add application into cron
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
echo
echo
echo "${green}${bold}Adding relaunch.sh in crontab${reset}"
echo
export VISUAL=nano
if [ -f "/home/pi/InternetSpeed/bin/crontab.cfg" ]; then
    rm "/home/pi/InternetSpeed/bin/crontab.cfg"
fi
croncmd="/home/pi/InternetSpeed/bin/relaunch.sh"
findjob=$((crontab -l 2>/dev/null || true) | grep -F "$croncmd")
if [ -z "$findjob" ]; then
    echo
    cronjob="@reboot sleep 30 && $croncmd"
    echo "${green}${bold}Adding cron job '$cronjob' to crontab of root${reset}"
    (crontab -l 2>/dev/null; echo "$cronjob") | awk '!x[$0]++' | crontab -
    cronjob="0 * * * * $croncmd"
    echo "${green}${bold}Adding cron job '$cronjob' to crontab of root${reset}"
    (crontab -l 2>/dev/null; echo "$cronjob") | awk '!x[$0]++' | crontab -
    cronjob="15 * * * * $croncmd"
    echo "${green}${bold}Adding cron job '$cronjob' to crontab of root${reset}"
    (crontab -l 2>/dev/null; echo "$cronjob") | awk '!x[$0]++' | crontab -
    cronjob="30 * * * * $croncmd"
    echo "${green}${bold}Adding cron job '$cronjob' to crontab of root${reset}"
    (crontab -l 2>/dev/null; echo "$cronjob") | awk '!x[$0]++' | crontab -
    cronjob="45 * * * * $croncmd"
    echo "${green}${bold}Adding cron job '$cronjob' to crontab of root${reset}"
    (crontab -l 2>/dev/null; echo "$cronjob") | awk '!x[$0]++' | crontab -
fi
echo
echo
crontab -l >"/home/pi/InternetSpeed/bin/crontab.cfg"
crontab -l
#------------------------------------------------------------------------------

echo
echo
NOW=$( date '+%F %H:%M:%S' )
echo "${NOW} - Ending   install InternetSpeed"
echo
