CWL tools for interacting with remote storage.

# S3

`mc` is used as the CLI for interacting with S3 compliant remote storage (eg. S3, minio).

To run the CWL tools a config directory is needed with all the aliases for remote storage systems configured.

# Openstack Swift

`swift` (Python library: python-swiftclient) is used as the CLI for interacting with OpenStack swift compliant remote storage.

The `OS_*` environment variables are needed as input parameters for each Swift CWL tool.

# WebDav

`cadaver` is used as CLI for interacting with WebDav servers.

The credentials are passed as CWL arguments.
