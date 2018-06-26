cd results
fname=$(date +%F--%T | sed s/://g)
mkdir $fname
mv *.results $fname/
chown $USER:$USER -R $fname
cd -
