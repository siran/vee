#!/bin/bash

docker tag vee:latest 480854905773.dkr.ecr.us-east-1.amazonaws.com/vee/vee:latest

docker push 480854905773.dkr.ecr.us-east-1.amazonaws.com/vee/vee:latest
