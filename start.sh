#!/bin/bash
twistd -y relay.tac & tail -f twistd.log
