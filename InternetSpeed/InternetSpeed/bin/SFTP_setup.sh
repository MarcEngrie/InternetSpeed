
#! /bin/bash
#------------------------------------------------------------------------------
# Main
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
echo

# check if root is used
if [ "$(id -u)" != 0 ]; then
  echo "${red}${bold}"
  echo 'Sorry, you need to run this script as root'
  echo 'type sudo -i     on the command line and then'
  echo 'type cd /home/pi on the command line'
  echo
  echo ' or login as root over SSH and then'
  echo 'type cd /home/pi on the command line'
  echo "${reset}"
  echo
  echo
  exit 1
fi

read -t 5 -p "${yellow}${bold}Running SFTP-setup ...${reset}" key
echo

#------------------------------------------------------------------------------
# Start of ToDo
#------------------------------------------------------------------------------

NOW=$( date '+%F %H:%M:%S' )
echo "${NOW} - Starting SFTP-setup" >>/home/pi/install.log

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

if [ -f /home/pi/fstab.ram ]; then
    echo
    echo "${red}${bold}Changing file system config to original setting${reset}"
    echo
    echo "${red}${bold}Will reboot before executing this script${reset}"
    cp /home/pi/fstab.org /etc/fstab
    mv /home/pi/fstab.ram /home/pi/fstab.txt
    echo
    read -t 5 -p "${yellow}${bold}Please wait for reboot.. ${reset}" key
    echo
    reboot
fi

# update packagelist first
echo "${green}${bold}Updating Raspbian OS${reset}"
echo
apt -y update
echo

echo
echo
echo "${green}${bold}Installing or Updating Python SFTP modules${reset}"
echo
apt -y install libffi-dev
if [[ $? -gt 0 ]]; then
    echo "apt install failed !!!"
    exit 1
fi
apt -y install build-essential
if [[ $? -gt 0 ]]; then
    echo "apt install failed !!!"
    exit 1
fi
apt -y install libssl-dev
if [[ $? -gt 0 ]]; then
    echo "apt install failed !!!"
    exit 1
fi
apt -y install python3-dev
if [[ $? -gt 0 ]]; then
    echo "apt install failed !!!"
    exit 1
fi
apt -y install pkg-config
if [[ $? -gt 0 ]]; then
    echo "apt install failed !!!"
    exit 1
fi

pip install --upgrade $pipparam1 $pipparam2 pip setuptools wheel
if [[ $? -gt 0 ]]; then
    echo "Install or upgrade of pip setuptools wheel failed !!!"
    exit 1
fi

pip install --upgrade $pipparam1 $pipparam2 p5py
if [[ $? -gt 0 ]]; then
    echo "Install or upgrade of p5py failed !!!"
    exit 1
fi

pip install --upgrade $pipparam1 $pipparam2 PEP517
if [[ $? -gt 0 ]]; then
    echo "Install or upgrade of PEP517 failed !!!"
    exit 1
fi

curl https://sh.rustup.rs -sSf | sh -s -- -y
source "$HOME/.cargo/env"

pip cache purge
pip install --upgrade $pipparam1 $pipparam2 bcrypt
if [[ $? -gt 0 ]]; then
    echo "Install or upgrade of bcrypt failed !!!"
    exit 1
fi

pip install --upgrade $pipparam1 $pipparam2 pysftp
if [[ $? -gt 0 ]]; then
    echo "Install or upgrade of pysftp failed !!!"
    exit 1
fi

echo
echo
ssh-keygen -f $HOME/.ssh/id_rsa -t rsa -N ''

echo
echo
echo "${green}${bold}Cleaning up Raspbian OS${reset}"
echo
apt -y clean
apt -y autoremove

# restore file system to what is was configured
if [ -f /home/pi/fstab.txt ]; then
    cp /home/pi/fstab.txt /etc/fstab
    mv /home/pi/fstab.txt /home/pi/fstab.ram
fi

NOW=$( date '+%F %H:%M:%S' )
echo "${NOW} - Ending   SFTP-setup" >>/home/pi/install.log

#------------------------------------------------------------------------------
# End of ToDo
#------------------------------------------------------------------------------
 
clear
reboot
