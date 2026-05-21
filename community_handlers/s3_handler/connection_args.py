from collections import OrderedDict

from mindsdb.integrations.libs.const import HANDLER_CONNECTION_ARG_TYPE as ARG_TYPE


connection_args = OrderedDict(
    aws_access_key_id={
        'type': ARG_TYPE.STR,
        'description': 'Access key for S3-compatible storage (AWS, DO Spaces, MinIO, R2, etc.).',
        'required': True,
        'label': 'Access Key',
    },
    aws_secret_access_key={
        'type': ARG_TYPE.STR,
        'description': 'Secret access key for S3-compatible storage.',
        'secret': True,
        'required': True,
        'label': 'Secret Access Key',
    },
    bucket={
        'type': ARG_TYPE.STR,
        'description': 'Name of the bucket / space.',
        'required': True,
        'label': 'Bucket',
    },
    region_name={
        'type': ARG_TYPE.STR,
        'description': 'Region. Required for non-AWS endpoints (DO Spaces, R2, etc.). Default us-east-1.',
        'required': False,
        'label': 'Region',
    },
    endpoint_url={
        'type': ARG_TYPE.STR,
        'description': (
            'Custom S3 endpoint URL for non-AWS providers. '
            'Example: https://nyc3.digitaloceanspaces.com for DigitalOcean Spaces. '
            'Leave blank for AWS S3.'
        ),
        'required': False,
        'label': 'Endpoint URL',
    },
    aws_session_token={
        'type': ARG_TYPE.STR,
        'description': 'Optional session token for temporary credentials.',
        'secret': True,
        'required': False,
        'label': 'Session Token',
    },
)

connection_args_example = OrderedDict(
    aws_access_key_id='DO00XXXXXXXXXXXXXXXX',
    aws_secret_access_key='...',
    bucket='my-space',
    region_name='nyc3',
    endpoint_url='https://nyc3.digitaloceanspaces.com',
)
