cd results
fname=$(date +%F--%T | sed s/://g)
mkdir $fname
mv shmoo.* $fname
cd -