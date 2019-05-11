if [ "$(id -u)" -ne 0 ]; then
    echo 'Error: this script must be run by root!' >&2
    exit 1
fi

SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")

cd $SCRIPTPATH
fname=$(date +%F--%T | sed s/://g)
mkdir $fname
mv *.results $fname/
chown $SUDO_USER:$SUDO_USER -R $fname
cd -
