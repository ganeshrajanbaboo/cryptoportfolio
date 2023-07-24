# Copyright 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------
import requests
from exceptions import CryptoportClientException

def send_request(url, suffix, data=None, 
                 content_type=None, name=None):
    if url.startswith("http://"):
        url = "{}/{}".format(url, suffix)
    else:
        url = "http://{}/{}".format(url, suffix)

    headers = {}

    if content_type is not None:
        headers['Content-Type'] = content_type

    try:
        if data is not None:
            result = requests.post(url, headers=headers, data=data)
        else:
            result = requests.get(url, headers=headers)

        if not result.ok and not result.status_code == 404:
            raise CryptoportClientException("Error {}: {}".format(
                result.status_code, result.reason))

    except requests.ConnectionError as err:
        raise CryptoportClientException(
            'Failed to connect to REST API: {}'.format(err)) from err

    except BaseException as err:
        raise CryptoportClientException(err) from err
    
    return result.text, result.status_code