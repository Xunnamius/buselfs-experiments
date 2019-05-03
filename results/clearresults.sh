if [ "$(id -u)" -ne 0 ]; then
    echo 'Error: this script must be run by root!' >&2
    exit 1
fi

cd results
rm -vf -- *.results
cd -
