#!/bin/bash

if [ "$#" -ne 3 ]; then
    echo print cameras and objects slugs in csv format
    echo "usage: ${BASH_SOURCE[0]} <api_base_url> <oidc_username> <oidc_password>"

    exit 1
fi

base_url=$1
username=$2
password=$3

set -o pipefail

token=$(curl $1/auth/token --header 'Content-Type: application/x-www-form-urlencoded' --data "username=$username&password=$password" | jq .access_token -r)

if [ -z "$token" ] || [ "$token" == "null" ]; then
  echo Unable to get access token

  exit 1
fi

echo id,objects
curl $1/cameras --header "Authorization: Bearer $token" | jq '.items[] | select(.objects | length > 0) | [.id, .objects]' -c -r | sed 's/"\|^\[\|]$//g' | sed 's/\[\(.*\)\]/"\1"/'
