# These global flags are included all over the place! For all of the paths
# below, there MUST NOT be a trailing / The units of BACKEND_SIZE_INT is
# "mebibytes," EXPAND_TABS_INT is "tab stops," and FREERUN_TIMEOUT_INT is
# "seconds".
#
# Note that any flag ending in (no quotes) "_INT" will be parsed as an integer!
#
# Below, there should be one configuration variable (-D) per line. Each line
# should end with either (no quotes) " \" or "". Anything else will result in
# undefined behavior elsewhere. Also, the backslash (\) should not appear
# anywhere except at the end of the line OR ELSE!
#
# Also, variables will not be expanded, so don't try any interpolation!
#
# DO NOT MODIFY IN ANY WAY THE LINE IMMEDIATELY FOLLOWING THIS COMMENT!
CONFIG_COMPILE_FLAGS := \
						-DBUSELFS_PATH="/home/xunnamius/repos/research/buselfs" \
						-DBUSE_PATH="/home/xunnamius/repos/.github/BUSE/buselogfs" \
						-DREPO_PATH="/home/xunnamius/repos/research/buselfs-experiments" \
						-DLOG_FILE_PATH="/home/xunnamius/repos/research/buselfs-experiments/bin/runner.log" \
						-DDROP_CACHE_PATH="/proc/sys/vm/drop_caches" \
						-DRAM0_PATH="/tmp/ram0" \
						-DTMP_ROOT_PATH="/tmp" \
						-DBACKEND_SIZE_INT=800 \
						-DEXPAND_TABS_INT=15  \
						-DFREERUN_TIMEOUT_INT=900 \
						-DTRIALS_INT=15
