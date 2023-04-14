#!/bin/bash

# initial build script
cp -v *.py src

# docker build --tag vee .
docker build -t vee .
