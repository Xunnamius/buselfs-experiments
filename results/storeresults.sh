if [ "$(id -u)" -ne 0 ]; then
    echo 'Error: this script must be run by root!' >&2
    exit 1
fi

cd results
fname=$(date +%F--%T | sed s/://g)
mkdir $fname
mv *.results $fname/
chown $USER:$USER -R $fname
cd -
